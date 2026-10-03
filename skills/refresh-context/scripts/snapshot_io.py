"""Approval checks and interruption-safe writes for derived snapshots."""
import hashlib
import os
from pathlib import Path
import tempfile
from typing import List


class Refused(Exception):
    """A source, proposal, path, or approval binding is unsafe."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise Refused("invalid_input", label + " must be nonempty text")
    return value


def relative(value: str) -> str:
    text(value, "path")
    parts = value.split("/")
    if ("\\" in value or ":" in value
            or any(part in ("", ".", "..") or part.startswith(".") for part in parts)):
        raise Refused("unsafe_path", "path must be a literal visible vault-relative route")
    return value


def target(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in requested path")
    return path


def regular(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise Refused("missing_source", "source is not a regular file")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise Refused("unreadable_source", "cannot read source bytes") from exc


def authorize(approval: dict, planned: dict) -> List[dict]:
    required = {"approval_state", "approval_effect", "approval_scope",
                "approval_basis", "approval_preimage", "approval_proposal"}
    if set(approval) != required:
        raise Refused("invalid_input", "invalid approval record")
    state = approval["approval_state"]
    if state not in ("approved", "partially-approved", "rejected"):
        raise Refused("invalid_input", "unsupported approval state")
    text(approval["approval_basis"], "approval_basis")
    paths = [item["path"] for item in planned["snapshots"]]
    scope = approval["approval_scope"]
    if (not isinstance(scope, list)
            or any(not isinstance(path, str) for path in scope)):
        raise Refused("invalid_input", "approval_scope must be a unique list")
    if len(scope) != len(set(scope)):
        raise Refused("invalid_input", "approval_scope must be a unique list")
    if any(path not in paths for path in scope):
        raise Refused("approval_required", "approval names an unknown snapshot")
    if state == "rejected":
        if scope:
            raise Refused("invalid_input", "rejected approval must have empty scope")
        return []
    if state == "approved" and set(scope) != set(paths):
        raise Refused("approval_required", "full approval must cover every snapshot")
    if state == "partially-approved" and (not scope or set(scope) == set(paths)):
        raise Refused("invalid_input", "partial approval must cover a strict subset")
    effects = approval["approval_effect"]
    preimages = approval["approval_preimage"]
    proposals = approval["approval_proposal"]
    if (not isinstance(effects, list) or not isinstance(preimages, dict)
            or not isinstance(proposals, dict)):
        raise Refused("invalid_input", "approval bindings have invalid types")
    selected = []
    for item in planned["snapshots"]:
        if item["path"] not in scope:
            continue
        if (item["effect"] not in effects
                or preimages.get(item["path"]) != item["preimage"]
                or proposals.get(item["path"]) != item["proposal_sha256"]):
            raise Refused("stale_approval", "approved effect or binding does not match")
        selected.append(item)
    return selected


def restore(path: Path, prior) -> None:
    if prior is None:
        path.unlink()
        return
    blob, mode = prior
    handle, recovery = tempfile.mkstemp(
        prefix=".refresh-context-recovery-", dir=str(path.parent))
    with os.fdopen(handle, "wb") as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(recovery, mode)
    os.replace(recovery, str(path))


def apply(root: Path, planned: dict, selected: List[dict]) -> List[str]:
    for source in planned["sources"]:
        if digest(regular(target(root, source["path"]))) != source["sha256"]:
            raise Refused("stale_source", "source changed after proposal")
    for item in selected:
        path = target(root, item["path"])
        current = "absent" if not path.exists() else digest(path.read_bytes())
        if current != item["preimage"]:
            raise Refused("stale_approval", "snapshot changed after approval")
    staged = []
    previous = {}
    try:
        for item in selected:
            path = target(root, item["path"])
            previous[path] = None if not path.exists() else (
                path.read_bytes(), path.stat().st_mode & 0o777)
            handle, scratch = tempfile.mkstemp(prefix=".refresh-context-", dir=str(path.parent))
            with os.fdopen(handle, "wb") as stream:
                stream.write(item["content"].encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(scratch, path.stat().st_mode & 0o777 if path.exists() else 0o644)
            staged.append((scratch, path))
        completed = []
        try:
            for scratch, path in staged:
                os.replace(scratch, str(path))
                completed.append(path)
        except (OSError, KeyboardInterrupt) as exc:
            try:
                for path in reversed(completed):
                    restore(path, previous[path])
            except OSError as rollback:
                raise Refused("rollback_failed",
                              "interrupted snapshot batch could not be restored") from rollback
            raise Refused("application_interrupted",
                          "interrupted snapshot batch was restored") from exc
        return [item["path"] for item in selected]
    finally:
        for scratch, _path in staged:
            if os.path.exists(scratch):
                os.unlink(scratch)
