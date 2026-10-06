"""Claim-range verification workflow over already selected evidence."""
from pathlib import Path
from typing import List, Optional

from verify_io import (
    Refused,
    authorize,
    digest,
    exact_fields,
    proposal,
    publish,
    relative,
    target,
    text,
)


def anchor(root: Path, entry: dict, manifest: List[str]) -> dict:
    exact_fields(entry, {"path", "start_line", "end_line"}, set(), "evidence")
    path = relative(text(entry["path"], "evidence path"))
    if path not in manifest:
        raise Refused("manifest_required", "evidence path is not in the manifest")
    start, end = entry["start_line"], entry["end_line"]
    if type(start) is not int or type(end) is not int or start < 1 or end < start:
        raise Refused("invalid_range", "line range is invalid")
    blob = target(root, path).read_bytes()
    lines = blob.decode("utf-8").splitlines(keepends=True)
    if end > len(lines):
        raise Refused("invalid_range", "line range exceeds the selected note")
    return {
        "path": path,
        "start_line": start,
        "end_line": end,
        "quote": "".join(lines[start - 1:end]),
        "sha256": digest(blob),
    }


def review_claim(root: Path, page: str, manifest: List[str], claim: dict, seen: set) -> dict:
    exact_fields(
        claim,
        {
            "id",
            "start_line",
            "end_line",
            "reviewed",
            "verdict",
            "counterpart",
            "evidence",
            "new_evidence",
        },
        set(),
        "claim",
    )
    identifier = text(claim["id"], "claim id")
    if identifier in seen:
        raise Refused("invalid_input", "claim identifiers must be unique")
    seen.add(identifier)
    claim_anchor = anchor(
        root,
        {"path": page, "start_line": claim["start_line"], "end_line": claim["end_line"]},
        manifest,
    )
    counterpart = text(claim["counterpart"], "counterpart", empty=True)
    evidence = claim["evidence"]
    new_evidence = claim["new_evidence"]
    if not isinstance(evidence, list) or not isinstance(new_evidence, list):
        raise Refused("invalid_input", "evidence fields must be lists")
    if claim["reviewed"] is False:
        if claim["verdict"] != "unverified" or counterpart or evidence or new_evidence:
            raise Refused("unreviewed_scope", "unreviewed claims must stay unverified")
        checked, newly_checked = [], []
    elif claim["reviewed"] is True:
        if claim["verdict"] not in ("supported", "disputed", "resolved"):
            raise Refused("invalid_input", "reviewed claim verdict is unsupported")
        if counterpart and counterpart not in manifest:
            raise Refused("manifest_required", "counterpart is not in the manifest")
        if claim["verdict"] == "resolved" and (not counterpart or not new_evidence):
            raise Refused("new_evidence_required", "resolution needs new evidence and counterpart")
        checked = [anchor(root, item, manifest) for item in evidence]
        newly_checked = [anchor(root, item, manifest) for item in new_evidence]
    else:
        raise Refused("invalid_input", "reviewed must be boolean")
    return {
        "id": identifier,
        "status": claim["verdict"],
        "reviewed": claim["reviewed"],
        "claim": claim_anchor,
        "counterpart": counterpart,
        "evidence": checked,
        "new_evidence": newly_checked,
    }


def evidence_is_current(root: Path, result: dict) -> bool:
    if digest(target(root, result["claim"]["path"]).read_bytes()) != result["claim"]["sha256"]:
        return False
    return all(
        digest(target(root, item["path"]).read_bytes()) == item["sha256"]
        for item in result["evidence"] + result["new_evidence"]
    )


def run(
    root: Path,
    request: dict,
    approval: Optional[dict] = None,
    write_disabled: bool = False,
) -> dict:
    exact_fields(request, {"schema", "page", "manifest", "claims"}, {"record_target"}, "request")
    if request["schema"] != "verify/request@1":
        raise Refused("invalid_input", "unsupported request schema")
    page = relative(text(request["page"], "page"))
    manifest = request["manifest"]
    if (
        not isinstance(manifest, list)
        or not manifest
        or any(not isinstance(item, str) for item in manifest)
        or len(manifest) != len(set(manifest))
    ):
        raise Refused("invalid_input", "manifest must be a unique path list")
    manifest = [relative(item) for item in manifest]
    if page not in manifest:
        raise Refused("manifest_required", "reviewed page is not in the manifest")
    target(root, page)
    claims = request["claims"]
    if not isinstance(claims, list) or not claims:
        raise Refused("invalid_input", "claims must be a nonempty list")
    seen = set()
    results = [review_claim(root, page, manifest, claim, seen) for claim in claims]
    record = {
        "schema": "verify/record@1",
        "page": page,
        "manifest": manifest,
        "claims": results,
    }
    proposals = []
    if "record_target" in request:
        record_target = relative(text(request["record_target"], "record_target"))
        if record_target != page:
            raise Refused("unsafe_destination", "verification records append only to the reviewed page")
        proposals.append(proposal(page, target(root, page).read_bytes(), record))
    mutations: List[str] = []
    if approval is not None and proposals and not write_disabled:
        authorize(approval, proposals[0])
        if not all(evidence_is_current(root, result) for result in results):
            raise Refused("stale_evidence", "reviewed evidence bytes changed")
        publish(root, proposals[0])
        mutations.append(page)
    return {
        "schema": "verify/result@1",
        "status": "applied" if mutations else "reviewed",
        "page": page,
        "manifest": manifest,
        "claims": results,
        "limitations": [
            "The helper verifies selected bytes and workflow gates, not semantic entailment.",
            "Unlisted and unreviewed scope remains unverified.",
            "Counterpart pages are read-only in this invocation.",
        ],
        "proposals": proposals,
        "mutations_performed": mutations,
    }
