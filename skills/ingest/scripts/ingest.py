#!/usr/bin/env python3
"""Direct source ingestion. Python 3.8+, standard library; no capture or policy plugin.

python3 skills/ingest/scripts/ingest.py --vault V --request R.json [--apply]
"""
import argparse
import json
from pathlib import Path
from typing import Optional, Tuple
from urllib.error import URLError

from request import Request, Refused, parse
from source import Source, read_source, candidate
from storage import Plan, digest, link, metadata, target


def same_source(fields: dict, request: Request) -> bool:
    existing_identity = fields.get("source_identity")
    # Explicitly different identities must never be collapsed by a shared locator.
    if existing_identity and request.identity:
        return existing_identity == request.identity
    return fields.get("source_locator") == request.locator


def checked_quote(source: Source, quote: str, anchor: str) -> None:
    if not quote or not anchor or quote not in source.body:
        raise Refused("analysis/citation needs an obtained quote and source location")
    if source.fidelity == "manifest-only":
        raise Refused("a source list cannot support compiled claims")


def build(vault: Path, request: Request, plan: Optional[Plan] = None) -> Tuple[Plan, dict]:
    """Produce an exact plan from evidence and caller-authored grounded analysis."""
    plan = plan if plan is not None else Plan(vault, request.note_fields)
    plan.note_fields.update(request.note_fields)
    outputs = [p for p in (request.raw_path, request.wiki_path, request.attachment_path,
                           request.persona_path) if p] + [a.path for a in request.analyses]
    if len(outputs) != len(set(outputs)):
        raise Refused("overlapping output roles within one member")
    if request.purpose_origin == "unknown" and (
            request.wiki_path or request.analyses or request.persona_path):
        raise Refused("unknown purpose permits preservation, not compilation")
    if request.source_input == "candidate":
        request, source = candidate(plan.vault, request)
    else:
        source = read_source(plan.vault, request)
    raw_path = request.raw_path
    wiki_path = request.wiki_path
    reused = False
    # Search only caller-designated bounded source notes, never the whole vault.
    matches = []
    for name in dict.fromkeys(request.catalog + (raw_path,)):
        blob = plan.read(name)
        if blob is not None:
            fields = metadata(blob)
            if same_source(fields, request):
                matches.append((name, fields))
    if len(matches) > 1:
        raise Refused("ambiguous source identities in bounded catalog")
    if matches:
        raw_path, fields = matches[0]
        reused = True
        prior_wiki = fields.get("compiled_target", "")
        if wiki_path and prior_wiki and wiki_path != prior_wiki:
            raise Refused("same source already has a different compiled target")
        if prior_wiki:
            wiki_path = prior_wiki
    content_digest = digest(source.body.encode("utf-8"))
    if reused:
        # A recapture never silently updates original content or extraction fields.
        stored = plan.read(raw_path)
        if stored is None:
            raise Refused("matched Raw disappeared")
        original_body = stored.decode("utf-8").split("\n---\n", 1)[1]
        marker = "\n## Original Content\n\n"
        if marker not in original_body:
            raise Refused("existing source is not a supported Raw artifact")
        entry = ("\n\n## Additional selected evidence\n\n"
                 + content_digest + "\nRange: " + source.selected_range
                 + "\nFidelity: " + source.fidelity
                 + "\nMissing: " + json.dumps(list(source.omissions))
                 + "\n\n" + source.body + "\n")
        initial_size = fields.get("source_content_bytes")
        if type(initial_size) is not int:
            raise Refused("Raw source extent is unavailable")
        original = original_body.split(marker, 1)[1].encode("utf-8")
        if digest(original[:initial_size]) != fields.get("source_content_digest"):
            raise Refused("stored Raw original changed")
        if (not (content_digest == fields["source_content_digest"]
                 and source.selected_range == fields.get("selected_range")
                 and source.fidelity == fields.get("fidelity")
                 and list(source.omissions) == fields.get("fidelity_omissions"))
                and entry.encode("utf-8") not in original[initial_size:]):
            plan.add(raw_path, entry.encode("utf-8"), append=True)
    if reused and wiki_path:
        plan.bind_compilation(raw_path, wiki_path)
    if source.fidelity == "full" and source.omissions:
        raise Refused("full conflicts with inherited missing ranges")
    fields = {
        "type": "raw", "created_by": "agent", "authorship": "agent",
        "purpose": request.purpose, "purpose_origin": request.purpose_origin,
        "source_input": request.source_input, "source_kind": request.source_kind,
        "source_extraction": source.extraction, "source_locator": request.locator,
        "source_identity": request.identity,
        "source_obtained_at": request.obtained_at,
        "fidelity": source.fidelity, "fidelity_omissions": list(source.omissions),
        "fidelity_conversion": list(source.conversion),
        "fidelity_checked": "not-checked", "selected_range": source.selected_range,
        "compiled_target": wiki_path, "approval_state": request.approval.get(
            "approval_state", "not-requested"),
        "approval_effect": request.approval.get("approval_effect", []),
        "approval_scope": request.approval.get("approval_scope", []),
        "approval_basis": request.approval.get("approval_basis", ""),
        "approval_preimage": request.approval.get("approval_preimage", {}),
    }
    fields["source_content_digest"] = content_digest
    fields["source_content_bytes"] = len(source.body.encode("utf-8"))
    fields.update(source.provenance)
    if fields["source_locator"].startswith(("http://", "https://")):
        fields["source_url"] = fields["source_locator"]
    if request.attachment_path:
        fields["original_attachment"] = request.attachment_path
        plan.add(request.attachment_path, source.original)
    if not reused:
        plan.new_note(raw_path, fields, "## Original Content\n\n" + source.body)
    target_links = []
    for name in request.targets:
        if not target(plan.vault, name).is_file():
            raise Refused("designated RQ/manuscript/link target is missing: " + name)
        target_links.append(link(name))
    entries = []
    for analysis in request.analyses:
        checked_quote(source, analysis.quote, analysis.anchor)
        text = ("\n\n## Source-grounded analysis\n\n" + analysis.body
                + "\n\nSource: " + link(raw_path) + " at " + analysis.anchor
                + "\n\nQuote:\n> " + analysis.quote.replace("\n", "\n> ")
                + "\n")
        if plan.read(analysis.path) is not None:
            plan.add(analysis.path, text.encode("utf-8"), append=True)
        else:
            plan.new_note(analysis.path,
                {"type": analysis.role, "created_by": "agent", "authorship": "agent",
                 "source_identity": request.identity, "source": link(raw_path),
                 "purpose": request.purpose, "purpose_origin": request.purpose_origin,
                 "fidelity": source.fidelity,
                 "fidelity_omissions": list(source.omissions)}, text)
        entries.append("- " + analysis.role + ": " + link(analysis.path))
    if request.chapters and request.source_kind != "book":
        raise Refused("chapters belong only to books")
    chapter_rows = []
    for chapter in request.chapters:
        state = "not-obtained; not-compiled"
        if chapter.lines:
            first, last = chapter.lines
            lines = source.body.splitlines()
            if last > len(lines):
                raise Refused("chapter range exceeds obtained source")
            state = "obtained; not-compiled"
            excerpt = "\n".join(lines[first - 1:last])
            if any(a.quote in excerpt for a in request.analyses):
                state = "obtained; selected analysis (not a completeness claim)"
        chapter_rows.append("- {}: {}".format(chapter.title, state))
    if wiki_path:
        if source.fidelity == "manifest-only" or request.purpose_origin == "unknown":
            raise Refused("compilation needs an owner purpose and obtained evidence")
        body = ("## Source\n\n" + link(raw_path) + "\n\n## Coverage\n\n"
                + source.selected_range + "\nFidelity: " + source.fidelity
                + "\nMissing: " + json.dumps(list(source.omissions), ensure_ascii=False)
                + "\n\n## Analysis catalog\n\n" + "\n".join(entries))
        if request.analyses:
            body += "\n\n## Source-grounded synthesis\n\n" + "\n\n".join(
                a.body + "\nSource: " + link(raw_path) + " at " + a.anchor
                for a in request.analyses)
        elif request.source_kind not in ("book", "paper"):
            raise Refused("Wiki synthesis needs supplied source-grounded analysis")
        if chapter_rows:
            body += "\n\n## Table of contents and chapter state\n\n" + "\n".join(chapter_rows)
        if request.source_kind == "paper":
            body += ("\n\n## Bibliography and method\n\n" + request.citation
                     + "\nIdentity: " + request.identity
                     + "\nMethodology: " + request.methodology
                     + "\n\nOptional bibliography links:\n" + "\n".join(request.optional_links))
        if target_links:
            body += "\n\n## Designated connections\n\n" + "\n".join(target_links)
        existing_wiki = plan.read(wiki_path)
        if existing_wiki is not None:
            prior = metadata(existing_wiki)
            if not same_source(prior, request):
                raise Refused("compiled target belongs to a different source")
            # Re-ingest is not a generic rewrite or duplicate page creation.
            plan.add(wiki_path, ("\n\n" + body + "\n").encode("utf-8"), append=True)
        else:
            hub_fields = {
                "type": "paper-hub" if request.source_kind == "paper" else "wiki",
                "source_identity": request.identity, "source_locator": request.locator,
                "created_by": "agent", "authorship": "agent",
                "source": link(raw_path),
                "purpose": request.purpose, "purpose_origin": request.purpose_origin,
                "fidelity": source.fidelity, "fidelity_omissions": list(source.omissions),
                "source_obtained_at": request.obtained_at,
                "analysis_catalog": [{"path": a.path, "role": a.role}
                                     for a in request.analyses],
                "chapter_states": [{"title": c.title, "obtained": bool(c.lines),
                                    "compiled": False} for c in request.chapters],
                "methodology": request.methodology,
                "citation": request.citation,
                "optional_links": list(request.optional_links)}
            plan.new_note(wiki_path, hub_fields, body)
    if request.persona_path:
        checked_quote(source, request.stance_quote, request.stance_anchor)
        if not request.stance:
            raise Refused("Persona citation needs an attributed stance")
        persona = plan.read(request.persona_path)
        if persona is None or metadata(persona).get("type") != "persona":
            raise Refused("designated Persona is not an existing Wiki Persona")
        citation = {"date": request.obtained_at, "source": link(raw_path),
                    "identity": request.identity, "anchor": request.stance_anchor,
                    "quote": request.stance_quote, "stance": request.stance}
        entry = ("\n\n## Citation and stance timeline\n\n"
                 + json.dumps(citation, ensure_ascii=False, sort_keys=True) + "\n")
        plan.add(request.persona_path, entry.encode("utf-8"), append=True)
    return plan, {"schema": "ingest/result@1", "raw_path": raw_path, "wiki_path": wiki_path,
                  "reused": reused, "fidelity": source.fidelity,
                  "omissions": list(source.omissions),
                  "source_identity": request.identity,
                  "selected_range": source.selected_range,
                  "changes": [change.receipt() for change in plan.changes]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--handoff", type=Path, help="actual inbox/handoff@1; --request then maps members")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.request.is_symlink() or not args.request.is_file():
            raise Refused("request must be an existing regular nonsymlink file")
        document = json.loads(args.request.read_text("utf-8"))
        approval = document.get("approval", {}) if isinstance(document, dict) else {}
        if args.handoff:
            from batch import build_batch
            if args.handoff.is_symlink() or not args.handoff.is_file():
                raise Refused("handoff must be a regular nonsymlink JSON file")
            plan, receipt = build_batch(args.vault, json.loads(args.handoff.read_text("utf-8")), document)
        else:
            plan, receipt = build(args.vault, parse(document))
        receipt["status"] = "planned"
        receipt["evidence_level"] = "static"
        if args.apply:
            receipt["applied"] = plan.apply(approval)
            receipt["status"] = "applied"
            receipt["evidence_level"] = "materialized"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (Refused, OSError, UnicodeError, json.JSONDecodeError,
            URLError) as exc:
        print(json.dumps({"schema": "ingest/error@1", "status": "refused", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
