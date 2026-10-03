"""Filesystem and approval boundaries for audit."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Set


class Refused(Exception):
    """A scope, sample, report, or approval cannot be used safely."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise Refused("invalid_input", field + " must be nonempty text")
    return value


def relative(value: str, markdown: bool = False) -> str:
    text(value, "path")
    parts = value.split("/")
    if (
        "\\" in value
        or ":" in value
        or any(part in ("", ".", "..") or part.startswith(".") for part in parts)
        or (markdown and not value.endswith(".md"))
    ):
        raise Refused("unsafe_path", "path must be literal and vault-relative")
    return value


def route(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in selected path")
    return path


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read JSON input") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "JSON input must be an object")
    return value


def fields(value, required: Set[str], optional: Set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) - required - optional or not required <= set(value):
        raise Refused("invalid_input", "unexpected or missing fields in " + label)
    return value


def make_proposal(path: str, report: dict) -> dict:
    content = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    binding = {"path": path, "preimage": "absent", "postimage": digest(content)}
    return {
        "path": path,
        "effect": "create",
        "preimage": "absent",
        "postimage": binding["postimage"],
        "content": content.decode("utf-8"),
        "proposal_sha256": digest(
            json.dumps(binding, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ),
    }


def authorize(approval: dict, item: dict) -> None:
    required = {
        "approval_state",
        "approval_effect",
        "approval_scope",
        "approval_basis",
        "approval_preimage",
        "approval_proposal",
    }
    fields(approval, required, set(), "approval")
    path = item["path"]
    if (
        approval["approval_state"] not in ("approved", "partially-approved")
        or not isinstance(approval["approval_effect"], list)
        or "create" not in approval["approval_effect"]
        or not isinstance(approval["approval_scope"], list)
        or path not in approval["approval_scope"]
        or not isinstance(approval["approval_preimage"], dict)
        or approval["approval_preimage"].get(path) != "absent"
        or not isinstance(approval["approval_proposal"], dict)
        or approval["approval_proposal"].get(path) != item["proposal_sha256"]
    ):
        raise Refused("approval_required", "approval does not bind the exact report")
    text(approval["approval_basis"], "approval_basis")


def publish(root: Path, item: dict) -> None:
    destination = route(root, item["path"])
    if destination.exists() or not destination.parent.is_dir():
        raise Refused("collision", "report destination must be absent with an existing parent")
    content = item["content"].encode("utf-8")
    handle, staged = tempfile.mkstemp(prefix=".audit-", dir=str(destination.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, 0o644)
        os.link(staged, str(destination))
        if destination.read_bytes() != content:
            raise Refused("readback_failed", "saved report bytes differ")
    finally:
        if os.path.exists(staged):
            os.unlink(staged)
