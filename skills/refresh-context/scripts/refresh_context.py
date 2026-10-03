#!/usr/bin/env python3
"""Exact proposal and approval application for named derived context snapshots.

Python >=3.8, standard library only.
"""
import argparse
import json
from pathlib import Path
import sys
from typing import Optional

from snapshot_io import Refused, apply, authorize, digest, regular, relative, target, text


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read JSON input") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "input must be an object")
    return value


def parse_request(value: dict) -> dict:
    required = {"schema", "sources", "snapshots", "counterpart_vault"}
    if set(value) != required or value["schema"] != "refresh-context/request@1":
        raise Refused("invalid_input", "unsupported refresh request")
    sources = value["sources"]
    snapshots = value["snapshots"]
    if not isinstance(sources, list) or not sources:
        raise Refused("invalid_input", "sources must be a nonempty list")
    if not isinstance(snapshots, list) or not snapshots:
        raise Refused("invalid_input", "snapshots must be a nonempty list")
    kinds = []
    source_names = []
    snapshot_names = []
    for entry in sources:
        if not isinstance(entry, dict) or set(entry) != {"name", "kind", "path"}:
            raise Refused("invalid_input", "invalid source entry")
        text(entry["name"], "source name")
        if entry["kind"] not in ("me", "policy", "user-instruction"):
            raise Refused("invalid_input", "unsupported source kind")
        relative(entry["path"])
        kinds.append(entry["kind"])
        source_names.append(entry["name"])
    if "me" not in kinds or "policy" not in kinds:
        raise Refused("missing_source_role", "Me and policy sources are both required")
    for entry in snapshots:
        if not isinstance(entry, dict) or set(entry) != {"name", "path", "content"}:
            raise Refused("invalid_input", "invalid snapshot entry")
        text(entry["name"], "snapshot name")
        relative(entry["path"])
        if not isinstance(entry["content"], str):
            raise Refused("invalid_input", "snapshot content must be text")
        snapshot_names.append(entry["name"])
    if len(source_names) != len(set(source_names)) or len(snapshot_names) != len(set(snapshot_names)):
        raise Refused("invalid_input", "source and snapshot names must be unique")
    if value["counterpart_vault"] is not None and not isinstance(value["counterpart_vault"], str):
        raise Refused("invalid_input", "counterpart_vault must be a path or null")
    return value


def proposal(root: Path, request: dict) -> dict:
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise Refused("missing_vault", "vault is not an existing plain directory")
    request = parse_request(request)
    sources = []
    source_paths = set()
    for entry in request["sources"]:
        blob = regular(target(root, entry["path"]))
        sources.append(dict(entry, sha256=digest(blob)))
        source_paths.add(entry["path"])
    source_binding = {entry["path"]: entry["sha256"] for entry in sources}
    snapshots = []
    for entry in request["snapshots"]:
        if entry["path"] in source_paths:
            raise Refused("source_snapshot_overlap", "derived snapshot cannot replace a source")
        path = target(root, entry["path"])
        if not path.parent.is_dir():
            raise Refused("missing_parent", "snapshot parent must already exist")
        if path.exists() and (not path.is_file() or path.is_symlink()):
            raise Refused("unsafe_path", "snapshot target is not a plain file")
        before = None if not path.exists() else path.read_bytes()
        content = entry["content"].encode("utf-8")
        binding = {
            "path": entry["path"],
            "effect": "create" if before is None else "update",
            "preimage": "absent" if before is None else digest(before),
            "postimage": digest(content),
            "sources": source_binding,
        }
        snapshots.append({
            "name": entry["name"], "path": entry["path"],
            "effect": binding["effect"], "preimage": binding["preimage"],
            "postimage": binding["postimage"], "content": entry["content"],
            "proposal_sha256": digest(json.dumps(
                binding, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")),
        })
    counterpart = request["counterpart_vault"]
    counterpart_status = "not-specified"
    if counterpart is not None:
        counterpart_status = "available" if Path(counterpart).is_dir() else "absent-allowed"
    return {
        "schema": "refresh-context/proposal@1", "status": "proposed",
        "sources": sources, "snapshots": snapshots,
        "counterpart_status": counterpart_status,
        "mutations_performed": [],
    }


def run(root: Path, request: dict, approval: Optional[dict] = None) -> dict:
    planned = proposal(root, request)
    if approval is None:
        return planned
    selected = authorize(approval, planned)
    changed = apply(root.absolute(), planned, selected)
    return dict(planned, status="rejected" if not selected else "applied",
                mutations_performed=changed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.vault, load(args.request),
                     None if args.approval is None else load(args.approval))
    except Refused as exc:
        print(json.dumps({"schema": "refresh-context/error@1", "status": "refused",
                          "code": exc.code, "error": str(exc),
                          "mutations_performed": []}))
        return 1
    except OSError as exc:
        print(json.dumps({"schema": "refresh-context/error@1", "status": "error",
                          "code": "io_error", "error": type(exc).__name__,
                          "mutations_performed": [],
                          "mutation_state": "inspect approved snapshot paths"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
