#!/usr/bin/env python3
"""Read-only counts for explicitly named knowledge-vault responsibility roots.

Python >=3.8, standard library only.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional

FRONTMATTER_LIMIT = 65536

class Refused(Exception):
    """The requested observation is ambiguous or unsafe."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read scope JSON") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "scope must be an object")
    return value


def relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise Refused("unsafe_path", "path must be nonempty vault-relative text")
    parts = value.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") for part in parts):
        raise Refused("unsafe_path", "hidden, empty, or traversal path component")
    if ":" in value or any(ord(char) < 32 for char in value):
        raise Refused("unsafe_path", "path is not a literal vault-relative path")
    return value


def target(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in requested path")
    return path


def markdown_files(root: Path, selected: Path) -> List[Path]:
    if not selected.is_dir():
        raise Refused("missing_root", "responsibility root is not a directory")
    found = []
    for parent, directories, filenames in os.walk(str(selected), followlinks=False):
        base = Path(parent)
        directories[:] = sorted(
            name for name in directories
            if not name.startswith(".") and not (base / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = base / filename
            if (filename.startswith(".") or path.is_symlink()
                    or not path.is_file() or path.suffix != ".md"):
                continue
            found.append(path)
    return found


def frontmatter_fields(path: Path) -> dict:
    """Read only bounded flat frontmatter; never consume the note body."""
    try:
        stream = path.open("rb", buffering=0)
    except OSError as exc:
        raise Refused("unreadable_note", "cannot read a counted Markdown file") from exc
    with stream:
        first = stream.readline(FRONTMATTER_LIMIT + 1)
        if first.rstrip(b"\r\n") != b"---":
            return {}
        consumed = len(first)
        fields = {}
        while consumed <= FRONTMATTER_LIMIT:
            raw = stream.readline(FRONTMATTER_LIMIT - consumed + 1)
            if not raw:
                raise Refused("invalid_note", "unterminated frontmatter")
            consumed += len(raw)
            if consumed > FRONTMATTER_LIMIT:
                raise Refused("invalid_note", "frontmatter exceeds the read boundary")
            if raw.rstrip(b"\r\n") == b"---":
                return fields
            try:
                line = raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError as exc:
                raise Refused("invalid_note", "frontmatter is not UTF-8") from exc
            if line[:1].isspace() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            if not key or key in fields:
                raise Refused("invalid_note", "frontmatter keys must be unique")
            raw_value = value.strip()
            try:
                fields[key] = json.loads(raw_value)
            except json.JSONDecodeError:
                fields[key] = raw_value
    raise Refused("invalid_note", "frontmatter exceeds the read boundary")


def property_counts(files: List[Path], properties: List[str]) -> Dict[str, int]:
    counts = {name: 0 for name in properties}
    for path in files:
        keys = frontmatter_fields(path)
        for name in properties:
            if name in keys:
                counts[name] += 1
    return counts


def parse_scope(value: dict) -> dict:
    required = {"schema", "roots", "paper_analyses", "inbox", "snapshots", "properties"}
    if set(value) != required or value["schema"] != "status/scope@1":
        raise Refused("invalid_input", "unsupported status scope")
    if not isinstance(value["roots"], list) or not value["roots"]:
        raise Refused("invalid_input", "roots must be a nonempty list")
    names = []
    for entry in value["roots"]:
        if not isinstance(entry, dict) or set(entry) != {"name", "path"}:
            raise Refused("invalid_input", "invalid responsibility root")
        if not isinstance(entry["name"], str) or not entry["name"].strip():
            raise Refused("invalid_input", "root name must be nonempty text")
        relative(entry["path"])
        names.append(entry["name"])
    if len(names) != len(set(names)):
        raise Refused("invalid_input", "responsibility root names must be unique")
    for key in ("paper_analyses", "inbox"):
        relative(value[key])
    if not isinstance(value["snapshots"], list):
        raise Refused("invalid_input", "snapshots must be a list")
    for entry in value["snapshots"]:
        if not isinstance(entry, dict) or set(entry) != {"name", "path"}:
            raise Refused("invalid_input", "invalid snapshot entry")
        relative(entry["path"])
    properties = value["properties"]
    if (not isinstance(properties, list)
            or any(not isinstance(item, str) or not item.strip() for item in properties)):
        raise Refused("invalid_input", "properties must be unique nonempty names")
    if len(properties) != len(set(properties)):
        raise Refused("invalid_input", "properties must be unique nonempty names")
    return value


def run(root: Path, scope: dict, now: Optional[float] = None) -> dict:
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise Refused("missing_vault", "vault is not an existing plain directory")
    scope = parse_scope(scope)
    roots = []
    for entry in scope["roots"]:
        files = markdown_files(root, target(root, entry["path"]))
        roots.append({
            "name": entry["name"], "path": entry["path"],
            "markdown_files": len(files),
            "properties": property_counts(files, scope["properties"]),
        })
    paper_path = target(root, scope["paper_analyses"])
    paper_files = markdown_files(root, paper_path)
    root_paper_files = sorted(
        item for item in paper_path.iterdir()
        if item.is_file() and not item.is_symlink() and item.suffix == ".md"
    )
    hub_identities = []
    hub_files = 0
    missing_hub_identities = 0
    for path in root_paper_files:
        fields = frontmatter_fields(path)
        if fields.get("type") != "paper-hub":
            continue
        hub_files += 1
        identity = fields.get("source_identity")
        if isinstance(identity, str) and identity.strip():
            hub_identities.append(identity)
        else:
            missing_hub_identities += 1
    unique_hub_identities = len(set(hub_identities))
    inbox_files = markdown_files(root, target(root, scope["inbox"]))
    observed_at = time.time() if now is None else now
    snapshots = []
    for entry in scope["snapshots"]:
        path = target(root, entry["path"])
        exists = path.is_file()
        snapshots.append({
            "name": entry["name"], "path": entry["path"], "exists": exists,
            "age_seconds": None if not exists else max(0, int(observed_at - path.stat().st_mtime)),
        })
    return {
        "schema": "status/report@1", "status": "observed",
        "roots": roots,
        "paper_analyses": {
            "path": scope["paper_analyses"],
            "top_level_directories": len([
                item for item in paper_path.iterdir()
                if item.is_dir() and not item.is_symlink() and not item.name.startswith(".")
            ]),
            "root_markdown_files": len(root_paper_files),
            "markdown_files": len(paper_files),
            "paper_hub_files": hub_files,
            "unique_source_identities": unique_hub_identities,
            "duplicate_identity_hub_files": (
                len(hub_identities) - unique_hub_identities),
            "hub_files_missing_source_identity": missing_hub_identities,
        },
        "inbox": {"path": scope["inbox"], "markdown_files": len(inbox_files)},
        "snapshots": snapshots,
        "limitations": [
            "Property presence is not purpose fulfillment, correctness, or review.",
            "Counts are not quality, feedback, verification, or runtime health.",
            "Paper hub containers and Markdown file totals are separate observations.",
        ],
        "semantics": {
            "property_presence_only": True,
            "quality_assessed": False,
            "purpose_fulfillment_assessed": False,
            "paper_hubs_deduplicated_by_source_identity": True,
            "note_body_read": False,
        },
        "mutations_performed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--scope", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.vault, load(args.scope))
    except Refused as exc:
        print(json.dumps({"schema": "status/error@1", "status": "refused",
                          "code": exc.code, "error": str(exc),
                          "mutations_performed": []}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
