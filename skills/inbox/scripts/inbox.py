#!/usr/bin/env python3
"""List Inbox candidates, emit one inbox/handoff@1 batch, delete only after 5-C.

Python >=3.8, stdlib only. Location is the processing state: there is no queue
status. list/preview/handoff never write; delete unlinks only separately approved
originals whose ingest session state proves the Raw preserved them (5-C).
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re

LANE = re.compile(r"^\d\d \S")


class Refused(Exception):
    """The requested selection or effect is outside its declared boundary."""


def sha(blob):
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def path_in(root, name):
    """Resolve a vault-relative path, refusing traversal and every symlink component."""
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        raise Refused("invalid relative path")
    if any(part in ("", "..", ".") for part in name.split("/")):
        raise Refused("path leaves the declared vault")
    current = root
    for part in name.split("/"):
        current = current / part
        if current.is_symlink():
            raise Refused("symlink path is not an Inbox candidate")
    return current


def within(root, scope, name):
    path = path_in(root, name)
    if not name.startswith(scope.rstrip("/") + "/"):
        raise Refused("path is outside the Inbox scope: " + name)
    return path


def frontmatter(content):
    if not content.startswith("---\n"):
        return {}
    header, separator, _body = content[4:].partition("\n---\n")
    if not separator:
        raise Refused("unterminated candidate frontmatter")
    fields = {}
    for line in header.splitlines():
        key, separator, value = line.partition(": ")
        if separator and not line.startswith((" ", "-")):
            if key in fields:
                raise Refused("duplicate candidate frontmatter key")
            try:
                fields[key] = json.loads(value)
            except ValueError:
                fields[key] = value  # other YAML scalars stay literal text
    return fields


def read_candidate(root, scope, name):
    path = within(root, scope, name)
    if not path.is_file():
        raise Refused("candidate must be a regular Markdown file")
    blob = path.read_bytes()
    content = blob.decode("utf-8")
    fields = frontmatter(content)
    sources = []
    if fields.get("capture_schema") == "capture/candidate@1":
        sources = fields.get("capture_sources")
        if not isinstance(sources, list) or not sources:
            raise Refused("capture candidate has no source records")
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("original_content"), str):
                raise Refused("invalid capture source")
            fidelity = source.get("fidelity")
            if fidelity not in ("full", "partial", "excerpt", "manifest-only"):
                raise Refused("invalid capture fidelity")
            if (fidelity == "manifest-only") == bool(source["original_content"]):
                raise Refused("fidelity contradicts original text presence")
            if not isinstance(source.get("source_locator"), str) or not source["source_locator"]:
                raise Refused("capture source has no locator")
            if not isinstance(source.get("source_identity", ""), str):
                raise Refused("invalid source identity")
        actual = sources[0]["fidelity"] if len(sources) == 1 else "mixed"
        if fields.get("fidelity") != actual:
            raise Refused("candidate fidelity contradicts its source records")
    parts = name[len(scope) + 1:].split("/")
    return {"path": name, "sha256": sha(blob), "lane": parts[0] if len(parts) > 1 and LANE.match(parts[0]) else None,
            "type": fields.get("type"), "session_id": fields.get("session_id"),
            "fidelity": fields.get("fidelity", "unknown"), "sources": sources,
            "preview": sources or content}


def listing(root, scope):
    directory = path_in(root, scope)
    if not directory.is_dir():
        raise Refused("Inbox scope must be an existing directory")
    entries, errors = [], []

    def walk_error(error):
        errors.append({"path": Path(error.filename).relative_to(root).as_posix(), "reason": error.strerror})

    for current, directories, files in os.walk(directory, followlinks=False, onerror=walk_error):
        directories[:] = sorted(d for d in directories if not (Path(current) / d).is_symlink())
        for filename in sorted(files):
            if filename.endswith(".md"):
                name = (Path(current) / filename).relative_to(root).as_posix()
                try:
                    entries.append(read_candidate(root, scope, name))
                except (Refused, OSError, UnicodeError) as exc:
                    errors.append({"path": name, "reason": str(exc)})
    return {"scope": scope, "complete": not errors, "count": len(entries),
            "candidates": entries, "errors": errors, "mutations_performed": []}


def selected(root, scope, request):
    names, preimages = request.get("selected_paths"), request.get("selected_preimages")
    if not isinstance(names, list) or not names or not isinstance(preimages, dict):
        raise Refused("select explicit candidates with selected_preimages")
    result = []
    for name in dict.fromkeys(names):
        candidate = read_candidate(root, scope, name)
        if preimages.get(name) != candidate["sha256"]:
            raise Refused("selected candidate changed since preview: " + name)
        result.append(candidate)
    return result


def handoff(root, scope, request):
    """One purpose-bearing batch; groups join proven identity/locator, never titles."""
    candidates = selected(root, scope, request)
    purpose, origin = request.get("purpose", ""), request.get("purpose_origin", "unknown")
    if not isinstance(purpose, str) or origin not in ("stated", "reused", "unknown"):
        raise Refused("invalid common purpose")
    if (origin == "unknown") == bool(purpose.strip()) or (origin == "unknown" and purpose):
        raise Refused("purpose must be empty exactly when its origin is unknown")
    groups = []
    for candidate in candidates:
        for index, source in enumerate(candidate["sources"]):
            identity, locator = source.get("source_identity", ""), source["source_locator"]
            matches = [g for g in groups if (identity and identity in g["identities"]) or locator in g["locators"]]
            group = matches[0] if matches else {"identities": [], "locators": [], "members": []}
            if not matches:
                groups.append(group)
            for other in matches[1:]:
                for key in group:
                    group[key] += other[key]
                groups.remove(other)
            if identity and identity not in group["identities"]:
                group["identities"].append(identity)
            if locator not in group["locators"]:
                group["locators"].append(locator)
            group["members"].append({"candidate_path": candidate["path"], "candidate_index": index, "source": source})
    return {"schema": "inbox/handoff@1", "consumer": "ingest", "scope": scope,
            "selected_paths": [c["path"] for c in candidates],
            "selected_preimages": {c["path"]: c["sha256"] for c in candidates},
            "lanes": {c["path"]: c["lane"] for c in candidates},
            "purpose": purpose, "purpose_origin": origin, "source_groups": groups,
            "unclassified_paths": [c["path"] for c in candidates if not c["sources"]],
            "mutations_performed": []}


def decode(value):
    """Inverse of ingest's session-state encoding ({"bytes_base64": ...} leaves)."""
    if isinstance(value, dict):
        if set(value) == {"bytes_base64"}:
            return base64.b64decode(value["bytes_base64"], validate=True)
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def read_or_none(path):
    return path.read_bytes() if path.is_file() else None


def predicate_5c(root, scope, name, session):
    """5-C: fresh original, exact Original Content span, independent Raw postimage."""
    approved = session["inputs"].get(name)
    captures = [c for c in session["captures"] if c.get("input") == name]
    if not isinstance(approved, bytes) or not captures:
        raise Refused("no ingest capture of this Inbox original: " + name)
    if read_or_none(within(root, scope, name)) != approved:
        raise Refused("stale original: current bytes differ from approved Inbox input: " + name)
    for capture in captures:
        start, end = capture["extent"]
        expected = next((r["after"] for r in session["changes"] if r["path"] == capture["path"]), None)
        if not isinstance(expected, bytes) or expected[start:end] != capture["selected"]:
            raise Refused("session expected postimage does not hold the selected span: " + capture["path"])
        raw = read_or_none(path_in(root, capture["path"]))
        if raw is None or raw[start:end] != capture["selected"]:
            raise Refused("Raw Original Content span mismatch: " + capture["path"])
        if raw != expected:
            raise Refused("Raw postimage mismatch: " + capture["path"])


def delete(root, scope, request, session):
    """Unlink separately approved originals; preflight all, recheck 5-C before each unlink."""
    names = request.get("approval_scope")
    preimages = request.get("approval_preimage")
    if (request.get("approval_state") not in ("approved", "partially-approved")
            or request.get("approval_effect") != ["delete"]
            or not isinstance(request.get("approval_basis"), str) or not request["approval_basis"].strip()
            or not isinstance(names, list) or not names or not isinstance(preimages, dict)
            or set(preimages) != set(names)):
        raise Refused("deletion needs a separate exact-path delete approval")
    if session.get("vault") != str(root):
        raise Refused("ingest session belongs to another vault")
    for name in names:
        if preimages[name] != sha(session["inputs"].get(name, b"")):
            raise Refused("delete approval is not bound to the ingested input bytes: " + name)
        predicate_5c(root, scope, name, session)
    removed = []
    try:
        for name in names:
            predicate_5c(root, scope, name, session)
            within(root, scope, name).unlink()
            removed.append(name)
    except (Refused, OSError) as exc:
        raise Refused("partial deletion; removed_paths=" + json.dumps(removed) + "; " + str(exc)) from exc
    return {"deleted_paths": removed, "mutations_performed": removed}


def load(path, root, what):
    if path is None or path.is_symlink() or not path.is_file():
        raise Refused(what + " must be a regular JSON file")
    if root in path.resolve().parents:
        raise Refused(what + " must live outside the vault")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Refused(what + " must be an object")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "preview", "handoff", "delete"))
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--scope", required=True, help="vault-relative Inbox, e.g. '00. Inbox'")
    parser.add_argument("--candidate")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--ingest-state", type=Path, help="delete: ingest session state of the run that wrote the Raw")
    args = parser.parse_args(argv)
    try:
        root = args.vault.resolve(strict=True)
        scope = args.scope.rstrip("/")
        path_in(root, scope)
        if args.command == "list":
            result = listing(root, scope)
        elif args.command == "preview":
            result = read_candidate(root, scope, args.candidate or "")
        elif args.command == "handoff":
            result = handoff(root, scope, load(args.request, root, "request"))
        else:
            session = decode(load(args.ingest_state, root, "ingest state"))
            result = delete(root, scope, load(args.request, root, "request"), session)
    except (Refused, OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"refused": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
