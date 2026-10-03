#!/usr/bin/env python3
"""Initialize reviewed two-role candidates, or apply exact approved settings edits.

Python >=3.8, standard library only. Candidate content is data, never executed.
The caller must quiesce other writers for the duration of an approved update.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import uuid
from typing import Dict, Iterator, List, Optional

ROLES = ("personal", "knowledge")
MANIFEST = "candidate-manifest.json"
DECLARATION = "90. Settings/04 Index/folder-structure.json"
SETTINGS = frozenset((
    ".obsidian/app.json", ".obsidian/daily-notes.json",
    ".obsidian/plugins/homepage/data.json",
    ".obsidian/plugins/templater-obsidian/data.json",
    ".obsidian/plugins/obsidian-excalidraw-plugin/data.json",
))
PLUGINS = (
    "templater-obsidian", "homepage", "omnisearch",
    "obsidian-excalidraw-plugin", "obsidian-outliner", "obsidian-linter",
)
# Schema eligibility, not approval to overwrite any of these files.
NATIVE = frozenset(
    [".obsidian/core-plugins.json", ".obsidian/community-plugins.json",
     ".obsidian/snippets/fix-nested-bullets.css", ".obsidian/snippets/mermaid-wide.css"]
    + [".obsidian/plugins/{}/{}".format(p, f)
       for p in PLUGINS for f in ("main.js", "manifest.json", "styles.css")]
    + ["90. Settings/02 Templates/auto/{}.template.md".format(n)
       for n in ("Daily Note", "Weekly Notes", "Monthly Notes",
                 "Quarterly Notes", "Yearly Note", "Dashboard")]
    + ["90. Settings/02 Templates/manual/{}.template.md".format(n)
       for n in ("note", "book", "guideline", "task", "project", "log", "video")]
    + ["90. Settings/05 Bases/Books.base", "90. Settings/05 Bases/Video.base"]
)


class Refused(ValueError):
    """Invalid input, conflicting bytes, or an effect without exact approval."""


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def canonical(value) -> bytes:
    """The candidate's documented canonical serialization."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused("duplicate JSON key")
        result[key] = value
    return result


def parse(blob: bytes):
    def reject_constant(value):
        raise Refused("nonfinite JSON number")
    return json.loads(blob, object_pairs_hook=pairs_unique,
                      parse_constant=reject_constant)


def relative(value: str, hidden: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise Refused("invalid relative path")
    path = PurePosixPath(value)
    if (path.is_absolute() or str(path) != value
            or any(p in (".", "..") for p in path.parts)
            or any(p == ".git" for p in path.parts)
            or (not hidden and any(p.startswith(".") for p in path.parts))):
        raise Refused("noncanonical or protected relative path")
    return value


@contextmanager
def directory(path: Path, create: bool = False) -> Iterator[int]:
    """Walk from / using directory descriptors; never follow a link."""
    absolute = Path(os.path.abspath(str(path)))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read_file(path: Path) -> Optional[bytes]:
    """Missing is distinct from a link, directory, or special file."""
    try:
        with directory(path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise Refused("not a regular file")
                return stream.read()
    except FileNotFoundError:
        return None


def required(path: Path) -> bytes:
    blob = read_file(path)
    if blob is None:
        raise Refused("required input is absent")
    return blob


def check_route(path: Path, is_directory: bool = False) -> None:
    """Preflight even absent paths, rejecting links at every existing ancestor."""
    absolute = Path(os.path.abspath(str(path)))
    current = Path("/")
    for index, part in enumerate(absolute.parts[1:]):
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return
        last = index == len(absolute.parts) - 2
        if stat.S_ISLNK(info.st_mode):
            raise Refused("symlink route refused")
        expected_dir = not last or is_directory
        if expected_dir and not stat.S_ISDIR(info.st_mode):
            raise Refused("directory route conflict")
        if last and not is_directory and (
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise Refused("nonregular or hardlinked destination")


@dataclass(frozen=True)
class Candidate:
    files: Dict[str, bytes]
    folders: List[str]
    settings: dict
    manifest: dict


def prepare(candidate: Path, role: str) -> Candidate:
    """Consume schema v1 using parent(candidate) as the source base."""
    if role not in ROLES:
        raise Refused("unknown role")
    check_route(candidate, True)
    base = candidate.parent
    definition = parse(required(candidate / (role + ".json")))
    native = parse(required(candidate / "common/native.json"))
    if (not isinstance(definition, dict)
            or set(definition) != {"schema_version", "role", "roots", "folders", "files"}
            or type(definition["schema_version"]) is not int
            or definition["schema_version"] != 1 or definition["role"] != role
            or not isinstance(native, dict) or set(native) != {"files", "settings"}):
        raise Refused("invalid candidate schema")
    roots, folders = definition["roots"], definition["folders"]
    for values in (roots, folders):
        if not isinstance(values, list):
            raise Refused("structure must be a list")
        for value in values:
            relative(value)
        if len(values) != len(set(values)):
            raise Refused("duplicate structure entry")
    if any("/" in r or r not in folders for r in roots):
        raise Refused("invalid root")
    for folder in folders:
        path = PurePosixPath(folder)
        if path.parts[0] not in roots or any(
                str(p) != "." and str(p) not in folders for p in path.parents):
            raise Refused("undeclared structure parent")
    files = {}

    def add(path: str, blob: bytes) -> None:
        relative(path, path in NATIVE or path in SETTINGS)
        parent = str(PurePosixPath(path).parent)
        if (path in files or path in (MANIFEST, DECLARATION) or path in folders
                or (parent != "." and not path.startswith(".obsidian/")
                    and parent not in folders)):
            raise Refused("duplicate, reserved, or undeclared destination")
        files[path] = blob

    if not isinstance(definition["files"], list) or not isinstance(native["files"], list):
        raise Refused("files must be a list")
    for entry in definition["files"]:
        if not isinstance(entry, dict) or set(entry) != {"source", "path"}:
            raise Refused("invalid file entry")
        source = relative(entry["source"])
        allowed = tuple(candidate.name + "/" + d + "/"
                        for d in ("common", role, "fixtures"))
        if not source.startswith(allowed):
            raise Refused("source outside candidate allowlist")
        add(entry["path"], required(base / source))
    seen_native = set()
    for entry in native["files"]:
        if not isinstance(entry, dict) or set(entry) != {"source", "path", "roles"}:
            raise Refused("invalid native entry")
        source = entry["source"]
        roles = entry["roles"]
        if (source not in NATIVE or entry["path"] != source or source in seen_native
                or not isinstance(roles, list) or not roles
                or any(r not in ROLES for r in roles) or len(set(roles)) != len(roles)):
            raise Refused("invalid native selection")
        seen_native.add(source)
        # Validate/read ALL rows, even rows belonging only to the other role.
        blob = required(base / source)
        if role in roles:
            add(source, blob)
    settings = native["settings"]
    if not isinstance(settings, dict) or set(settings) != set(ROLES):
        raise Refused("invalid role settings")
    for role_settings in settings.values():
        if not isinstance(role_settings, dict):
            raise Refused("settings must be objects")
        for path, value in role_settings.items():
            if path not in SETTINGS or not isinstance(value, dict):
                raise Refused("unapproved setting")
    for path, value in settings[role].items():
        add(path, canonical(value))
    if str(PurePosixPath(DECLARATION).parent) not in folders:
        raise Refused("missing declaration parent")
    files[DECLARATION] = canonical({
        "schema_version": 1, "description": "Independent {} candidate structure".format(role),
        "roots": roots, "folders": folders,
    })
    all_folders = sorted(set(folders) | {
        str(p) for name in files for p in PurePosixPath(name).parents if str(p) != "."
    })
    if set(all_folders) & set(files):
        raise Refused("file/directory collision")
    inventory = {
        "schema_version": 1, "role": role, "folders": all_folders,
        "files": [{"path": name, "sha256": digest(blob), "size": len(blob)}
                  for name, blob in sorted(files.items())],
    }
    manifest = dict(inventory, candidate_sha256=digest(canonical(inventory)))
    files[MANIFEST] = canonical(manifest)
    return Candidate(files, all_folders, settings[role], manifest)


def setting_bytes(before: Optional[bytes], desired: dict, keys: List[str]) -> bytes:
    """Splice only selected top-level JSON value spans; retain every other byte."""
    if (not isinstance(keys, list) or any(not isinstance(k, str) for k in keys)
            or not keys or keys != sorted(set(keys)) or any(k not in desired for k in keys)):
        raise Refused("invalid approved keys")
    if before is None:
        return canonical({key: desired[key] for key in keys})
    value = parse(before)
    if not isinstance(value, dict):
        raise Refused("existing setting is not an object")
    text = before.decode("utf-8")
    decoder = json.JSONDecoder()
    skip = lambda i: re.compile(r"\s*").match(text, i).end()
    index = skip(0) + 1
    spans = {}
    while text[skip(index)] != "}":
        index = skip(index)
        key, index = decoder.raw_decode(text, index)
        index = skip(index) + 1  # colon; full JSON was already validated
        start = skip(index)
        _, end = decoder.raw_decode(text, start)
        spans[key] = (start, end)
        index = skip(end)
        if text[index] == ",":
            index += 1
    close = skip(index)
    edits = []
    for key in keys:
        if key in value and canonical(value[key]) != canonical(desired[key]):
            start, end = spans[key]
            replacement = json.dumps(desired[key], ensure_ascii=False, allow_nan=False)
            edits.append((start, end, replacement))
    missing = [k for k in keys if k not in value]
    if missing:
        additions = ", ".join(json.dumps(k, ensure_ascii=False) + ": "
                              + json.dumps(desired[k], ensure_ascii=False, allow_nan=False)
                              for k in missing)
        edits.append((close, close, (", " if value else "") + additions))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text.encode("utf-8")


def proposal(target: Path, selected: Candidate, selections: dict) -> dict:
    """Return exact preimage/postimage bytes for owner review, without writing."""
    if not isinstance(selections, dict) or any(p not in selected.settings for p in selections):
        raise Refused("selection outside settings allowlist")
    changes = []
    for path, keys in sorted(selections.items()):
        check_route(target / path)
        before = read_file(target / path)
        after = setting_bytes(before, selected.settings[path], keys)
        if before == after:
            continue
        changes.append({
            "path": path, "keys": keys,
            "approval_preimage": "absent" if before is None else "sha256:" + digest(before),
            "before": None if before is None else before.decode("utf-8"),
            "after": after.decode("utf-8"), "postimage_sha256": digest(after),
            "recovery": "Restore the exact before bytes; if absent, remove only this created file.",
        })
    return {
        "schema_version": 1, "role": selected.manifest["role"],
        "candidate_sha256": selected.manifest["candidate_sha256"],
        "approval_state": "not-requested", "approval_effect": [],
        "approval_scope": [c["path"] for c in changes], "approval_basis": "",
        "changes": changes,
    }


def publish(path: Path, blob: bytes, before: Optional[bytes]) -> None:
    """Publish a complete file within its destination directory, no outside scratch."""
    with directory(path.parent, True) as parent:
        name = ".onboard-" + uuid.uuid4().hex
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
            check_route(path)
            if read_file(path) != before:
                raise Refused("destination changed during application")
            if before is None:
                os.link(name, path.name, src_dir_fd=parent, dst_dir_fd=parent,
                        follow_symlinks=False)
            else:
                info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
                os.chmod(name, stat.S_IMODE(info.st_mode), dir_fd=parent)
                os.replace(name, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        finally:
            try:
                os.unlink(name, dir_fd=parent)
            except FileNotFoundError:
                pass


def apply_approval(target: Path, selected: Candidate, approval: dict) -> List[str]:
    if (not isinstance(approval, dict)
            or set(approval) != {"schema_version", "role", "candidate_sha256",
                                 "approval_state", "approval_effect", "approval_scope",
                                 "approval_basis", "changes"}
            or approval["schema_version"] != 1
            or approval["role"] != selected.manifest["role"]
            or approval["candidate_sha256"] != selected.manifest["candidate_sha256"]
            or approval["approval_state"] not in ("approved", "partially-approved")
            or not isinstance(approval["approval_basis"], str)
            or not approval["approval_basis"].strip()
            or not isinstance(approval["changes"], list)):
        raise Refused("invalid or unapproved settings diff")
    pending = []
    seen = []
    effects = set()
    for change in approval["changes"]:
        if (not isinstance(change, dict)
                or set(change) != {"path", "keys", "approval_preimage", "before", "after",
                                   "postimage_sha256", "recovery"}
                or change["path"] not in selected.settings or change["path"] in seen
                or (change["before"] is not None and not isinstance(change["before"], str))
                or not isinstance(change["after"], str)
                or not isinstance(change["recovery"], str) or not change["recovery"].strip()):
            raise Refused("invalid approved change")
        path = change["path"]
        seen.append(path)
        before = None if change["before"] is None else change["before"].encode("utf-8")
        after = setting_bytes(before, selected.settings[path], change["keys"])
        expected_preimage = "absent" if before is None else "sha256:" + digest(before)
        if (change["approval_preimage"] != expected_preimage
                or change["after"].encode("utf-8") != after
                or change["postimage_sha256"] != digest(after) or before == after):
            raise Refused("approved diff does not match exact key spans")
        effects.add("create" if before is None else "update")
        check_route(target / path)
        current = read_file(target / path)
        if current == after:
            continue  # exact postimage is a completed application, not renewed approval
        if current != before:
            raise Refused("stale approval preimage")
        pending.append((path, before, after))
    if (approval["approval_scope"] != seen
            or not isinstance(approval["approval_effect"], list)
            or set(approval["approval_effect"]) != effects):
        raise Refused("effect or scope mismatch")
    # All approvals and all preimages are checked before any write.
    changed = []
    for path, before, after in pending:
        publish(target / path, after, before)
        if read_file(target / path) != after:
            raise Refused("materialized setting readback failed")
        changed.append(path)
    return changed


def initialize(target: Path, selected: Candidate, resume: bool) -> List[str]:
    """Exclusive fresh creation, or exact-manifest resume without replacement."""
    for folder in selected.folders:
        check_route(target / folder, True)
    for path in selected.files:
        check_route(target / path)
    new_folders = [folder for folder in selected.folders if not (target / folder).exists()]
    if resume and required(target / MANIFEST) != selected.files[MANIFEST]:
        raise Refused("resume candidate identity mismatch")
    pending = []
    for path, blob in selected.files.items():
        current = read_file(target / path)
        if current is not None and current != blob:
            raise Refused("resume conflict; existing bytes retained")
        if current is None:
            pending.append(path)
    with directory(target, True):
        pass
    # Manifest first makes an interrupted fresh initialization resumable.
    for path in sorted(pending, key=lambda p: (p != MANIFEST, p)):
        publish(target / path, selected.files[path], None)
    for folder in selected.folders:
        with directory(target / folder, True):
            pass
    for path, blob in selected.files.items():
        if read_file(target / path) != blob:
            raise Refused("materialized candidate readback failed")
    return pending + new_folders


def run(candidate: Path, role: str, target: Path, mode: str = "auto",
        approval: Optional[dict] = None, preview: bool = False,
        selections: Optional[dict] = None) -> dict:
    selected = prepare(candidate, role)
    check_route(target, True)
    if not target.parent.is_dir() or target == target.parent:
        raise Refused("target parent must already exist")
    # Never initialize over, or beneath, the candidate's input tree.
    source = Path(os.path.abspath(str(candidate.parent)))
    destination = Path(os.path.abspath(str(target)))
    if source == destination or source in destination.parents or destination in source.parents:
        raise Refused("source and target overlap")
    fresh = not target.exists() or not any(target.iterdir())
    if preview:
        if approval is not None:
            raise Refused("preview and approval are mutually exclusive")
        return proposal(target, selected, selections if selections is not None else {
            p: sorted(v) for p, v in selected.settings.items() if v
        })
    if mode == "auto":
        mode = "fresh" if fresh else (
            "resume" if read_file(target / MANIFEST) == selected.files[MANIFEST] else "additive")
    if mode == "fresh":
        if not fresh or approval is not None:
            raise Refused("fresh requires empty/absent target and no settings approval")
        changed = initialize(target, selected, False)
    elif mode == "resume":
        if approval is not None:
            raise Refused("resume cannot apply settings approval")
        changed = initialize(target, selected, True)
    elif mode == "additive":
        if approval is None:
            raise Refused("additive requires an exact approved settings diff")
        changed = apply_approval(target, selected, approval)
    else:
        raise Refused("unknown mode")
    return {"schema_version": 1, "role": role, "mode": mode, "changed": sorted(changed),
            "diff_count": len(changed), "candidate_sha256": selected.manifest["candidate_sha256"],
            "evidence_level": "materialized"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mode", choices=("auto", "fresh", "additive", "resume"), default="auto")
    parser.add_argument("--preview", action="store_true", help="emit unapproved exact settings diff")
    parser.add_argument("--select", type=Path, help="JSON object mapping eligible paths to sorted keys")
    parser.add_argument("--approval", type=Path, help="owner-approved preview JSON; never inferred")
    args = parser.parse_args(argv)
    try:
        if args.select and not args.preview:
            raise Refused("--select requires --preview")
        result = run(args.candidate, args.role, args.target, args.mode,
                     parse(required(args.approval)) if args.approval else None, args.preview,
                     parse(required(args.select)) if args.select else None)
    except (Refused, OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        # Do not echo private input or host paths. A refused run may retain completed
        # files after I/O interruption; there is no misleading zero-diff success.
        print(json.dumps({"status": "refused", "partial_writes_possible": True,
                          "recovery": "Inspect target; resume exact candidate or approved diff."}),
              file=sys.stderr)
        return 1
    print(canonical(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
