"""Parse the ingest invocation; no destination or permission is inferred."""
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlsplit
import re


class Refused(ValueError):
    """An invalid or unauthorized invocation, with no inferred replacement."""


def string(value, label: str, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise Refused("expected text: " + label)
    return value


def strings(value, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise Refused("expected list: " + label)
    return tuple(string(item, label) for item in value)


def mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise Refused("expected mapping: " + label)
    return value


def records(value, label: str) -> list:
    if not isinstance(value, list):
        raise Refused("expected list: " + label)
    return value


def public_locator(value: str) -> str:
    """Reject credential-bearing URLs and host paths in persisted identifiers."""
    parts = urlsplit(value)
    if parts.scheme:
        if parts.scheme not in ("http", "https", "doi", "urn"):
            raise Refused("unsupported locator scheme")
        if parts.username or parts.password:
            raise Refused("credentials in locator")
        if parts.scheme in ("http", "https") and not parts.hostname:
            raise Refused("URL has no host")
        if parts.query:
            raise Refused("use a credential-free canonical URL without query")
    elif value.startswith(("/", "~")) or "\\" in value or ".." in value.split("/"):
        raise Refused("host path or escaping locator")
    return value


def source_identity(value: str) -> str:
    """Content digests are opaque identities, never acquisition locations."""
    if value.startswith("sha256:"):
        if re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
            raise Refused("invalid SHA-256 source identity")
        return value
    return public_locator(value)


@dataclass(frozen=True)
class Analysis:
    path: str
    body: str
    quote: str
    anchor: str
    role: str


@dataclass(frozen=True)
class Chapter:
    title: str
    lines: Optional[Tuple[int, int]]


@dataclass(frozen=True)
class Request:
    source_input: str
    source_kind: str
    locator: str
    identity: str
    text: str
    obtained_at: str
    purpose: str
    purpose_origin: str
    fidelity: str
    omissions: Tuple[str, ...]
    selection: Optional[Tuple[int, int]]
    raw_path: str
    attachment_path: str
    wiki_path: str
    analyses: Tuple[Analysis, ...]
    chapters: Tuple[Chapter, ...]
    methodology: str
    citation: str
    optional_links: Tuple[str, ...]
    targets: Tuple[str, ...]
    persona_path: str
    stance: str
    stance_quote: str
    stance_anchor: str
    catalog: Tuple[str, ...]
    approval: dict
    candidate_index: Optional[int]
    note_fields: dict


def line_range(value) -> Optional[Tuple[int, int]]:
    if value is None:
        return None
    if (not isinstance(value, list) or len(value) != 2
            or any(type(n) is not int for n in value)
            or value[0] < 1 or value[1] < value[0]):
        raise Refused("lines must be inclusive [first, last], starting at 1")
    return (value[0], value[1])


def parse(value) -> Request:
    """Parse JSON values once, rejecting unsupported behavior and unknown keys."""
    data = mapping(value, "request")
    allowed = set(Request.__dataclass_fields__)
    if set(data) - allowed:
        raise Refused("unknown request keys: " + ", ".join(sorted(set(data) - allowed)))
    source_input = string(data.get("source_input"), "source_input")
    kind = string(data.get("source_kind"), "source_kind")
    if source_input not in ("url", "file", "text", "candidate"):
        raise Refused("this CLI accepts url, file, text or candidate")
    if kind not in ("article", "video", "repository", "mail", "conversation",
                    "book", "paper", "other"):
        raise Refused("unsupported source_kind")
    purpose = string(data.get("purpose", ""), "purpose", True)
    origin = string(data.get("purpose_origin", "unknown"), "purpose_origin")
    if origin not in ("stated", "reused", "unknown") or (origin != "unknown" and not purpose):
        raise Refused("purpose and purpose_origin disagree")
    if origin == "unknown" and purpose:
        raise Refused("unknown purpose must be empty")
    fidelity = string(data.get("fidelity", "partial"), "fidelity")
    if fidelity not in ("full", "partial", "excerpt", "manifest-only", "mixed"):
        raise Refused("unsupported fidelity")
    omissions = strings(data.get("omissions", []), "omissions")
    if fidelity == "full" and omissions:
        raise Refused("full conflicts with known omissions")
    date = string(data.get("obtained_at"), "obtained_at")
    from datetime import datetime
    try:
        datetime.fromisoformat(date.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refused("obtained_at must be ISO 8601") from exc
    analyses = []
    for item in records(data.get("analyses", []), "analyses"):
        item = mapping(item, "analysis")
        if set(item) != {"path", "body", "quote", "anchor", "role"}:
            raise Refused("analysis requires path/body/quote/anchor/role")
        role = string(item["role"], "role")
        if role not in ("atom", "concept"):
            raise Refused("analysis role must be atom or concept")
        analyses.append(Analysis(*(string(item[k], k) for k in
                                   ("path", "body", "quote", "anchor")), role))
    chapters = []
    for item in records(data.get("chapters", []), "chapters"):
        item = mapping(item, "chapter")
        if set(item) - {"title", "lines"}:
            raise Refused("unknown chapter keys")
        chapters.append(Chapter(string(item.get("title"), "chapter title"),
                                line_range(item.get("lines"))))
    methodology = string(data.get("methodology", ""), "methodology", True)
    if kind == "paper" and methodology not in (
            "quantitative", "qualitative", "theory-concept", "mixed-methods",
            "scale-development", "meta-analysis"):
        raise Refused("paper requires one of the six methodology types")
    identity = source_identity(string(data.get("identity", ""), "identity", True))
    if identity.lower().startswith(("https://doi.org/", "doi:")):
        identity = "doi:" + re.sub(r"^(https://doi.org/|doi:)", "", identity,
                                  flags=re.I).lower()
    if kind == "paper" and not identity:
        raise Refused("paper requires DOI or full citekey identity")
    index = data.get("candidate_index")
    if index is not None and (type(index) is not int or index < 0):
        raise Refused("candidate_index must be a nonnegative integer")
    locator = string(data.get("locator"), "locator")
    if source_input == "url" and not locator.startswith(("http://", "https://")):
        raise Refused("URL input requires http or https")
    note_fields = mapping(data.get("note_fields", {}), "note_fields")
    for name, fields in note_fields.items():
        string(name, "note_fields path")
        mapping(fields, "note_fields entry")
        if set(fields) - {"type", "tags", "date_created", "date_modified",
                          "user_intent_interview", "title"}:
            raise Refused("note_fields may supply only destination core metadata")
        for key, value in fields.items():
            if key == "tags":
                strings(value, "note tags")
            else:
                string(value, key)
    return Request(
        source_input, kind, public_locator(locator),
        identity, string(data.get("text", ""), "text", True), date, purpose,
        origin, fidelity, omissions, line_range(data.get("selection")),
        string(data.get("raw_path"), "raw_path"),
        string(data.get("attachment_path", ""), "attachment_path", True),
        string(data.get("wiki_path", ""), "wiki_path", True), tuple(analyses),
        tuple(chapters), methodology,
        string(data.get("citation", ""), "citation", True),
        tuple(public_locator(s) for s in strings(data.get("optional_links", []), "optional_links")),
        strings(data.get("targets", []), "targets"),
        string(data.get("persona_path", ""), "persona_path", True),
        string(data.get("stance", ""), "stance", True),
        string(data.get("stance_quote", ""), "stance_quote", True),
        string(data.get("stance_anchor", ""), "stance_anchor", True),
        strings(data.get("catalog", []), "catalog"),
        mapping(data.get("approval", {}), "approval"),
        index,
        note_fields,
    )
