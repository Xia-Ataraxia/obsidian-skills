"""Consume actual inbox/handoff@1 members through one preflighted ingest plan."""
from pathlib import Path
from dataclasses import replace

from ingest import build
from request import Refused, mapping, parse, records, string, strings
from storage import Plan, digest, metadata, target


def selected_members(plan: Plan, handoff: dict) -> dict:
    """Bind all emitted members to current selected files; grouping is not identity."""
    keys = {"schema", "status", "consumer", "scope", "selected_paths", "selected_preimages",
            "purpose", "purpose_origin", "source_groups", "unclassified_paths",
            "mutations_performed"}
    if set(handoff) != keys or (
            handoff["schema"] != "inbox/handoff@1"
            or handoff["status"] != "ready-for-ingest"
            or handoff["consumer"] != "ingest"
            or handoff["mutations_performed"] != []):
        raise Refused("requires actual ready-for-ingest inbox/handoff@1")
    paths = strings(handoff["selected_paths"], "selected_paths")
    if not paths or len(set(paths)) != len(paths):
        raise Refused("selected_paths must be nonempty and unique")
    preimages = mapping(handoff["selected_preimages"], "selected_preimages")
    if set(preimages) != set(paths):
        raise Refused("selected_preimages must exactly cover selected_paths")
    scope = target(plan.vault, string(handoff["scope"], "scope"))
    if not scope.is_dir():
        raise Refused("handoff scope is not an existing directory")
    actual = {}
    unclassified = []
    for name in paths:
        path = target(plan.vault, name)
        try:
            path.relative_to(scope)
        except ValueError as exc:
            raise Refused("candidate outside selected Inbox scope") from exc
        if not path.is_file():
            raise Refused("selected candidate is not a regular file")
        blob = path.read_bytes()
        if digest(blob) != preimages[name]:
            raise Refused("selected candidate changed since handoff: " + name)
        # Only the capture protocol is parsed. Unclassified UTF-8 files stay verbatim.
        header = blob[4:].split(b"\n---\n", 1)[0] if blob.startswith(b"---\n") else b""
        declared_capture = any(line.startswith(b"capture_schema: ") for line in header.splitlines())
        fields = metadata(blob) if declared_capture else {}
        if fields.get("capture_schema") == "capture/candidate@1":
            sources = records(fields.get("capture_sources"), "capture_sources")
            if not sources:
                raise Refused("capture has no sources")
            for index, source in enumerate(sources):
                actual[(name, index)] = mapping(source, "captured source")
        else:
            unclassified.append(name)
    if sorted(strings(handoff["unclassified_paths"], "unclassified_paths")) != sorted(unclassified):
        raise Refused("unclassified_paths disagree with selected files")
    emitted = {}
    for group in records(handoff["source_groups"], "source_groups"):
        group = mapping(group, "source group")
        if set(group) != {"identities", "locators", "members"}:
            raise Refused("invalid source group")
        strings(group["identities"], "group identities")
        strings(group["locators"], "group locators")
        for member in records(group["members"], "group members"):
            member = mapping(member, "member")
            if set(member) != {"candidate_path", "candidate_index", "source"}:
                raise Refused("member requires candidate_path/candidate_index/source")
            name = string(member["candidate_path"], "candidate_path")
            index = member["candidate_index"]
            if type(index) is not int:
                raise Refused("captured member index must be an integer")
            key = (name, index)
            if key in emitted or key not in actual or member["source"] != actual[key]:
                raise Refused("duplicate, unselected or altered source member")
            emitted[key] = actual[key]
    if set(emitted) != set(actual):
        raise Refused("handoff omits selected captured members")
    for name in unclassified:
        emitted[(name, None)] = None
    plan.input_preimages.update(preimages)
    return emitted


def build_batch(vault: Path, handoff_value, mapping_value):
    """Plan the complete selected batch without creating temporary output files."""
    plan = Plan(vault, {})
    handoff = mapping(handoff_value, "handoff")
    document = mapping(mapping_value, "batch mapping")
    if set(document) != {"members", "approval"}:
        raise Refused("batch mapping requires only members and approval")
    approval = mapping(document["approval"], "batch approval")
    selected = selected_members(plan, handoff)
    purpose = string(handoff["purpose"], "batch purpose", True)
    origin = handoff["purpose_origin"]
    if origin not in ("stated", "reused", "unknown") or (
            origin == "unknown" and purpose) or (origin != "unknown" and not purpose.strip()):
        raise Refused("invalid common batch purpose")
    mapped = {}
    forbidden = {"source_input", "locator", "candidate_index", "purpose", "purpose_origin", "approval"}
    capture_fields = {"source_kind", "identity", "text", "obtained_at", "selection"}
    for item in records(document["members"], "member mappings"):
        item = mapping(item, "member mapping")
        if set(item) != {"candidate_path", "candidate_index", "request"}:
            raise Refused("mapping requires candidate_path/candidate_index/request")
        name = string(item["candidate_path"], "candidate_path")
        index = item["candidate_index"]
        if index is not None and type(index) is not int:
            raise Refused("mapping candidate_index must be integer or null")
        key = (name, index)
        if key not in selected or key in mapped:
            raise Refused("duplicate or unselected member mapping")
        value = dict(mapping(item["request"], "member request"))
        if set(value) & forbidden:
            raise Refused("member cannot override selection, common purpose or approval")
        source = selected[key]
        if source is not None:
            if set(value) & capture_fields:
                raise Refused("captured source metadata comes from the bound member")
            value.update(source_input="candidate", candidate_index=index,
                         source_kind=source.get("source_kind"),
                         identity=source.get("source_identity", ""),
                         obtained_at=source.get("source_obtained_at"))
        else:
            # Unknown provenance is not invented: direct file metadata must be supplied.
            value["source_input"] = "file"
        value.update(locator=name, purpose=purpose,
                     purpose_origin="unknown" if origin == "unknown" else "reused",
                     approval=approval)
        parsed = parse(value)
        for fields in parsed.note_fields.values():
            if "user_intent_interview" in fields and fields["user_intent_interview"] != purpose:
                raise Refused("destination purpose contradicts common batch purpose")
        mapped[key] = parsed
    if set(mapped) != set(selected):
        raise Refused("explicit mappings must cover every selected member")
    results = []
    for key in selected:
        request = mapped[key]
        # Only earlier outputs in this exact batch extend the bounded identity catalog.
        request = replace(request, catalog=tuple(dict.fromkeys(
            request.catalog + tuple(row["raw_path"] for row in results))))
        _, receipt = build(plan.vault, request, plan)
        results.append({"candidate_path": key[0], "candidate_index": key[1],
                        **{name: receipt[name] for name in (
                            "raw_path", "wiki_path", "reused", "fidelity",
                            "omissions", "source_identity", "selected_range")}})
    if any(change.path in handoff["selected_paths"] for change in plan.changes):
        raise Refused("selected candidates must be retained unchanged")
    return plan, {"schema": "ingest/batch-result@1", "purpose": purpose,
                  "purpose_origin": origin, "selected_paths": handoff["selected_paths"],
                  "selected_preimages": handoff["selected_preimages"], "members": results,
                  "changes": [change.receipt() for change in plan.changes]}
