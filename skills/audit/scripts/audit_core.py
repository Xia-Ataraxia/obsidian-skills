"""Sample-based audit analysis with explicit scope and limits."""
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

from audit_io import (
    Refused,
    authorize,
    fields,
    load,
    make_proposal,
    publish,
    relative,
    route,
    text,
)


def corpus(root: Path, scopes: List[str]) -> List[str]:
    notes: Set[str] = set()
    for scope in scopes:
        selected = route(root, scope)
        if selected.is_file() and selected.suffix == ".md":
            notes.add(relative(scope, markdown=True))
        elif selected.is_dir():
            for parent, directories, filenames in os.walk(str(selected), followlinks=False):
                base = Path(parent)
                directories[:] = sorted(
                    name
                    for name in directories
                    if not name.startswith(".") and not (base / name).is_symlink()
                )
                for filename in sorted(filenames):
                    item = base / filename
                    if (
                        filename.startswith(".")
                        or item.is_symlink()
                        or not item.is_file()
                        or item.suffix != ".md"
                    ):
                        continue
                    notes.add(item.relative_to(root).as_posix())
        else:
            raise Refused("missing_scope", "scope is not an existing note or directory")
    return sorted(notes)


def title_index(root: Path) -> Set[str]:
    titles: Set[str] = set()
    for parent, directories, filenames in os.walk(str(root), followlinks=False):
        base = Path(parent)
        directories[:] = [
            name
            for name in directories
            if not name.startswith(".") and not (base / name).is_symlink()
        ]
        for filename in filenames:
            item = base / filename
            if (
                filename.startswith(".")
                or item.is_symlink()
                or not item.is_file()
                or item.suffix != ".md"
            ):
                continue
            relative_path = item.relative_to(root).as_posix()
            titles.add(relative_path[:-3])
            titles.add(item.stem)
    return titles


def frontmatter(body: str) -> Dict[str, str]:
    if not body.startswith("---\n"):
        return {}
    end = body.find("\n---\n", 4)
    if end < 0:
        return {"__error__": "unterminated"}
    result: Dict[str, str] = {}
    for line in body[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("\"'")
    return result


def inspect(root: Path, path: str, known_titles: Set[str]) -> List[dict]:
    body = route(root, path).read_text(encoding="utf-8")
    properties = frontmatter(body)
    findings: List[dict] = []
    if not properties:
        findings.append({"category": "structure", "path": path, "detail": "missing frontmatter"})
    elif properties.get("__error__") == "unterminated":
        findings.append({"category": "structure", "path": path, "detail": "unterminated frontmatter"})
    fidelity = properties.get("fidelity")
    if fidelity in ("partial", "excerpt", "manifest-only", "mixed"):
        findings.append({"category": "partial_source", "path": path, "detail": fidelity})
    if properties.get("verification_status") == "verified" and not properties.get(
        "verification_manifest"
    ):
        findings.append(
            {"category": "verification_followup", "path": path, "detail": "verified without manifest"}
        )
    for link in re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", body):
        link_without_suffix = link[:-3] if link.endswith(".md") else link
        if link not in known_titles and link_without_suffix not in known_titles:
            findings.append({"category": "broken_link", "path": path, "detail": link})
    return findings


def compare(previous: dict, counts: Dict[str, int]) -> List[dict]:
    if previous.get("schema") != "audit/report@1" or not isinstance(
        previous.get("category_counts"), dict
    ):
        raise Refused("invalid_previous_report", "previous report schema is unsupported")
    old = previous["category_counts"]
    categories = sorted(set(old) | set(counts))
    return [
        {
            "category": category,
            "previous": old.get(category, 0),
            "current": counts.get(category, 0),
            "change": counts.get(category, 0) - old.get(category, 0),
        }
        for category in categories
        if type(old.get(category, 0)) is int
    ]


def parse_request(request: dict) -> tuple:
    fields(
        request,
        {"schema", "scope", "sample", "sample_method", "limits"},
        {"previous_report", "report_path"},
        "request",
    )
    if request["schema"] != "audit/request@1":
        raise Refused("invalid_input", "unsupported request schema")
    scopes, sample, limits = request["scope"], request["sample"], request["limits"]
    if (
        not isinstance(scopes, list)
        or not scopes
        or any(not isinstance(item, str) for item in scopes)
        or not isinstance(sample, list)
        or not sample
        or any(not isinstance(item, str) for item in sample)
        or len(sample) != len(set(sample))
        or not isinstance(limits, list)
        or not limits
        or any(not isinstance(item, str) or not item.strip() for item in limits)
    ):
        raise Refused("invalid_input", "scope, sample, and limits must be explicit lists")
    return scopes, sample, limits


def run(
    root: Path,
    request: dict,
    approval: Optional[dict] = None,
    write_disabled: bool = False,
) -> dict:
    scopes, sample, limits = parse_request(request)
    resolved = corpus(root, [relative(item) for item in scopes])
    sample = [relative(item, markdown=True) for item in sample]
    if any(item not in resolved for item in sample):
        raise Refused("sample_outside_scope", "sample note is outside the declared scope")
    known_titles = title_index(root)
    findings = [finding for path in sample for finding in inspect(root, path, known_titles)]
    counts: Dict[str, int] = {}
    for finding in findings:
        category = finding["category"]
        counts[category] = counts.get(category, 0) + 1
    report = {
        "schema": "audit/report@1",
        "status": "reported",
        "scope": [relative(item) for item in scopes],
        "resolved_scope_notes": resolved,
        "sample": sample,
        "sample_method": text(request["sample_method"], "sample_method"),
        "limits": limits
        + ["Unsampled notes were not inspected and are not represented as verified."],
        "findings": findings,
        "category_counts": counts,
        "followup_priorities": sorted(counts, key=lambda key: (-counts[key], key)),
        "comparison": [],
        "proposals": [],
        "mutations_performed": [],
    }
    if "previous_report" in request:
        previous_path = relative(text(request["previous_report"], "previous_report"))
        report["comparison"] = compare(load(route(root, previous_path)), counts)
    if "report_path" in request:
        report_path = relative(text(request["report_path"], "report_path"))
        if not report_path.endswith(".json"):
            raise Refused("unsafe_destination", "audit report must be a JSON file")
        report["proposals"].append(make_proposal(report_path, report))
    if approval is not None and report["proposals"] and not write_disabled:
        item = report["proposals"][0]
        authorize(approval, item)
        publish(root, item)
        report["status"] = "saved"
        report["mutations_performed"].append(item["path"])
    return report
