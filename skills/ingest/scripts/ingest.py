#!/usr/bin/env python3
"""Preflight/apply exact package-local writes. Git orchestration is a caller seam."""
import argparse
import base64
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from urllib.error import URLError
from urllib.parse import parse_qsl, quote, urlsplit
from source import Refused, body_offset, candidate, digest, identity, metadata, note, outside_file, parse, parse_update, public_locator, read_source, target

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
ORIGINAL_HEADING = re.compile(rb"(?m)^## Original Content[ \t]*\r?\n(?:[ \t]*\r?\n)?")
IDENTITY_FIELDS = ("source_identity", "source_locator", "source_url")
# Roles to which the frontmatter table applies identity fields (Raw types, legacy `raw`, Paper hub, books).
IDENTITY_TYPES = {"raw", "article", "video", "paper", "book", "repo", "mail", "chat"}
# Raw role for the original-order prefix rule: the canonical Raw leaf, or a type no Paper hub, Book or Concept uses.
# `paper`/`book` are shared with Paper hubs, so outside the Raw leaf only a body Original Content heading marks them Raw.
RAW_ROOT = "10. Raw Sources/"
RAW_ONLY_TYPES = {"raw", "article", "video", "repo", "mail", "chat"}
LINK_FIELDS = ("author", "referenced", "source", "related")
# Explicit allow-list of mothership vault names accepted in `obsidian://open` deeplinks.
MOTHERSHIP_VAULTS = ("Ataraxia",)

RAW_FIELDS = {"tags", "type", "date_created", "date_modified", "created_by", "authorship", "model", "effort", "aliases", "description", "author", "source_url", "source_locator", "source_identity", "source_input", "source_kind", "source_extraction", "source_obtained_at", "date_published", "referenced", "purpose", "purpose_origin", "source_attachment", "mothership", "isbn", "doi", "citekey", "venue"}


def link(name):
    if any(c in name for c in "[]|#\n\r"):
        raise Refused("unrepresentable wikilink")
    return "[[" + (name[:-3] if name.endswith(".md") else name) + "]]"


def same_source(fields, request):
    for key, value in (("source_identity", request["identity"]), ("source_url", request["locator"]), ("source_locator", request["locator"])):
        if fields.get(key) and value:
            return fields[key] == value
    return False


def link_list(fields, key):
    """Vault-relative `.md` targets of a plain-wikilink list field; absent means none."""
    if key not in fields:
        return []
    value = fields[key]
    if not isinstance(value, list):
        raise Refused(key + " must be a list of plain [[path]] wikilinks")
    return [wikilink_target(item) for item in value]


def exact_entry(parent, part):
    """lstat of `parent/part` only when that exact (case-sensitive) name is listed; never follows links."""
    try:
        if part not in os.listdir(parent):
            return None
        return os.lstat(os.path.join(parent, part))
    except FileNotFoundError:
        return None


def exact_file(root, relative):
    """True when `relative` names a regular file under `root` with exact names and no symlink component."""
    parent = str(root)
    parts = relative.split("/")
    for index, part in enumerate(parts):
        info = exact_entry(parent, part)
        if info is None:
            return False
        if stat.S_ISLNK(info.st_mode):
            raise Refused("symlink in path: " + relative)
        if index + 1 < len(parts) and not stat.S_ISDIR(info.st_mode):
            return False
        parent = os.path.join(parent, part)
    return stat.S_ISREG(info.st_mode)


def resolve_links(vault, links, staged):
    """Every wikilink target must be exactly one existing regular file or a path written by this session."""
    for name in links:
        target(vault, name)
        bare = name[:-3]
        found = name in staged or exact_file(vault, name)
        if not found:
            raise Refused("link target neither exists nor is written by this ingest: " + name)
        if bare in staged or exact_file(vault, bare):
            raise Refused("ambiguous link target: " + name + " and " + bare)


def mothership_root(vault, root):
    """Explicit read-only mothership vault root: canonical absolute directory, disjoint from the destination vault."""
    name = str(root)
    if not root.is_absolute() or os.path.realpath(name) != name or not root.is_dir():
        raise Refused("mothership root must be a canonical absolute directory without symlinks: " + name)
    if root == vault or vault in root.parents or root in vault.parents:
        raise Refused("mothership root must be disjoint from the destination vault")
    if root.name not in MOTHERSHIP_VAULTS:
        raise Refused("mothership root is not an allowed vault: " + root.name)
    return root


def verify_mothership(mothership, links, known=()):
    """Each new deeplink must be canonical `obsidian://open?vault=<allowed>&file=<path>` naming one stat'ed regular file.

    Only lstat/listdir run against the mothership; its files are never opened or written.
    """
    if not isinstance(links, list) or any(not isinstance(v, str) or not v for v in links) or len(set(links)) != len(links):
        raise Refused("mothership must be a list of unique deeplinks")
    for value in links:
        if value in known:
            continue
        if mothership is None or mothership.get("root") is None:
            raise Refused("mothership links require --mothership-root for stat verification")
        parts = urlsplit(value)
        try:
            query = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise Refused("malformed mothership deeplink: " + value) from exc
        if parts.scheme != "obsidian" or parts.netloc != "open" or parts.path or parts.fragment or [k for k, _ in query] != ["vault", "file"]:
            raise Refused("mothership entries must be obsidian://open?vault=…&file=… deeplinks: " + value)
        vault_name, name = query[0][1], query[1][1]
        if value != "obsidian://open?vault=" + quote(vault_name, safe="") + "&file=" + quote(name, safe=""):
            raise Refused("mothership deeplink is not canonically encoded: " + value)
        if vault_name not in MOTHERSHIP_VAULTS or vault_name != mothership["root"].name:
            raise Refused("mothership deeplink names a vault other than the stat'ed root: " + vault_name)
        relative = Path(name).as_posix()
        if (not name or relative != name or name.startswith("/") or "\\" in name
                or any(not p or p in (".", "..") or p.startswith(".") for p in name.split("/"))):
            raise Refused("mothership file must be a canonical visible vault-relative path: " + name)
        candidates = [name] if name.endswith(".md") else [name, name + ".md"]
        matches = [c for c in candidates if exact_file(mothership["root"], c)]
        if len(matches) != 1:
            raise Refused(("ambiguous" if matches else "unverified") + " mothership target: " + name)
        mothership["verified"].append({"link": value, "file": matches[0], "check": "lstat regular file"})


def stage(vault, changes, name, after, mode="create", span=None):
    path = target(vault, name)
    if not path.parent.is_dir() or (path.exists() and not path.is_file()):
        raise Refused("destination parent missing or not a file: " + name)
    pending = next((r for r in changes if r["path"] == name), None)
    current = pending["after"] if pending else path.read_bytes() if path.exists() else None
    if mode == "create" and current is not None:
        if current == after:
            return
        raise Refused("exclusive destination collision: " + name)
    if mode == "append":
        if current is None:
            raise Refused("append target missing")
        if after in current:
            return
        after = current + after
    if current == after:
        return
    before = pending["before"] if pending else current
    row = {"path": name, "before": before, "after": after, "mode": mode, "span": span}
    if before is not None:
        row["body_start"] = body_offset(before)
        if mode == "metadata" and after[body_offset(after):] != before[row["body_start"]:]:
            raise Refused("metadata change altered body")
        if mode == "append" and not after[body_offset(after):].startswith(before[row["body_start"]:]):
            raise Refused("append changed body prefix")
    if pending:
        changes[changes.index(pending)] = row
    else:
        changes.append(row)


def core(request, kind, tags):
    date = request["obtained_at"].split("T", 1)[0]
    return {"tags": tags, "type": kind, "date_created": date, "date_modified": date, "created_by": "agent", "authorship": "agent", "model": "default", "effort": "default", "aliases": [], "description": ""}


def checked_quote(evidence, quote, anchor):
    """`evidence` is obtained text, or None when nothing citable was obtained (manifest-only)."""
    if evidence is None or not isinstance(quote, str) or not quote or not isinstance(anchor, str) or not anchor or quote not in evidence:
        raise Refused("analysis requires obtained quote and location")


def wikilink_target(value):
    match = re.fullmatch(r"\[\[([^\[\]|#\n\r]+)\]\]", value) if isinstance(value, str) else None
    if not match:
        raise Refused("link entries must be plain [[path]] wikilinks")
    return match.group(1) + ".md"


def render_entity(request, raw, analysis):
    """Fill the package entity template; its frontmatter keys and slots must match exactly."""
    template = (TEMPLATES / "entity.md").read_bytes()
    values = dict(core(request, "note", ["knowledge/entity"]), description=analysis["description"], source=[link(raw)], related=list(analysis["related"]),
                  mothership=list(analysis["mothership"]), explored=False)
    keys = list(metadata(template))
    if set(keys) != set(values):
        raise Refused("entity template fields differ from the renderer")
    quote = "> " + analysis["quote"].replace("\n", "\n> ")
    slots = {"name": Path(analysis["path"]).stem, "source_grounded_identity": analysis["body"],
             "attributed_facts": quote + "\n\n\u2014 " + link(raw) + " at " + analysis["anchor"],
             "verified_links": "\n".join("- " + item for item in analysis["related"]) or "None recorded.",
             "raw_links_and_anchors": "- " + link(raw) + " \u2014 " + analysis["anchor"]}
    body = template[body_offset(template):].decode("utf-8").lstrip("\n")
    found = set(re.findall(r"\{\{([a-z_]+)\}\}", body))
    if found != set(slots):
        raise Refused("entity template slots differ from the renderer")
    # Single pass: substituted values are never rescanned for slots.
    # `mothership` is optional: omitted unless verified deeplinks were supplied.
    return note({k: values[k] for k in keys if k != "mothership" or values[k]}, re.sub(r"\{\{([a-z_]+)\}\}", lambda m: slots[m.group(1)], body))


def render_concept(request, raw, analysis, text):
    """New Concept/atom note: exactly the concept template's frontmatter keys, in template order.

    The body is the source-grounded analysis; the template's synthesis sections (Overview, Bias Check, Open
    Questions, ...) are agent work an analysis does not supply, so the helper never fabricates them.
    """
    template = (TEMPLATES / "concept.md").read_bytes()
    values = dict(core(request, "note", ["knowledge/concept"]), description=analysis["description"], source=[link(raw)],
                  related=list(analysis["related"]), confidence=analysis["confidence"], explored=False)
    keys = list(metadata(template))
    if set(keys) != set(values):
        raise Refused("concept template fields differ from the renderer")
    return note({k: values[k] for k in keys}, text)


def one_line(value):
    return isinstance(value, str) and bool(value.strip()) and "\n" not in value and "\r" not in value


def compile_analyses(vault, request, raw, evidence, changes, links, mothership=None):
    for analysis in request["analyses"]:
        if not isinstance(analysis, dict) or not {"path", "body", "quote", "anchor", "role"} <= set(analysis):
            raise Refused("analysis requires path/body/quote/anchor/role")
        if analysis["role"] not in ("atom", "concept", "entity"):
            raise Refused("analysis role must be atom/concept/entity")
        extra = {"description", "related", "mothership"} if analysis["role"] == "entity" else {"description", "related", "confidence"}
        if set(analysis) - {"path", "body", "quote", "anchor", "role"} - extra:
            raise Refused("unknown analysis keys; mothership belongs to entity analyses, confidence to concept/atom analyses")
        if not isinstance(analysis["body"], str) or not analysis["body"].strip():
            raise Refused("analysis body must be nonempty text")
        checked_quote(evidence, analysis["quote"], analysis["anchor"])
        exists = target(vault, analysis["path"]).exists() or any(r["path"] == analysis["path"] for r in changes)
        text = "\n\n## Source-grounded analysis\n\n" + analysis["body"] + "\n\nSource: " + link(raw) + " at " + analysis["anchor"] + "\n\nQuote:\n> " + analysis["quote"].replace("\n", "\n> ") + "\n"
        if exists:
            # Existing pages only gain an appended analysis; frontmatter edits use an update member.
            if extra & set(analysis):
                raise Refused("description/related/mothership/confidence apply only to a new Entity or Concept; use an update member for an existing page")
            stage(vault, changes, analysis["path"], text.encode(), "append")
        elif analysis["role"] == "entity":
            analysis = dict(analysis, related=analysis.get("related", []), mothership=analysis.get("mothership", []))
            if not isinstance(analysis.get("description"), str) or not analysis["description"].strip() or "\n" in analysis["description"]:
                raise Refused("new Entity requires a one-line description")
            if not isinstance(analysis["related"], list):
                raise Refused("related must be a list")
            links.extend(wikilink_target(item) for item in analysis["related"])
            verify_mothership(mothership, analysis["mothership"])
            stage(vault, changes, analysis["path"], render_entity(request, raw, analysis))
        else:
            analysis = dict(analysis, description=analysis.get("description", ""), related=analysis.get("related", []))
            if not one_line(analysis.get("confidence")):
                raise Refused("new Concept requires an explicit one-line evidence-grounded confidence")
            if not isinstance(analysis["description"], str) or (analysis["description"] and not one_line(analysis["description"])):
                raise Refused("Concept description must be one line")
            if not isinstance(analysis["related"], list):
                raise Refused("related must be a list")
            links.extend(wikilink_target(item) for item in analysis["related"])
            stage(vault, changes, analysis["path"], render_concept(request, raw, analysis, text))


def original_spans(blob, start, end):
    """Original Content heading matches outside [start,end); quoted decoys inside a checked span are ignored."""
    return [m for m in ORIGINAL_HEADING.finditer(blob, body_offset(blob)) if m.end() <= start or m.start() >= end]


def identity_applies(fields, blob):
    """Raw, Paper hub and book notes carry identity; so does any note with an Original Content heading."""
    tags = fields.get("tags")
    tags = tags if isinstance(tags, list) else [tags]
    return (fields.get("type") in IDENTITY_TYPES or any(isinstance(t, str) and t.startswith("reference/") for t in tags)
            or ORIGINAL_HEADING.search(blob, body_offset(blob)) is not None)


def update(vault, member, changes, links, mothership=None):
    """Replace one existing note with a reviewed outside-vault postimage; nothing is appended automatically."""
    name = member["update_path"]
    path = target(vault, name)
    pending = next((r["after"] for r in changes if r["path"] == name), None)
    if pending is None and not path.is_file():
        raise Refused("update target must be an existing regular file: " + name)
    before = pending if pending is not None else path.read_bytes()
    if digest(before) != member["preimage_sha256"]:
        raise Refused("update preimage drift: " + name)
    after = outside_file(vault, member["postimage_file"], member["postimage_sha256"])
    before_fields, after_fields = metadata(before), metadata(after)
    # Nonempty identity is immutable everywhere; an empty legacy value may only be dropped (never changed)
    # where the frontmatter table does not apply identity fields (before and after).
    droppable = not identity_applies(before_fields, before) and not identity_applies(after_fields, after)
    for key in IDENTITY_FIELDS:
        if key not in before_fields or after_fields.get(key) == before_fields[key]:
            continue
        if not (droppable and before_fields[key] in ("", None) and key not in after_fields):
            raise Refused("update changes source identity field: " + key)
    for key in LINK_FIELDS:
        links.extend(link_list(after_fields, key))
    known = before_fields.get("mothership") if isinstance(before_fields.get("mothership"), list) else []
    verify_mothership(mothership, after_fields.get("mothership", []), known)
    if "promotion" in member:
        return promote(vault, member, before, after, changes, links, mothership)
    after_start, kept, evidence = body_offset(after), [], None
    for block in sorted(member["preserve"], key=lambda b: b["start"]):
        start, end = block["start"], block["end"]
        if not body_offset(before) <= start < end <= len(before) or digest(before[start:end]) != block["sha256"]:
            raise Refused("preserved span outside body or hash mismatch: [%d,%d)" % (start, end))
        if kept and start < kept[-1][1]:
            raise Refused("preserved spans overlap")
        protected = before[start:end]
        if block["block"] == "original_content":
            if evidence is not None:
                raise Refused("only one Original Content span may be preserved")
            headings = original_spans(before, start, end)
            if len(headings) != 1 or headings[0].end() != start:
                raise Refused("Original Content heading missing or ambiguous before span")
            protected = before[headings[0].start():end]
            evidence = before[start:end].decode("utf-8")
        if after.count(protected, after_start) != 1:
            raise Refused("preserved block missing or ambiguous in postimage: [%d,%d)" % (start, end))
        offset = after.index(protected, after_start)
        if block["block"] == "original_content":
            moved = offset + len(protected) - (end - start)
            if len(original_spans(after, moved, moved + end - start)) != 1:
                raise Refused("postimage adds another Original Content heading")
        kept.append((start, end, offset + len(protected) - (end - start)))
    if evidence is None and ORIGINAL_HEADING.search(before, body_offset(before)):
        raise Refused("Raw update must preserve its Original Content span")
    # Every Raw, legacy ones without an Original Content heading included, keeps every current body byte as an
    # unchanged prefix: metadata may be replaced and notes appended, but a correctly hashed shorter span must not
    # let the rest of the existing body be dropped, edited or reordered.
    raw = evidence is not None or name.startswith(RAW_ROOT) or before_fields.get("type") in RAW_ONLY_TYPES
    if raw and not after.startswith(before[body_offset(before):], after_start):
        raise Refused("Raw update must keep the complete current body as an unchanged prefix of the postimage body")
    # Appended notes never fabricate Original Content that later quotes could be grounded in.
    if raw and len(ORIGINAL_HEADING.findall(after, after_start)) > len(ORIGINAL_HEADING.findall(before, body_offset(before))):
        raise Refused("Raw update appends an Original Content heading")
    if evidence is None and member["purpose_origin"] == "unknown":
        raise Refused("unknown purpose permits preservation only")
    if member["analyses"]:
        if member["purpose_origin"] == "unknown":
            raise Refused("unknown purpose permits preservation only")
        if any(a.get("path") == name for a in member["analyses"] if isinstance(a, dict)):
            raise Refused("an update member's analyses cannot target its own update_path")
        compile_analyses(vault, member, name, evidence, changes, links, mothership)
    stage(vault, changes, name, after, "update")
    return {"update_path": name, "preimage": digest(before), "postimage": digest(after),
            "preserved": [{"before": [s, e], "after": [o, o + e - s]} for s, e, o in kept]}


def patch_fields(blob, updates):
    """Replace designated scalar keys only; leave all other YAML bytes untouched."""
    import re
    metadata(blob)
    end = body_offset(blob)
    header, body = blob[:end], blob[end:]
    newline = b"\r\n" if header.startswith(b"---\r\n") else b"\n"
    for key, value in updates.items():
        line = (key + ": " + json.dumps(value, ensure_ascii=False)).encode("utf-8") + newline
        pattern = rb"(?m)^" + re.escape(key.encode()) + rb":[^\r\n]*(?:\r?\n)(?:(?:[ \t]+[^\r\n]*|- [^\r\n]*)(?:\r?\n))*"
        if len(re.findall(pattern, header)) != 1:
            raise Refused("updated scalar key missing or ambiguous: " + key)
        header = re.sub(pattern, lambda match: line, header)
    result = header + body
    fields = metadata(result)
    if any(fields.get(k) != v for k, v in updates.items()):
        raise Refused("scalar patch verification failed")
    return result


def stub_placeholder():
    """The pending-fill placeholder of the package chapter template: its whole Original Content section text."""
    template = (TEMPLATES / "book-chapter.md").read_bytes()
    match = re.search(rb"^## Original Content\n\n(.*?)\n\n## ", template, re.M | re.S)
    if not match or b"STUB: pending verbatim fill" not in match.group(1) or b"{{" in match.group(1):
        raise Refused("chapter template lacks the pending-fill placeholder")
    return match.group(1)


def book_chapters(request):
    """Validated TOC chapters; a locator is kept only when the request supplies it as obtained evidence."""
    if not request["chapters"]:
        return []
    if request["source_kind"] != "book" or not request["raw_path"].endswith(".md"):
        raise Refused("chapters belong only to a book whose Index is a .md note")
    if "book_title" not in request:
        raise Refused("a chapter scaffold requires book_title: the exact obtained one-line book title")
    seen, part, chapters = {request["raw_path"]}, "", []
    for chapter in request["chapters"]:
        if (not isinstance(chapter, dict) or set(chapter) - {"path", "title", "part", "locator", "toc_description"} or not isinstance(chapter.get("path"), str)
                or not chapter["path"].endswith(".md") or not isinstance(chapter.get("title"), str) or not chapter["title"].strip()
                or "\n" in chapter["title"] or "\r" in chapter["title"]):
            raise Refused("chapter requires explicit .md path/single-line title and optional part/locator/toc_description")
        described = chapter.get("toc_description")
        if "toc_description" in chapter and (not isinstance(described, str) or not described.strip() or "\n" in described or "\r" in described):
            raise Refused("chapter toc_description must be nonempty one-line obtained text; omit it when the source supplies none")
        current = chapter.get("part", "")
        if not isinstance(current, str) or "\n" in current or "\r" in current:
            raise Refused("chapter part must be single-line text")
        if part and not current:
            raise Refused("an unparted chapter cannot follow a part heading in the TOC")
        if chapter["path"] in seen:
            raise Refused("duplicate chapter path or chapter equals the Book Index: " + chapter["path"])
        seen.add(chapter["path"])
        part = current
        locator = public_locator(chapter["locator"]) if "locator" in chapter else None
        chapters.append({"path": chapter["path"], "title": chapter["title"], "part": current, "locator": locator, "toc_description": described})
    return chapters


def fill(text, slots):
    # Single pass: substituted values are never rescanned for slots.
    return re.sub(r"\{\{([a-z_]+)\}\}", lambda m: slots[m.group(1)], text)


def template_parts(name, divider):
    """Template frontmatter keys and the body split around the one span the renderer records."""
    template = (TEMPLATES / name).read_bytes()
    body = template[body_offset(template):].decode("utf-8").lstrip("\n")
    if body.count(divider) != 1:
        raise Refused(name + " lacks its single recorded span")
    head, tail = body.split(divider)
    return list(metadata(template)), head, tail


NO_READING_PATHS = "Not recorded: this scaffold request supplied no author-provided reading paths."
UNAVAILABLE_READING_PATHS = "Not recorded: the caller reported author-provided reading paths as unavailable; none inferred."
NO_TOC_DESCRIPTION = "Not recorded: the TOC source supplied no one-line description for this chapter; only its title is TOC evidence."


def reading_paths_state(request):
    if "reading_paths" not in request:
        return "not-supplied"
    return "unavailable" if request["reading_paths"] is None else "supplied"


def render_book_index(request, fields, raw, preface, chapters, notes):
    """templates/book-index.md: verbatim preface under Original Content, then TOC, Reading Paths, Progress Tracking, Ingest Notes."""
    keys, head, tail = template_parts("book-index.md", "{{verbatim_preface}}")
    toc_block = "### {{part_in_original_language}}\n\n- [ ] [[{{chapter_stub}}]] — {{verbatim_toc_one_liner}}"
    row_block = "| {{number}} | [[{{chapter_stub}}]] | stub | — |"
    if tail.count(toc_block) != 1 or tail.count(row_block) != 1:
        raise Refused("book index template TOC/Progress blocks changed")
    tail = tail.replace(toc_block, "{{toc}}").replace(row_block, "{{rows}}")
    toc, part = [], ""
    for chapter in chapters:
        if chapter["part"] != part:
            part = chapter["part"]
            toc += ([""] if toc else []) + ["### " + part, ""]
        # The TOC entry is the obtained title, followed by the obtained one-liner only when the source supplied one.
        toc.append("- [ ] " + link(chapter["path"]) + " — " + chapter["title"] + (" — " + chapter["toc_description"] if chapter["toc_description"] else ""))
    located = sum(1 for c in chapters if c["locator"])
    described = sum(1 for c in chapters if c["toc_description"])
    state = reading_paths_state(request)
    notes = (notes[len("## Ingest Notes\n\n"):].rstrip("\n") + "\nChapter locators: %d of %d supplied as obtained evidence; none inferred." % (located, len(chapters))
             + "\nChapter TOC descriptions: %d of %d supplied as obtained text; none inferred." % (described, len(chapters))
             + "\nReading Paths: " + {"supplied": "supplied verbatim by the caller.", "unavailable": "reported unavailable by the caller; none inferred.",
                                     "not-supplied": "not supplied; none inferred."}[state])
    slots = {"book_title": request["book_title"], "toc": "\n".join(toc),
             "author_provided_reading_paths_verbatim_if_present": {"supplied": request.get("reading_paths"), "unavailable": UNAVAILABLE_READING_PATHS,
                                                                   "not-supplied": NO_READING_PATHS}[state],
             "rows": "\n".join("| %d | %s | stub | — |" % (i + 1, link(c["path"])) for i, c in enumerate(chapters)),
             "verified_url_pattern_and_coverage_limits": notes}
    if set(re.findall(r"\{\{([a-z_]+)\}\}", head + tail)) != set(slots):
        raise Refused("book index template slots differ from the renderer")
    fields = dict(fields)
    for key in keys:
        fields.setdefault(key, None)
    prefix = note(fields, fill(head, slots))
    return prefix + preface + fill(tail, slots).encode("utf-8"), [len(prefix), len(prefix) + len(preface)]


def render_chapter(request, raw, chapters, number, published):
    """templates/book-chapter.md stub; navigation is the adjacent TOC chapter, null at both endpoints."""
    placeholder = stub_placeholder().decode("utf-8")
    keys, head, tail = template_parts("book-chapter.md", placeholder)
    chapter = chapters[number - 1]
    locator = chapter["locator"]
    url = locator if locator and locator.startswith(("http://", "https://")) else None
    prev = link(chapters[number - 2]["path"]) if number > 1 else None
    following = link(chapters[number]["path"]) if number < len(chapters) else None
    # description is the obtained TOC one-liner only; a title is never relabelled as one.
    values = dict(core(request, "book", ["reference/book"]), status="stub", description=chapter["toc_description"] or "", author=list(request["author"]),
                  source_url=url, source_identity=identity(locator) if locator else "", source_locator=locator, source_input="url" if url else None,
                  source_kind="book", source_extraction="none", source_obtained_at=request["obtained_at"], date_published=published,
                  purpose=request["purpose"], purpose_origin="reused" if request["purpose"] else "unknown", bookIndex=link(raw),
                  chapterNumber=number, chapterPart=chapter["part"], chapterPrev=prev, chapterNext=following)
    if set(keys) != set(values):
        raise Refused("book chapter template fields differ from the renderer")
    slots = {"full_chapter_title": chapter["title"], "verbatim_toc_one_liner": chapter["toc_description"] or NO_TOC_DESCRIPTION, "book_index": raw[:-3], "human_notes_preserved": "",
             "verified_direct_chapter_url": url or "Not recorded: no direct chapter URL was supplied as obtained evidence.",
             "verified_chapter_links_or_null": (prev or "null") + " / " + (following or "null")}
    if set(re.findall(r"\{\{([a-z_]+)\}\}", head + tail)) != set(slots):
        raise Refused("book chapter template slots differ from the renderer")
    prefix = note({k: values[k] for k in keys}, fill(head, slots))
    return prefix + placeholder.encode("utf-8") + fill(tail, slots).encode("utf-8"), [len(prefix), len(prefix) + len(placeholder.encode("utf-8"))]


def resolve_note(vault, value, home, staged):
    """A plain wikilink resolves to exactly one regular note: its vault-relative path or, for a bare name, a sibling of `home`."""
    name = wikilink_target(value)
    candidates = {name} if "/" in name else {name, (PurePosixPath(home).parent / name).as_posix()}
    found = []
    for candidate_path in sorted(candidates):
        target(vault, candidate_path)
        if candidate_path in staged or exact_file(vault, candidate_path):
            found.append(candidate_path)
        if candidate_path[:-3] in staged or exact_file(vault, candidate_path[:-3]):
            raise Refused("ambiguous link target: " + value)
    if len(found) != 1:
        raise Refused(("ambiguous" if found else "unresolved") + " link target: " + value)
    return found[0]


def names(value, path, home):
    """A plain wikilink names `path` by vault-relative stem, or by basename when it lives beside `home`."""
    found = wikilink_target(value)
    return found == path or (found == PurePosixPath(path).name and PurePosixPath(path).parent == PurePosixPath(home).parent)


def section(body, position):
    headings = re.findall(rb"(?m)^## ([^\r\n]*)", body[:position])
    return headings[-1].strip() if headings else None


def index_progress(vault, chapter, fields, spec, status, changes):
    """Exact Index edit for one read chapter: its TOC checkbox and its stub Progress row; nothing else."""
    meta = spec["index"]
    name = meta["path"]
    path = target(vault, name)
    pending = next((r["after"] for r in changes if r["path"] == name), None)
    if name == chapter or (pending is None and not path.is_file()):
        raise Refused("promotion index must be another existing regular file: " + name)
    before = pending if pending is not None else path.read_bytes()
    if digest(before) != meta["preimage_sha256"]:
        raise Refused("index preimage drift: " + name)
    index_fields = metadata(before)
    if index_fields.get("type") != "book" or "status" in index_fields or "chapterNumber" in index_fields:
        raise Refused("promotion index is not a Book Index (type book, no status/chapterNumber): " + name)
    if not names(fields["bookIndex"], name, chapter):
        raise Refused("chapter bookIndex does not name the promotion index")
    start = body_offset(before)
    body = before[start:]
    toc = [m for m in re.finditer(rb"(?m)^- \[([ x])\] \[\[([^\[\]|#\r\n]+)\]\]", body) if names("[[" + m.group(2).decode("utf-8") + "]]", chapter, name)]
    rows = [m for m in re.finditer(rb"(?m)^\|[ \t]*([0-9]+)[ \t]*\|[ \t]*\[\[([^\[\]|#\r\n]+)\]\][^\r\n]*", body) if names("[[" + m.group(2).decode("utf-8") + "]]", chapter, name)]
    if len(toc) != 1 or toc[0].group(1) != b" " or section(body, toc[0].start()) != b"TOC":
        raise Refused("Index needs exactly one unchecked TOC entry for the chapter under ## TOC")
    label = "[[" + rows[0].group(2).decode("utf-8") + "]]" if len(rows) == 1 else ""
    stub_row = "| %d | %s | stub | — |" % (fields["chapterNumber"], label)
    if len(rows) != 1 or rows[0].group(0).decode("utf-8") != stub_row or section(body, rows[0].start()) != b"Progress Tracking":
        raise Refused("Index needs exactly one `| N | [[chapter]] | stub | — |` row under ## Progress Tracking")
    staged = {r["path"] for r in changes if r["after"] is not None}
    if resolve_note(vault, fields["bookIndex"], chapter, staged) != name:
        raise Refused("chapter bookIndex does not resolve to the promotion index")
    entries = [m for m in re.finditer(rb"(?m)^- \[[ x]\] \[\[([^\[\]|#\r\n]+)\]\]", body) if section(body, m.start()) == b"TOC"]
    position = next(i for i, m in enumerate(entries) if m.start() == toc[0].start())
    for key, near in (("chapterPrev", position - 1), ("chapterNext", position + 1)):
        expected = resolve_note(vault, "[[" + entries[near].group(1).decode("utf-8") + "]]", name, staged) if 0 <= near < len(entries) else None
        if (None if fields[key] is None else resolve_note(vault, fields[key], chapter, staged)) != expected:
            raise Refused(key + " must resolve to the adjacent Index TOC chapter (null at the endpoints)")
    row = rows[0]
    edited = body[:row.start()] + ("| %d | %s | %s | %s |" % (fields["chapterNumber"], label, status, spec["date"])).encode("utf-8") + body[row.end():]
    # The actually read chapter is checked for reading and completed alike; the row status keeps partial coverage explicit.
    box = toc[0].start(1)
    edited = edited[:box] + b"x" + edited[box + 1:]
    after = outside_file(vault, meta["postimage_file"], meta["postimage_sha256"])
    if after != before[:start] + edited:
        raise Refused("index postimage must change only the chapter's TOC checkbox and Progress row")
    stage(vault, changes, name, after, "update")
    return {"path": name, "preimage": digest(before), "postimage": digest(after)}


def promote(vault, member, before, after, changes, links, mothership):
    """Approved Book chapter promotion: replace only the recorded template placeholder with the acquired text."""
    name, spec = member["update_path"], member["promotion"]
    if member["purpose_origin"] == "unknown":
        raise Refused("unknown purpose cannot promote a chapter")
    fields = metadata(before)
    if fields.get("type") != "book" or fields.get("status") != "stub":
        raise Refused("promotion requires a Book chapter stub (type book, status stub)")
    number = fields.get("chapterNumber")
    if (type(number) is not int or number < 1 or not isinstance(fields.get("chapterPart"), str) or not isinstance(fields.get("bookIndex"), str)
            or any(k not in fields or (fields[k] is not None and not isinstance(fields[k], str)) for k in ("chapterPrev", "chapterNext"))):
        raise Refused("promotion requires valid bookIndex/chapterNumber/chapterPart/chapterPrev/chapterNext")
    for key in ("bookIndex", "chapterPrev", "chapterNext"):
        if fields[key] is not None:
            wikilink_target(fields[key])
    recorded = fields.get("source_locator") or fields.get("source_url")
    if not recorded or spec["locator"] != recorded:
        raise Refused("promotion locator differs from the stub's recorded source locator")
    start, end = spec["placeholder"]["start"], spec["placeholder"]["end"]
    placeholder = stub_placeholder()
    if not body_offset(before) <= start < end <= len(before) or digest(before[start:end]) != spec["placeholder"]["sha256"] or before[start:end] != placeholder:
        raise Refused("promotion span is not the template pending-fill placeholder: [%d,%d)" % (start, end))
    headings = original_spans(before, start, end)
    if len(headings) != 1 or headings[0].end() != start or not re.match(rb"(?:\r?\n)*(?:## |\Z)", before[end:]):
        raise Refused("promotion placeholder must be the whole Original Content section")
    text = outside_file(vault, spec["text_file"], spec["text_sha256"])
    evidence = text.decode("utf-8")
    if not evidence.strip() or placeholder in text:
        raise Refused("acquired chapter text is empty or still the placeholder")
    status = "completed" if spec["coverage"] == "full" else "reading"
    # The postimage is fully determined: placeholder -> acquired bytes, plus status/date_modified; every other byte stays.
    expected = patch_fields(before[:start] + text + before[end:], {"status": status, "date_modified": spec["date"]})
    if after != expected:
        raise Refused("promotion postimage must equal the preimage with only the placeholder replaced by the acquired text and status/date_modified set")
    index = index_progress(vault, name, fields, spec, status, changes)
    if member["analyses"]:
        if any(a.get("path") in (name, index["path"]) for a in member["analyses"] if isinstance(a, dict)):
            raise Refused("promotion analyses cannot target the chapter or its index")
        compile_analyses(vault, member, name, evidence, changes, links, mothership)
    offset = body_offset(after) - body_offset(before)
    stage(vault, changes, name, after, "update", [start + offset, start + offset + len(text)])
    return {"update_path": name, "preimage": digest(before), "postimage": digest(after), "status": status, "coverage": spec["coverage"],
            "placeholder": [start, end], "text": [start + offset, start + offset + len(text)], "text_sha256": spec["text_sha256"], "index": index}


def build(vault, request, changes, inputs, captures, links=None, mothership=None):
    links = [] if links is None else links
    original_input, original_locator = request["source_input"], request["locator"]
    if original_input in ("file", "candidate"):
        inputs[original_locator] = target(vault, original_locator).read_bytes()
    if original_input == "candidate":
        request, _ = candidate(vault, request)
    source = read_source(vault, request)
    if request["purpose_origin"] == "unknown" and (request["wiki_path"] or request["analyses"] or request["persona_path"]):
        raise Refused("unknown purpose permits preservation only")
    raw = request["raw_path"]
    chapters, published = book_chapters(request), None
    reused = False
    # An explicitly new Raw is never redirected to an older capture (better extraction).
    existing = target(vault, raw)
    staged = next((r["after"] for r in changes if r["path"] == raw), None)
    if existing.exists() or staged is not None:
        fields = metadata(staged if staged is not None else existing.read_bytes())
        if not same_source(fields, request):
            raise Refused("Raw belongs to a different source")
        if fields.get("status") == "stub":
            raise Refused("a Book chapter stub gains evidence only through an approved promotion update")
        if chapters:
            raise Refused("a chapter scaffold requires a new Book Index Raw")
        reused = True
    notes = ("## Ingest Notes\n\nExtraction: " + source["extraction"] + "\nConversion: "
             + json.dumps(source["conversion"], ensure_ascii=False) + "\nCoverage: " + source["coverage"]
             + "\nOmissions: " + json.dumps(source["omissions"], ensure_ascii=False) + "\n")
    if request["notes"]:
        # Caller-authored acquisition narrative, rendered for every coverage level.
        notes += "Notes:\n" + "".join("- " + item.replace("\n", "\n  ") + "\n" for item in request["notes"])
    notes += "\n"
    if reused:
        addition = ("\n\n## Additional selected evidence\n\n" + notes + source["body"]).encode("utf-8")
        stage(vault, changes, raw, addition, "append")
    else:
        raw_type = {"repository": "repo", "conversation": "chat"}.get(request["source_kind"], request["source_kind"])
        fields = core(request, raw_type, ["reference/" + raw_type])
        fields.update({"author": request["author"], "source_locator": request["locator"], "source_identity": request["identity"], "source_input": original_input, "source_kind": request["source_kind"], "source_extraction": source["extraction"], "source_obtained_at": request["obtained_at"], "referenced": request["referenced"], "purpose": request["purpose"], "purpose_origin": request["purpose_origin"]})
        if request["locator"].startswith(("http://", "https://")):
            fields["source_url"] = request["locator"]
        if request["attachment_path"]:
            fields["source_attachment"] = request["attachment_path"]
        extra = request.get("note_fields", {}).get(raw, {})
        if not isinstance(extra, dict) or set(extra) - RAW_FIELDS:
            raise Refused("unsupported Raw metadata")
        fields.update(extra)
        for key in ("author", "referenced"):
            links.extend(link_list(fields, key))
        verify_mothership(mothership, fields.get("mothership", []))
        selected = source["body"].encode("utf-8")
        if chapters:
            blob, span = render_book_index(request, fields, raw, selected, chapters, notes)
            published = fields.get("date_published")
        else:
            prefix = note(fields, notes + "## Original Content\n\n")
            blob, span = prefix + selected, [len(prefix), len(prefix) + len(selected)]
        stage(vault, changes, raw, blob, span=span)
        captures.append({"path": raw, "extent": span, "selected": selected, "input": original_locator if original_input in ("file", "candidate") else None})
    if request["attachment_path"]:
        if original_input in ("text", "candidate"):
            # Text input is already converted; the attachment must be the real original file, never the text.
            if not request["attachment_source"]:
                raise Refused("text input attachment_path requires attachment_source and attachment_sha256")
            original = outside_file(vault, request["attachment_source"], request["attachment_sha256"])
        elif request["attachment_source"]:
            raise Refused("attachment_source applies to text input only; file/url originals are the obtained bytes")
        else:
            original = source["original"]
        stage(vault, changes, request["attachment_path"], original)
    elif request["attachment_source"]:
        raise Refused("attachment_source requires attachment_path")
    for name in request["targets"]:
        if not target(vault, name).is_file():
            raise Refused("designated connection missing")
    compile_analyses(vault, request, raw, None if source["coverage"] == "manifest-only" else source["body"], changes, links, mothership)
    if request["wiki_path"]:
        if source["coverage"] == "manifest-only":
            raise Refused("manifest cannot support synthesis")
        fields = core(request, "paper" if request["source_kind"] == "paper" else "note", ["reference/paper"] if request["source_kind"] == "paper" else ["knowledge/entity"])
        if request["source_kind"] == "paper":
            fields["status"] = "todo"
        fields.update({"source_identity": request["identity"], "source_locator": request["locator"], "source": [link(raw)]})
        text = "\n\n## Captures\n\n- " + source["coverage"] + ": " + link(raw) + "\n\n" + "\n\n".join(a["body"] for a in request["analyses"])
        if request["targets"]:
            text += "\n\n## Designated connections\n\n" + "\n".join(link(n) for n in request["targets"])
        staged_wiki = next((r["after"] for r in changes if r["path"] == request["wiki_path"]), None)
        exists = target(vault, request["wiki_path"]).exists() or staged_wiki is not None
        current_wiki = staged_wiki if staged_wiki is not None else target(vault, request["wiki_path"]).read_bytes() if exists else None
        if exists and not same_source(metadata(current_wiki), request):
            raise Refused("compiled destination belongs to different source")
        if exists and request["source_kind"] == "paper":
            prior = current_wiki
            sources = metadata(prior).get("source", [])
            if not isinstance(sources, list):
                raise Refused("paper hub source must be a list")
            if link(raw) not in sources:
                revised = patch_fields(prior, {"source": sources + [link(raw)]})
                stage(vault, changes, request["wiki_path"], revised, "metadata")
        stage(vault, changes, request["wiki_path"], text.encode() if exists else note(fields, text), "append" if exists else "create")
    for number in range(1, len(chapters) + 1):
        stub, span = render_chapter(request, raw, chapters, number, published)
        stage(vault, changes, chapters[number - 1]["path"], stub, span=span)
    if chapters:
        # bookIndex/chapterPrev/chapterNext must resolve to exactly one note written by this session.
        links.extend([raw] + [c["path"] for c in chapters])
    if request["persona_path"]:
        checked_quote(None if source["coverage"] == "manifest-only" else source["body"], request["stance_quote"], request["stance_anchor"])
        persona = target(vault, request["persona_path"])
        if not persona.is_file() or metadata(persona.read_bytes()).get("type") != "persona" or not request["stance"]:
            raise Refused("existing Persona and attributed stance required")
        text = "\n\n## Citation and stance timeline\n\n" + json.dumps({"source": link(raw), "quote": request["stance_quote"], "anchor": request["stance_anchor"], "stance": request["stance"]}, ensure_ascii=False) + "\n"
        stage(vault, changes, request["persona_path"], text.encode(), "append")
    result = {"raw_path": raw, "reused": reused, "extraction": source["extraction"], "source_identity": request["identity"]}
    if chapters:
        result["book"] = {"title": request["book_title"], "reading_paths": reading_paths_state(request), "chapters": len(chapters),
                          "chapter_locators": sum(1 for c in chapters if c["locator"]),
                          "toc_descriptions_absent": [c["path"] for c in chapters if not c["toc_description"]]}
    return result


def receipt(row):
    return {"path": row["path"], "effect": "create" if row["before"] is None else "update", "preimage": "absent" if row["before"] is None else digest(row["before"]), "sha256": digest(row["after"]), "extent": row["span"]}


def apply(vault, changes, inputs, captures):
    for name, before in inputs.items():
        if target(vault, name).read_bytes() != before:
            raise Refused("input drift: " + name)
    for row in changes:
        path = target(vault, row["path"])
        current = path.read_bytes() if path.exists() else None
        if current != row["before"]:
            raise Refused("preimage drift: " + row["path"])
    completed = []
    try:
        for row in changes:
            path = target(vault, row["path"])
            if row["before"] is None:
                with path.open("xb") as stream:
                    stream.write(row["after"])
            else:
                if path.read_bytes() != row["before"]:
                    raise Refused("preimage drift: " + row["path"])
                fd, name = tempfile.mkstemp(prefix=".ingest-", dir=str(path.parent))
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(row["after"])
                    os.replace(name, path)
                finally:
                    if os.path.exists(name):
                        os.unlink(name)
            result = receipt(row)
            result["readback"] = digest(path.read_bytes())
            completed.append(result)
            if path.read_bytes() != row["after"]:
                raise Refused("readback mismatch: " + row["path"])
        for capture in captures:
            path = target(vault, capture["path"])
            start, end = capture["extent"]
            expected = next(r["after"] for r in changes if r["path"] == capture["path"])
            current = path.read_bytes()
            if current != expected or current[start:end] != capture["selected"]:
                raise Refused("capture span/postimage mismatch")
    except (OSError, Refused) as exc:
        raise Refused("partial apply; completed writes: " + json.dumps(completed) + "; " + str(exc)) from exc
    return completed


def state_encode(value):
    if isinstance(value, bytes):
        return {"bytes_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {k: state_encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [state_encode(v) for v in value]
    return value


def state_decode(value):
    if isinstance(value, dict):
        if set(value) == {"bytes_base64"}:
            return base64.b64decode(value["bytes_base64"], validate=True)
        return {k: state_decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [state_decode(v) for v in value]
    return value


def save_state(path, session):
    staged = str(path) + ".tmp"
    with open(staged, "w", encoding="utf-8") as stream:
        os.chmod(staged, 0o600)
        json.dump(state_encode(session), stream, ensure_ascii=False)
    os.replace(staged, str(path))


def git_apply(vault, session, state_path, title=None):
    """Opt-in Phase 3-b transaction; session state records written/committed-local/published."""
    import vaultgit
    first = session["members"][0]
    primary = first.get("raw_path") or first["update_path"]
    title = title or Path(primary).stem
    source = first.get("source_identity") or primary
    applied = []

    def write():
        applied.extend(apply(vault, session["changes"], session["inputs"], session["captures"]))
    result = vaultgit.transact(vault, session, write, lambda: save_state(state_path, session), title, source)
    result["applied"] = applied
    return result


def git_record_deletions(vault, session, state_path, deleted):
    """Commit `inbox delete`'s already-performed 5-C unlinks as one `inbox:` commit.

    Packages stay independent: inbox only unlinks and reports paths; this ingest-owned
    step records them with the vaultgit discipline. The deletion is treated as an
    already-written transaction: base must still hold the ingested input bytes and
    each path must be absent locally (ARCH-008 written-restart comparison).
    """
    import vaultgit
    if session.get("git", {}).get("state") != "published":
        raise Refused("ingest commit must be published before recording Inbox deletions")
    if not isinstance(deleted, list) or not deleted or len(set(deleted)) != len(deleted):
        raise Refused("deleted paths must be a nonempty unique list")
    captured = {c["input"] for c in session["captures"] if c.get("input")}
    for name in deleted:
        if name not in captured or name not in session["inputs"]:
            raise Refused("not an input captured by this ingest: " + name)
    record = session.setdefault("deletion", {"changes": [{"path": n, "before": session["inputs"][n], "after": None} for n in sorted(deleted)],
                                             "git": {"state": "written"}})
    if sorted(r["path"] for r in record["changes"]) != sorted(deleted):
        raise Refused("recorded deletion differs from the requested paths")
    title = "delete %d ingested originals" % len(deleted)
    return vaultgit.transact(vault, record, lambda: None, lambda: save_state(state_path, session), title, session["git"]["sha"], "inbox")


def plan(vault, document, mothership_dir=None):
    """Preflight a single member or a batch into one session; update members carry `update_path`."""
    changes, inputs, captures, results, links = [], {}, [], [], []
    mothership = {"root": None if mothership_dir is None else mothership_root(vault, mothership_dir), "verified": []}
    members = document.get("members") if isinstance(document, dict) else None
    if members is None:
        members = [document]
    elif not isinstance(members, list) or not members or set(document) - {"members", "purpose"} or not isinstance(document.get("purpose"), str) or not document["purpose"].strip():
        raise Refused("batch requires members and common purpose")
    for member in members:
        if not isinstance(member, dict):
            raise Refused("member must be a mapping")
        if "members" in document:
            member = dict(member, purpose=document["purpose"], purpose_origin="reused")
        if "update_path" in member:
            results.append(update(vault, parse_update(member), changes, links, mothership))
        else:
            results.append(build(vault, parse(member), changes, inputs, captures, links, mothership))
    resolve_links(vault, links, {r["path"] for r in changes if r["after"] is not None})
    return {"vault": str(vault), "changes": changes, "inputs": inputs, "captures": captures, "members": results,
            "mothership": mothership["verified"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--state", type=Path, help="preflight session JSON outside vault")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--apply-state", type=Path, help="apply exact previously reviewed session")
    parser.add_argument("--git", action="store_true", help="wrap apply in one ingest commit (vault = repo top level)")
    parser.add_argument("--record-deletions", type=Path, help="with --apply-state: commit an `inbox delete` result's deleted_paths")
    parser.add_argument("--title", help="commit title for --git; defaults to the first Raw name")
    parser.add_argument("--mothership-root", type=Path, help="read-only mothership vault root used only to lstat deeplink targets")
    args = parser.parse_args()
    try:
        if not args.vault.is_dir() or any(p.is_symlink() for p in (args.vault,) + tuple(args.vault.parents)):
            raise Refused("vault must be existing nonsymlink directory")
        vault = args.vault.resolve()
        if args.apply_state:
            if args.request or args.state or args.apply or args.mothership_root:
                raise Refused("apply-state cannot be combined with request/state/apply/mothership-root")
            if args.apply_state.is_symlink() or vault == args.apply_state.resolve().parent or vault in args.apply_state.resolve().parents:
                raise Refused("session state must be outside vault and nonsymlink")
            session = state_decode(json.loads(args.apply_state.read_text("utf-8")))
            if session["vault"] != str(vault):
                raise Refused("session belongs to another vault")
        else:
            if not args.request or args.request.is_symlink():
                raise Refused("request must be regular nonsymlink JSON")
            session = plan(vault, json.loads(args.request.read_text("utf-8")), args.mothership_root)
            if args.state:
                if args.state.is_symlink() or vault in args.state.resolve().parents:
                    raise Refused("session state must be outside vault")
                with args.state.open("x", encoding="utf-8") as stream:
                    os.chmod(args.state, 0o600)
                    json.dump(state_encode(session), stream, ensure_ascii=False)
        if args.record_deletions:
            if not args.apply_state:
                raise Refused("--record-deletions requires --apply-state")
            deleted = json.loads(args.record_deletions.read_text("utf-8")).get("deleted_paths")
            result = git_record_deletions(vault, session, args.apply_state, deleted)
            print(json.dumps(dict(result, schema="ingest/result@2", status=result["state"]), ensure_ascii=False, indent=2))
            return 0
        result = {"schema": "ingest/result@2", "status": "planned", "members": session["members"], "changes": [receipt(r) for r in session["changes"]],
                  "mothership_verified": session.get("mothership", [])}
        if args.git:
            if not (args.apply or args.apply_state) or not (args.state or args.apply_state):
                raise Refused("--git requires --apply with --state, or --apply-state")
            result.update(git_apply(vault, session, args.state or args.apply_state, args.title))
            result["status"] = result["state"]
        elif args.apply or args.apply_state:
            result["applied"] = apply(vault, session["changes"], session["inputs"], session["captures"])
            result["status"] = "applied"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (Refused, OSError, UnicodeError, ValueError, TypeError, KeyError, URLError) as exc:
        print(json.dumps({"schema": "ingest/error@2", "status": "refused", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
