#!/usr/bin/env python3
"""Package copier for ``install.sh copy`` — every write is anchored to a handle.

``install.sh`` owns the user-facing surface: the route table, the help text, the
option grammar, and the selection rules. This file owns the part that touches a
consumer's filesystem, because that part cannot be written safely with path
strings alone.

Why a separate program
    A shell installer can only name paths. Between the moment it checks a path
    and the moment it writes through it, the object behind that name can be
    replaced — an already-checked directory becomes a symlink, a reservation is
    renamed away and a foreign directory takes its place. Every check then still
    passes while the write, or worse the rollback, lands on somebody else's
    data. POSIX ``sh`` has no way to hold a directory open and keep writing into
    *that object*; ``openat``-style calls do, and Python's ``os`` module exposes
    them as ``dir_fd=`` arguments.

What that buys, concretely
    * The route below the approved anchor is walked one component at a time with
      ``O_DIRECTORY | O_NOFOLLOW``. A symlink is refused by the kernel, in the
      same call that would otherwise have followed it. Missing components are
      created relative to the handle of the parent that was just opened, so a
      component swapped for a symlink after the pre-flight cannot redirect the
      ``mkdir``.
    * Containment is proved by object identity, not by string prefixes: the
      destination root's real parent chain, walked through ``..``, must reach the
      approved anchor and must not pass through this checkout.
    * A package is copied and verified through held handles in private staging.
      A macOS/Linux atomic no-replace rename publishes it only after verification.
      No cleanup recursively removes a public destination.
    * Rollback removes exactly the entries this run recorded creating, each one
      re-identified by (device, inode) first. Anything else — a foreign
      replacement at the path, or content somebody planted inside the
      reservation — stops the rollback and is reported instead. A public
      destination that is no longer ours is never removed, never merged into and
      never recursively deleted.
    * Generated caches are never copied at all, so there is no prune step whose
      failure could be swallowed, and a generated entry found in the destination
      during the readback is a failure rather than an exclusion.

Exit codes, matching install.sh: 0 ok, 1 refused, 2 usage, 128+N interrupted.

This program never reaches the network, never runs another program, reads
nothing outside the source packages it copies and the destination it created,
and has no environment-driven behaviour of any kind: nothing here changes what
it does except its arguments and what it finds on disk.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import os
import signal
import stat
import sys
import uuid

# ── platform primitives ───────────────────────────────────────────────────────

O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)

# Opening one already-known-to-be-a-directory component. O_NOFOLLOW makes the
# kernel refuse a symlink instead of following it; O_DIRECTORY makes it refuse a
# regular file. Both refusals happen inside the one call, so there is no window
# between deciding and using.
DIR_FLAGS = os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW

# Reading a regular file. O_NONBLOCK keeps the open from blocking if the entry
# turned into a FIFO after it was classified; the fstat below then rejects it.
FILE_FLAGS = os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK

CHUNK = 256 * 1024
MAX_ANCESTORS = 64

# Build residue, never package content. The set matches this repository's
# .gitignore and install.sh's documented exclusion list.
GENERATED_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
GENERATED_FILES = frozenset({".DS_Store"})
GENERATED_SUFFIXES = (".pyc", ".pyo")


class Refused(Exception):
    """A refusal. The run stops, prints the reason, and exits 1."""


class CopyFailed(Exception):
    """The copy could not complete. The reservation is rolled back."""


class VerifyFailed(Exception):
    """The readback could not prove the destination matches its source."""


class Interrupted(BaseException):
    """INT or TERM arrived. Derived from BaseException so no ``except
    Exception`` in this file can swallow a signal and let the copy continue."""

    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


# ── output, byte-identical in shape to install.sh's own helpers ───────────────


def say(text=""):
    sys.stdout.write(text + "\n")


def blank():
    sys.stdout.write("\n")


def title(text):
    sys.stdout.write("\n== %s ==\n\n" % text)


def kv(label, value):
    sys.stdout.write("  %-22s %s\n" % (label, value))


def note(text):
    sys.stdout.write("  note: %s\n" % text)


def plan_line(state, name, detail):
    sys.stdout.write("    %-10s %-22s %s\n" % (state, name, detail))


def apply_line(state, name, detail):
    sys.stdout.write("    %-11s %-22s %s\n" % (state, name, detail))


# ── validation ────────────────────────────────────────────────────────────────


SEGMENT_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")


def is_safe_segment(name):
    """One Agent Skills-legal path segment: 1-64 chars, lowercase alphanumerics
    and hyphens, no leading, trailing or consecutive hyphen. Same rule as
    install.sh's own gate; re-applied here because this program builds paths."""
    if not name or len(name) > 64:
        return False
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False
    return all(char in SEGMENT_CHARS for char in name)


def is_generated(name):
    return (
        name in GENERATED_DIRS
        or name in GENERATED_FILES
        or name.endswith(GENERATED_SUFFIXES)
    )


def require_platform():
    """No unsafe fallback: without anchored calls this program refuses to run."""
    missing = []
    if not O_DIRECTORY or not O_NOFOLLOW:
        missing.append("O_DIRECTORY/O_NOFOLLOW")
    for function, label in (
        (os.open, "open"),
        (os.mkdir, "mkdir"),
        (os.stat, "stat"),
        (os.unlink, "unlink"),
        (os.rmdir, "rmdir"),
        (os.symlink, "symlink"),
        (os.readlink, "readlink"),
    ):
        if function not in os.supports_dir_fd:
            missing.append(label + "(dir_fd)")
    if os.listdir not in os.supports_fd:
        missing.append("listdir(fd)")
    if missing:
        raise Refused(
            "this platform cannot anchor a copy to directory handles (%s), so the "
            "destination could not be protected against a path swapped mid-run. "
            "There is no unanchored fallback." % ", ".join(missing)
        )


# ── directory handles ─────────────────────────────────────────────────────────


def ident(st):
    """The identity of a filesystem object: same device, same inode."""
    return (st.st_dev, st.st_ino)


def lstat_at(name, dir_fd):
    return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)


def open_dir_at(name, dir_fd):
    return os.open(name, DIR_FLAGS, dir_fd=dir_fd)


def kind_at(name, dir_fd):
    """Classify one entry below ``dir_fd`` without following a symlink."""
    try:
        st = lstat_at(name, dir_fd)
    except FileNotFoundError:
        return "missing", None
    except OSError:
        return "unreadable", None
    if stat.S_ISLNK(st.st_mode):
        return "symlink", st
    if stat.S_ISDIR(st.st_mode):
        return "directory", st
    if stat.S_ISREG(st.st_mode):
        return "file", st
    return "other", st


def open_relative(base_fd, relative):
    """Open a directory below ``base_fd``, one no-follow component at a time."""
    if not relative:
        return os.dup(base_fd)
    current = os.dup(base_fd)
    try:
        for component in relative.split("/"):
            following = open_dir_at(component, current)
            os.close(current)
            current = following
        opened, current = current, -1
        return opened
    finally:
        if current >= 0:
            os.close(current)


def close_all(*fds):
    for fd in fds:
        if fd is not None and fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def ancestor_idents(fd, stop_ident):
    """Identity of ``fd`` and of every real parent above it, up to ``stop_ident``.

    ``..`` is resolved by the kernel from the open directory itself, so this
    walk reports where the object actually lives rather than where a path string
    claims it lives. The walk stops at the anchor, at the filesystem root, at the
    first parent it may not open, or after MAX_ANCESTORS levels.
    """
    chain = []
    current = os.dup(fd)
    try:
        for _ in range(MAX_ANCESTORS):
            here = ident(os.fstat(current))
            chain.append(here)
            if here == stop_ident:
                return chain
            try:
                parent = os.open("..", os.O_RDONLY | O_DIRECTORY, dir_fd=current)
            except OSError:
                return chain
            if ident(os.fstat(parent)) == here:
                os.close(parent)
                return chain
            os.close(current)
            current = parent
        return chain
    finally:
        close_all(current)


# ── route ──


def split_route(route):
    components = [part for part in route.split("/") if part]
    if not components:
        raise Refused("the destination route below the approved root is empty")
    for component in components:
        if component in (".", ".."):
            raise Refused(
                "the destination route contains '%s', which is not a single path "
                "segment: %s" % (component, route)
            )
    return components


def refuse_symlink_route(display, anchor_display):
    return Refused(
        "the route to the destination root crosses a symlink: %s. A symlink below "
        "the approved root %s is refused, so the link and whatever it points at "
        "are left exactly as they are." % (display, anchor_display)
    )


def open_route(anchor_fd, components, anchor_display, create):
    """Walk the route below the anchor through no-follow directory handles.

    Returns ``(root_fd, created_root)``. In check mode a missing component ends
    the walk with ``(None, False)``: the root simply does not exist yet. In
    create mode each missing component is created relative to the handle of the
    parent just opened, never through a path string, and never with ``mkdir -p``.
    """
    current, owned = anchor_fd, False
    created_root = False
    try:
        for index, component in enumerate(components):
            display = "%s/%s" % (anchor_display, "/".join(components[: index + 1]))
            made = False
            try:
                following = open_dir_at(component, current)
            except OSError as exc:
                what, _st = kind_at(component, current)
                if what == "symlink":
                    raise refuse_symlink_route(display, anchor_display)
                if what in ("file", "other"):
                    raise Refused(
                        "the route to the destination root is blocked by a "
                        "non-directory: %s" % display
                    )
                if what in ("directory", "unreadable"):
                    raise Refused(
                        "the route to the destination root cannot be opened: %s (%s)"
                        % (display, exc.strerror)
                    )
                if not create:
                    return None, False
                try:
                    os.mkdir(component, 0o755, dir_fd=current)
                    made = True
                except FileExistsError:
                    made = False
                except OSError as err:
                    raise Refused(
                        "cannot create destination route component: %s (%s)"
                        % (display, err.strerror)
                    )
                try:
                    following = open_dir_at(component, current)
                except OSError as err:
                    what, _st = kind_at(component, current)
                    if what == "symlink":
                        raise refuse_symlink_route(display, anchor_display)
                    raise Refused(
                        "cannot open destination route component: %s (%s)"
                        % (display, err.strerror)
                    )
            if owned:
                os.close(current)
            current, owned = following, True
            if made and index == len(components) - 1:
                created_root = True
        if not owned:
            current, owned = os.dup(anchor_fd), True
        opened, owned = current, False
        return opened, created_root
    finally:
        if owned:
            close_all(current)


def assert_anchored(root_fd, anchor_ident, repo_ident, root_display, anchor_display,
                    package_name):
    """Prove by identity that the root really lives under the approved anchor."""
    chain = ancestor_idents(root_fd, anchor_ident)
    if anchor_ident not in chain:
        raise Refused(
            "the destination root resolves to %s, outside the approved root %s. "
            "Nothing was written." % (root_display, anchor_display)
        )
    if repo_ident in chain:
        raise Refused(
            "destination root resolves inside the %s checkout (%s); a package would "
            "be copied over its own source." % (package_name, root_display)
        )


# ── source packages ───────────────────────────────────────────────────────────


def open_source_package(skills_fd, name):
    """Open ``skills/<name>``. A symlinked package is refused, not followed.

    Copying through a linked package would read a tree the checkout does not
    own, so what lands in the destination would not be what this repository
    ships. The link itself is left exactly as it is.
    """
    what, _st = kind_at(name, skills_fd)
    if what == "symlink":
        return None, "SRC LINK", "the source package is a symlink; a linked package is refused"
    if what != "directory":
        return None, "MISSING", "no skills/%s/SKILL.md in this checkout" % name
    try:
        fd = open_dir_at(name, skills_fd)
    except OSError as exc:
        return None, "MISSING", "skills/%s cannot be opened (%s)" % (name, exc.strerror)
    if kind_at("SKILL.md", fd)[0] != "file":
        close_all(fd)
        return None, "MISSING", "no skills/%s/SKILL.md in this checkout" % name
    return fd, None, None


# ── copying ───────────────────────────────────────────────────────────────────


def join_rel(parent, name):
    return name if not parent else parent + "/" + name


def copy_file(name, src_fd, dst_fd, relative, created, src_st):
    source = destination = None
    try:
        source = os.open(name, FILE_FLAGS, dir_fd=src_fd)
        if not stat.S_ISREG(os.fstat(source).st_mode):
            raise CopyFailed("source entry changed type during the copy: %s" % relative)
        destination = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW, 0o600, dir_fd=dst_fd
        )
        created.append((relative, "f", ident(os.fstat(destination))))
        while True:
            chunk = os.read(source, CHUNK)
            if not chunk:
                break
            written = 0
            while written < len(chunk):
                written += os.write(destination, chunk[written:])
        os.fchmod(destination, src_st.st_mode & 0o777)
    finally:
        close_all(source, destination)


def copy_tree(src_fd, dst_fd, relative, created, deferred_modes):
    """Copy one directory level, recursing through handles opened no-follow.

    Directory permissions are *not* applied here. A copied directory stays
    owner-writable until the readback has passed, so a package whose source
    carries a read-only directory can still be rolled back completely; the
    recorded modes are applied once, at the end, by ``apply_modes``.

    Entry types this program will not create in somebody's skill directory — a
    FIFO, socket or device node — are skipped here and reported by the readback,
    which is the check that decides whether the package may stay.
    """
    for name in sorted(os.listdir(src_fd)):
        if is_generated(name):
            continue
        child = join_rel(relative, name)
        what, src_st = kind_at(name, src_fd)
        if what == "missing":
            raise CopyFailed("source entry disappeared during the copy: %s" % child)
        if what == "unreadable":
            raise CopyFailed("source entry cannot be read: %s" % child)
        try:
            if what == "symlink":
                raise CopyFailed("source symlink is not a standalone resource: %s" % child)
            elif what == "directory":
                sub_src = sub_dst = None
                try:
                    os.mkdir(name, 0o700, dir_fd=dst_fd)
                    sub_dst = open_dir_at(name, dst_fd)
                    created.append((child, "d", ident(os.fstat(sub_dst))))
                    deferred_modes.append((child, src_st.st_mode & 0o777))
                    sub_src = open_dir_at(name, src_fd)
                    copy_tree(sub_src, sub_dst, child, created, deferred_modes)
                finally:
                    close_all(sub_src, sub_dst)
            elif what == "file":
                copy_file(name, src_fd, dst_fd, child, created, src_st)
        except CopyFailed:
            raise
        except OSError as exc:
            raise CopyFailed("copy failed at %s (%s)" % (child, exc.strerror or exc))


def apply_modes(reservation_fd, deferred_modes, root_mode):
    """Reproduce the source's directory permissions, deepest first.

    Called only after the readback passed, so nothing that still had to be
    verified or rolled back was ever made unwritable.
    """
    for relative, mode in reversed(deferred_modes):
        fd = None
        try:
            fd = open_relative(reservation_fd, relative)
            os.fchmod(fd, mode)
        except OSError as exc:
            raise CopyFailed("cannot restore permissions on %s (%s)"
                             % (relative, exc.strerror or exc))
        finally:
            close_all(fd)
    os.fchmod(reservation_fd, root_mode)


# ── readback ──────────────────────────────────────────────────────────────────


def read_exact(fd, size):
    """Read up to ``size`` bytes, tolerating short reads so that a comparison
    never mistakes a split read for different content."""
    parts = []
    remaining = size
    while remaining > 0:
        chunk = os.read(fd, remaining)
        if not chunk:
            break
        parts.append(chunk)
        remaining -= len(chunk)
    return b"".join(parts)


def same_bytes(name, src_fd, dst_fd):
    source = destination = None
    try:
        source = os.open(name, FILE_FLAGS, dir_fd=src_fd)
        destination = os.open(name, FILE_FLAGS, dir_fd=dst_fd)
        src_st, dst_st = os.fstat(source), os.fstat(destination)
        if not stat.S_ISREG(src_st.st_mode) or not stat.S_ISREG(dst_st.st_mode):
            return False
        if src_st.st_size != dst_st.st_size:
            return False
        while True:
            left = read_exact(source, CHUNK)
            right = read_exact(destination, CHUNK)
            if left != right:
                return False
            if not left:
                return True
    finally:
        close_all(source, destination)


def verify_tree(src_fd, dst_fd, relative, counted):
    """Compare one directory level of the destination against its source.

    Types are classified from the source first, so an entry this program cannot
    prove identical is reported as unsupported rather than as a bare absence.
    The destination side is listed unfiltered: a generated cache entry there is
    an unexpected path, not an exclusion.
    """
    source_names = sorted(name for name in os.listdir(src_fd) if not is_generated(name))
    kinds = {}
    for name in source_names:
        child = join_rel(relative, name)
        what, src_st = kind_at(name, src_fd)
        if what in ("missing", "unreadable"):
            raise VerifyFailed("the source package inventory could not be read at %s" % child)
        if what == "other":
            raise VerifyFailed("unsupported entry type at %s" % child)
        kinds[name] = (what, src_st)

    destination_names = sorted(os.listdir(dst_fd))
    if source_names != destination_names:
        unexpected = [name for name in destination_names if name not in kinds]
        if unexpected:
            raise VerifyFailed("unexpected entry at %s" % join_rel(relative, unexpected[0]))
        present = set(destination_names)
        absent = [name for name in source_names if name not in present]
        raise VerifyFailed("missing entry at %s" % join_rel(relative, absent[0]))

    for name in source_names:
        child = join_rel(relative, name)
        what, _src_st = kinds[name]
        found, _dst_st = kind_at(name, dst_fd)
        if found != what:
            raise VerifyFailed("type differs at %s" % child)
        if what == "symlink":
            if os.readlink(name, dir_fd=src_fd) != os.readlink(name, dir_fd=dst_fd):
                raise VerifyFailed("symlink target differs at %s" % child)
        elif what == "directory":
            sub_src = sub_dst = None
            try:
                sub_src = open_dir_at(name, src_fd)
                sub_dst = open_dir_at(name, dst_fd)
                verify_tree(sub_src, sub_dst, child, counted)
            except OSError as exc:
                raise VerifyFailed("%s cannot be read back (%s)" % (child, exc.strerror or exc))
            finally:
                close_all(sub_src, sub_dst)
        else:
            try:
                identical = same_bytes(name, src_fd, dst_fd)
            except OSError as exc:
                raise VerifyFailed("%s cannot be read back (%s)" % (child, exc.strerror or exc))
            if not identical:
                raise VerifyFailed("content differs at %s" % child)
            counted[0] += 1


def verify_package(src_fd, dst_fd):
    """Readback by content, not by count: a path total would accept a truncated
    or substituted file. Returns the number of byte-identical regular files."""
    if kind_at("SKILL.md", dst_fd)[0] != "file":
        raise VerifyFailed("SKILL.md is missing from the destination")
    counted = [0]
    verify_tree(src_fd, dst_fd, "", counted)
    return counted[0]


# ── rollback ──────────────────────────────────────────────────────────────────


def rollback(reservation_fd, created):
    """Remove exactly the entries this run recorded creating, and nothing else.

    Every entry is re-identified by (device, inode) before it is removed, so a
    path that something else has since taken over is left alone. An entry that
    cannot be removed, or a directory somebody planted content in, makes the
    rollback incomplete; the caller then reports the reservation instead of
    recursively deleting content that is not this run's.
    """
    complete = True
    for relative, what, created_ident in reversed(created):
        parent_relative, _, name = relative.rpartition("/")
        try:
            parent_fd = open_relative(reservation_fd, parent_relative)
        except OSError:
            complete = False
            continue
        try:
            try:
                st = lstat_at(name, parent_fd)
            except FileNotFoundError:
                continue
            except OSError:
                complete = False
                continue
            if ident(st) != created_ident:
                complete = False
                continue
            try:
                if what == "d":
                    os.rmdir(name, dir_fd=parent_fd)
                else:
                    os.unlink(name, dir_fd=parent_fd)
            except OSError:
                complete = False
        finally:
            close_all(parent_fd)
    return complete


def release_reservation(root_fd, name, reservation_ident, emptied):
    """Remove the reservation directory itself, only while it is still ours."""
    if not emptied:
        return "left-behind"
    try:
        st = lstat_at(name, root_fd)
    except FileNotFoundError:
        return "rolled-back"
    except OSError:
        return "left-behind"
    if ident(st) != reservation_ident:
        return "replaced"
    try:
        os.rmdir(name, dir_fd=root_fd)
    except OSError:
        return "left-behind"
    return "rolled-back"


# ── one package ───────────────────────────────────────────────────────────────


RENAME_EXCL = 4  # macOS <stdio.h>
RENAME_NOREPLACE = 1  # Linux renameat2(2)


def publication_primitive():
    """Resolve the required primitive before creating any destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function, flag = getattr(libc, "renameatx_np", None), RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function, flag = getattr(libc, "renameat2", None), RENAME_NOREPLACE
    else:
        function, flag = None, 0
    if function is None:
        raise OSError("atomic no-replace publication is unavailable")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                        ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function, flag


def publish_exclusive(root_fd, staged, name):
    """Publish a complete directory without ever replacing an existing entry."""
    function, flag = publication_primitive()
    if function(root_fd, os.fsencode(staged), root_fd, os.fsencode(name), flag):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def quarantine_staging(root_fd, staged):
    """Remove the callable entrypoint from retained, unpublished staging."""
    fd = None
    try:
        fd = open_dir_at(staged, root_fd)
        os.rename("SKILL.md", "SKILL.unpublished", src_dir_fd=fd, dst_dir_fd=fd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        apply_line("WARNING", staged, "entrypoint quarantine failed: %s" % exc)
    finally:
        close_all(fd)


def install_one(root_fd, name, src_fd, src_root_st, destination):
    """Verify in private staging, then publish atomically without replacement."""
    staged = ".obsidian-stage-" + uuid.uuid4().hex
    success, reason = stage_one(root_fd, staged, src_fd, src_root_st, destination)
    if not success:
        return success, reason
    try:
        publish_exclusive(root_fd, staged, name)
    except Interrupted:
        quarantine_staging(root_fd, staged)
        apply_line("interrupted", staged, "inspect retained staging and public destination")
        raise
    except OSError as exc:
        # Never remove an occupied public name. Keep verified staging for
        # explicit recovery rather than recursively deleting possibly changed
        # contents after a failed publication.
        quarantine_staging(root_fd, staged)
        apply_line("NOT OURS", name, "%s  (left untouched)" % destination)
        apply_line("LEFT BEHIND", staged, "verified private staging; publication failed")
        if exc.errno in (errno.EEXIST, errno.ENOTEMPTY):
            return False, "the destination was claimed by something else before publication"
        return False, "exclusive publication failed: %s" % exc
    apply_line("installed", name, "%s  (verified bytes; atomic publication)" % destination)
    return True, None


def stage_one(root_fd, name, src_fd, src_root_st, destination):
    """Reserve, fill, read back and publish one package.

    Returns ``(True, None)`` when the package is published, or ``(False,
    reason)`` after the outcome has already been reported. Every write goes
    through the handle taken at reservation time, so the object this run created
    stays the object this run acts on.
    """
    try:
        os.mkdir(name, 0o700, dir_fd=root_fd)
    except FileExistsError:
        apply_line("NOT OURS", name, "%s  (left untouched)" % destination)
        return False, "the destination was claimed by something else after the pre-flight"
    except OSError as exc:
        apply_line("NO RESERVE", name, "%s  (nothing was written: %s)" % (destination, exc.strerror))
        return False, "the destination could not be reserved"

    try:
        reservation_fd = open_dir_at(name, root_fd)
    except OSError:
        # The name stopped pointing at the directory just created, so this run
        # can no longer reach its own reservation. Whatever is there now is not
        # ours and is left exactly as it is.
        apply_line("NOT OURS", name, "%s  (replaced during the reservation; left untouched)" % destination)
        return False, "the destination was replaced while it was being reserved"

    created = []
    deferred_modes = []
    reservation_ident = ident(os.fstat(reservation_fd))
    try:
        try:
            copy_tree(src_fd, reservation_fd, "", created, deferred_modes)
        except CopyFailed as exc:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created, str(exc))
        except OSError as exc:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created,
                                  "copy failed (%s)" % (exc.strerror or exc))

        try:
            files = verify_package(src_fd, reservation_fd)
        except VerifyFailed as exc:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created,
                                  "readback failed: %s" % exc)
        except OSError as exc:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created,
                                  "readback failed: %s" % (exc.strerror or exc))

        # The readback proved the *reservation* is complete. It does not prove
        # the destination name still leads to it, so that is checked separately;
        # a replacement is reported and left untouched, never overwritten.
        try:
            published = lstat_at(name, root_fd)
            still_ours = ident(published) == reservation_ident
        except OSError:
            still_ours = False
        if not still_ours:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created,
                                  "the destination was replaced after the reservation")

        try:
            apply_modes(reservation_fd, deferred_modes, src_root_st.st_mode & 0o777)
        except CopyFailed as exc:
            return finish_failure(root_fd, name, destination, reservation_fd,
                                  reservation_ident, created, str(exc))

        return True, None
    except Interrupted:
        emptied = rollback(reservation_fd, created)
        outcome = release_reservation(root_fd, name, reservation_ident, emptied)
        apply_line(
            "interrupted", name,
            "%s  (%s)" % (destination,
                          "rolled back" if outcome == "rolled-back" else "left behind"),
        )
        raise
    finally:
        close_all(reservation_fd)


def finish_failure(root_fd, name, destination, reservation_fd, reservation_ident,
                   created, reason):
    emptied = rollback(reservation_fd, created)
    outcome = release_reservation(root_fd, name, reservation_ident, emptied)
    if outcome == "rolled-back":
        apply_line("rolled back", name, destination)
    elif outcome == "replaced":
        apply_line("NOT OURS", name, "%s  (replaced after the reservation; left untouched)" % destination)
    else:
        apply_line("LEFT BEHIND", name, "%s  (remove it by hand)" % destination)
    return False, reason


# ── the copy command ──────────────────────────────────────────────────────────


def build_plan(names, skills_fd, root_fd, root_display, source_fds):
    """One row per selected package, decided before anything is written."""
    rows = []
    for name in names:
        destination = "%s/%s" % (root_display, name)
        if not is_safe_segment(name):
            rows.append(("bad", "ESCAPE", name, "name is not a single legal path segment", destination))
            continue
        src_fd, state, detail = open_source_package(skills_fd, name)
        if src_fd is None:
            rows.append(("bad", state, name, detail, destination))
            continue
        source_fds[name] = src_fd
        if root_fd is not None:
            what, _st = kind_at(name, root_fd)
            if what == "symlink":
                try:
                    os.stat(name, dir_fd=root_fd)
                    detail = "symlink occupies the destination"
                except FileNotFoundError:
                    detail = "dangling symlink occupies the destination"
                except OSError:
                    detail = "symlink occupies the destination"
                rows.append(("bad", "COLLISION", name, detail, destination))
                continue
            if what == "unreadable":
                rows.append(("bad", "COLLISION", name, "the destination cannot be inspected", destination))
                continue
            if what != "missing":
                rows.append(("bad", "COLLISION", name, "path already exists", destination))
                continue
        rows.append(("ok", "copy", name, destination, destination))
    return rows


def run(args):
    require_platform()
    try:
        publication_primitive()
    except OSError as exc:
        raise Refused(str(exc))
    repo_real = os.path.realpath(args.repo)
    try:
        repo_ident = ident(os.stat(args.repo))
    except OSError:
        raise Refused("cannot resolve the %s checkout: %s" % (args.package, args.repo))

    anchor = args.anchor
    if not anchor:
        if args.anchor_kind == "home":
            raise Refused("HOME is not an existing directory: <unset>")
        raise Refused("project root is not an existing directory: <empty>")
    try:
        anchor_fd = os.open(anchor, os.O_RDONLY | O_DIRECTORY)
    except OSError:
        if args.anchor_kind == "home":
            raise Refused("HOME is not an existing directory: %s" % anchor)
        raise Refused("project root is not an existing directory: %s" % anchor)

    skills_fd = None
    root_fd = None
    source_fds = {}
    try:
        anchor_display = os.path.realpath(anchor)
        anchor_ident = ident(os.fstat(anchor_fd))
        if anchor_display == repo_real or anchor_display.startswith(repo_real.rstrip("/") + "/"):
            raise Refused(
                "the approved root must be a consumer location, not the %s checkout "
                "(%s)." % (args.package, anchor_display)
            )

        components = split_route(args.route)
        root_display = "%s/%s" % (anchor_display, "/".join(components))

        root_fd, _created = open_route(anchor_fd, components, anchor_display, create=False)
        if root_fd is not None:
            assert_anchored(root_fd, anchor_ident, repo_ident, root_display,
                            anchor_display, args.package)

        try:
            skills_fd = os.open(args.source, os.O_RDONLY | O_DIRECTORY)
        except OSError:
            raise Refused("the package source directory is missing: %s" % args.source)

        mode_label = "APPLY" if args.mode == "apply" else "DRY RUN"
        title("Copy plan — %s · scope %s · %s" % (args.label, args.scope, mode_label))
        kv("source", "%s/<name>" % args.source)
        kv("approved root", anchor_display)
        kv("destination root", root_display)
        kv("route kind", args.kind)
        kv("selection", " ".join(args.names))
        if args.kind == "skill-directory":
            note("generic Agent Skills import — %s has no self-serve native plugin route"
                 % args.label)
        else:
            note("generic Agent Skills import — the native route is './%s native --runtime %s'"
                 % (args.prog, args.runtime))
        blank()

        rows = build_plan(args.names, skills_fd, root_fd, root_display, source_fds)

        copyable = [row for row in rows if row[0] == "ok"]
        refused = [row for row in rows if row[0] != "ok"]
        say("  Collision report")
        for _verdict, state, name, detail, _destination in rows:
            plan_line(state, name, detail)
        blank()
        say("  %d copyable, %d refused." % (len(copyable), len(refused)))
        blank()

        if refused:
            say("  Nothing was written. Every selected package must be clean before any copy")
            say("  runs, so an existing file, directory, symlink or dangling symlink at a")
            say("  destination refuses the whole operation. Resolve or deselect it, re-run.")
            blank()
            return 1

        if args.mode != "apply":
            say("  Dry run only — nothing was written. Re-run with --apply to copy.")
            blank()
            return 0

        # The route is re-walked and created through fresh no-follow handles. A
        # component swapped for a symlink or a file since the pre-flight is
        # refused by the same call that would have created through it.
        close_all(root_fd)
        root_fd = None
        root_fd, created_root = open_route(anchor_fd, components, anchor_display, create=True)
        if created_root:
            say("  created  %s" % root_display)
        assert_anchored(root_fd, anchor_ident, repo_ident, root_display, anchor_display,
                        args.package)

        done = 0
        failure = None
        for _verdict, _state, name, _detail, destination in copyable:
            if failure is not None:
                apply_line("skipped", name, "an earlier package failed")
                continue
            src_fd = source_fds[name]
            src_root_st = os.fstat(src_fd)
            published, reason = install_one(root_fd, name, src_fd, src_root_st, destination)
            if published:
                done += 1
            else:
                failure = "%s (%s)" % (name, reason)

        blank()
        if failure is not None:
            say("  Stopped after %d of %d package(s). Failure: %s" % (done, len(copyable), failure))
            say("  Only this run\u2019s own reservation was rolled back; a destination claimed")
            say("  by anything else is reported and left exactly as it was found.")
            say("  Packages listed as installed above were read back byte-for-byte against")
            say("  their source and were left in place.")
            blank()
            return 1
        say("  Done. %d package(s) published into reservations this run created," % done)
        say("  each read back byte-for-byte against its source. No pre-existing file,")
        say("  symlink, cache entry or profile setting was modified or removed.")
        blank()
        return 0
    finally:
        close_all(anchor_fd, skills_fd, root_fd, *source_fds.values())


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="install_packages.py",
        description="fd-anchored package copier used by install.sh copy.",
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--anchor-kind", required=True, choices=("home", "project"))
    parser.add_argument("--route", required=True)
    parser.add_argument("--scope", required=True, choices=("user", "project"))
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--prog", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--mode", required=True, choices=("plan", "apply"))
    parser.add_argument("names", nargs="+")
    return parser.parse_args(argv)


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        # Line buffering keeps the report on the pipe as it is produced, so an
        # interrupted run still shows how far it got.
        sys.stdout.reconfigure(line_buffering=True)

    def stop(signum, _frame):
        raise Interrupted(signum)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    args = parse_args(argv)
    try:
        return run(args)
    except Refused as exc:
        sys.stdout.flush()
        sys.stderr.write("REFUSED: %s\n" % exc)
        return 1
    except Interrupted as exc:
        sys.stdout.flush()
        sys.stderr.write(
            "REFUSED: interrupted by signal %d. The run stopped. Inspect reported "
            "staging and destinations; complete packages may remain published "
            "and cleanup may be incomplete.\n" % exc.signum
        )
        return 128 + exc.signum


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
