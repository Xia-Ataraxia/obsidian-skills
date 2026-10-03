"""Path, proposal, approval, and publication boundaries for verify."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import tempfile


class Refused(Exception):
    """A request, evidence range, or approval is unsafe or incomplete."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def exact_fields(value, required: set, optional: set, label: str) -> dict:
    if not isinstance(value, dict) or set(value) - required - optional or not required <= set(value):
        raise Refused("invalid_input", "unexpected or missing fields in " + label)
    return value


def text(value, field: str, empty: bool = False) -> str:
    if not isinstance(value, str) or "\x00" in value or (not empty and not value.strip()):
        raise Refused("invalid_input", field + " must be text")
    return value


def relative(value: str) -> str:
    text(value, "path")
    parts = value.split("/")
    if (
        "\\" in value
        or ":" in value
        or any(part in ("", ".", "..") or part.startswith(".") for part in parts)
    ):
        raise Refused("unsafe_path", "path must be literal and vault-relative")
    return value


def target(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in selected path")
    if not path.is_file() or path.suffix != ".md":
        raise Refused("missing_input", "selected path is not a Markdown file")
    return path


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read JSON input") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "JSON input must be an object")
    return value


def proposal(path: str, before: bytes, record: dict) -> dict:
    addition = (
        "\n\n```json verify-record\n"
        + json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
    ).encode("utf-8")
    after = before + addition
    diff = "".join(
        difflib.unified_diff(
            before.decode("utf-8").splitlines(keepends=True),
            after.decode("utf-8").splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )
    binding = {
        "path": path,
        "preimage": digest(before),
        "postimage": digest(after),
        "diff": diff,
    }
    return {
        "path": path,
        "effect": "update",
        "preimage": binding["preimage"],
        "postimage": binding["postimage"],
        "diff": diff,
        "content": after.decode("utf-8"),
        "proposal_sha256": digest(
            json.dumps(binding, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ),
    }


def authorize(approval: dict, item: dict) -> None:
    exact_fields(
        approval,
        {
            "approval_state",
            "approval_effect",
            "approval_scope",
            "approval_basis",
            "approval_preimage",
            "approval_proposal",
        },
        set(),
        "approval",
    )
    if approval["approval_state"] not in ("approved", "partially-approved"):
        raise Refused("approval_required", "record update is not approved")
    text(approval["approval_basis"], "approval_basis")
    path = item["path"]
    if (
        not isinstance(approval["approval_effect"], list)
        or "update" not in approval["approval_effect"]
        or not isinstance(approval["approval_scope"], list)
        or path not in approval["approval_scope"]
        or not isinstance(approval["approval_preimage"], dict)
        or not isinstance(approval["approval_proposal"], dict)
        or approval["approval_preimage"].get(path) != item["preimage"]
        or approval["approval_proposal"].get(path) != item["proposal_sha256"]
    ):
        raise Refused("stale_approval", "approval does not bind the exact proposal")


def publish(root: Path, item: dict) -> None:
    path = target(root, item["path"])
    if digest(path.read_bytes()) != item["preimage"]:
        raise Refused("stale_approval", "reviewed page changed before application")
    content = item["content"].encode("utf-8")
    handle, staged = tempfile.mkstemp(prefix=".verify-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, path.stat().st_mode & 0o777)
        os.replace(staged, str(path))
        if path.read_bytes() != content:
            raise Refused("readback_failed", "verification record readback differs")
    finally:
        if os.path.exists(staged):
            os.unlink(staged)
