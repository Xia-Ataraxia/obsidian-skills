#!/usr/bin/env python3
"""Capture explicitly selected material as a new Markdown Inbox candidate.

Python >=3.8, standard library only. No network or runtime session discovery.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Union
from urllib.parse import urlsplit

Json = Union[None, bool, int, str, List["Json"], Dict[str, "Json"]]


class Refused(Exception):
    """An input, selection, or approval does not permit this capture."""


def relative_path(root: Path, value: str) -> Path:
    """Resolve an exact relative path without traversing symlinks."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise Refused("path must be a nonempty vault-relative path")
    path = Path(value)
    if path.is_absolute() or any(part in ("..", ".") for part in value.split("/")):
        raise Refused("path leaves the declared base")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise Refused("symlink routes are not selected source paths")
    return current


def text(value: Json, field: str, empty: bool = False) -> str:
    """Parse a scalar without interpreting content as instructions."""
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise Refused("invalid " + field)
    return value


def locator(value: Json) -> str:
    """Accept public URLs, stable identifiers, or relative source paths."""
    result = text(value, "source_locator")
    parsed = urlsplit(result)
    if parsed.scheme in ("http", "https"):
        if not parsed.netloc or parsed.username or parsed.password or parsed.query:
            raise Refused("source URL must be canonical, with a host and no credentials/query")
    elif parsed.scheme:
        if parsed.scheme not in ("urn", "doi"):
            raise Refused("source locator scheme is not supported")
    elif result.startswith("~") or Path(result).is_absolute() or ".." in Path(result).parts or "\\" in result:
        raise Refused("source locator must not contain a host path")
    return result


def obtain(root: Path, source: Dict[str, Json]) -> Dict[str, Json]:
    """Obtain only the designated export or extraction; retain missing ranges."""
    result: Dict[str, Json] = {}
    choices = {
        "source_input": ("tabs", "url", "file", "text", "session", "candidate"),
        "source_kind": ("article", "video", "repository", "mail", "conversation", "book", "paper", "other"),
        "source_extraction": ("browser", "reader", "transcript", "document-conversion", "runtime-query", "direct-read", "none"),
        "mode": ("transcript", "manifest-only", "excerpt"),
    }
    for key, allowed in choices.items():
        if source.get(key) not in allowed:
            raise Refused("invalid " + key)
        result[key] = source[key]
    result["source_locator"] = locator(source.get("source_locator"))
    identity = text(source.get("source_identity", ""), "source_identity", empty=True)
    if identity:
        # Digests are identities, not locations.
        if identity.startswith("sha256:"):
            digest = identity[7:]
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise Refused("invalid SHA-256 source identity")
        else:
            locator(identity)
    result["source_identity"] = identity
    obtained_at = text(source.get("source_obtained_at"), "source_obtained_at")
    try:
        datetime.fromisoformat(obtained_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refused("source_obtained_at must be ISO 8601") from exc
    result["source_obtained_at"] = obtained_at
    omissions = source.get("fidelity_omissions", [])
    if not isinstance(omissions, list) or any(not isinstance(item, str) for item in omissions):
        raise Refused("fidelity_omissions must be a list of statements")
    omissions = list(omissions)
    conversion = source.get("fidelity_conversion", [])
    if not isinstance(conversion, list) or any(
        not isinstance(item, dict) or set(item) != {"tool", "from", "to"}
        or any(not isinstance(value, str) for value in item.values())
        for item in conversion
    ):
        raise Refused("invalid fidelity_conversion")
    result["fidelity_conversion"] = conversion
    # An extraction report is not a comparison performed by this program.
    result["fidelity_checked"] = "not-checked"
    content = ""
    if source["mode"] == "manifest-only":
        if source.get("content") or source.get("content_file") or source.get("span"):
            raise Refused("manifest-only capture cannot carry obtained text")
        omissions.append("Original content not obtained; source manifest only.")
    else:
        if ("content" in source) == ("content_file" in source):
            raise Refused("select exactly one content or content_file")
        if "content_file" in source:
            path = relative_path(root, text(source["content_file"], "content_file"))
            try:
                if not path.is_file():
                    raise OSError("selected content is not a regular file")
                content = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeError):
                omissions.append("Selected content file is inaccessible or not UTF-8.")
        else:
            content = text(source["content"], "content", empty=True)
        span = source.get("span")
        if span is not None:
            if not isinstance(span, dict) or set(span) != {"start", "end"}:
                raise Refused("span requires inclusive start and end line numbers")
            start, end = span["start"], span["end"]
            if type(start) is not int or type(end) is not int or start < 1 or end < start:
                raise Refused("invalid span")
            lines = content.splitlines(keepends=True)
            if end > len(lines):
                omissions.append("Selected span extends beyond the available original.")
            content = "".join(lines[start - 1:end])
            result["selected_span"] = span
        if not content:
            omissions.append("No original text was obtained for the selected scope.")
    result["fidelity"] = (
        "manifest-only" if not content else
        "excerpt" if source["mode"] == "excerpt" else
        "partial" if omissions else "full"
    )
    result["fidelity_omissions"] = omissions
    result["original_content"] = content
    return result


def capture(root: Path, request: Dict[str, Json]) -> Dict[str, Json]:
    """Create one exact approved candidate, refusing replacement of any file."""
    candidate = text(request.get("candidate_path"), "candidate_path")
    destination = relative_path(root, candidate)
    if destination.suffix != ".md":
        raise Refused("candidate_path must name a Markdown file")
    effects = request.get("approval_effect")
    scope = request.get("approval_scope")
    preimages = request.get("approval_preimage")
    if (
        request.get("approval_state") not in ("approved", "partially-approved")
        or not isinstance(effects, list) or "create" not in effects
        or not isinstance(scope, list) or candidate not in scope
        or not isinstance(preimages, dict) or preimages.get(candidate) != "absent"
    ):
        raise Refused("candidate creation requires exact create approval and absent preimage")
    basis = text(request.get("approval_basis"), "approval_basis")
    sources = request.get("sources")
    if not isinstance(sources, list) or not sources or any(not isinstance(item, dict) for item in sources):
        raise Refused("sources must explicitly select at least one source")
    obtained = [obtain(root, source) for source in sources]
    purpose = text(request.get("purpose", ""), "purpose", empty=True)
    origin = request.get("purpose_origin", "unknown")
    if origin not in ("stated", "reused", "unknown") or (origin != "unknown" and not purpose.strip()):
        raise Refused("invalid purpose_origin")
    if origin == "unknown" and purpose:
        raise Refused("unknown purpose must be empty")
    title = text(request.get("title"), "title")
    notes = text(request.get("agent_capture_notes", ""), "agent_capture_notes", empty=True)
    fields: Dict[str, Json] = {
        "capture_schema": "capture/candidate@1", "title": title,
        "purpose": purpose, "purpose_origin": origin,
        "approval_state": request["approval_state"],
        "approval_effect": request["approval_effect"],
        "approval_scope": request["approval_scope"],
        "approval_basis": basis, "approval_preimage": request["approval_preimage"],
        "fidelity": obtained[0]["fidelity"] if len(obtained) == 1 else "mixed",
        "fidelity_omissions": [item for source in obtained for item in source["fidelity_omissions"]],
        "fidelity_conversion": [item for source in obtained for item in source["fidelity_conversion"]],
        "fidelity_checked": "not-checked",
        "capture_sources": obtained,
    }
    for key in ("source_input", "source_kind", "source_extraction", "source_locator", "source_identity", "source_obtained_at"):
        fields[key] = obtained[0][key]
    # JSON scalars/arrays are YAML-compatible; no YAML dependency is required.
    header = "\n".join(key + ": " + json.dumps(value, ensure_ascii=False) for key, value in fields.items())
    sections = []
    for index, source in enumerate(obtained, 1):
        sections.append("### Source " + str(index) + "\n\n" + str(source["original_content"]))
    body = "---\n" + header + "\n---\n\n# " + title.replace("\n", " ") + "\n\n## Original Content\n\n"
    body += "\n\n".join(sections) + "\n\n## Agent Capture Notes\n\n" + notes + "\n"
    if destination.exists():
        raise Refused("candidate already exists; create approval cannot overwrite it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Link a complete staged file exclusively: interruption never exposes a
    # half-written candidate and a competing writer is not overwritten.
    handle, staged = tempfile.mkstemp(dir=str(destination.parent), prefix=".capture-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(body)
        os.link(staged, destination)
    finally:
        os.unlink(staged)
    blob = destination.read_bytes()
    return {"status": "captured", "candidate_path": candidate,
            "fidelity": fields["fidelity"], "fidelity_omissions": fields["fidelity_omissions"],
            "sha256": hashlib.sha256(blob).hexdigest(), "evidence_level": "materialized"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if not args.request.is_file():
            raise Refused("request must be a regular JSON file")
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise Refused("request must be an object")
        root = args.vault.resolve(strict=True)
        if not root.is_dir():
            raise Refused("vault must be an existing directory")
        result = capture(root, request)
    except (Refused, OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
