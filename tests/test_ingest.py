"""Behavioral ports and A/B/Book replays against synthetic temporary vaults."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/ingest/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("ingest_runtime", SCRIPTS / "ingest.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
from source import Refused, body_offset, metadata, note, parse, read_source


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.vault = self.root / "vault"
        for name in ("Raw", "Wiki", "Inbox", "Concepts", "Entities", "Personas"):
            (self.vault / name).mkdir(parents=True)
        (self.vault / "untouched.md").write_bytes(b"Human bytes\r\n")

    def request(self, **updates):
        data = dict(source_input="text", source_kind="article", locator="urn:synthetic:one", identity="urn:synthetic:one", text="Selected evidence\r\n## Additional selected evidence\r\n```\r\n## Original Content\r\n```", obtained_at="2026-10-08", purpose="Study preservation", purpose_origin="stated", raw_path="Raw/one.md", extraction="defuddle", conversion=[{"tool": "defuddle", "from": "html", "to": "markdown"}])
        data.update(updates)
        return data

    def run_cli(self, data=None, *flags):
        command = [sys.executable, "-B", str(SCRIPTS / "ingest.py"), "--vault", str(self.vault)]
        if data is not None:
            request = self.root / "request.json"
            request.write_text(json.dumps(data), encoding="utf-8")
            command += ["--request", str(request)]
        run = subprocess.run(command + list(flags), capture_output=True, text=True, timeout=10)
        self.assertEqual(run.stderr, "")
        return run.returncode, json.loads(run.stdout)

    def session(self, request):
        changes, inputs, captures = [], {}, []
        runtime.build(self.vault, parse(request), changes, inputs, captures)
        return changes, inputs, captures

    def assert_raw(self, path, extraction):
        blob = (self.vault / path).read_bytes()
        fields = metadata(blob)
        expected = {"tags", "type", "date_created", "date_modified", "created_by", "authorship", "model", "effort", "aliases", "description", "author", "source_locator", "source_identity", "source_input", "source_kind", "source_extraction", "source_obtained_at", "referenced", "purpose", "purpose_origin"}
        self.assertEqual(set(fields), expected)
        self.assertEqual(fields["source_extraction"], extraction)
        self.assertIn(("Extraction: " + extraction).encode(), blob[body_offset(blob):])
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")
        return blob

    def test_canary_a_batch_raw_entity_concept_and_declared_conversion(self):
        member = self.request(author=["[[Entities/source]]"], analyses=[dict(path="Concepts/scope.md", body="Bounded evidence", quote="Selected evidence", anchor="line 1", role="concept", confidence="medium"), dict(path="Entities/source.md", body="Public synthetic source", quote="Selected evidence", anchor="line 1", role="entity", description="Synthetic public source", related=["[[Concepts/scope]]"])])
        other = self.request(raw_path="Raw/two.md", identity="urn:synthetic:two", extraction="markitdown")
        code, result = self.run_cli({"purpose": "Study preservation", "members": [member, other]}, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(len(result["applied"]), 4)
        blob = self.assert_raw("Raw/one.md", "defuddle")
        self.assertEqual(metadata(blob)["author"], ["[[Entities/source]]"])
        self.assertIn(b'"tool": "defuddle"', blob)
        self.assert_raw("Raw/two.md", "markitdown")
        extent = next(r["extent"] for r in result["changes"] if r["path"] == "Raw/one.md")
        self.assertEqual(blob[extent[0]:extent[1]], member["text"].encode())
        self.assertTrue(all(r["sha256"] == r["readback"] for r in result["applied"]))
        entity = (self.vault / "Entities/source.md").read_bytes()
        template = (REPO / "skills/ingest/templates/entity.md").read_bytes()
        fields = metadata(entity)
        # Optional `mothership` is omitted when no verified deeplink was supplied.
        self.assertEqual(list(fields), [k for k in metadata(template) if k != "mothership"])
        self.assertEqual((fields["description"], fields["related"], fields["explored"], fields["source"]), ("Synthetic public source", ["[[Concepts/scope]]"], False, ["[[Raw/one]]"]))
        body = entity[body_offset(entity):].decode()
        self.assertNotIn("{{", body)
        self.assertEqual([line for line in body.splitlines() if line.startswith("#")], ["# source", "## Overview", "## Details", "## Related", "## Sources"])
        self.assertIn("> Selected evidence", body)

    def test_new_concept_and_atom_carry_template_fields_existing_concept_only_appends(self):
        (self.vault / "Entities/known.md").write_bytes(b"Known\n")
        existing = self.vault / "Concepts/old.md"
        old = b"---\ntype: note\ntags: [knowledge/concept]\nconfidence: high\n---\n\n# Old\r\nHuman notes\r\n"
        existing.write_bytes(old)
        concept = dict(path="Concepts/new.md", role="concept", body="Bounded idea", quote="Selected evidence", anchor="line 1", confidence="medium", related=["[[Entities/known]]"], description="One-line scope")
        atom = dict(path="Concepts/atom.md", role="atom", body="Atomic claim", quote="Selected evidence", anchor="line 1", confidence="low")
        append = dict(path="Concepts/old.md", role="concept", body="Added analysis", quote="Selected evidence", anchor="line 1")
        before = sorted(p.relative_to(self.vault) for p in self.vault.rglob("*"))
        refused = {
            "missing confidence": [dict(concept, confidence=None)],
            "absent confidence": [{k: v for k, v in atom.items() if k != "confidence"}],
            "multiline confidence": [dict(atom, confidence="low\nhigh")],
            "multiline description": [dict(concept, description="a\nb")],
            "related not a list": [dict(concept, related="[[Entities/known]]")],
            "related target missing": [dict(concept, related=["[[Entities/absent]]"])],
            "mothership on concept": [dict(concept, mothership=[])],
            "confidence on existing page": [dict(append, confidence="low")],
            "related on existing page": [dict(append, related=[])],
        }
        for label, analyses in refused.items():
            code, result = self.run_cli(self.request(analyses=analyses), "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertEqual(sorted(p.relative_to(self.vault) for p in self.vault.rglob("*")), before, label)
            self.assertEqual(existing.read_bytes(), old, label)
        code, result = self.run_cli(self.request(analyses=[concept, atom, append]), "--apply")
        self.assertEqual(code, 0, result)
        template = list(metadata((REPO / "skills/ingest/templates/concept.md").read_bytes()))
        for path, expected in (("Concepts/new.md", concept), ("Concepts/atom.md", atom)):
            blob = (self.vault / path).read_bytes()
            fields = metadata(blob)
            self.assertEqual(list(fields), template, path)
            self.assertEqual((fields["type"], fields["tags"], fields["aliases"], fields["date_created"], fields["date_modified"]), ("note", ["knowledge/concept"], [], "2026-10-08", "2026-10-08"), path)
            self.assertEqual((fields["source"], fields["related"], fields["confidence"], fields["explored"], fields["description"]),
                             (["[[Raw/one]]"], expected.get("related", []), expected["confidence"], False, expected.get("description", "")), path)
            body = blob[body_offset(blob):].decode()
            self.assertIn(expected["body"], body)
            self.assertIn("> Selected evidence", body)
            self.assertIn("[[Raw/one]] at line 1", body)
            self.assertNotIn("{{", blob.decode())
        # The existing Concept keeps its exact bytes as a prefix and gains no template fields.
        after = existing.read_bytes()
        self.assertTrue(after.startswith(old))
        self.assertIn(b"Added analysis", after[len(old):])
        self.assertEqual(metadata(after), metadata(old))
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")

    def test_canary_b_better_extraction_new_raw_and_hub_lists_both(self):
        first = self.request(source_kind="paper", identity="doi:10.1234/public", extraction="OCR", wiki_path="Wiki/paper.md", coverage="excerpt", omissions=["pages 2-4 not obtained"])
        self.assertEqual(self.run_cli(first, "--apply")[0], 0)
        before = self.assert_raw("Raw/one.md", "OCR")
        # A block-list YAML hub is read and patched without touching other header bytes.
        hub = self.vault / "Wiki/paper.md"
        hub.write_bytes(hub.read_bytes().replace(b'description: ""', b"description: 'owner keeps this spelling'"))
        second = self.request(source_kind="paper", identity=first["identity"], raw_path="Raw/full.md", wiki_path="Wiki/paper.md", extraction="marker", referenced=["[[Raw/one]]"], text="Full public synthetic paper", coverage="full", conversion=[dict(tool="marker", **{"from": "pdf", "to": "markdown"})])
        code, result = self.run_cli(second, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "Raw/one.md").read_bytes(), before)
        self.assert_raw("Raw/full.md", "marker")
        fields = metadata(hub.read_bytes())
        self.assertEqual(fields["type"], "paper")
        self.assertEqual(fields["source"], ["[[Raw/one]]", "[[Raw/full]]"])
        self.assertIn(b"description: 'owner keeps this spelling'", hub.read_bytes())

    BOOK_TITLE = "질서 너머: A Synthetic Order — 2nd ed."
    READING_PATHS = "Path A: read Part One, then Part Two.\n\n- Path B — skim [[Raw/ch2]] first\n  indented line kept\n### Author's note\r\nTrailing {{not_a_slot}}"

    def scaffold_book(self):
        data = self.request(source_kind="book", raw_path="Raw/book.md", text="Public preface", book_title=self.BOOK_TITLE, reading_paths=self.READING_PATHS, chapters=[
            dict(path="Raw/ch1.md", title="First", part="Part One", locator="https://example.org/book/ch1", toc_description="Where order begins."),
            dict(path="Raw/ch2.md", title="Second", part="Part Two", locator="https://example.org/book/ch2")])
        code, result = self.run_cli(data, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")
        return result

    def render(self, name, **values):
        text = (REPO / "skills/ingest/templates" / name).read_text("utf-8")
        return re.sub(r"\{\{([a-z_]+)\}\}", lambda m: values.get(m.group(1), "synthetic " + m.group(1).replace("_", " ")), text).encode("utf-8")

    def template_book(self, notes="제 생각: 질서 너머의 첫 장을 다시 읽고 싶다."):
        """Template-shaped synthetic Index and chapter stub (basename links, human Reading Notes)."""
        (self.vault / "Raw/Books").mkdir()
        stem, index_stem = "2026-10-01-synthetic-order-ch01-first", "2026-10-01-synthetic-order-book-index"
        chapter = self.render("book-chapter.md", date="2026-10-01", integer="1", book_index=index_stem, verified_direct_chapter_url="https://example.org/order/ch01",
                              chapter_locator="https://example.org/order/ch01", chapter_identity="urn:synthetic:order:ch01", part_in_original_language="제1부",
                              human_notes_preserved=notes)
        index = self.render("book-index.md", date="2026-10-01", obtained_at="2026-10-01", book_url="https://example.org/order", edition_identity="urn:synthetic:order",
                            preface_locator="https://example.org/order/preface", number="1", chapter_stub=stem)
        toc = ("- [ ] [[%s]] — synthetic verbatim toc one liner\n" % stem).encode()
        row = ("| 1 | [[%s]] | stub | — |\n" % stem).encode()
        index = index.replace(toc, toc + "- [ ] [[2026-10-01-synthetic-order-ch02-second]] — Second\n".encode()).replace(row, row + "| 2 | [[2026-10-01-synthetic-order-ch02-second]] | stub | — |\n".encode())
        chapter = chapter.replace(b"chapterNext: null", b'chapterNext: "[[2026-10-01-synthetic-order-ch02-second]]"')
        second = self.render("book-chapter.md", date="2026-10-01", integer="2", book_index=index_stem, verified_direct_chapter_url="https://example.org/order/ch02",
                             chapter_locator="https://example.org/order/ch02", chapter_identity="urn:synthetic:order:ch02", part_in_original_language="제1부", human_notes_preserved="")
        second = second.replace(b"chapterPrev: null", ('chapterPrev: "[[%s]]"' % stem).encode())
        (self.vault / "Raw/Books/2026-10-01-synthetic-order-ch02-second.md").write_bytes(second)
        (self.vault / ("Raw/Books/%s.md" % stem)).write_bytes(chapter)
        (self.vault / ("Raw/Books/%s.md" % index_stem)).write_bytes(index)
        return "Raw/Books/%s.md" % stem, "Raw/Books/%s.md" % index_stem, stem

    def placeholder(self):
        template = (REPO / "skills/ingest/templates/book-chapter.md").read_bytes()
        return template.split(b"## Original Content\n\n", 1)[1].split(b"\n\n## Reading Notes", 1)[0]

    def promotion(self, chapter_path, index_path, label, text, coverage="partial", date="2026-10-09", locator=None, chapter=None, index=None, start=None, **spec):
        """A reviewed promotion member whose postimages are derived independently from the preimages."""
        self.count = getattr(self, "count", 0) + 1
        chapter = (self.vault / chapter_path).read_bytes() if chapter is None else chapter
        index = (self.vault / index_path).read_bytes() if index is None else index
        placeholder = self.placeholder()
        start = chapter.index(placeholder) if start is None else start
        end = start + len(placeholder)
        status = "completed" if coverage == "full" else "reading"
        post = runtime.patch_fields(chapter[:start] + text + chapter[end:], {"status": status, "date_modified": date})
        number = metadata(chapter).get("chapterNumber")
        index_post = index.replace(("| %s | [[%s]] | stub | — |" % (number, label)).encode(), ("| %s | [[%s]] | %s | %s |" % (number, label, status, date)).encode(), 1)
        # The actually read chapter is checked for reading and completed alike (plan §9 promotion).
        index_post = index_post.replace(("- [ ] [[%s]]" % label).encode(), ("- [x] [[%s]]" % label).encode(), 1)
        post_file, post_sha = self.outside("chapter-post-%d.md" % self.count, post)
        text_file, text_sha = self.outside("chapter-text-%d.txt" % self.count, text)
        index_file, index_sha = self.outside("index-post-%d.md" % self.count, index_post)
        fields = metadata(chapter)
        member = {"update_path": chapter_path, "preimage_sha256": runtime.digest(chapter), "postimage_file": post_file, "postimage_sha256": post_sha,
                  "purpose": "Read the selected chapter", "purpose_origin": "stated",
                  "promotion": dict({"placeholder": {"start": start, "end": end, "sha256": runtime.digest(chapter[start:end])}, "text_file": text_file, "text_sha256": text_sha,
                                     "locator": locator or fields.get("source_locator") or fields.get("source_url") or "urn:none", "coverage": coverage, "date": date,
                                     "index": {"path": index_path, "preimage_sha256": runtime.digest(index), "postimage_file": index_file, "postimage_sha256": index_sha}}, **spec)}
        return member, post, index_post

    def test_scaffold_partial_promotion_keeps_reading_explicit_and_grounds_analysis(self):
        result = self.scaffold_book()
        chapter = (self.vault / "Raw/ch1.md").read_bytes()
        index = (self.vault / "Raw/book.md").read_bytes()
        sibling = (self.vault / "Raw/ch2.md").read_bytes()
        fields = metadata(chapter)
        self.assertEqual((fields["status"], fields["source_locator"], fields["chapterNumber"]), ("stub", "https://example.org/book/ch1", 1))
        extent = next(r["extent"] for r in result["changes"] if r["path"] == "Raw/ch1.md")
        self.assertEqual(chapter[extent[0]:extent[1]], self.placeholder())
        text = "Acquired synthetic chapter, opening pages only.\r\nSecond line\r\n".encode()
        member, post, index_post = self.promotion("Raw/ch1.md", "Raw/book.md", "Raw/ch1", text)
        grounded = dict(path="Concepts/opening.md", role="concept", body="Opening idea", quote="opening pages only", anchor="p. 1", confidence="low")
        # Analyses are grounded in the acquired chapter text, never in the placeholder.
        stale = dict(grounded, quote="Chapter body not obtained")
        self.assertEqual(self.run_cli(dict(member, analyses=[stale], obtained_at="2026-10-09"), "--apply")[0], 1)
        state = self.root / "promotion.json"
        code, planned = self.run_cli(dict(member, analyses=[grounded], obtained_at="2026-10-09"), "--state", str(state))
        self.assertEqual(code, 0, planned)
        self.assertEqual((self.vault / "Raw/ch1.md").read_bytes(), chapter)
        code, applied = self.run_cli(None, "--apply-state", str(state))
        self.assertEqual(code, 0, applied)
        self.assertEqual({r["path"]: r["effect"] for r in applied["applied"]}, {"Raw/ch1.md": "update", "Raw/book.md": "update", "Concepts/opening.md": "create"})
        after = (self.vault / "Raw/ch1.md").read_bytes()
        self.assertEqual(after, post)
        new_fields = metadata(after)
        self.assertEqual((new_fields["status"], new_fields["date_modified"]), ("reading", "2026-10-09"))
        self.assertEqual({k: v for k, v in new_fields.items() if k not in ("status", "date_modified")}, {k: v for k, v in fields.items() if k not in ("status", "date_modified")})
        self.assertEqual(after[body_offset(after):], chapter[body_offset(chapter):extent[0]] + text + chapter[extent[1]:])
        offset = body_offset(after) - body_offset(chapter)
        self.assertEqual(planned["members"][0]["text"], [extent[0] + offset, extent[0] + offset + len(text)])
        book = (self.vault / "Raw/book.md").read_bytes()
        self.assertEqual(book, index_post)
        # Checked means the chapter was actually read; the row keeps partial coverage explicit as `reading`.
        self.assertIn(b"- [x] [[Raw/ch1]]", book)
        self.assertIn(b"- [ ] [[Raw/ch2]]", book)
        self.assertEqual(planned["members"][0]["coverage"], "partial")
        self.assertIn("| 1 | [[Raw/ch1]] | reading | 2026-10-09 |".encode(), book)
        self.assertIn("| 2 | [[Raw/ch2]] | stub | — |".encode(), book)
        self.assertEqual(len(book) - len(index), len(b"reading | 2026-10-09") - len("stub | —".encode()))
        self.assertEqual((self.vault / "Raw/ch2.md").read_bytes(), sibling)
        self.assertEqual(metadata((self.vault / "Concepts/opening.md").read_bytes())["source"], ["[[Raw/ch1]]"])
        # A promoted chapter is no longer a stub: a second promotion is refused.
        again, _, _ = self.promotion("Raw/ch1.md", "Raw/book.md", "Raw/ch1", b"More", chapter=chapter, index=book)
        again["preimage_sha256"] = runtime.digest(after)
        self.assertEqual(self.run_cli(again, "--apply")[1]["error"], "promotion requires a Book chapter stub (type book, status stub)")

    def test_template_full_promotion_preserves_human_reading_notes_and_index_rest(self):
        chapter_path, index_path, stem = self.template_book()
        chapter = (self.vault / chapter_path).read_bytes()
        index = (self.vault / index_path).read_bytes()
        text = "질서 너머 synthetic chapter one, complete public test text.\n".encode()
        member, post, index_post = self.promotion(chapter_path, index_path, stem, text, coverage="full")
        code, result = self.run_cli(member, "--apply")
        self.assertEqual(code, 0, result)
        after = (self.vault / chapter_path).read_bytes()
        self.assertEqual(after, post)
        self.assertEqual(metadata(after)["status"], "completed")
        notes = "## Reading Notes\n\n제 생각: 질서 너머의 첫 장을 다시 읽고 싶다.\n\n## Ingest Notes".encode()
        self.assertIn(notes, chapter)
        self.assertIn(notes, after)
        head = chapter[body_offset(chapter):chapter.index(self.placeholder())]
        self.assertTrue(after[body_offset(after):].startswith(head + text + b"\n\n## Reading Notes"))
        self.assertNotIn(b"STUB: pending verbatim fill", after)
        for key in ("bookIndex", "chapterNumber", "chapterPart", "chapterPrev", "chapterNext", "source_identity", "source_locator", "source_url"):
            self.assertEqual(metadata(after)[key], metadata(chapter)[key])
        book = (self.vault / index_path).read_bytes()
        self.assertEqual(book, index_post)
        self.assertIn(("- [x] [[%s]]" % stem).encode(), book)
        self.assertIn(("| 1 | [[%s]] | completed | 2026-10-09 |" % stem).encode(), book)
        self.assertIn(b"- [ ] [[2026-10-01-synthetic-order-ch02-second]]", book)
        self.assertEqual(book[:body_offset(book)], index[:body_offset(index)])
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")

    def test_promotion_refusals_leave_chapter_and_index_untouched(self):
        chapter_path, index_path, stem = self.template_book(notes="Human note")
        chapter = (self.vault / chapter_path).read_bytes()
        index = (self.vault / index_path).read_bytes()
        text = b"Acquired synthetic text\n"
        good, post, index_post = self.promotion(chapter_path, index_path, stem, text)
        notes = chapter.index(b"Human note")
        placeholder = self.placeholder()

        def variant(**changes):
            blob = changes.get("chapter")
            member, _, _ = self.promotion(chapter_path, index_path, stem, changes.pop("text", text), **{k: changes.pop(k) for k in list(changes) if k in ("coverage", "date", "locator", "chapter", "start")})
            if blob is not None:
                # A differently shaped preimage lives beside the Index under its own name.
                member["update_path"] = "Raw/Books/variant-%d.md" % self.count
                (self.vault / member["update_path"]).write_bytes(blob)
            for key, value in changes.items():
                if key.startswith("spec_"):
                    member["promotion"][key[5:]] = value
                else:
                    member[key] = value
            return member

        def reviewed(name, blob):
            path, sha = self.outside(name, blob)
            return {"postimage_file": path, "postimage_sha256": sha}
        (self.root / "real").mkdir()
        (self.root / "real/text.txt").write_bytes(text)
        (self.root / "alias").symlink_to(self.root / "real", target_is_directory=True)
        (self.vault / "Inbox/text.txt").write_bytes(text)
        (self.vault / "Alias").symlink_to(self.vault / "Raw", target_is_directory=True)
        decoy = chapter.replace(b"Human note", b"## Original Content\n\n" + placeholder)
        decoy_start = decoy.rindex(placeholder)
        nonstub = chapter.replace(b"status: stub", b"status: reading")
        ordinary = note({"type": "article", "status": "stub", "date_modified": "2026-10-01", "source_locator": "urn:synthetic:article"}, "## Original Content\n\n" + placeholder.decode() + "\n")
        bad_number = chapter.replace(b"chapterNumber: 1", b'chapterNumber: "1"')
        wrong_index = chapter.replace(b"book-index]]", b"other-index]]")
        human_edit = runtime.patch_fields(chapter[:chapter.index(placeholder)] + text + chapter[chapter.index(placeholder) + len(placeholder):].replace(b"Human note", b"Human note!"), {"status": "reading", "date_modified": "2026-10-09"})
        cases = {
            "forged span over Reading Notes": dict(good, promotion=dict(good["promotion"], placeholder={"start": notes, "end": notes + 10, "sha256": runtime.digest(b"Human note")})),
            "shifted span": dict(good, promotion=dict(good["promotion"], placeholder=dict(good["promotion"]["placeholder"], start=good["promotion"]["placeholder"]["start"] + 1))),
            "span hash mismatch": dict(good, promotion=dict(good["promotion"], placeholder=dict(good["promotion"]["placeholder"], sha256=runtime.digest(b"x")))),
            "decoy placeholder in Reading Notes": variant(chapter=decoy, start=decoy_start),
            "nonstub chapter": variant(chapter=nonstub),
            "ordinary Raw": variant(chapter=ordinary),
            "string chapterNumber": variant(chapter=bad_number),
            "bookIndex names another index": variant(chapter=wrong_index),
            "body edit outside span": dict(good, **reviewed("human-edit.md", human_edit)),
            "extra frontmatter change": dict(good, **reviewed("extra.md", runtime.patch_fields(post, {"description": "changed"}))),
            "navigation change": dict(good, **reviewed("nav.md", runtime.patch_fields(post, {"chapterNext": "[[Raw/elsewhere]]"}))),
            "status inconsistent with coverage": dict(good, **reviewed("status.md", runtime.patch_fields(post, {"status": "completed"}))),
            "unchanged placeholder": variant(text=placeholder),
            "empty text": variant(text=b"  \n"),
            "text digest mismatch": variant(spec_text_sha256=runtime.digest(b"other")),
            "text inside vault": variant(spec_text_file=str(self.vault / "Inbox/text.txt"), spec_text_sha256=runtime.digest(text)),
            "text via symlink": variant(spec_text_file=str(self.root / "alias/text.txt"), spec_text_sha256=runtime.digest(text)),
            "text traversal": variant(spec_text_file=str(self.root / "alias/../real/text.txt"), spec_text_sha256=runtime.digest(text)),
            "locator differs": variant(locator="https://example.org/order/ch99"),
            "unknown purpose": dict(good, purpose="", purpose_origin="unknown"),
            "index edits another row": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], **reviewed("index-extra.md", index_post.replace("| 2 | [[2026-10-01-synthetic-order-ch02-second]] | stub |".encode(), "| 2 | [[2026-10-01-synthetic-order-ch02-second]] | reading |".encode()))))),
            "index leaves read chapter unchecked": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], **reviewed("index-box.md", index_post.replace(b"- [x] [[" + stem.encode(), b"- [ ] [[" + stem.encode(), 1))))),
            "index checks another chapter": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], **reviewed("index-other.md", index_post.replace(b"- [ ] [[2026-10-01", b"- [x] [[2026-10-01", 1))))),
            "index preimage drift": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], preimage_sha256=runtime.digest(b"old")))),
            "index path traversal": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], path="Raw/../Raw/Books/x.md"))),
            "index is the chapter": dict(good, promotion=dict(good["promotion"], index=dict(good["promotion"]["index"], path=chapter_path))),
            "update via symlink": dict(good, update_path="Alias/" + chapter_path[4:]),
            "both preserve and promotion": dict(good, preserve=[{"block": "body", "start": 0, "end": 1, "sha256": runtime.digest(b"-")}]),
            "missing promotion key": dict(good, promotion={k: v for k, v in good["promotion"].items() if k != "coverage"}),
            "manifest coverage": variant(spec_coverage="manifest-only"),
            "malformed date": variant(spec_date="2026-13-40"),
            "weak toggle": variant(spec_preserve_original=False),
            "legacy build promotion": self.request(source_kind="book", raw_path=chapter_path, locator="https://example.org/order/ch01", promotion={"start": 0, "end": 1, "placeholder": "-", "status": "completed"}),
            "append onto stub": self.request(source_kind="book", raw_path=chapter_path, locator="https://example.org/order/ch01", identity=""),
        }
        reasons = {}
        for label, member in cases.items():
            code, result = self.run_cli(member, "--apply")
            self.assertEqual(code, 1, (label, result))
            reasons[label] = result["error"]
            self.assertEqual((self.vault / chapter_path).read_bytes(), chapter, label)
            self.assertEqual((self.vault / index_path).read_bytes(), index, label)
        expected = {"forged span over Reading Notes": "not the template pending-fill placeholder", "shifted span": "not the template pending-fill placeholder",
                    "span hash mismatch": "not the template pending-fill placeholder", "decoy placeholder in Reading Notes": "whole Original Content section",
                    "nonstub chapter": "Book chapter stub", "ordinary Raw": "Book chapter stub", "string chapterNumber": "valid bookIndex/chapterNumber",
                    "bookIndex names another index": "does not name the promotion index", "body edit outside span": "only the placeholder replaced",
                    "extra frontmatter change": "only the placeholder replaced", "navigation change": "only the placeholder replaced",
                    "status inconsistent with coverage": "only the placeholder replaced", "unchanged placeholder": "still the placeholder", "empty text": "empty",
                    "text digest mismatch": "digest mismatch", "text inside vault": "inside the vault", "text via symlink": "without symlinks", "text traversal": "without symlinks",
                    "locator differs": "recorded source locator", "unknown purpose": "unknown purpose", "index edits another row": "index postimage",
                    "index leaves read chapter unchecked": "index postimage", "index checks another chapter": "index postimage", "index preimage drift": "index preimage drift", "index path traversal": "canonical visible",
                    "index is the chapter": "another existing regular file", "update via symlink": "symlink in path", "both preserve and promotion": "one of preserve/promotion",
                    "missing promotion key": "promotion requires exactly", "manifest coverage": "full, partial or excerpt", "malformed date": "YYYY-MM-DD",
                    "weak toggle": "promotion requires exactly", "legacy build promotion": "unknown request keys", "append onto stub": "approved promotion update"}
        self.assertEqual(set(expected), set(cases))
        for label, fragment in expected.items():
            self.assertIn(fragment, reasons[label], label)
        # The good member still succeeds after every refusal: nothing was partially written.
        self.assertEqual(self.run_cli(good, "--apply")[0], 0)
        self.assertEqual((self.vault / chapter_path).read_bytes(), post)

    def test_scaffold_renders_book_index_and_chapter_templates(self):
        result = self.scaffold_book()
        index = (self.vault / "Raw/book.md").read_bytes()
        body = index[body_offset(index):].decode()
        # Every template slot is filled; the only `{{` left is the caller's verbatim Reading Paths text.
        self.assertEqual(body.count("{{"), 1)
        self.assertNotIn("{{", body.replace(self.READING_PATHS, ""))
        # Preface first under Original Content, then TOC (grouped by part), Reading Paths, Progress Tracking, Ingest Notes.
        self.assertEqual([line for line in body.splitlines() if line.startswith("#")],
                         ["# " + self.BOOK_TITLE, "## Original Content", "## TOC", "### Part One", "### Part Two", "## Reading Paths", "### Author's note",
                          "## Progress Tracking", "## Ingest Notes"])
        self.assertNotIn("# book\n", body)
        extent = next(r["extent"] for r in result["changes"] if r["path"] == "Raw/book.md")
        self.assertEqual(index[extent[0]:extent[1]], b"Public preface")
        self.assertTrue(body.startswith("\n# " + self.BOOK_TITLE + "\n\n## Original Content\n\nPublic preface\n\n## TOC\n"))
        self.assertIn("- [ ] [[Raw/ch1]] — First — Where order begins.\n\n### Part Two\n\n- [ ] [[Raw/ch2]] — Second\n\n## Reading Paths", body)
        # Reading Paths are the supplied bytes, unchanged (CR, indentation, slot-like text and all).
        self.assertIn(("## Reading Paths\n\n" + self.READING_PATHS + "\n\n## Progress Tracking\n").encode(), index)
        self.assertIn("| 1 | [[Raw/ch1]] | stub | — |\n| 2 | [[Raw/ch2]] | stub | — |", body)
        self.assertIn("Extraction: defuddle", body)
        self.assertIn("Chapter locators: 2 of 2 supplied as obtained evidence; none inferred.", body)
        self.assertIn("Chapter TOC descriptions: 1 of 2 supplied as obtained text; none inferred.\nReading Paths: supplied verbatim by the caller.", body)
        self.assertEqual(result["members"][0]["book"], {"title": self.BOOK_TITLE, "reading_paths": "supplied", "chapters": 2, "chapter_locators": 2,
                                                        "toc_descriptions_absent": ["Raw/ch2.md"]})
        index_template = list(metadata((REPO / "skills/ingest/templates/book-index.md").read_bytes()))
        self.assertEqual(set(metadata(index)) - set(index_template), {"referenced"})
        self.assertLessEqual(set(index_template), set(metadata(index)))
        chapter_template = list(metadata((REPO / "skills/ingest/templates/book-chapter.md").read_bytes()))
        expected_nav = {"Raw/ch1.md": (None, "[[Raw/ch2]]", "Part One", "First", "Where order begins."), "Raw/ch2.md": ("[[Raw/ch1]]", None, "Part Two", "Second", None)}
        for path, (prev, following, part, title, described) in expected_nav.items():
            chapter = (self.vault / path).read_bytes()
            fields = metadata(chapter)
            self.assertEqual(list(fields), chapter_template)
            self.assertEqual((fields["bookIndex"], fields["chapterPrev"], fields["chapterNext"], fields["chapterPart"]), ("[[Raw/book]]", prev, following, part))
            self.assertEqual((fields["source_extraction"], fields["purpose_origin"], fields["source_url"]), ("none", "reused", fields["source_locator"]))
            text = chapter[body_offset(chapter):].decode()
            self.assertNotIn("{{", text)
            self.assertEqual([line for line in text.splitlines() if line.startswith("#")],
                             ["# " + title, "## Source", "## TOC Preview", "## Original Content", "## Reading Notes", "## Ingest Notes"])
            self.assertIn("- Original URL: " + fields["source_url"] + "\n- Book: [[Raw/book]]\n- Previous/next: %s / %s" % (prev or "null", following or "null"), text)
            self.assertIn("> [!info] Reading Status: Stub", text)
            # The description is the obtained TOC one-liner or empty; a title is never relabelled as one.
            self.assertEqual(fields["description"], described or "")
            self.assertIn("## TOC Preview\n\n" + (described or runtime.NO_TOC_DESCRIPTION) + "\n\n## Original Content", text)

    def test_scaffold_never_invents_chapter_locator_and_refuses_bad_navigation(self):
        data = self.request(source_kind="book", raw_path="Raw/book.md", text="Preface", book_title="Obtained Book Title", chapters=[dict(path="Raw/ch1.md", title="First"), dict(path="Raw/ch2.md", title="Second")])
        (self.vault / "Raw/ch2").write_bytes(b"bare alias")
        cases = {"ambiguous alias": (data, "ambiguous link target"),
                 "duplicate chapter": (dict(data, chapters=[dict(path="Raw/ch1.md", title="A"), dict(path="Raw/ch1.md", title="B")]), "duplicate chapter path"),
                 "chapter is index": (dict(data, chapters=[dict(path="Raw/book.md", title="A")]), "duplicate chapter path"),
                 "non-md chapter": (dict(data, chapters=[dict(path="Raw/ch1", title="A")]), ".md path"),
                 "traversal chapter": (dict(data, chapters=[dict(path="Raw/../ch1.md", title="A")]), "canonical visible"),
                 "unparted after part": (dict(data, chapters=[dict(path="Raw/ch1.md", title="A", part="I"), dict(path="Raw/ch3.md", title="B")]), "unparted chapter"),
                 "not a book": (dict(data, source_kind="article"), "book_title/reading_paths belong only to a book chapter scaffold"),
                 "not a book without book keys": (dict({k: v for k, v in data.items() if k != "book_title"}, source_kind="article"), "belong only to a book")}
        for label, (request, fragment) in cases.items():
            code, result = self.run_cli(request, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn(fragment, result["error"], label)
            self.assertEqual(sorted(p.name for p in (self.vault / "Raw").iterdir()), ["ch2"], label)
        (self.vault / "Raw/ch2").unlink()
        self.assertEqual(self.run_cli(data, "--apply")[0], 0)
        chapter = (self.vault / "Raw/ch1.md").read_bytes()
        fields = metadata(chapter)
        # No obtained chapter locator: nothing is inferred from the book URL.
        self.assertEqual((fields["source_url"], fields["source_locator"], fields["source_identity"], fields["source_input"]), (None, None, "", None))
        self.assertIn(b"- Original URL: Not recorded: no direct chapter URL was supplied as obtained evidence.", chapter)
        index = (self.vault / "Raw/book.md").read_bytes()
        self.assertIn(b"Chapter locators: 0 of 2 supplied as obtained evidence; none inferred.", index)
        self.assertIn(b"# Obtained Book Title\n", index)
        # Absent reading_paths and absent TOC one-liners are reported, never fabricated.
        self.assertIn(("## Reading Paths\n\n" + runtime.NO_READING_PATHS + "\n\n## Progress Tracking").encode(), index)
        self.assertIn(b"Chapter TOC descriptions: 0 of 2 supplied as obtained text; none inferred.\nReading Paths: not supplied; none inferred.", index)
        self.assertIn("- [ ] [[Raw/ch1]] — First\n- [ ] [[Raw/ch2]] — Second\n".encode(), index)
        self.assertEqual(fields["description"], "")
        self.assertIn(("## TOC Preview\n\n" + runtime.NO_TOC_DESCRIPTION + "\n").encode(), chapter)
        member, _, _ = self.promotion("Raw/ch1.md", "Raw/book.md", "Raw/ch1", b"Text\n", locator="https://example.org/book/ch1")
        code, result = self.run_cli(member, "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("recorded source locator", result["error"])
        self.assertEqual((self.vault / "Raw/ch1.md").read_bytes(), chapter)

    def test_scaffold_book_title_reading_paths_and_toc_description_inputs(self):
        chapters = [dict(path="Raw/ch1.md", title="First"), dict(path="Raw/ch2.md", title="Second")]
        good = self.request(source_kind="book", raw_path="Raw/book.md", text="Preface", book_title="Exact Title", reading_paths=None, chapters=chapters)
        without = {k: v for k, v in good.items() if k != "book_title"}
        cases = {
            "missing title": (without, "requires book_title"),
            "empty title": (dict(good, book_title=" "), "book_title must be nonempty one-line"),
            "multiline title": (dict(good, book_title="Exact\nTitle"), "book_title must be nonempty one-line"),
            "non-text title": (dict(good, book_title=["Exact Title"]), "book_title must be nonempty one-line"),
            "empty reading paths": (dict(good, reading_paths="\n "), "reading_paths must be nonempty verbatim text or null"),
            "non-text reading paths": (dict(good, reading_paths=["Path A"]), "reading_paths must be nonempty verbatim text or null"),
            "section heading in reading paths": (dict(good, reading_paths="Path A\n## TOC\n"), "level-1/2 headings"),
            "title on article": (dict(good, source_kind="article"), "belong only to a book chapter scaffold"),
            "reading paths on article": (dict(self.request(), reading_paths="Path A"), "belong only to a book chapter scaffold"),
            "title without chapters": (dict(good, chapters=[]), "belong only to a book chapter scaffold"),
            "empty toc description": (dict(good, chapters=[dict(chapters[0], toc_description=""), chapters[1]]), "toc_description must be nonempty one-line"),
            "multiline toc description": (dict(good, chapters=[dict(chapters[0], toc_description="a\nb"), chapters[1]]), "toc_description must be nonempty one-line"),
            "null toc description": (dict(good, chapters=[dict(chapters[0], toc_description=None), chapters[1]]), "toc_description must be nonempty one-line"),
            "unknown chapter key": (dict(good, chapters=[dict(chapters[0], one_liner="x"), chapters[1]]), "optional part/locator/toc_description"),
        }
        for label, (request, fragment) in cases.items():
            code, result = self.run_cli(request, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn(fragment, result["error"], label)
            self.assertEqual(list((self.vault / "Raw").iterdir()), [], label)
        code, result = self.run_cli(good, "--apply")
        self.assertEqual(code, 0, result)
        index = (self.vault / "Raw/book.md").read_bytes()
        # The title is the supplied one, not the filename; an explicitly unavailable Reading Paths section says so.
        self.assertTrue(index[body_offset(index):].startswith(b"\n# Exact Title\n\n## Original Content\n\nPreface\n\n## TOC\n"))
        self.assertIn(("## Reading Paths\n\n" + runtime.UNAVAILABLE_READING_PATHS + "\n\n## Progress Tracking").encode(), index)
        self.assertIn(b"Reading Paths: reported unavailable by the caller; none inferred.", index)
        self.assertEqual(result["members"][0]["book"], {"title": "Exact Title", "reading_paths": "unavailable", "chapters": 2, "chapter_locators": 0,
                                                        "toc_descriptions_absent": ["Raw/ch1.md", "Raw/ch2.md"]})

    def test_promotion_navigation_targets_must_resolve_to_adjacent_toc_notes(self):
        chapter_path, index_path, stem = self.template_book(notes="Human note")
        chapter = (self.vault / chapter_path).read_bytes()
        index = (self.vault / index_path).read_bytes()
        second = "2026-10-01-synthetic-order-ch02-second"
        (self.vault / "Linked").symlink_to(self.vault / "Raw", target_is_directory=True)
        nav = lambda **values: runtime.patch_fields(chapter, values)
        cases = {
            "unresolved next": (nav(chapterNext="[[missing-chapter]]"), None, "unresolved link target"),
            "traversal next": (nav(chapterNext="[[../" + second + "]]"), None, "canonical visible"),
            "symlinked next": (nav(chapterNext="[[Linked/Books/" + second + "]]"), None, "symlink in path"),
            "ambiguous alias next": (chapter, second + ".md", "ambiguous link target"),
            "bare-name alias next": (chapter, "Raw/Books/" + second, "ambiguous link target"),
            "ambiguous bookIndex": (chapter, "Raw/Books/2026-10-01-synthetic-order-book-index", "ambiguous link target"),
            "first chapter has prev": (nav(chapterPrev="[[" + second + "]]"), None, "chapterPrev must resolve to the adjacent"),
            "next not adjacent": (nav(chapterNext="[[" + index_path[:-3] + "]]"), None, "chapterNext must resolve to the adjacent"),
            "next endpoint before last": (nav(chapterNext=None), None, "chapterNext must resolve to the adjacent"),
        }
        for label, (blob, decoy, fragment) in cases.items():
            (self.vault / chapter_path).write_bytes(blob)
            if decoy:
                (self.vault / decoy).write_bytes(b"decoy")
            member, _, _ = self.promotion(chapter_path, index_path, stem, b"Read text\n")
            code, result = self.run_cli(member, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn(fragment, result["error"], label)
            self.assertEqual((self.vault / chapter_path).read_bytes(), blob, label)
            self.assertEqual((self.vault / index_path).read_bytes(), index, label)
            if decoy:
                (self.vault / decoy).unlink()
        (self.vault / chapter_path).write_bytes(chapter)
        member, post, _ = self.promotion(chapter_path, index_path, stem, b"Read text\n")
        self.assertEqual(self.run_cli(member, "--apply")[0], 0)
        self.assertEqual((self.vault / chapter_path).read_bytes(), post)

    def test_promotion_refuses_source_and_offset_drift(self):
        chapter_path, index_path, stem = self.template_book(notes="Human note")
        chapter = (self.vault / chapter_path).read_bytes()
        index = (self.vault / index_path).read_bytes()
        member, post, index_post = self.promotion(chapter_path, index_path, stem, b"Acquired text\n")
        state = self.root / "drift.json"
        self.assertEqual(self.run_cli(member, "--state", str(state))[0], 0)
        # A human edits Reading Notes after review: apply refuses before any write.
        edited = chapter.replace(b"Human note", b"Human note, revised")
        (self.vault / chapter_path).write_bytes(edited)
        code, result = self.run_cli(None, "--apply-state", str(state))
        self.assertEqual(code, 1, result)
        self.assertIn("preimage drift", result["error"])
        self.assertEqual((self.vault / chapter_path).read_bytes(), edited)
        self.assertEqual((self.vault / index_path).read_bytes(), index)
        # Re-reviewing with the stale offsets/hash refuses; the placeholder moved by the inserted bytes.
        shifted = chapter.replace(b"# synthetic full chapter title", b"# synthetic full chapter title, longer")
        (self.vault / chapter_path).write_bytes(shifted)
        stale = dict(member, preimage_sha256=runtime.digest(shifted))
        code, result = self.run_cli(stale, "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("not the template pending-fill placeholder", result["error"])
        self.assertEqual((self.vault / chapter_path).read_bytes(), shifted)
        # Index drift after review is refused at apply, leaving the chapter unwritten too.
        (self.vault / chapter_path).write_bytes(chapter)
        state2 = self.root / "drift2.json"
        self.assertEqual(self.run_cli(member, "--state", str(state2))[0], 0)
        index_file = self.vault / index_path
        index_file.write_bytes(index_file.read_bytes() + b"\nHuman index edit\n")
        code, result = self.run_cli(None, "--apply-state", str(state2))
        self.assertEqual(code, 1, result)
        self.assertIn("preimage drift: " + index_path, result["error"])
        self.assertEqual((self.vault / chapter_path).read_bytes(), chapter)

    def test_state_preimages_outside_notes_and_drift_refusal(self):
        state = self.root / "session.json"
        data = self.request()
        code, result = self.run_cli(data, "--state", str(state))
        self.assertEqual(code, 0, result)
        self.assertFalse((self.vault / "Raw/one.md").exists())
        (self.vault / "Raw/one.md").write_bytes(b"Concurrent owner")
        code, result = self.run_cli(None, "--apply-state", str(state))
        self.assertEqual(code, 1, result)
        self.assertEqual((self.vault / "Raw/one.md").read_bytes(), b"Concurrent owner")
        self.assertEqual(self.run_cli(data, "--state", str(self.vault / "state.json"))[0], 1)

    def test_append_preserves_crlf_no_final_newline_and_heading_decoys(self):
        self.assertEqual(self.run_cli(self.request(), "--apply")[0], 0)
        path = self.vault / "Raw/one.md"
        for text in ("New evidence", "Third evidence\r\n"):
            before = path.read_bytes()
            self.assertEqual(self.run_cli(self.request(text=text), "--apply")[0], 0)
            self.assertTrue(path.read_bytes().startswith(before))

    def test_metadata_preserves_body_and_unknown_yaml(self):
        blob = b'---\r\ntype: paper\r\nauthor:\r\n  - "[[Public Author]]"\r\nsource: ["[[Old]]"]\r\nunknown: "keep quoting"\r\n---\r\n\r\nNo final newline'
        after = runtime.patch_fields(blob, {"source": ["[[Old]]", "[[New]]"]})
        self.assertEqual(after[body_offset(after):], blob[body_offset(blob):])
        self.assertIn(b'unknown: "keep quoting"', after)
        self.assertEqual(metadata(after)["author"], ["[[Public Author]]"])
        with self.assertRaises(Refused):
            metadata(b"---\na: 1\na: 2\n---\nbody")
        folded = metadata(b"---\nsource: >\n  folded\nplain: 'it''s'\ninline: [a, b]\n---\n")
        self.assertEqual((folded["plain"], folded["inline"]), ("it's", ["a", "b"]))
        with self.assertRaises(Refused):
            folded.get("source")
        fields = {"tags": ["reference/article"], "author": [], "title": 'a "q": #x', "n": None}
        emitted = note(fields, "body")
        self.assertEqual(yaml.safe_load(emitted.split(b"---\n")[1]), fields)
        self.assertEqual(dict(metadata(emitted)), fields)
        for path in SCRIPTS.glob("*.py"):
            if path.name in ("ingest.py", "source.py"):
                self.assertNotIn("import yaml", path.read_text("utf-8"))

    def test_selection_file_conversion_and_original_preservation(self):
        original = b"first\r\nselected\r\nlast"
        (self.vault / "Inbox/source.md").write_bytes(original)
        data = self.request(source_input="file", locator="Inbox/source.md", selection=[2, 2], extraction="OCR", coverage="full")
        code, result = self.run_cli(data, "--apply")
        self.assertEqual(code, 0, result)
        blob = self.assert_raw("Raw/one.md", "OCR")
        extent = result["changes"][0]["extent"]
        self.assertEqual(blob[extent[0]:extent[1]], b"selected\r\n")
        self.assertIn(b"Coverage: excerpt", blob)
        self.assertEqual((self.vault / "Inbox/source.md").read_bytes(), original)

    def test_candidate_provenance_and_read_only_legacy_evidence(self):
        fields = {"capture_schema": "capture/candidate@1", "capture_sources": [{"source_locator": "urn:synthetic:capture", "source_identity": "sha256:" + "a" * 64, "source_kind": "article", "source_extraction": "reader", "source_obtained_at": "2026-10-08", "original_content": "Selected candidate", "fidelity": "excerpt", "fidelity_omissions": ["not complete"], "fidelity_conversion": [{"tool": "defuddle", "from": "html", "to": "markdown"}]}]}
        path = self.vault / "Inbox/candidate.md"
        path.write_bytes(note(fields, "Not the actual content"))
        before = path.read_bytes()
        code, result = self.run_cli(self.request(source_input="candidate", locator="Inbox/candidate.md"), "--apply")
        self.assertEqual(code, 0, result)
        blob = self.assert_raw("Raw/one.md", "reader")
        self.assertEqual(metadata(blob)["source_locator"], "urn:synthetic:capture")
        self.assertIn(b"not complete", blob)
        self.assertEqual(path.read_bytes(), before)

    def test_input_and_raw_rechecks_and_ingest_never_deletes_input(self):
        path = self.vault / "Inbox/original.md"
        path.write_bytes(b"Selected inbox")
        data = self.request(source_input="file", locator="Inbox/original.md")
        changes, inputs, captures = self.session(data)
        path.write_bytes(b"Concurrent edit")
        with self.assertRaisesRegex(Refused, "input drift"):
            runtime.apply(self.vault, changes, inputs, captures)
        self.assertFalse((self.vault / "Raw/one.md").exists())
        path.write_bytes(b"Selected inbox")
        changes, inputs, captures = self.session(data)
        real_digest = runtime.digest
        def corrupt_after_write(blob):
            raw = self.vault / "Raw/one.md"
            if raw.exists():
                raw.write_bytes(raw.read_bytes() + b"Concurrent raw")
            return real_digest(blob)
        with patch.object(runtime, "digest", side_effect=corrupt_after_write):
            with self.assertRaisesRegex(Refused, "partial apply"):
                runtime.apply(self.vault, changes, inputs, captures)
        (self.vault / "Raw/one.md").unlink()
        code, result = self.run_cli(data, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(path.read_bytes(), b"Selected inbox")
        self.assertNotIn("delete", [row["effect"] for row in result["applied"]])
        self.assertEqual(captures[0]["selected"], b"Selected inbox")
        self.assertEqual(self.run_cli(dict(data, raw_path="Raw/two.md", delete_input=True), "--apply")[0], 1)
        self.assertTrue(path.exists())

    def test_partial_failure_reports_completed_and_failed_written_path(self):
        changes, inputs, captures = self.session(self.request())
        runtime.stage(self.vault, changes, "Raw/two.md", b"Second output")
        original = Path.open
        def fail_second(path, *args, **kwargs):
            if path.name == "two.md" and args and args[0] == "xb":
                raise OSError("injected second write failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", fail_second):
            with self.assertRaisesRegex(Refused, "completed writes.*Raw/one.md"):
                runtime.apply(self.vault, changes, inputs, captures)
        self.assertTrue((self.vault / "Raw/one.md").exists())
        self.assertFalse((self.vault / "Raw/two.md").exists())

    def test_persona_append_and_grounding(self):
        persona = self.vault / "Personas/public.md"
        persona.write_bytes(note({"type": "persona", "maturity": "established"}, "Contrary earlier stance"))
        before = persona.read_bytes()
        data = self.request(persona_path="Personas/public.md", stance="Bounded updates", stance_quote="Selected evidence", stance_anchor="line 1")
        self.assertEqual(self.run_cli(data, "--apply")[0], 0)
        self.assertTrue(persona.read_bytes().startswith(before))
        self.assertEqual(metadata(persona.read_bytes())["maturity"], "established")
        self.assertEqual(self.run_cli(self.request(raw_path="Raw/new.md", analyses=[dict(path="Concepts/new.md", role="concept", body="Unsupported", quote="Not obtained", anchor="p9")]), "--apply")[0], 1)
        self.assertFalse((self.vault / "Raw/new.md").exists())

    def test_unknown_purpose_collision_symlink_bad_input_and_distinct_identity(self):
        for updates in ({"selection": [2, 1]}, {"raw_path": "../escape.md"}, {"source_input": "url", "locator": {}}, {"identity": "sha256:bad"}, {"note_fields": {"Raw/one.md": {"status": "done"}}}, {"purpose": "", "purpose_origin": "unknown", "wiki_path": "Wiki/new.md"}):
            self.assertEqual(self.run_cli(self.request(**updates), "--apply")[0], 1)
        (self.vault / "Alias").symlink_to(self.vault / "Raw", target_is_directory=True)
        self.assertEqual(self.run_cli(self.request(raw_path="Alias/new.md"), "--apply")[0], 1)
        self.assertEqual(self.run_cli(self.request(purpose="", purpose_origin="unknown"), "--apply")[0], 0)
        self.assertEqual(self.run_cli(self.request(identity="urn:synthetic:different"), "--apply")[0], 1)
        self.assertEqual(self.run_cli(self.request(identity="urn:synthetic:different", raw_path="Raw/different.md"), "--apply")[0], 0)

    def test_notes_render_for_every_coverage_and_full_omissions_stay_refused(self):
        notes = ["Acquisition order: HTML had no text", "Earlier capture [[Raw/old]] kept\nunchanged"]
        for index, coverage in enumerate(("full", "partial", "excerpt")):
            raw = "Raw/notes%d.md" % index
            code, result = self.run_cli(self.request(raw_path=raw, identity="urn:synthetic:n%d" % index, coverage=coverage, notes=notes), "--apply")
            self.assertEqual(code, 0, result)
            blob = (self.vault / raw).read_bytes()
            ingest_notes = blob[body_offset(blob):blob.index(b"## Original Content")].decode()
            self.assertIn("Coverage: " + coverage, ingest_notes)
            self.assertIn("Notes:\n- Acquisition order: HTML had no text\n- Earlier capture [[Raw/old]] kept\n  unchanged\n", ingest_notes)
        for updates in ({"coverage": "full", "omissions": ["x"], "notes": notes}, {"notes": "not a list"}, {"notes": [""]}):
            code, result = self.run_cli(self.request(raw_path="Raw/refused.md", **updates), "--apply")
            self.assertEqual(code, 1, result)
        self.assertFalse((self.vault / "Raw/refused.md").exists())

    def outside(self, name, blob):
        path = self.root / name
        path.write_bytes(blob)
        return str(path), "sha256:" + hashlib.sha256(blob).hexdigest()

    def test_text_input_attachment_stores_real_original_bytes(self):
        pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nsynthetic\n%%EOF\n"
        source, sha = self.outside("orig.pdf", pdf)
        code, result = self.run_cli(self.request(attachment_path="Raw/orig.pdf", attachment_source=source, attachment_sha256=sha), "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "Raw/orig.pdf").read_bytes(), pdf)
        self.assertEqual(metadata((self.vault / "Raw/one.md").read_bytes())["source_attachment"], "Raw/orig.pdf")
        (self.root / "link.pdf").symlink_to(self.root / "orig.pdf")
        (self.vault / "Inbox/in.pdf").write_bytes(pdf)
        refusals = [{"attachment_source": "", "attachment_sha256": ""},
                    {"attachment_sha256": "sha256:" + "0" * 64},
                    {"attachment_source": str(self.root / "link.pdf")},
                    {"attachment_source": str(self.root / "x" / ".." / "orig.pdf")},
                    {"attachment_source": "orig.pdf"},
                    {"attachment_source": str(self.vault / "Inbox/in.pdf")},
                    {"attachment_sha256": ""}]
        for index, updates in enumerate(refusals):
            data = self.request(raw_path="Raw/a%d.md" % index, identity="urn:synthetic:a%d" % index, attachment_path="Raw/a%d.pdf" % index, attachment_source=source, attachment_sha256=sha)
            data.update(updates)
            code, result = self.run_cli(data, "--apply")
            self.assertEqual(code, 1, (updates, result))
            self.assertFalse((self.vault / ("Raw/a%d.pdf" % index)).exists())
        (self.vault / "Inbox/page.html").write_bytes(b"<html><p>Obtained</p></html>")
        file_input = self.request(source_input="file", locator="Inbox/page.html", raw_path="Raw/f.md", identity="urn:synthetic:f", attachment_path="Raw/f.html")
        self.assertEqual(self.run_cli(dict(file_input, attachment_source=source, attachment_sha256=sha), "--apply")[0], 1)
        self.assertEqual(self.run_cli(file_input, "--apply")[0], 0)
        self.assertEqual((self.vault / "Raw/f.html").read_bytes(), b"<html><p>Obtained</p></html>")

    def raw_fixture(self):
        (self.vault / "Raw/primary.md").write_bytes(b"---\ntype: article\n---\n\nPrimary\n")
        body = "Quoted author line\n## Original Content\ninside decoy\n"
        self.assertEqual(self.run_cli(self.request(raw_path="Raw/secondary.md", text=body), "--apply")[0], 0)
        before = (self.vault / "Raw/secondary.md").read_bytes()
        start = before.index(b"## Original Content\n\n") + len(b"## Original Content\n\n")
        return before, start, len(before)

    def update_member(self, before, postimage, preserve, name="post.md", **extra):
        path, sha = self.outside(name, postimage)
        member = {"update_path": "Raw/secondary.md", "preimage_sha256": runtime.digest(before), "postimage_file": path,
                  "postimage_sha256": sha, "preserve": preserve, "purpose": "Study preservation", "purpose_origin": "stated"}
        member.update(extra)
        return member

    def span(self, blob, start, end, block="original_content"):
        return {"block": block, "start": start, "end": end, "sha256": runtime.digest(blob[start:end])}

    def test_update_member_replaces_exact_postimage_and_grounds_entity_in_preserved_raw(self):
        before, start, end = self.raw_fixture()
        after = runtime.patch_fields(before, {"referenced": ["[[Raw/primary]]"]})
        entity = dict(path="Entities/author.md", role="entity", body="Public author", quote="Quoted author line", anchor="line 1", description="Synthetic author")
        member = self.update_member(before, after, [self.span(before, start, end)], analyses=[entity], obtained_at="2026-10-09")
        state = self.root / "update-session.json"
        code, result = self.run_cli(member, "--state", str(state))
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), before)
        offset = len(after) - (end - start)
        self.assertEqual(result["members"][0]["preserved"], [{"before": [start, end], "after": [offset, len(after)]}])
        code, result = self.run_cli(None, "--apply-state", str(state))
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), after)
        self.assertEqual(metadata((self.vault / "Entities/author.md").read_bytes())["source"], ["[[Raw/secondary]]"])
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")
        self.assertEqual({r["path"]: r["effect"] for r in result["applied"]}, {"Raw/secondary.md": "update", "Entities/author.md": "create"})
        # A quote present only in the postimage's new bytes is not grounded in the preserved Raw.
        grown = after + b"\nInjected claim\n"
        bad = self.update_member(after, grown, [self.span(after, offset, len(after))], name="grown.md", analyses=[dict(entity, path="Entities/x.md", quote="Injected claim")], obtained_at="2026-10-09")
        self.assertEqual(self.run_cli(bad, "--apply")[0], 1)
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), after)

    def test_update_member_refuses_unsafe_spans_drift_and_paths(self):
        before, start, end = self.raw_fixture()
        good = runtime.patch_fields(before, {"referenced": ["[[Raw/primary]]"]})
        span = self.span(before, start, end)
        header = before[:body_offset(before)]
        (self.root / "real").mkdir()
        (self.root / "real/post.md").write_bytes(good)
        (self.root / "alias").symlink_to(self.root / "real", target_is_directory=True)
        (self.vault / "Alias").symlink_to(self.vault / "Raw", target_is_directory=True)
        (self.vault / "Inbox/post.md").write_bytes(good)
        sha = runtime.digest(good)
        cases = {
            "no Original Content span": self.update_member(before, good, [self.span(before, start, start + 5, "body")]),
            "hash mismatch": self.update_member(before, good, [dict(span, sha256=runtime.digest(b"other"))]),
            "shifted start": self.update_member(before, good, [self.span(before, start + 1, end)]),
            "span in header": self.update_member(before, good, [self.span(before, 0, 3)]),
            "block removed": self.update_member(before, header + b"\nReplaced body\n", [span], name="p1.md"),
            "block duplicated": self.update_member(before, good + b"\n" + before[start - len(b"## Original Content\n\n"):end], [span], name="p2.md"),
            "second heading": self.update_member(before, good + b"\n## Original Content\n\nfake\n", [span], name="p3.md"),
            "identity changed": self.update_member(before, runtime.patch_fields(good, {"source_identity": "urn:synthetic:other"}), [span], name="p4.md"),
            "preimage drift": self.update_member(before + b" ", good, [span], name="p5.md"),
            "postimage digest": dict(self.update_member(before, good, [span], name="p6.md"), postimage_sha256=runtime.digest(b"x")),
            "postimage symlink dir": dict(self.update_member(before, good, [span]), postimage_file=str(self.root / "alias/post.md"), postimage_sha256=sha),
            "postimage traversal": dict(self.update_member(before, good, [span]), postimage_file=str(self.root / "alias/../real/post.md"), postimage_sha256=sha),
            "postimage inside vault": dict(self.update_member(before, good, [span]), postimage_file=str(self.vault / "Inbox/post.md"), postimage_sha256=sha),
            "update traversal": dict(self.update_member(before, good, [span]), update_path="Raw/../Raw/secondary.md"),
            "update symlink": dict(self.update_member(before, good, [span]), update_path="Alias/secondary.md"),
            "update missing": dict(self.update_member(before, good, [span]), update_path="Raw/absent.md"),
            "unknown key": dict(self.update_member(before, good, [span]), body="append me"),
            "self analysis": self.update_member(before, good, [span], analyses=[dict(path="Raw/secondary.md", role="concept", body="b", quote="Quoted author line", anchor="l1")], obtained_at="2026-10-09"),
        }
        reasons = {'no Original Content span': 'must preserve its Original Content', 'hash mismatch': 'hash mismatch', 'shifted start': 'heading missing or ambiguous', 'span in header': 'outside body', 'block removed': 'missing or ambiguous in postimage', 'block duplicated': 'missing or ambiguous in postimage', 'second heading': 'another Original Content heading', 'identity changed': 'source identity', 'preimage drift': 'preimage drift', 'postimage digest': 'digest mismatch', 'postimage symlink dir': 'without symlinks', 'postimage traversal': 'without symlinks', 'postimage inside vault': 'inside the vault', 'update traversal': 'canonical visible', 'update symlink': 'symlink in path', 'update missing': 'existing regular file', 'unknown key': 'update requires exactly', 'self analysis': 'own update_path'}
        self.assertEqual(set(reasons), set(cases))
        for label, member in cases.items():
            code, result = self.run_cli(member, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn(reasons[label], result["error"], label)
            self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), before, label)
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")
        self.assertEqual(sorted(p.name for p in (self.vault / "Entities").iterdir()), [])

    def test_raw_update_keeps_complete_current_body_prefix(self):
        before, start, end = self.raw_fixture()
        good = runtime.patch_fields(before, {"referenced": ["[[Raw/primary]]"]})
        cut = end - 6
        self.assertGreater(cut, start)
        short = self.span(before, start, cut)
        cases = {
            "shortened end drops suffix": self.update_member(before, good[:len(good) - 6], [short], name="s1.md"),
            "shortened end edits suffix": self.update_member(before, good[:len(good) - 6] + b"EDITED\n", [short], name="s2.md"),
        }
        for label, member in cases.items():
            code, result = self.run_cli(member, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn("unchanged prefix", result["error"], label)
            self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), before, label)
        appended = good + b"\n## Reviewer Notes\n- Appended after the full body\n"
        code, result = self.run_cli(self.update_member(before, appended, [self.span(before, start, end)], name="s3.md"), "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), appended)
        self.assertEqual(metadata(appended)["referenced"], ["[[Raw/primary]]"])

    def legacy_member(self, name, before, after, span, label, **extra):
        path, sha = self.outside(label + ".md", after)
        start = before.index(span)
        member = {"update_path": name, "preimage_sha256": runtime.digest(before), "postimage_file": path, "postimage_sha256": sha,
                  "preserve": [self.span(before, start, start + len(span), "body")], "purpose": "Study preservation", "purpose_origin": "stated"}
        member.update(extra)
        return member

    def test_legacy_raw_without_original_content_keeps_whole_body_prefix(self):
        (self.vault / "10. Raw Sources").mkdir()
        leaf = "10. Raw Sources/legacy.md"
        header = b"---\r\ntitle: legacy\r\n---\r\n"
        body = "\ufeff\r\n# Legacy capture\r\n\r\nPara one\r\n\r\nPara two tail\r\n  \r\n".encode()
        before = header + body
        (self.vault / leaf).write_bytes(before)
        typed = b"---\ntype: article\n---\n\nTyped legacy head\nTyped legacy tail\n"
        (self.vault / "Raw/typed.md").write_bytes(typed)
        migrated = b'---\r\ntype: "article"\r\ntags:\r\n  - "reference/article"\r\ntitle: legacy\r\n---\r\n'
        span = b"Para one\r\n"
        shuffled = "\ufeff\r\n# Legacy capture\r\n\r\nPara two tail\r\n  \r\nPara one\r\n\r\n".encode()
        refusals = {
            "truncates legacy tail": (leaf, before, migrated + body[:body.index(b"Para two")], span, "unchanged prefix"),
            "reorders whole body": (leaf, before, migrated + shuffled, span, "unchanged prefix"),
            "strips BOM": (leaf, before, migrated + body[len("\ufeff".encode()):], span, "unchanged prefix"),
            "normalizes CRLF": (leaf, before, migrated + body.replace(b"\r\n", b"\n"), b"Para one", "unchanged prefix"),
            "drops trailing whitespace": (leaf, before, migrated + body.rstrip() + b"\r\n", span, "unchanged prefix"),
            "heading before body": (leaf, before, migrated + b"## Original Content\r\n\r\n" + body, span, "unchanged prefix"),
            "appends fabricated heading": (leaf, before, migrated + body + b"\r\n## Original Content\r\n\r\nFabricated\r\n", span, "appends an Original Content heading"),
            "typed Raw outside leaf truncated": ("Raw/typed.md", typed, typed[:typed.index(b"Typed legacy tail")], b"Typed legacy head\n", "unchanged prefix"),
        }
        for label, (name, pre, post, kept, reason) in refusals.items():
            member = self.legacy_member(name, pre, post, kept, label.replace(" ", "-"))
            self.assertIn(kept, post, label)
            for flags in ((), ("--apply",)):
                code, result = self.run_cli(member, *flags)
                self.assertEqual(code, 1, (label, result))
                self.assertIn(reason, result["error"], label)
            self.assertEqual((self.vault / name).read_bytes(), pre, label)
        # Quotes cannot be grounded in a legacy Raw: there is no Original Content span to check them against.
        grounded = self.legacy_member(leaf, before, migrated + body, span, "grounded", obtained_at="2026-10-09",
                                      analyses=[dict(path="Entities/legacy.md", role="entity", body="b", quote="Para one", anchor="l1", description="Synthetic")])
        self.assertEqual(self.run_cli(grounded, "--apply")[0], 1)
        self.assertEqual(sorted(p.name for p in (self.vault / "Entities").iterdir()), [])
        self.assertEqual((self.vault / leaf).read_bytes(), before)
        # Canonical metadata migration plus an appended note keeps every legacy body byte as the prefix.
        appended = migrated + body + b"\r\n## Reviewer Notes\r\n- Appended after the full legacy body\r\n"
        code, result = self.run_cli(self.legacy_member(leaf, before, appended, span, "legacy-ok"), "--apply")
        self.assertEqual(code, 0, result)
        after = (self.vault / leaf).read_bytes()
        self.assertEqual(after, appended)
        self.assertTrue(after[body_offset(after):].startswith(body))
        self.assertEqual(metadata(after)["type"], "article")
        self.assertEqual((self.vault / "Raw/typed.md").read_bytes(), typed)
        self.assertEqual((self.vault / "untouched.md").read_bytes(), b"Human bytes\r\n")

    def test_paper_hub_and_paper_analysis_reviewed_restructure_stays_valid(self):
        (self.vault / "40. Paper Analyses").mkdir()
        hub = b'---\ntype: paper\ntags:\n  - "reference/paper"\nsource_identity: "doi:10.1234/public"\n---\n\n# Paper\n\n## Owner\nHuman hub text\n\n## Captures\n- old\n'
        analysis = b"---\ntype: note\n---\n\n# Analysis\n\n## Owner\nHuman analysis\n\n## Scratch\nobsolete\n"
        for name, pre in (("Wiki/paper.md", hub), ("40. Paper Analyses/analysis.md", analysis)):
            (self.vault / name).write_bytes(pre)
            owner = pre[pre.index(b"## Owner"):pre.index(b"\n\n## ", pre.index(b"## Owner")) + 1]
            post = pre[:body_offset(pre)] + b"\n## Overview\nReviewed\n\n" + owner
            code, result = self.run_cli(self.legacy_member(name, pre, post, owner, name.replace("/", "-").replace(" ", "")), "--apply")
            self.assertEqual(code, 0, (name, result))
            self.assertEqual((self.vault / name).read_bytes(), post, name)

    def test_update_member_body_block_on_compiled_note(self):
        concept = self.vault / "Concepts/topic.md"
        concept.write_bytes(note({"type": "note", "keep": "yes"}, "# Topic\n\n## Owner section\nHuman paragraph\n\n## Sources\n- [[Raw/one]]\n"))
        before = concept.read_bytes()
        start = before.index(b"## Owner section")
        end = before.index(b"## Sources")
        after = before.replace(b"# Topic\n\n", b"# Topic\n\n## Overview\nReviewed summary\n\n")
        path, sha = self.outside("concept.md", after)
        member = {"update_path": "Concepts/topic.md", "preimage_sha256": runtime.digest(before), "postimage_file": path, "postimage_sha256": sha,
                  "preserve": [self.span(before, start, end, "body")], "purpose": "Study preservation", "purpose_origin": "stated"}
        self.assertEqual(self.run_cli(dict(member, purpose="", purpose_origin="unknown"), "--apply")[0], 1)
        rewritten, rsha = self.outside("rewritten.md", after.replace(b"Human paragraph", b"Human paragraph edited"))
        self.assertEqual(self.run_cli(dict(member, postimage_file=rewritten, postimage_sha256=rsha), "--apply")[0], 1)
        self.assertEqual(concept.read_bytes(), before)
        code, result = self.run_cli(member, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(concept.read_bytes(), after)

    def concept_update(self, header, body="# Topic\n\n## Owner\nHuman paragraph\n", new_header=None, name="c.md"):
        concept = self.vault / "Concepts/legacy.md"
        concept.write_bytes(("---\n" + header + "---\n\n" + body).encode())
        before = concept.read_bytes()
        start = before.index(b"## Owner")
        after = ("---\n" + (new_header if new_header is not None else header) + "---\n\n" + body).encode()
        path, sha = self.outside(name, after)
        return {"update_path": "Concepts/legacy.md", "preimage_sha256": runtime.digest(before), "postimage_file": path, "postimage_sha256": sha,
                "preserve": [self.span(before, start, len(before), "body")], "purpose": "Study preservation", "purpose_origin": "stated"}, concept, before, after

    def test_update_drops_only_empty_legacy_identity_on_non_raw(self):
        member, concept, before, after = self.concept_update('type: concept\nsource_identity: ""\nsource_url: ""\n', new_header='type: "note"\ntags:\n  - "knowledge/concept"\n')
        code, result = self.run_cli(member, "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(concept.read_bytes(), after)
        refusals = {
            "nonempty dropped": ('type: concept\nsource_identity: "urn:synthetic:c"\n', 'type: note\n', ""),
            "empty changed": ('type: concept\nsource_identity: ""\n', 'type: note\nsource_identity: "urn:synthetic:c"\n', ""),
            "empty to null": ('type: concept\nsource_identity: ""\n', 'type: note\nsource_identity: null\n', ""),
            "post becomes Raw": ('type: concept\nsource_identity: ""\n', 'type: article\n', ""),
            "reference tag": ('type: note\ntags: [reference/paper]\nsource_identity: ""\n', 'type: note\ntags: [reference/paper]\n', ""),
            "paper hub": ('type: paper\nsource_identity: ""\n', 'type: paper\n', ""),
        }
        for index, (label, (old, new, _)) in enumerate(refusals.items()):
            member, concept, before, _ = self.concept_update(old, new_header=new, name="r%d.md" % index)
            code, result = self.run_cli(member, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn("source identity", result["error"], label)
            self.assertEqual(concept.read_bytes(), before, label)
        # A body with Original Content is Raw-like even when typed as a note.
        member, concept, before, _ = self.concept_update('type: note\nsource_identity: ""\n', body="## Owner\nx\n\n## Original Content\n\ny\n", new_header="type: note\n", name="oc.md")
        member["preserve"] = [self.span(before, before.index(b"## Owner"), before.index(b"## Original"), "body")]
        code, result = self.run_cli(member, "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("source identity", result["error"])

    def test_update_raw_identity_is_protected_even_when_empty(self):
        self.assertEqual(self.run_cli(self.request(raw_path="Raw/secondary.md", identity="", text="Quoted author line\n"), "--apply")[0], 0)
        before = (self.vault / "Raw/secondary.md").read_bytes()
        self.assertEqual(metadata(before)["source_identity"], "")
        start = before.index(b"## Original Content\n\n") + len(b"## Original Content\n\n")
        dropped = before.replace(b'source_identity: ""\n', b"")
        moved = before.replace(b'source_locator: "urn:synthetic:one"', b'source_locator: "urn:synthetic:two"')
        for name, post in (("drop.md", dropped), ("moved.md", moved)):
            code, result = self.run_cli(self.update_member(before, post, [self.span(before, start, len(before))], name=name), "--apply")
            self.assertEqual(code, 1, result)
            self.assertIn("source identity", result["error"])
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), before)

    def test_link_fields_resolve_to_existing_or_planned_paths(self):
        (self.vault / "Raw/twin.md").write_bytes(b"---\ntype: article\n---\n")
        (self.vault / "Raw/twin").write_bytes(b"attachment")
        (self.vault / "Raw/one.md").write_bytes(b"---\ntype: article\n---\n")
        bad = {
            "unresolved author": self.request(raw_path="Raw/n1.md", author=["[[Entities/nobody]]"]),
            "unresolved referenced": self.request(raw_path="Raw/n2.md", referenced=["[[Raw/absent]]"]),
            "ambiguous": self.request(raw_path="Raw/n3.md", referenced=["[[Raw/twin]]"]),
            "case mismatch": self.request(raw_path="Raw/n4.md", referenced=["[[raw/one]]"]),
            "aliased link": self.request(raw_path="Raw/n5.md", author=["[[Raw/one|One]]"]),
            "note_fields override": self.request(raw_path="Raw/n6.md", note_fields={"Raw/n6.md": {"author": ["[[Entities/ghost]]"]}}),
            "directory target": self.request(raw_path="Raw/n7.md", referenced=["[[Entities]]"]),
        }
        for label, data in bad.items():
            code, result = self.run_cli(data, "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertFalse((self.vault / data["raw_path"]).exists(), label)
        good = self.request(raw_path="Raw/n8.md", referenced=["[[Raw/one]]"], author=["[[Entities/writer]]"],
                            analyses=[dict(path="Entities/writer.md", role="entity", body="Writer", quote="Selected evidence", anchor="l1", description="Synthetic writer")])
        code, result = self.run_cli(good, "--apply")
        self.assertEqual(code, 0, result)
        # Update postimage link fields: existing or same-session planned targets only, lists only.
        before, start, end = self.raw_fixture()
        span = [self.span(before, start, end)]
        cases = {
            "postimage related unresolved": (runtime.patch_fields(before, {"referenced": ["[[Raw/ghost]]"]}), "neither exists"),
            "postimage scalar source": (before.replace(b"referenced: []", b'referenced: "[[Raw/primary]]"'), "must be a list"),
        }
        for index, (label, (post, reason)) in enumerate(cases.items()):
            code, result = self.run_cli(self.update_member(before, post, span, name="l%d.md" % index), "--apply")
            self.assertEqual(code, 1, (label, result))
            self.assertIn(reason, result["error"], label)
        self.assertEqual((self.vault / "Raw/secondary.md").read_bytes(), before)
        planned = runtime.patch_fields(before, {"referenced": ["[[Raw/fresh]]"]})
        code, result = self.run_cli({"purpose": "Study preservation", "members": [self.request(raw_path="Raw/fresh.md", identity="urn:synthetic:fresh"),
                                                                                 self.update_member(before, planned, span, name="planned.md")]})
        self.assertEqual(code, 0, result)

    def mothership(self):
        root = self.root / "Ataraxia"
        (root / "70. Collections/01 People").mkdir(parents=True)
        person = root / "70. Collections/01 People/Public Person.md"
        person.write_bytes(b"mothership bytes")
        return root, person

    def deeplink(self, name, vault="Ataraxia"):
        from urllib.parse import quote
        return "obsidian://open?vault=" + quote(vault, safe="") + "&file=" + quote(name, safe="")

    def entity_request(self, links, raw="Raw/one.md"):
        return self.request(raw_path=raw, analyses=[dict(path="Entities/person.md", role="entity", body="Public person", quote="Selected evidence", anchor="l1",
                                                         description="Synthetic person", mothership=links)])

    def test_entity_mothership_links_are_stat_verified_read_only(self):
        root, person = self.mothership()
        link = self.deeplink("70. Collections/01 People/Public Person.md")
        code, result = self.run_cli(self.entity_request([link]), "--mothership-root", str(root), "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["mothership_verified"], [{"link": link, "file": "70. Collections/01 People/Public Person.md", "check": "lstat regular file"}])
        fields = metadata((self.vault / "Entities/person.md").read_bytes())
        self.assertEqual(fields["mothership"], [link])
        self.assertEqual(list(fields), list(metadata((REPO / "skills/ingest/templates/entity.md").read_bytes())))
        self.assertEqual(person.read_bytes(), b"mothership bytes")
        # Extension-less file parameter resolves to the single `.md` note.
        bare = self.deeplink("70. Collections/01 People/Public Person")
        code, result = self.run_cli(self.entity_request([bare], raw="Raw/b.md") | {"identity": "urn:synthetic:b"}, "--mothership-root", str(root))
        self.assertEqual(code, 1, result)  # Entities/person.md already exists: mothership belongs to new Entities only
        self.assertIn("new Entity", result["error"])
        (self.vault / "Entities/person.md").unlink()
        code, result = self.run_cli(self.entity_request([bare], raw="Raw/b.md") | {"identity": "urn:synthetic:b"}, "--mothership-root", str(root))
        self.assertEqual(code, 0, result)
        self.assertEqual(result["mothership_verified"][0]["file"], "70. Collections/01 People/Public Person.md")

    def test_mothership_refusals(self):
        root, person = self.mothership()
        (root / "70. Collections/01 People/Twin").write_bytes(b"x")
        (root / "70. Collections/01 People/Twin.md").write_bytes(b"x")
        (root / "Linked.md").symlink_to(person)
        (root / "LinkDir").symlink_to(root / "70. Collections", target_is_directory=True)
        (self.root / "Other").mkdir()
        (self.root / "Alias").symlink_to(root, target_is_directory=True)
        good = self.deeplink("70. Collections/01 People/Public Person.md")
        cases = {
            "no root": ([good], None, '--mothership-root'),
            "slash unescaped": (["obsidian://open?vault=Ataraxia&file=70.%20Collections/01%20People/Public%20Person.md"], root, 'canonically encoded'),
            "plus space": ([good.replace("%20", "+")], root, 'canonically encoded'),
            "other vault": ([self.deeplink("70. Collections/01 People/Public Person.md", "Other")], root, "other than the stat'ed root"),
            "extra query": ([good + "&line=1"], root, 'must be obsidian://open'),
            "wrong action": ([good.replace("//open", "//new")], root, 'must be obsidian://open'),
            "https": (["https://example.com/x"], root, 'must be obsidian://open'),
            "missing file": ([self.deeplink("70. Collections/01 People/Nobody.md")], root, 'unverified'),
            "case mismatch": ([self.deeplink("70. collections/01 People/Public Person.md")], root, 'unverified'),
            "ambiguous": ([self.deeplink("70. Collections/01 People/Twin")], root, 'ambiguous'),
            "symlink file": ([self.deeplink("Linked.md")], root, 'symlink in path'),
            "symlink dir": ([self.deeplink("LinkDir/01 People/Public Person.md")], root, 'symlink in path'),
            "traversal": ([self.deeplink("70. Collections/../70. Collections/01 People/Public Person.md")], root, 'canonical visible'),
            "hidden": ([self.deeplink(".obsidian/app.json")], root, 'canonical visible'),
            "absolute": ([self.deeplink(str(person))], root, 'canonical visible'),
            "duplicate": ([good, good], root, 'unique deeplinks'),
            "directory": ([self.deeplink("70. Collections")], root, 'unverified'),
            "root symlink": ([good], self.root / "Alias", 'without symlinks'),
            "root not allowed": ([good], self.root / "Other", 'not an allowed vault'),
            "root traversal": ([good], Path(str(root) + "/../Ataraxia"), 'without symlinks'),
            "root inside vault": ([good], self.vault, 'disjoint'),
        }
        for label, (links, mothership_root, reason) in cases.items():
            flags = ["--apply"] + (["--mothership-root", str(mothership_root)] if mothership_root else [])
            code, result = self.run_cli(self.entity_request(links), *flags)
            self.assertEqual(code, 1, (label, result))
            self.assertIn(reason, result["error"], label)
            self.assertFalse((self.vault / "Raw/one.md").exists(), label)
            self.assertFalse((self.vault / "Entities/person.md").exists(), label)
        # Raw note_fields and update postimages cannot carry an unverified deeplink either.
        raw = self.request(note_fields={"Raw/one.md": {"mothership": [self.deeplink("70. Collections/01 People/Nobody.md")]}})
        code, result = self.run_cli(raw, "--mothership-root", str(root))
        self.assertEqual(code, 1, result)
        before, start, end = self.raw_fixture()
        post = runtime.patch_fields(before, {"referenced": ["[[Raw/primary]]"]}).replace(b"referenced:", b'mothership: ["' + good.encode() + b'"]\nreferenced:', 1)
        member = self.update_member(before, post, [self.span(before, start, end)], name="m.md")
        code, result = self.run_cli(member)
        self.assertEqual(code, 1, result)
        self.assertIn("--mothership-root", result["error"])
        code, result = self.run_cli(member, "--mothership-root", str(root))
        self.assertEqual(code, 0, result)
        self.assertEqual([v["link"] for v in result["mothership_verified"]], [good])
        self.assertEqual(person.read_bytes(), b"mothership bytes")

    def test_html_requires_attachment_and_declared_file_chain(self):
        data = parse(self.request(text="<html><p>Obtained</p><script>hidden</script></html>", attachment_path="Raw/source.html"))
        source = read_source(self.vault, data)
        self.assertEqual(source["extraction"], "reader")
        self.assertNotIn("hidden", source["body"])
        self.assertEqual(source["conversion"][-1]["tool"], "stdlib HTMLParser")
        with self.assertRaises(Refused):
            read_source(self.vault, parse(self.request(text="<html>text</html>")))


if __name__ == "__main__":
    unittest.main()
