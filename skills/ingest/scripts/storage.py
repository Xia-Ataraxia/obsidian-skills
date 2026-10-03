"""Exact-path plans and preserved appends for one independent ingest package."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import List
import hashlib
import json
import os
import tempfile

from request import Refused


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def target(vault: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or relative.as_posix() != name
            or "\\" in name or any(p in ("..", ".") or p.startswith(".")
                                   for p in relative.parts)):
        raise Refused("expected canonical visible vault-relative path: " + name)
    path = vault
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise Refused("symlink in path: " + name)
    return path


def metadata(blob: bytes) -> dict:
    text = blob.decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise Refused("note has no bounded frontmatter")
    result = {}
    for line in text.split("\n---\n", 1)[0][4:].splitlines():
        key, separator, value = line.partition(": ")
        if not separator or key in result:
            raise Refused("requires unique flat frontmatter keys with JSON values")
        try:
            result[key] = json.loads(value)
        except json.JSONDecodeError:
            # Native simple scalars (e.g. type: persona); nested YAML is not guessed.
            if value.startswith(("[", "{", "'", '"', "|", ">")):
                raise Refused("unsupported non-JSON frontmatter value")
            result[key] = value
    return result


def note(fields: dict, body: str) -> bytes:
    # JSON is a YAML subset. Values cannot escape into extra YAML keys.
    return ("---\n" + "\n".join(
        key + ": " + json.dumps(value, ensure_ascii=False) for key, value in fields.items())
            + "\n---\n\n" + body + "\n").encode("utf-8")


def link(name: str) -> str:
    if any(char in name for char in ("[", "]", "|", "#", "\n", "\r")):
        raise Refused("unrepresentable wikilink target")
    return "[[" + (name[:-3] if name.endswith(".md") else name) + "]]"


@dataclass(frozen=True)
class Change:
    path: str
    before: bytes
    after: bytes
    exists: bool
    compiled_target: str = ""

    def receipt(self) -> dict:
        row = {"path": self.path, "effect": "update" if self.exists else "create",
               "preimage": digest(self.before) if self.exists else "absent",
               "sha256": digest(self.after)}
        if self.exists:
            if self.compiled_target:
                row["update_sha256"] = digest(self.after)
                row["approval_diff_sha256"] = row["update_sha256"]
                row["proposed_diff"] = {"compiled_target": {
                    "before": metadata(self.before).get("compiled_target", ""),
                    "after": self.compiled_target}}
                before_body = self.before.split(b"\n---\n", 1)[1]
                after_body = self.after.split(b"\n---\n", 1)[1]
                addition = after_body[len(before_body):]
            else:
                addition = self.after[len(self.before):]
                row["append_sha256"] = digest(addition)
                row["approval_diff_sha256"] = row["append_sha256"]
            row["proposed_append"] = addition.decode("utf-8")
        return row


class Plan:
    """Accumulate preflighted changes; existing bytes are only appended."""

    def __init__(self, vault: Path, note_fields: dict):
        if (any(p.is_symlink() for p in (vault,) + tuple(vault.parents))
                or not vault.is_dir()):
            raise Refused("vault must be an existing nonsymlink directory")
        self.vault = vault.resolve()
        self.changes: List[Change] = []
        self.note_fields = note_fields
        self.input_preimages = {}

    def read(self, name: str):
        """Read the staged output view, falling through to actual destination bytes."""
        for change in self.changes:
            if change.path == name:
                return change.after
        path = target(self.vault, name)
        if not path.exists():
            return None
        if not path.is_file():
            raise Refused("expected a regular note: " + name)
        return path.read_bytes()

    def new_note(self, name: str, fields: dict, body: str) -> None:
        """Apply only explicit destination metadata, without rewriting shared fields."""
        fields = dict(fields)
        fields.update(self.note_fields.get(name, {}))
        self.add(name, note(fields, body))

    def bind_compilation(self, name: str, wiki: str) -> None:
        """Persist only the generated Raw association under exact update approval."""
        current = self.read(name)
        if current is None:
            raise Refused("Raw binding target disappeared")
        fields = metadata(current)
        old = fields.get("compiled_target")
        if old == wiki:
            return
        if old != "":
            raise Refused("Raw compiled target is missing or already bound")
        header, separator, body = current.partition(b"\n---\n")
        lines = header.split(b"\n")
        index = next(i for i, line in enumerate(lines) if line.startswith(b"compiled_target: "))
        lines[index] = ("compiled_target: " + json.dumps(wiki, ensure_ascii=False)).encode("utf-8")
        after = b"\n".join(lines) + separator + body
        pending = next((change for change in self.changes if change.path == name), None)
        change = Change(name, pending.before if pending else current, after,
                        pending.exists if pending else True, wiki)
        if pending:
            self.changes[self.changes.index(pending)] = change
        else:
            self.changes.append(change)

    def add(self, name: str, blob: bytes, append: bool = False) -> None:
        path = target(self.vault, name)
        if not path.parent.is_dir() or (path.exists() and not path.is_file()):
            raise Refused("destination parent missing or target not a file: " + name)
        pending = next((change for change in self.changes if change.path == name), None)
        current = self.read(name)
        exists = current is not None
        before = current if exists else b""
        if append:
            if not exists:
                raise Refused("designated append target does not exist: " + name)
            if blob in before:
                return
            after = before + blob
        else:
            if exists:
                if before == blob:
                    return
                raise Refused("refusing to replace existing note: " + name)
            after = blob
        if pending:
            index = self.changes.index(pending)
            self.changes[index] = Change(name, pending.before, after, pending.exists,
                                         pending.compiled_target)
        else:
            self.changes.append(Change(name, before, after, exists))

    def authorize(self, approval: dict) -> None:
        if approval.get("approval_state") not in ("approved", "partially-approved"):
            raise Refused("writes require explicit approved effects")
        if not isinstance(approval.get("approval_basis"), str) or not approval["approval_basis"].strip():
            raise Refused("approval_basis is missing")
        scope = approval.get("approval_scope", [])
        effects = approval.get("approval_effect", [])
        preimages = approval.get("approval_preimage", {})
        if (not isinstance(scope, list) or not isinstance(effects, list)
                or not isinstance(preimages, dict)
                or not isinstance(approval.get("approval_diff", {}), dict)):
            raise Refused("malformed approval scope/effects/preimages/diff")
        for change in self.changes:
            row = change.receipt()
            if (row["path"] not in scope or row["effect"] not in effects
                    or preimages.get(row["path"]) != row["preimage"]):
                raise Refused("unapproved effect, scope or preimage: " + change.path)
            if change.exists:
                diffs = approval.get("approval_diff", {})
                if diffs.get(change.path) != row["approval_diff_sha256"]:
                    raise Refused("existing update needs its exact proposed diff hash")

    def apply(self, approval: dict) -> List[dict]:
        self.authorize(approval)
        for name, expected in self.input_preimages.items():
            path = target(self.vault, name)
            if not path.is_file() or digest(path.read_bytes()) != expected:
                raise Refused("selected input drift: " + name)
        # Recheck the entire plan before the first mutation.
        for change in self.changes:
            path = target(self.vault, change.path)
            actual = path.read_bytes() if path.exists() else None
            if actual != (change.before if change.exists else None):
                raise Refused("preimage drift: " + change.path)
        applied = []
        try:
            for change in self.changes:
                path = target(self.vault, change.path)
                if change.exists:
                    if path.read_bytes() != change.before:
                        raise Refused("preimage drift: " + change.path)
                    fd, staged = tempfile.mkstemp(prefix=".ingest-", dir=str(path.parent))
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(change.after)
                        os.replace(staged, str(path))
                    finally:
                        if os.path.exists(staged):
                            os.unlink(staged)
                else:
                    with path.open("xb") as stream:
                        stream.write(change.after)
                row = change.receipt()
                row["readback"] = digest(path.read_bytes())
                if row["readback"] != row["sha256"]:
                    raise Refused("readback mismatch: " + change.path)
                applied.append(row)
        except (OSError, Refused) as exc:
            raise Refused("partial apply; preserved completed writes: "
                          + json.dumps(applied) + "; " + str(exc)) from exc
        return applied
