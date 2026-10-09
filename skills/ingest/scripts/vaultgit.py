"""One ingest = one git commit, in a fixed order. Stdlib only; opt-in via ingest.py --git.

fetch -> reset --mixed origin/main -> write -> add -- <exact paths> -> commit -> push.
Never --hard, never force-push, never checkout/revert to settle content.
"""
import hashlib
import os
import subprocess

from source import Refused

HOOK = None  # test seam: callable(point) at "written", "pre-add", "committed"


def git(repo, *args, check=True, data=None):
    # Every path this module passes is an exact owned filename: never glob or pathspec magic (`Raw/*.md`, `:(top)`).
    run = subprocess.run(["git", "--literal-pathspecs", "-C", str(repo)] + list(args), input=data, capture_output=True)
    if check and run.returncode:
        raise Refused("git " + args[0] + " failed: " + run.stderr.decode("utf-8", "replace").strip())
    return run


def base_bytes(repo, path):
    """Bytes of path in fetched origin/main, or None when absent there."""
    if not git(repo, "ls-tree", "--name-only", "origin/main", "--", path).stdout.strip():
        return None
    return git(repo, "cat-file", "blob", "origin/main:" + path).stdout


def local_bytes(repo, path):
    full = os.path.join(str(repo), path)
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as f:
        return f.read()


def index_bytes(repo, path):
    """Stage-0 regular-file blob bytes of path in the index, or None when the index has no entry."""
    rows = [row for row in git(repo, "ls-files", "--stage", "-z", "--", path).stdout.split(b"\0") if row]
    rows = [row for row in rows if row.split(b"\t", 1)[1] == path.encode("utf-8")]
    if not rows:
        return None
    mode, sha, stage = rows[0].split(b"\t", 1)[0].split(b" ")
    if len(rows) != 1 or stage != b"0" or mode not in (b"100644", b"100755"):
        raise Refused("index entry is unmerged or not a regular file: " + path)
    return git(repo, "cat-file", "blob", sha.decode()).stdout


def owned(session):
    """{path: (preimage-or-None, postimage)} for every create/update this ingest writes."""
    return {r["path"]: (r["before"], r["after"]) for r in session["changes"]}


def point(name):
    if HOOK:
        HOOK(name)


def ahead(repo):
    return git(repo, "rev-list", "origin/main..HEAD").stdout.decode().split()


def staged(repo):
    return set(git(repo, "diff", "--cached", "--name-only", "-z").stdout.decode().split("\0")) - {""}


def human_dirty(repo, paths):
    """Uncommitted edits relative to HEAD on owned paths (index or work tree)."""
    out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *paths).stdout
    return out.decode().replace("\0", " ").strip()


def push(repo, git_state, save):
    sha = git_state["sha"]
    if git(repo, "push", "origin", sha + ":refs/heads/main", check=False).returncode:
        git(repo, "fetch", "origin")
        git_state["state"] = "committed-local"
        save()
        raise Refused("non-fast-forward push; local commit " + sha + " kept as committed-local; inspect and republish")
    git(repo, "fetch", "origin")
    git_state["state"] = "published"
    save()


def transact(repo, session, write, save, title, source, kind="ingest"):
    """Run the fixed sequence; `write` performs byte-checked writes, `save` persists session state."""
    top = git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip()
    if os.path.realpath(top) != os.path.realpath(str(repo)):
        raise Refused("vault must be the git repository top level")
    # Byte guards compare blobs with disk bytes; any line-ending conversion breaks them.
    eol = git(repo, "config", "--get", "core.autocrlf", check=False).stdout.decode().strip()
    if eol not in ("", "false"):
        raise Refused("core.autocrlf=" + eol + " converts bytes; set `git config core.autocrlf false` in the vault repo")
    lock = os.path.join(top, ".git", "ingest.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise Refused("repository ingest lock held: " + lock)
    os.close(fd)
    try:
        return _transact(repo, session, write, save, title, source, kind)
    finally:
        os.unlink(lock)


def _transact(repo, session, write, save, title, source, kind="ingest"):
    state = session.setdefault("git", {"state": "planned"})
    paths = owned(session)
    git(repo, "fetch", "origin")
    local_ahead = ahead(repo)
    if state["state"] in ("committed-local", "published"):
        sha = state["sha"]
        if git(repo, "merge-base", "--is-ancestor", sha, "origin/main", check=False).returncode == 0:
            state["state"] = "published"
            save()
        elif local_ahead != [sha]:
            raise Refused("recorded commit is not the only unpublished local commit; not resetting")
        else:
            push(repo, state, save)
        return {"sha": sha, "paths": sorted(paths), "state": state["state"]}
    if local_ahead:
        raise Refused("local commits ahead of origin/main: " + " ".join(local_ahead) + "; publish them first, not resetting")
    unrelated = staged(repo) - set(paths)
    if unrelated:
        raise Refused("unrelated staged entries: " + ", ".join(sorted(unrelated)))
    if state["state"] in ("writing", "written"):
        # ARCH-008: after writes, recorded preimages must equal base and local must equal postimages.
        for path, (before, after) in sorted(paths.items()):
            if base_bytes(repo, path) != before:
                raise Refused("remote preimage drift since write: " + path)
            if local_bytes(repo, path) != after:
                raise Refused("local postimage drift since write: " + path)
        # reset --mixed rewrites the index: a staged owned entry may hold human-only bytes even when disk matches.
        for path in sorted(staged(repo) & set(paths)):
            if index_bytes(repo, path) != paths[path][1]:
                raise Refused("staged owned entry differs from intended postimage since write: " + path)
        git(repo, "reset", "--mixed", "origin/main")
    else:
        if staged(repo):
            raise Refused("staged entries present before ingest")
        for path, (before, _after) in sorted(paths.items()):
            base, local = base_bytes(repo, path), local_bytes(repo, path)
            if before is None and (base is not None or local is not None):
                raise Refused("create path not absent in base and local (base %s, local %s): %s" % (
                    "present" if base is not None else "absent", "present" if local is not None else "absent", path))
            if before is not None and not (base == before == local):
                raise Refused("owned path stale or human-edited: " + path)
        git(repo, "reset", "--mixed", "origin/main")
        state["state"] = "writing"
        save()
        write()
        state["state"] = "written"
        save()
        point("written")
    for path, (_before, after) in sorted(paths.items()):
        if local_bytes(repo, path) != after:
            raise Refused("owned path edited after write: " + path)
    point("pre-add")
    git(repo, "add", "-A", "--", *sorted(paths))
    if staged(repo) != {p for p, (b, a) in paths.items() if b != a}:
        raise Refused("staged set differs from owned paths")
    for path, (_before, after) in sorted(paths.items()):
        if index_bytes(repo, path) != after:
            raise Refused("staged blob differs from intended postimage: " + path)
    path_hash = hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest()
    message = "%s: %s\n\nIngest-Source: %s\nIngest-Paths: sha256:%s\n" % (kind, title, source, path_hash)
    git(repo, "commit", "--no-verify", "-q", "-F", "-", data=message.encode("utf-8"))
    state["sha"] = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    state["state"] = "committed-local"
    save()
    point("committed")
    push(repo, state, save)
    return {"sha": state["sha"], "paths": sorted(paths), "state": state["state"]}
