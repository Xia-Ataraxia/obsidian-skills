"""Package-local input, YAML and acquisition helpers; no write authority."""
import hashlib
import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class Refused(ValueError):
    pass


def digest(blob):
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def target(vault, name):
    if not isinstance(name, str):
        raise Refused("path must be text")
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or relative.as_posix() != name
            or "\\" in name or any(p.startswith(".") for p in relative.parts)):
        raise Refused("expected canonical visible vault-relative path: " + name)
    path = vault
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise Refused("symlink in path: " + name)
    return path


def public_locator(value):
    if not isinstance(value, str) or not value:
        raise Refused("locator must be nonempty text")
    parts = urlsplit(value)
    if parts.scheme:
        if (parts.scheme not in ("http", "https", "doi", "urn") or parts.username
                or parts.password or parts.query or (parts.scheme in ("http", "https")
                and not parts.hostname)):
            raise Refused("unsupported or credential-bearing locator")
    elif value.startswith(("/", "~")) or "\\" in value or ".." in value.split("/"):
        raise Refused("host path or escaping locator")
    return value


def identity(value):
    if not isinstance(value, str):
        raise Refused("identity must be text")
    if not value:
        return ""
    if value.startswith("sha256:"):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise Refused("invalid SHA-256 identity")
        return value
    public_locator(value)
    return re.sub(r"^(https://doi.org/|doi:)", "doi:", value, flags=re.I).lower() if value.lower().startswith(("doi:", "https://doi.org/")) else value


UNPARSED = object()


class Fields(dict):
    """Top-level frontmatter; reading a value the strict reader could not parse refuses."""

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        if value is UNPARSED:
            raise Refused("unsupported frontmatter value: " + key)
        return value

    def get(self, key, default=None):
        return self[key] if key in self else default


def scalar(text):
    text = text.strip()
    if not text or text == "~" or text == "null":
        return None if text in ("~", "null") else ""
    if text[0] in "[{\"":
        try:
            return json.loads(text)
        except ValueError:
            if text[0] != "[":
                return UNPARSED
            inner = text[1:-1].strip() if text.endswith("]") else None
            if inner is None or any(c in inner for c in "[]{}\"'"):
                return UNPARSED
            return [scalar(item) for item in inner.split(",")] if inner else []
    if text[0] == "'":
        if len(text) < 2 or not text.endswith("'") or "'" in text[1:-1].replace("''", ""):
            return UNPARSED
        return text[1:-1].replace("''", "'")
    if text[0] in "|>&*!%@`" or " #" in text or text.startswith("- "):
        return UNPARSED
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?[0-9]+", text):
        return int(text)
    return text


def body_offset(blob):
    match = re.match(rb"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)", blob, re.S)
    if not match:
        raise Refused("note has no bounded frontmatter")
    return match.end()


def metadata(blob):
    lines = blob[:body_offset(blob)].decode("utf-8").splitlines()[1:-1]
    fields, key = Fields(), None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t-":
            if key is None:
                raise Refused("frontmatter continuation without key")
            item = line.strip()
            current = dict.__getitem__(fields, key)
            if item.startswith("- ") or item == "-":
                if current == "":
                    current = []
                if isinstance(current, list):
                    value = scalar(item[1:])
                    current.append(value)
                    dict.__setitem__(fields, key, UNPARSED if value is UNPARSED else current)
                    continue
            dict.__setitem__(fields, key, UNPARSED)
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s(.*))?", line)
        if not match:
            raise Refused("unsupported frontmatter line")
        key = match.group(1)
        if key in fields:
            raise Refused("duplicate YAML key")
        dict.__setitem__(fields, key, scalar(match.group(2) or ""))
    return fields


def note(fields, body):
    rows = []
    for key, value in fields.items():
        if isinstance(value, list) and value:
            rows.append(key + ":")
            rows += ["  - " + json.dumps(item, ensure_ascii=False) for item in value]
        else:
            rows.append(key + ": " + json.dumps(value, ensure_ascii=False))
    return ("---\n" + "\n".join(rows) + "\n---\n\n" + body).encode("utf-8")


def parse(data):
    allowed = {"source_input", "source_kind", "locator", "identity", "text", "obtained_at",
               "purpose", "purpose_origin", "coverage", "omissions", "selection", "raw_path",
               "attachment_path", "wiki_path", "analyses", "chapters", "methodology", "citation",
               "optional_links", "targets", "persona_path", "stance", "stance_quote", "stance_anchor",
               "catalog", "candidate_index", "note_fields", "extraction", "conversion", "author",
               "referenced", "notes", "attachment_source", "attachment_sha256", "book_title", "reading_paths"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise Refused("unknown request keys or nonmapping request")
    data = dict(data)
    book_keys(data)
    for key in ("source_input", "source_kind", "locator", "obtained_at", "raw_path"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise Refused("expected text: " + key)
    if data["source_input"] not in ("text", "file", "url", "candidate"):
        raise Refused("unsupported input")
    if data["source_kind"] not in ("article", "video", "book", "paper", "conversation", "repository", "mail", "other"):
        raise Refused("unsupported source kind")
    public_locator(data["locator"])
    if data["source_input"] == "url" and not data["locator"].startswith(("http://", "https://")):
        raise Refused("URL input requires HTTP(S)")
    data["identity"] = identity(data.get("identity", ""))
    try:
        datetime.fromisoformat(data["obtained_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refused("obtained_at must be ISO 8601") from exc
    for key in ("text", "purpose", "wiki_path", "attachment_path", "attachment_source", "attachment_sha256", "persona_path", "stance", "stance_quote", "stance_anchor", "citation", "methodology"):
        data.setdefault(key, "")
        if not isinstance(data[key], str):
            raise Refused("expected text: " + key)
    purpose_checked(data)
    for key in ("omissions", "conversion", "author", "referenced", "analyses", "chapters", "targets", "catalog", "optional_links", "notes"):
        data.setdefault(key, [])
        if not isinstance(data[key], list):
            raise Refused("expected list: " + key)
    for step in data["conversion"]:
        if not isinstance(step, dict) or set(step) != {"tool", "from", "to"} or any(not isinstance(v, str) or not v for v in step.values()):
            raise Refused("conversion requires tool/from/to strings")
    if bool(data["attachment_source"]) != bool(data["attachment_sha256"]):
        raise Refused("attachment_source and attachment_sha256 go together")
    for key in ("omissions", "author", "referenced", "targets", "catalog", "optional_links", "notes"):
        if any(not isinstance(v, str) or not v for v in data[key]):
            raise Refused("expected text list: " + key)
    if not isinstance(data.get("note_fields", {}), dict):
        raise Refused("invalid note_fields")
    data.setdefault("coverage", "partial")
    if data["coverage"] not in ("full", "partial", "excerpt", "manifest-only") or (data["coverage"] == "full" and data["omissions"]):
        raise Refused("invalid coverage or conflicting omissions")
    data.setdefault("extraction", "direct-read")
    if not isinstance(data["extraction"], str) or not data["extraction"]:
        raise Refused("extraction must be nonempty text")
    selection = data.get("selection")
    if selection is not None and (not isinstance(selection, list) or len(selection) != 2 or any(type(n) is not int for n in selection) or selection[0] < 1 or selection[1] < selection[0]):
        raise Refused("selection must be inclusive [first,last]")
    return data


def book_keys(data):
    """Book-scaffold-only keys: an exact obtained one-line title and verbatim author Reading Paths (or explicit null)."""
    present = [key for key in ("book_title", "reading_paths") if key in data]
    if not present:
        return
    if data.get("source_kind") != "book" or not isinstance(data.get("chapters"), list) or not data["chapters"]:
        raise Refused("book_title/reading_paths belong only to a book chapter scaffold request")
    title = data.get("book_title")
    if "book_title" in data and (not isinstance(title, str) or not title.strip() or "\n" in title or "\r" in title):
        raise Refused("book_title must be nonempty one-line text")
    paths = data.get("reading_paths")
    if paths is not None:
        if not isinstance(paths, str) or not paths.strip():
            raise Refused("reading_paths must be nonempty verbatim text or null (explicitly unavailable)")
        # A level-1/2 heading would split the Index sections that promotion locates by `## ` headings.
        if re.search(r"(?m)^#{1,2}(?:[ \t]|\r?$)", paths):
            raise Refused("reading_paths must not contain level-1/2 headings")


def purpose_checked(data):
    data.setdefault("purpose", "")
    data.setdefault("purpose_origin", "unknown")
    if not isinstance(data["purpose"], str) or data["purpose_origin"] not in ("unknown", "stated", "reused") or bool(data["purpose"]) != (data["purpose_origin"] != "unknown"):
        raise Refused("purpose and origin disagree")


SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
UPDATE_KEYS = {"update_path", "preimage_sha256", "postimage_file", "postimage_sha256", "preserve", "promotion", "analyses", "obtained_at", "purpose", "purpose_origin"}
PROMOTION_KEYS = {"placeholder", "text_file", "text_sha256", "locator", "coverage", "date", "index"}
INDEX_KEYS = {"path", "preimage_sha256", "postimage_file", "postimage_sha256"}


def parse_promotion(spec):
    """Book chapter promotion: exact placeholder span, outside-vault acquired text and the Index progress postimage."""
    if not isinstance(spec, dict) or set(spec) != PROMOTION_KEYS:
        raise Refused("promotion requires exactly placeholder/text_file/text_sha256/locator/coverage/date/index")
    span, index = spec["placeholder"], spec["index"]
    if (not isinstance(span, dict) or set(span) != {"start", "end", "sha256"} or type(span["start"]) is not int or type(span["end"]) is not int
            or not isinstance(span["sha256"], str) or not SHA256.fullmatch(span["sha256"])):
        raise Refused("promotion placeholder requires integer start/end and sha256")
    if not isinstance(index, dict) or set(index) != INDEX_KEYS or any(not isinstance(index[k], str) or not index[k] for k in INDEX_KEYS):
        raise Refused("promotion index requires exactly path/preimage_sha256/postimage_file/postimage_sha256")
    for value in (spec["text_sha256"], index["preimage_sha256"], index["postimage_sha256"]):
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise Refused("promotion digests must be sha256:<64 lowercase hex>")
    if not isinstance(spec["text_file"], str) or not spec["text_file"]:
        raise Refused("expected text: text_file")
    public_locator(spec["locator"])
    if spec["coverage"] not in ("full", "partial", "excerpt"):
        raise Refused("promotion coverage must be full, partial or excerpt")
    try:
        if not isinstance(spec["date"], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", spec["date"]):
            raise ValueError(spec["date"])
        datetime.strptime(spec["date"], "%Y-%m-%d")
    except ValueError as exc:
        raise Refused("promotion date must be YYYY-MM-DD") from exc


def parse_update(data):
    """Hash-guarded whole-note update member; content comes only from the reviewed postimage file."""
    if (not isinstance(data, dict) or set(data) - UPDATE_KEYS or not {"update_path", "preimage_sha256", "postimage_file", "postimage_sha256"} <= set(data)
            or ("preserve" in data) == ("promotion" in data)):
        raise Refused("update requires exactly update_path/preimage_sha256/postimage_file/postimage_sha256 and one of preserve/promotion [analyses/obtained_at/purpose/purpose_origin]")
    data = dict(data)
    for key in ("update_path", "postimage_file"):
        if not isinstance(data[key], str) or not data[key]:
            raise Refused("expected text: " + key)
    for key in ("preimage_sha256", "postimage_sha256"):
        if not isinstance(data[key], str) or not SHA256.fullmatch(data[key]):
            raise Refused(key + " must be sha256:<64 lowercase hex>")
    purpose_checked(data)
    if "promotion" in data:
        parse_promotion(data["promotion"])
        data["preserve"] = []
    preserve = data["preserve"]
    if "promotion" not in data and (not isinstance(preserve, list) or not preserve):
        raise Refused("preserve must be a nonempty list")
    for block in preserve:
        if (not isinstance(block, dict) or set(block) != {"block", "start", "end", "sha256"} or block["block"] not in ("original_content", "body")
                or type(block["start"]) is not int or type(block["end"]) is not int or not isinstance(block["sha256"], str) or not SHA256.fullmatch(block["sha256"])):
            raise Refused("preserve entries require block (original_content/body), integer start/end and sha256")
    data.setdefault("analyses", [])
    if not isinstance(data["analyses"], list):
        raise Refused("expected list: analyses")
    if data["analyses"]:
        if not isinstance(data.get("obtained_at"), str):
            raise Refused("analyses require obtained_at")
        try:
            datetime.fromisoformat(data["obtained_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise Refused("obtained_at must be ISO 8601") from exc
    return data


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "pre"):
            self.fragments.append("\n")
        if tag == "a":
            self.fragments.append(" [" + dict(attrs).get("href", "") + "] ")
        if tag == "img":
            self.fragments.append(" [image: " + repr(dict(attrs)) + "] ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.fragments.append(data)


def read_file(vault, name):
    path = target(vault, name)
    if not path.is_file():
        raise Refused("source must be a regular file")
    return path.read_bytes()


def outside_file(vault, name, expected):
    """Bytes of a caller-reviewed absolute regular file outside the vault, bound to its digest."""
    path = Path(name)
    # realpath equality refuses relative paths, `..` traversal and a symlink in any component.
    if not path.is_absolute() or str(path) != name or os.path.realpath(name) != name:
        raise Refused("outside file must be a canonical absolute path without symlinks: " + name)
    if path == vault or vault in path.parents:
        raise Refused("outside file must not be inside the vault: " + name)
    if not path.is_file():
        raise Refused("outside file must be a regular file: " + name)
    blob = path.read_bytes()
    if digest(blob) != expected:
        raise Refused("outside file digest mismatch: " + name)
    return blob


def fetch(locator):
    public_locator(locator)
    with urlopen(Request(locator, headers={"User-Agent": "secondbrain-ingest"}), timeout=30) as response:
        public_locator(response.geturl())
        if response.headers.get_content_type() not in ("text/html", "text/plain", "text/markdown"):
            raise Refused("provide converted text and retain original attachment")
        return response.read()


def candidate(vault, request):
    blob = read_file(vault, request["locator"])
    fields = metadata(blob)
    members = fields.get("capture_sources")
    if fields.get("capture_schema") != "capture/candidate@1" or not isinstance(members, list):
        raise Refused("candidate must use capture/candidate@1")
    index = request.get("candidate_index", 0 if len(members) == 1 else None)
    if type(index) is not int or not 0 <= index < len(members):
        raise Refused("select an available candidate_index")
    member = members[index]
    effective = dict(request)
    for dest, key in (("locator", "source_locator"), ("identity", "source_identity"), ("source_kind", "source_kind"), ("extraction", "source_extraction"), ("obtained_at", "source_obtained_at"), ("text", "original_content"), ("coverage", "fidelity"), ("omissions", "fidelity_omissions"), ("conversion", "fidelity_conversion")):
        effective[dest] = member.get(key, effective.get(dest))
    if request.get("selection") or effective["source_kind"] != request["source_kind"]:
        raise Refused("candidate kind/selection disagrees")
    effective["source_input"] = "text"
    effective = parse(effective)
    return effective, blob


def read_source(vault, request):
    blob = {"text": lambda: request["text"].encode("utf-8"), "file": lambda: read_file(vault, request["locator"]), "url": lambda: fetch(request["locator"])}[request["source_input"]]()
    text = blob.decode("utf-8")
    extraction, conversion = request["extraction"], list(request["conversion"])
    if text.lstrip().lower().startswith(("<!doctype html", "<html")):
        if not request["attachment_path"]:
            raise Refused("HTML requires original attachment path")
        parser = HTMLText()
        parser.feed(text)
        text = "".join(parser.fragments).strip()
        extraction = "reader"
        conversion.append({"tool": "stdlib HTMLParser", "from": "html", "to": "text"})
    omissions, coverage = list(request["omissions"]), request["coverage"]
    if request.get("selection"):
        first, last = request["selection"]
        lines = text.splitlines(keepends=True)
        if last > len(lines):
            raise Refused("selection exceeds obtained content")
        text = "".join(lines[first - 1:last])
        if first > 1:
            omissions.append("lines 1-{} outside selection".format(first - 1))
        if last < len(lines):
            omissions.append("lines {}-{} outside selection".format(last + 1, len(lines)))
        if omissions:
            coverage = "excerpt"
    if (not text.strip() and coverage != "manifest-only") or (coverage == "manifest-only" and text):
        raise Refused("no content or conflicting manifest-only content")
    return {"body": text, "original": blob, "extraction": extraction, "conversion": conversion, "coverage": coverage, "omissions": omissions}
