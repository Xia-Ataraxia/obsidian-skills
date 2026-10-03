#!/usr/bin/env python3
"""Read recursive candidates and prepare one explicitly selected ingest batch.

Python >=3.8. No compilation or deletion occurs during list/preview/handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Union

Json = Union[None, bool, int, str, List["Json"], Dict[str, "Json"]]


class Refused(Exception):
    """The requested selection or effect is outside its declared boundary."""


def path_in(root: Path, name: str) -> Path:
    """Resolve a relative path, refusing traversal and all symlink components."""
    if not isinstance(name, str) or not name or "\\" in name:
        raise Refused("invalid relative path")
    path = Path(name)
    if path.is_absolute() or any(part in ("..", ".") for part in name.split("/")):
        raise Refused("path leaves the declared vault")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise Refused("symlink path is not an Inbox candidate")
    return current


def read_candidate(root: Path, name: str) -> Dict[str, Json]:
    """Preview captured originals structurally; arbitrary notes stay unclassified."""
    path = path_in(root, name)
    if not path.is_file():
        raise Refused("candidate must be a regular Markdown file")
    blob = path.read_bytes()
    content = blob.decode("utf-8")
    metadata: Dict[str, Json] = {}
    if content.startswith("---\n"):
        header, separator, body = content[4:].partition("\n---\n")
        if not separator:
            raise Refused("unterminated candidate frontmatter")
        for line in header.splitlines():
            key, separator, value = line.partition(": ")
            if separator:
                if key in metadata:
                    raise Refused("duplicate candidate frontmatter key")
                try:
                    metadata[key] = json.loads(value)
                except ValueError:
                    # This reader does not guess values from other YAML dialects.
                    metadata[key] = value
    else:
        body = content
    sources = metadata.get("capture_sources", [])
    if metadata.get("capture_schema") == "capture/candidate@1":
        if not isinstance(sources, list) or not sources:
            raise Refused("capture candidate has no source records")
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("original_content"), str):
                raise Refused("invalid capture source")
            fidelity = source.get("fidelity")
            if fidelity not in ("full", "partial", "excerpt", "manifest-only"):
                raise Refused("invalid capture fidelity")
            if fidelity == "manifest-only" and source["original_content"]:
                raise Refused("manifest-only candidate contains purported original text")
            if fidelity != "manifest-only" and not source["original_content"]:
                raise Refused("obtained fidelity requires original text")
            if not isinstance(source.get("source_locator"), str) or not source["source_locator"]:
                raise Refused("capture source has no locator")
            if not isinstance(source.get("source_identity", ""), str):
                raise Refused("invalid source identity")
        actual_fidelity = sources[0]["fidelity"] if len(sources) == 1 else "mixed"
        if metadata.get("fidelity") != actual_fidelity:
            raise Refused("candidate fidelity contradicts its selected source records")
        preview: Json = [{"source_locator": source["source_locator"],
                          "fidelity": source["fidelity"],
                          "fidelity_omissions": source.get("fidelity_omissions", []),
                          "original_content": source["original_content"]} for source in sources]
    else:
        preview = body
        sources = []
    return {"path": name, "sha256": hashlib.sha256(blob).hexdigest(),
            "status": metadata.get("status", "unknown"),
            "fidelity": metadata.get("fidelity", "unknown"),
            "sources": sources, "preview": preview,
            "evidence_level": "materialized"}


def listing(root: Path, scope: str) -> Dict[str, Json]:
    """List every regular Markdown candidate recursively without writing."""
    directory = path_in(root, scope)
    if not directory.is_dir():
        raise Refused("Inbox scope must be an existing directory")
    entries = []
    errors = []
    def walk_error(error: OSError) -> None:
        errors.append({"path": str(Path(error.filename).relative_to(root)), "reason": error.strerror})

    for current, directories, files in os.walk(directory, followlinks=False, onerror=walk_error):
        directories[:] = sorted(name for name in directories if not (Path(current) / name).is_symlink())
        for filename in sorted(files):
            path = Path(current) / filename
            if path.suffix != ".md":
                continue
            name = path.relative_to(root).as_posix()
            try:
                entries.append(read_candidate(root, name))
            except (Refused, OSError, UnicodeError) as exc:
                errors.append({"path": name, "reason": str(exc)})
    statuses: Dict[str, Json] = {}
    for entry in entries:
        status = str(entry["status"])
        statuses[status] = statuses.get(status, 0) + 1
    return {"status": "partial" if errors else "observed", "scope": scope,
            "count": len(entries), "statuses": statuses, "candidates": entries,
            "errors": errors, "mutations_performed": []}


def selected(root: Path, scope: str, request: Dict[str, Json]) -> List[Dict[str, Json]]:
    """Resolve only explicitly chosen files, binding each to its preview digest."""
    directory = path_in(root, scope)
    names = request.get("selected_paths")
    preimages = request.get("selected_preimages")
    if not isinstance(names, list) or not names or not isinstance(preimages, dict):
        raise Refused("select explicit candidates with selected_preimages")
    result = []
    for name in dict.fromkeys(names):
        path = path_in(root, name)
        try:
            path.relative_to(directory)
        except ValueError as exc:
            raise Refused("selected candidate is outside the Inbox scope") from exc
        candidate = read_candidate(root, name)
        if preimages.get(name) != "sha256:" + candidate["sha256"]:
            raise Refused("selected candidate changed since preview")
        result.append(candidate)
    return result


def handoff(root: Path, scope: str, request: Dict[str, Json]) -> Dict[str, Json]:
    """Prepare one purpose-bearing batch; source groups retain all selected spans."""
    candidates = selected(root, scope, request)
    purpose = request.get("purpose", "")
    origin = request.get("purpose_origin", "unknown")
    if not isinstance(purpose, str) or origin not in ("stated", "reused", "unknown"):
        raise Refused("invalid common purpose")
    if origin != "unknown" and not purpose.strip():
        raise Refused("stated or reused purpose must not be empty")
    if origin == "unknown" and purpose:
        raise Refused("unknown purpose must be empty")
    groups = []
    # Union overlapping proven identities/locators, never titles or folders.
    for candidate in candidates:
        for index, source in enumerate(candidate["sources"]):
            identity = source.get("source_identity", "")
            locator = source["source_locator"]
            matches = [group for group in groups
                       if (identity and identity in group["identities"]) or locator in group["locators"]]
            group = matches[0] if matches else {"identities": [], "locators": [], "members": []}
            if not matches:
                groups.append(group)
            for other in matches[1:]:
                group["identities"] += other["identities"]
                group["locators"] += other["locators"]
                group["members"] += other["members"]
                groups.remove(other)
            if identity and identity not in group["identities"]:
                group["identities"].append(identity)
            if locator not in group["locators"]:
                group["locators"].append(locator)
            member = {"candidate_path": candidate["path"], "candidate_index": index, "source": source}
            if member not in group["members"]:
                group["members"].append(member)
    return {"schema": "inbox/handoff@1", "status": "ready-for-ingest",
            "consumer": "ingest", "scope": scope,
            "selected_paths": [item["path"] for item in candidates],
            "selected_preimages": {item["path"]: "sha256:" + item["sha256"] for item in candidates},
            "purpose": purpose, "purpose_origin": origin,
            "source_groups": groups,
            "unclassified_paths": [item["path"] for item in candidates if not item["sources"]],
            "mutations_performed": []}


def delete(root: Path, scope: str, request: Dict[str, Json]) -> Dict[str, Json]:
    """Delete only separately approved, still-matching candidate bytes."""
    candidates = selected(root, scope, request)
    if (
        request.get("approval_state") not in ("approved", "partially-approved")
        or request.get("approval_effect") != ["delete"]
        or not isinstance(request.get("approval_basis"), str)
        or not request["approval_basis"].strip()
        or set(request.get("approval_scope", [])) != {item["path"] for item in candidates}
        or request.get("approval_preimage") != request["selected_preimages"]
    ):
        raise Refused("deletion needs separate exact delete approval")
    removed = []
    # Preflight all before effects, and recheck immediately before each unlink.
    try:
        for candidate in candidates:
            current = read_candidate(root, candidate["path"])
            if current["sha256"] != candidate["sha256"]:
                raise Refused("candidate changed before deletion")
            path_in(root, candidate["path"]).unlink()
            removed.append(candidate["path"])
    except (Refused, OSError) as exc:
        raise Refused("partial deletion; removed_paths=" + json.dumps(removed) + "; " + str(exc)) from exc
    return {"status": "deleted", "deleted_paths": removed, "mutations_performed": removed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "count", "status", "preview", "handoff", "delete"))
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--request", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.vault.resolve(strict=True)
        if args.command in ("list", "count", "status"):
            result = listing(root, args.scope)
            if args.command != "list":
                result.pop("candidates")
        elif args.command == "preview":
            if not args.candidate:
                raise Refused("preview requires --candidate")
            candidate = path_in(root, args.candidate)
            candidate.relative_to(path_in(root, args.scope))
            result = read_candidate(root, args.candidate)
        else:
            if args.request is None:
                raise Refused("handoff/delete requires --request")
            if not args.request.is_file():
                raise Refused("request must be a regular JSON file")
            request = json.loads(args.request.read_text(encoding="utf-8"))
            if not isinstance(request, dict):
                raise Refused("request must be an object")
            result = {"handoff": handoff, "delete": delete}[args.command](root, args.scope, request)
    except (Refused, OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
