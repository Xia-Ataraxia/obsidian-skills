"""Read a selected source and retain conversion and range evidence."""
from dataclasses import dataclass, replace
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Tuple
from urllib.request import Request as URLRequest, urlopen

from request import Request, Refused, public_locator, source_identity, string, strings
from storage import target, metadata


class HTMLText(HTMLParser):
    """Extract readable text; the original HTML is retained as an attachment."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "pre"):
            self.fragments.append("\n")
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.fragments.append(" [" + value + "] ")
        if tag == "img":
            self.fragments.append(" [image: " + repr(dict(attrs)) + "] ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.fragments.append(data)


@dataclass(frozen=True)
class Source:
    body: str
    original: bytes
    extraction: str
    conversion: Tuple[dict, ...]
    fidelity: str
    omissions: Tuple[str, ...]
    selected_range: str
    provenance: dict


def candidate(vault: Path, request: Request) -> Tuple[Request, Source]:
    """Consume one actual capture/candidate@1 structured source, never its prose."""
    blob = read_file(vault, request.locator)
    fields = metadata(blob)
    members = fields.get("capture_sources")
    if fields.get("capture_schema") != "capture/candidate@1" or not isinstance(members, list):
        raise Refused("candidate must use actual capture/candidate@1")
    index = request.candidate_index
    if index is None:
        if len(members) != 1:
            raise Refused("mixed candidate needs an explicitly selected candidate_index")
        index = 0
    if index >= len(members) or not isinstance(members[index], dict):
        raise Refused("candidate_index is unavailable")
    member = members[index]
    fidelity = member.get("fidelity")
    if fidelity not in ("full", "partial", "excerpt", "manifest-only"):
        raise Refused("candidate fidelity unavailable")
    text = string(member.get("original_content"), "original_content", True)
    if fidelity == "manifest-only" and text:
        raise Refused("manifest-only candidate contains purported content")
    if request.selection:
        raise Refused("candidate span is already selected by capture")
    provenance = {key: string(member.get(key, ""), key, key == "source_identity")
                  for key in ("source_input", "source_kind", "source_extraction",
                              "source_locator", "source_identity", "source_obtained_at")}
    public_locator(provenance["source_locator"])
    source_identity(provenance["source_identity"])
    if provenance["source_kind"] != request.source_kind:
        raise Refused("candidate kind disagrees with requested kind")
    effective = replace(request, locator=provenance["source_locator"],
                        identity=provenance["source_identity"])
    omissions = strings(member.get("fidelity_omissions", []), "candidate omissions")
    conversion = member.get("fidelity_conversion", [])
    if not isinstance(conversion, list):
        raise Refused("candidate conversions malformed")
    return effective, Source(text, blob, provenance["source_extraction"],
                             tuple(conversion), fidelity, omissions,
                             "capture selected span: " + json.dumps(member.get("selected_span")),
                             provenance)


def read_source(vault: Path, request: Request) -> Source:
    readers = {
        "text": lambda: request.text.encode("utf-8"),
        "file": lambda: read_file(vault, request.locator),
        "url": lambda: fetch(request.locator),
    }
    blob = readers[request.source_input]()
    text = blob.decode("utf-8")
    conversion = ()
    extraction = "direct-read"
    html = text.lstrip().lower().startswith(("<!doctype html", "<html"))
    if html:
        if not request.attachment_path:
            raise Refused("HTML conversion requires an exact original attachment path")
        parser = HTMLText()
        parser.feed(text)
        text = "".join(parser.fragments).strip()
        conversion = ({"tool": "stdlib HTMLParser", "from": "html", "to": "text"},)
        extraction = "reader"
    omissions = list(request.omissions)
    fidelity = request.fidelity
    selected_range = "obtained content; total original extent unverified"
    if request.selection:
        lines = text.splitlines(keepends=True)
        first, last = request.selection
        if last > len(lines):
            raise Refused("selected range exceeds obtained source")
        text = "".join(lines[first - 1:last])
        selected_range = "lines {}-{} inclusive of obtained content".format(first, last)
        if first > 1:
            omissions.append("lines 1-{} outside selection".format(first - 1))
        if last < len(lines):
            omissions.append("lines {}-{} outside selection".format(last + 1, len(lines)))
        if omissions:
            fidelity = "excerpt"
    if not text.strip() and fidelity != "manifest-only":
        raise Refused("no source content obtained")
    return Source(text, blob, extraction, conversion, fidelity,
                  tuple(omissions), selected_range, {})


def read_file(vault: Path, name: str) -> bytes:
    path = target(vault, name)
    if not path.is_file():
        raise Refused("source must be an existing regular file")
    return path.read_bytes()


def fetch(locator: str) -> bytes:
    public_locator(locator)
    with urlopen(URLRequest(locator, headers={"User-Agent": "secondbrain-ingest"}),
                 timeout=30) as response:
        public_locator(response.geturl())
        if response.headers.get_content_type() not in ("text/html", "text/plain",
                                                        "text/markdown"):
            raise Refused("provide a converted text export and preserve the original")
        return response.read()
