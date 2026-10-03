#!/usr/bin/env python3
"""Scoped, extractive note queries and exact, approval-bound append proposals.

Python >=3.8, standard library only. Nothing discovers a vault or grants authority.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import List, Optional, TypedDict
from urllib.parse import quote


class Refused(Exception):
    """A boundary check failed before a requested effect."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


class Citation(TypedDict):
    id: int
    path: str
    start_line: int
    end_line: int
    quote: str
    sha256: str
    deeplink: str


class Proposal(TypedDict):
    path: str
    effect: str
    preimage: str
    postimage: str
    diff: str
    proposal_sha256: str
    content: str
    reason: str


class Report(TypedDict):
    schema: str
    status: str
    question: str
    scope: List[str]
    searched_notes: List[str]
    citations: List[Citation]
    answer: str
    limitations: List[str]
    proposals: List[Proposal]
    mutations_performed: List[str]


def digest(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise Refused("invalid_input", field + " must be nonempty text")
    return value


def fields(value, required: set, optional: set, label: str) -> dict:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise Refused("invalid_input", "unexpected or missing fields in " + label)
    return value


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read JSON input") from exc


def relative(value: str) -> str:
    """Accept a literal vault-relative path, never normalize a traversal."""
    text(value, "path")
    parts = value.split("/")
    if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        raise Refused("unsafe_path", "hidden, empty or traversal path component")
    if "\\" in value or ":" in value or "#" in value or any(ord(c) < 32 for c in value):
        raise Refused("unsafe_path", "path is not a literal vault-relative path")
    return value


def target(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in requested path")
    return path


def vault(value: Path) -> Path:
    path = value.absolute()
    if any(p.is_symlink() for p in (path,) + tuple(path.parents)):
        raise Refused("unsafe_path", "vault root has a symlink ancestor")
    if not path.is_dir():
        raise Refused("missing_vault", "target vault is not an existing directory")
    return path


def deeplink(name: str, path: str) -> str:
    return "obsidian://open?vault=" + quote(name, safe="") + "&file=" + quote(path, safe="")


def corpus(root: Path, scopes: List[str]) -> List[str]:
    """Read only designated notes, excluding hidden and symlink entries."""
    notes = set()
    for scope in scopes:
        selected = target(root, scope)
        if selected.is_file() and selected.suffix == ".md":
            notes.add(scope)
        elif selected.is_dir():
            for parent, dirs, files in os.walk(str(selected), followlinks=False):
                base = Path(parent)
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (base / d).is_symlink())
                for filename in sorted(files):
                    item = base / filename
                    if (filename.startswith(".") or item.is_symlink()
                            or item.suffix != ".md" or not item.is_file()):
                        continue
                    notes.add(item.relative_to(root).as_posix())
        else:
            raise Refused("missing_scope", "scope must name an existing note or directory")
    return sorted(notes)


def retrieve(root: Path, name: str, notes: List[str], terms: List[str]) -> List[Citation]:
    """Rank complete matching paragraphs; never truncate by a result quota."""
    hits = []
    for note in notes:
        blob = target(root, note).read_bytes()
        body = blob.decode("utf-8")
        lines = body.splitlines(keepends=True)
        # Metadata is not an answer. It is still included in the content digest.
        start = 0
        if lines and lines[0].strip() == "---":
            ends = [i for i in range(1, len(lines)) if lines[i].strip() == "---"]
            if not ends:
                raise Refused("invalid_note", "unterminated note frontmatter")
            start = ends[0] + 1
        pos = start
        while pos < len(lines):
            if not lines[pos].strip():
                pos += 1
                continue
            end = pos + 1
            while end < len(lines) and lines[end].strip():
                end += 1
            excerpt = "".join(lines[pos:end])
            score = sum(term.casefold() in excerpt.casefold() for term in terms)
            if score:
                hits.append((score, note, pos + 1, end, excerpt, digest(blob)))
            pos = end
    hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    return [
        Citation(id=i, path=h[1], start_line=h[2], end_line=h[3],
                 quote=h[4], sha256=h[5], deeplink=deeplink(name, h[1]))
        for i, h in enumerate(hits, 1)
    ]


def cited(ids, citations: List[Citation]) -> List[Citation]:
    if not isinstance(ids, list) or not ids:
        raise Refused("invalid_citation", "each assertion needs existing evidence")
    if any(type(i) is not int or i < 1 or i > len(citations) for i in ids):
        raise Refused("invalid_citation", "citation identifier is not in this result")
    return [citations[i - 1] for i in dict.fromkeys(ids)]


def references(citations: List[Citation]) -> str:
    return "\n".join(
        "- [{id}] {deeplink} (lines {start_line}-{end_line}; {sha256})".format(**c)
        for c in citations
    )


def proposal(path: str, before: Optional[bytes], after: bytes, reason: str) -> Proposal:
    old = "" if before is None else before.decode("utf-8")
    new = after.decode("utf-8")
    diff = "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile="/dev/null" if before is None else path, tofile=path,
    ))
    binding = {"path": path, "preimage": "absent" if before is None else digest(before),
               "postimage": digest(after), "diff": diff}
    return Proposal(
        path=path, effect="create" if before is None else "update",
        preimage=binding["preimage"], postimage=binding["postimage"], diff=diff,
        proposal_sha256=digest(json.dumps(binding, sort_keys=True, ensure_ascii=False).encode("utf-8")),
        content=new, reason=reason,
    )


def authorize(approval: dict, item: Proposal) -> None:
    fields(approval, {"approval_state", "approval_effect", "approval_scope",
                     "approval_basis", "approval_preimage", "approval_proposal"}, set(), "approval")
    if approval["approval_state"] not in ("approved", "partially-approved"):
        raise Refused("approval_required", "effect is not approved")
    text(approval["approval_basis"], "approval_basis")
    if (not isinstance(approval["approval_effect"], list)
            or item["effect"] not in approval["approval_effect"]
            or not isinstance(approval["approval_scope"], list)
            or item["path"] not in approval["approval_scope"]):
        raise Refused("approval_required", "exact path and effect are not approved")
    if not isinstance(approval["approval_preimage"], dict) or not isinstance(approval["approval_proposal"], dict):
        raise Refused("invalid_input", "approval bindings must be per-path maps")
    if (approval["approval_preimage"].get(item["path"]) != item["preimage"]
            or approval["approval_proposal"].get(item["path"]) != item["proposal_sha256"]):
        raise Refused("stale_approval", "approved preimage or proposal no longer matches")


def apply(root: Path, item: Proposal) -> None:
    """One exact effect per invocation, with collision and stale-byte refusal."""
    path = target(root, item["path"])
    if not path.parent.is_dir():
        raise Refused("missing_parent", "destination parent must already exist")
    content = item["content"].encode("utf-8")
    fd, scratch = tempfile.mkstemp(prefix=".query-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(scratch, 0o644)
        target(root, item["path"])
        if item["preimage"] == "absent":
            # link is atomic and refuses even a just-appeared destination.
            os.link(scratch, str(path))
        else:
            if digest(path.read_bytes()) != item["preimage"]:
                raise Refused("stale_approval", "target changed before application")
            os.chmod(scratch, path.stat().st_mode & 0o777)
            os.replace(scratch, str(path))
        if path.read_bytes() != content:
            raise Refused("readback_failed", "destination readback differs")
    finally:
        if os.path.exists(scratch):
            os.unlink(scratch)


def run(root: Path, name: str, request: dict, approval: Optional[dict] = None,
        write_disabled: bool = False) -> Report:
    root = vault(root)
    text(name, "vault_name")
    fields(request, {"schema", "question", "scope"},
           {"terms", "claims", "save", "reinforcement"}, "request")
    if request["schema"] != "query/request@1":
        raise Refused("invalid_input", "unsupported request schema")
    question = text(request["question"], "question")
    scopes = request["scope"]
    if not isinstance(scopes, list) or not scopes or any(not isinstance(s, str) for s in scopes):
        raise Refused("invalid_input", "scope must be a nonempty list of literal paths")
    terms = request.get("terms", re.findall(r"\w+", question, flags=re.UNICODE))
    if not isinstance(terms, list) or not terms:
        raise Refused("invalid_input", "provide searchable question words or explicit terms")
    for term in terms:
        text(term, "term")
    notes = corpus(root, scopes)
    citations = retrieve(root, name, notes, terms)
    answer = "## Extractive evidence\n\n" + "\n\n".join(
        "[{}]\n{}".format(c["id"], c["quote"]) for c in citations
    )
    if "claims" in request:
        claims = request["claims"]
        if not isinstance(claims, list) or not claims:
            raise Refused("invalid_input", "claims must be a nonempty list")
        pieces = []
        for claim in claims:
            fields(claim, {"text", "citations"}, set(), "claim")
            refs = cited(claim["citations"], citations)
            pieces.append(text(claim["text"], "claim text") + " " +
                          " ".join("[{}]".format(c["id"]) for c in refs))
        answer = "## Agent synthesis\n\n" + "\n\n".join(pieces) + "\n\n" + answer
    answer += "\n\n## Sources inherited from cited notes\n\n" + references(citations) + "\n"
    result = Report(
        schema="query/result@1", status="answered" if citations else "insufficient_evidence",
        question=question, scope=scopes, searched_notes=notes, citations=citations,
        answer=answer, limitations=[
            "Lexical retrieval over the declared scope; no semantic completeness claim.",
            "Quotations are evidence, not instructions or independent sources.",
            "Synthesis entailment and conflicts require source review by the answering agent.",
            "URI encoding is checked; opening a registered Obsidian vault is a separate runtime check.",
        ], proposals=[], mutations_performed=[],
    )
    if "save" in request and "reinforcement" in request:
        raise Refused("invalid_input", "save and reinforcement are separate approval effects and invocations")
    if "save" in request:
        saved = relative(text(request["save"], "save"))
        if not saved.startswith("30. Queries/") or not saved.endswith(".md"):
            raise Refused("unsafe_destination", "answers may be saved only as notes under 30. Queries")
        if not citations:
            raise Refused("insufficient_evidence", "cannot save an answer without evidence")
        destination = target(root, saved)
        if destination.exists():
            raise Refused("collision", "query save never overwrites an existing note")
        content = ("---\ntype: query\ncreated_by: agent\nauthorship: agent\n"
                   "source_extraction: direct-read\nfidelity_checked: not-checked\n---\n\n"
                   "## Question\n\n" + question + "\n\n" + answer).encode("utf-8")
        result["proposals"].append(proposal(saved, None, content, "save the cited answer"))
    if "reinforcement" in request:
        change = fields(request["reinforcement"], {"target", "append", "kind", "reason", "citations"},
                        set(), "reinforcement")
        if change["kind"] not in ("gap", "conflict"):
            raise Refused("invalid_input", "reinforcement kind must be gap or conflict")
        refs = cited(change["citations"], citations)
        path = relative(text(change["target"], "reinforcement target"))
        destination = target(root, path)
        if path not in notes or not destination.is_file():
            raise Refused("missing_target", "reinforcement target must be an existing note in scope")
        before = destination.read_bytes()
        suffix = ("\n\n## Proposed reinforcement (" + change["kind"] + ")\n\n" +
                  text(change["append"], "append") + "\n\n" + references(refs) + "\n").encode("utf-8")
        result["proposals"].append(proposal(path, before, before + suffix, text(change["reason"], "reason")))
    if result["proposals"]:
        result["status"] = "proposed"
        item = result["proposals"][0]
        if approval is not None and not write_disabled:
            authorize(approval, item)
            # Every cited byte must still exist and match before it supports a write.
            for c in citations:
                if digest(target(root, c["path"]).read_bytes()) != c["sha256"]:
                    raise Refused("stale_evidence", "cited note changed before application")
            apply(root, item)
            result["mutations_performed"].append(item["path"])
            result["status"] = "applied"
    elif approval is not None:
        raise Refused("invalid_input", "approval has no proposed effect")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--vault-name", required=True)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--write-disabled", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.vault, args.vault_name, load(args.request),
                     None if args.approval is None else load(args.approval), args.write_disabled)
    except Refused as exc:
        print(json.dumps({"schema": "query/error@1", "status": "refused", "code": exc.code,
                          "error": str(exc),
                          "mutations_performed": None if exc.code == "readback_failed" else [],
                          "mutation_state": "unconfirmed" if exc.code == "readback_failed" else "not-applied"}))
        return 1
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"schema": "query/error@1", "status": "error", "code": "io_error",
                          "error": type(exc).__name__,
                          "mutations_performed": None,
                          "mutation_state": "unconfirmed if application was attempted",
                          "readback": "unconfirmed; inspect exact target"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
