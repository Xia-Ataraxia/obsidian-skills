"""Candidate tests for the `obsidian-visualize` package.

Run: `python3 -m unittest discover -s tests -t . -v`

These tests exercise the generator's behavior — measurement, geometry, validation,
refusals, byte-level determinism, and what the writer leaves alone — not the
wording of the skill documents. Nothing here opens Obsidian, installs a plugin, or
renders a drawing; rendered QA is a separate claim the package documents but this
suite cannot make.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import unicodedata
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = (REPO_ROOT / "skills" / "obsidian-visualize").resolve()
SCRIPT = PACKAGE / "scripts" / "excalidraw_scene.py"

#: Codepoints that must not add advance width, spelled out because they are
#: invisible in source: combining acute, zero-width joiner, variation selector-16.
COMBINING_ACUTE = "\u0301"
ZERO_WIDTH_JOINER = "\u200d"
VARIATION_SELECTOR = "\ufe0f"
#: One fullwidth latin capital A: east-asian wide, so a full fontSize per character.
FULLWIDTH_A = "\uff21"
#: One precomposed Hangul syllable, used only to compare NFC against NFD widths.
HANGUL_SYLLABLE = "\uac01"


def _load_generator():
    spec = importlib.util.spec_from_file_location("excalidraw_scene_under_test", SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging failure
        raise ImportError(f"cannot load the generator at {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ex = _load_generator()


def flow_scene(namespace="Vault/Flow", stages=3, spacing=400):
    """A three-card pipeline with labelled arrows: the shape a generator produces."""
    scene = ex.Scene(namespace=namespace)
    previous = None
    for index in range(stages):
        card = scene.box(
            index * spacing, 0, 240, f"Stage {index}\nstep detail", 18, "#0369a1", "#ffffff"
        )
        if previous is not None:
            scene.arrow(previous, card, f"step {index}")
        previous = card
    return scene


def hard_defects(defects):
    """Drop the overlap heuristic; what is left is a schema failure."""
    return [defect for defect in defects if not defect.startswith(ex.OVERLAP_DEFECT_PREFIX)]


def scene_fence(document):
    return ex.extract_scene(document)


class TextMeasurementTests(unittest.TestCase):
    """Edge cases in the Unicode-aware measurement the layout depends on."""

    def test_wide_characters_cost_a_full_font_size(self):
        self.assertAlmostEqual(ex.text_width(FULLWIDTH_A, 10), 10.0)
        self.assertAlmostEqual(ex.text_width("A", 10), 6.0)

    def test_zero_width_characters_add_nothing(self):
        for char in (COMBINING_ACUTE, ZERO_WIDTH_JOINER, VARIATION_SELECTOR):
            with self.subTest(codepoint=f"U+{ord(char):04X}"):
                self.assertEqual(ex.char_ratio(char), 0.0)

    def test_decomposed_text_measures_like_its_precomposed_form(self):
        for sample in ("e" + COMBINING_ACUTE, HANGUL_SYLLABLE):
            nfc = unicodedata.normalize("NFC", sample)
            nfd = unicodedata.normalize("NFD", sample)
            with self.subTest(sample=f"U+{ord(nfc):04X}"):
                self.assertGreater(len(nfd), len(nfc))
                self.assertAlmostEqual(ex.text_width(nfd, 20), ex.text_width(nfc, 20))

    def test_tab_is_four_narrow_characters(self):
        self.assertAlmostEqual(ex.char_ratio("\t"), ex.NARROW_RATIO * 4)

    def test_empty_text_still_occupies_one_line(self):
        width, height = ex.dims("", 10)
        self.assertEqual(width, 0.0)
        self.assertAlmostEqual(height, 10 * ex.DEFAULT_LINE_HEIGHT)

    def test_blank_lines_survive_as_hard_breaks(self):
        self.assertEqual(ex.wrap("a\n\nb", 10, 100), "a\n\nb")
        _, height = ex.dims("a\n\nb", 10)
        self.assertAlmostEqual(height, 3 * 10 * ex.DEFAULT_LINE_HEIGHT)

    def test_runs_of_spaces_collapse(self):
        self.assertEqual(ex.wrap("a   b", 10, 100), "a b")

    def test_unspaced_run_is_broken_to_fit(self):
        wrapped = ex.wrap(FULLWIDTH_A * 10, 10, 30)
        self.assertGreater(len(wrapped.split("\n")), 1)
        for line in wrapped.split("\n"):
            self.assertLessEqual(ex.text_width(line, 10), 30)
        self.assertEqual(wrapped.replace("\n", ""), FULLWIDTH_A * 10)

    def test_a_cluster_wider_than_the_limit_takes_its_own_line(self):
        self.assertEqual(ex.wrap(FULLWIDTH_A, 10, 5), FULLWIDTH_A)

    def test_wrapping_never_separates_a_mark_from_its_base(self):
        wrapped = ex.wrap(("e" + COMBINING_ACUTE) * 5, 10, 12)
        for line in wrapped.split("\n"):
            self.assertFalse(line.startswith(COMBINING_ACUTE))

    def test_measurement_rejects_a_non_positive_font_size(self):
        for size in (0, -12):
            with self.subTest(font_size=size), self.assertRaises(ValueError):
                ex.text_width("a", size)


class SceneGeometryTests(unittest.TestCase):
    """Element construction, bindings and membership."""

    def test_box_fits_its_wrapped_label_and_binds_it_both_ways(self):
        scene = ex.Scene(namespace="Vault/Card")
        card = scene.box(0, 0, 240, "Ingest", 18, "#0369a1", "#ffffff")
        label = scene.elements[1]
        self.assertEqual(card["type"], "rectangle")
        self.assertEqual(label["containerId"], card["id"])
        self.assertIn({"type": "text", "id": label["id"]}, card["boundElements"])
        self.assertAlmostEqual(card["height"], label["height"] + 2 * 10)
        self.assertEqual(scene.check(), [])

    def test_box_wraps_its_label_inside_the_horizontal_padding(self):
        scene = ex.Scene(namespace="Vault/Card")
        scene.box(0, 0, 120, "a much longer label than fits on one line", 16, "#111", "#fff")
        label = scene.elements[1]
        self.assertGreater(len(label["text"].split("\n")), 1)
        self.assertLessEqual(label["width"], 120 - 2 * 14)

    def test_straight_arrow_starts_at_its_own_origin(self):
        scene = ex.Scene(namespace="Vault/Flow")
        left = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        right = scene.box(400, 0, 200, "B", 16, "#111", "#fff")
        arrow = scene.arrow(left, right)
        self.assertEqual(arrow["points"][0], [0.0, 0.0])
        self.assertEqual(arrow["x"], left["x"] + left["width"])
        self.assertAlmostEqual(arrow["width"], 200.0)
        self.assertEqual(arrow["height"], 0.0)
        self.assertEqual(scene.check(), [])

    def test_offset_endpoints_produce_an_elbowed_route(self):
        scene = ex.Scene(namespace="Vault/Flow")
        left = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        lower = scene.box(400, 220, 200, "B", 16, "#111", "#fff")
        arrow = scene.arrow(left, lower)
        self.assertEqual(len(arrow["points"]), 4)
        self.assertEqual(arrow["points"][0], [0.0, 0.0])
        self.assertEqual(hard_defects(scene.check()), [])

    def test_explicit_elbow_routes_through_the_given_y(self):
        scene = ex.Scene(namespace="Vault/Flow")
        first = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        second = scene.box(400, 220, 200, "B", 16, "#111", "#fff")
        arrow = scene.arrow(first, second, elbow_y=500)
        absolute_y = [arrow["y"] + point[1] for point in arrow["points"]]
        self.assertIn(500.0, absolute_y)

    def test_arrow_binds_and_mirrors_on_both_endpoints(self):
        scene = ex.Scene(namespace="Vault/Flow")
        first = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        second = scene.box(400, 0, 200, "B", 16, "#111", "#fff")
        arrow = scene.arrow(first, second, "events")
        self.assertEqual(arrow["startBinding"]["elementId"], first["id"])
        self.assertEqual(arrow["endBinding"]["elementId"], second["id"])
        for endpoint in (first, second):
            self.assertIn({"type": "arrow", "id": arrow["id"]}, endpoint["boundElements"])
        self.assertEqual(scene.check(), [])

    def test_arrow_label_is_bound_text_on_the_arrow(self):
        scene = ex.Scene(namespace="Vault/Flow")
        first = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        second = scene.box(400, 0, 200, "B", 16, "#111", "#fff")
        arrow = scene.arrow(first, second, "events")
        labels = [
            element
            for element in scene.elements
            if element["type"] == "text" and element.get("containerId") == arrow["id"]
        ]
        self.assertEqual([element["text"] for element in labels], ["events"])
        self.assertIn({"type": "text", "id": labels[0]["id"]}, arrow["boundElements"])

    def test_frame_membership_and_groups_resolve(self):
        scene = ex.Scene(namespace="Vault/Frame")
        frame = scene.frame(-40, -40, 900, 400, "Pipeline")
        first = scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        second = scene.box(400, 0, 200, "B", 16, "#111", "#fff")
        scene.add_to_frame(frame, first, second)
        group_id = scene.group(first, second)
        self.assertEqual(first["frameId"], frame["id"])
        self.assertEqual(second["frameId"], frame["id"])
        self.assertIn(group_id, first["groupIds"])
        self.assertIn(group_id, second["groupIds"])
        self.assertEqual(scene.check(), [])

    def test_summary_counts_and_bounds_match_the_elements(self):
        scene = flow_scene(stages=2)
        summary = scene.summary()
        self.assertEqual(summary["total"], len(scene.elements))
        self.assertEqual(summary["by_type"], {"arrow": 1, "rectangle": 2, "text": 3})
        self.assertEqual(summary["bounds"]["min_x"], 0.0)
        self.assertAlmostEqual(summary["bounds"]["max_x"], 400 + 240)

    def test_stacked_fills_are_reported_as_an_overlap_not_a_schema_error(self):
        scene = ex.Scene(namespace="Vault/Stack")
        scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        scene.box(10, 10, 200, "B", 16, "#111", "#fff")
        defects = scene.check()
        self.assertTrue(all(defect.startswith(ex.OVERLAP_DEFECT_PREFIX) for defect in defects))
        self.assertEqual(scene.check(ignore_overlaps=True), [])


class InvalidBuilderInputTests(unittest.TestCase):
    """Bad input is refused at construction time, before anything is written."""

    def setUp(self):
        self.scene = ex.Scene(namespace="Vault/Guard")
        self.card = self.scene.box(0, 0, 200, "A", 16, "#111", "#fff")

    def test_non_finite_geometry_is_refused(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.scene.rect(value, 0, 10, 10, "#111")
            with self.subTest(extent=value), self.assertRaises(ValueError):
                self.scene.rect(0, 0, value, 10, "#111")

    def test_negative_extent_is_refused(self):
        with self.assertRaises(ValueError):
            self.scene.rect(0, 0, -5, 10, "#111")

    def test_booleans_are_not_coordinates(self):
        with self.assertRaises(TypeError):
            self.scene.rect(True, 0, 10, 10, "#111")

    def test_blank_color_is_refused(self):
        with self.assertRaises(ValueError):
            self.scene.rect(0, 0, 10, 10, "   ")

    def test_empty_namespace_is_refused(self):
        with self.assertRaises(ValueError):
            ex.Scene(namespace="  ")

    def test_unknown_anchor_side_is_refused(self):
        other = self.scene.box(0, 300, 200, "B", 16, "#111", "#fff")
        with self.assertRaises(ValueError):
            self.scene.arrow(self.card, other, start_side="north")

    def test_arrow_cannot_bind_an_element_to_itself(self):
        with self.assertRaises(ValueError):
            self.scene.arrow(self.card, self.card)

    def test_arrow_cannot_bind_across_scenes(self):
        foreign = ex.Scene(namespace="Other/Scene")
        stranger = foreign.box(0, 0, 200, "B", 16, "#111", "#fff")
        with self.assertRaises(ValueError):
            self.scene.arrow(self.card, stranger)
        with self.assertRaises(ValueError):
            self.scene.text(0, 0, "x", 16, "#111", container=stranger)

    def test_identity_fields_cannot_be_overridden(self):
        for field in ("id", "type", "seed", "versionNonce"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.scene.rect(0, 500, 10, 10, "#111", **{field: "forced"})

    def test_padding_wider_than_the_card_is_refused(self):
        with self.assertRaises(ValueError):
            self.scene.box(0, 600, 20, "A", 16, "#111", "#fff", pad_x=14)

    def test_text_alignment_values_are_checked(self):
        with self.assertRaises(ValueError):
            self.scene.text(0, 0, "x", 16, "#111", align="middle")
        with self.assertRaises(ValueError):
            self.scene.text(0, 0, "x", 16, "#111", valign="center")

    def test_a_group_needs_more_than_one_member(self):
        with self.assertRaises(ValueError):
            self.scene.group(self.card)

    def test_only_a_frame_can_hold_frame_members(self):
        with self.assertRaises(ValueError):
            self.scene.add_to_frame(self.card, self.card)


class ValidationTests(unittest.TestCase):
    """`validate_scene` is the gate for scenes this module did not build."""

    def element(self, **overrides):
        element = {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10}
        element.update(overrides)
        return element

    def test_a_clean_scene_has_no_defects(self):
        self.assertEqual(ex.validate_scene(flow_scene().to_scene()), [])

    def test_a_non_object_scene_is_a_defect(self):
        self.assertEqual(len(ex.validate_scene([])), 1)

    def test_envelope_fields_are_checked(self):
        scene = flow_scene().to_scene()
        scene["type"] = "drawing"
        scene["appState"] = None
        defects = ex.validate_scene(scene)
        self.assertTrue(any("scene.type" in defect for defect in defects))
        self.assertTrue(any("appState" in defect for defect in defects))

    def test_missing_required_keys_are_reported_once(self):
        defects = ex.validate_scene(ex.build_scene([{"id": "a", "type": "rectangle"}]))
        self.assertEqual(len(defects), 1)
        self.assertIn("missing required key", defects[0])

    def test_duplicate_ids_are_reported(self):
        scene = ex.build_scene([self.element(), self.element()])
        self.assertTrue(any("duplicate element id" in defect for defect in ex.validate_scene(scene)))

    def test_non_finite_geometry_in_a_foreign_scene_is_reported(self):
        scene = ex.build_scene([self.element(x=float("nan"))])
        self.assertTrue(any("must be a finite number" in defect for defect in ex.validate_scene(scene)))

    def test_arrow_points_must_start_at_the_origin(self):
        scene = ex.build_scene(
            [self.element(type="arrow", points=[[5, 5], [10, 0]], height=0)]
        )
        self.assertTrue(any("points[0] must be [0, 0]" in defect for defect in ex.validate_scene(scene)))

    def test_arrow_needs_at_least_two_points(self):
        scene = ex.build_scene([self.element(type="arrow", points=[[0, 0]])])
        self.assertTrue(any("at least two points" in defect for defect in ex.validate_scene(scene)))

    def test_dangling_arrow_binding_is_reported(self):
        scene = ex.build_scene(
            [
                self.element(
                    type="arrow",
                    points=[[0, 0], [10, 0]],
                    startBinding={"elementId": "nope", "focus": 0, "gap": 4},
                )
            ]
        )
        self.assertTrue(any("missing element 'nope'" in defect for defect in ex.validate_scene(scene)))

    def test_one_sided_arrow_binding_is_reported(self):
        target = self.element(id="target")
        arrow = self.element(
            id="arrow",
            type="arrow",
            points=[[0, 0], [10, 0]],
            endBinding={"elementId": "target", "focus": 0, "gap": 4},
        )
        defects = ex.validate_scene(ex.build_scene([target, arrow]))
        self.assertTrue(any("not mirrored" in defect for defect in defects))

    def test_one_sided_bound_text_is_reported(self):
        container = self.element(id="card")
        label = self.element(id="label", type="text", text="A", containerId="card")
        defects = ex.validate_scene(ex.build_scene([container, label]))
        self.assertTrue(any("not mirrored in container" in defect for defect in defects))

    def test_frame_id_must_name_a_frame(self):
        card = self.element(id="card")
        member = self.element(id="member", frameId="card")
        defects = ex.validate_scene(ex.build_scene([card, member]))
        self.assertTrue(any("not a frame" in defect for defect in defects))

    def test_unparseable_json_text_is_a_single_defect(self):
        defects = ex.validate_scene_json("{")
        self.assertEqual(len(defects), 1)
        self.assertIn("not parseable JSON", defects[0])


class DocumentTests(unittest.TestCase):
    """The Markdown wrapper the plugin actually reads."""

    def test_rendered_document_carries_the_plugin_marker_and_sections(self):
        document = flow_scene().render(description="Ingest overview.")
        self.assertTrue(document.startswith("---\n"))
        self.assertIn(f"{ex.PLUGIN_FRONTMATTER_KEY}: {ex.PLUGIN_FRONTMATTER_VALUE}", document)
        for heading in (ex.DRAWING_HEADING, ex.TEXT_INDEX_HEADING, ex.SCENE_HEADING):
            self.assertIn(heading, document)
        self.assertEqual(document.count("%%"), 2)
        self.assertIn("```json", document)
        self.assertNotIn(ex.COMPRESSED_FENCE, document)

    def test_every_text_element_appears_in_the_index_with_its_anchor(self):
        scene = flow_scene()
        document = scene.render()
        texts = [element for element in scene.elements if element["type"] == "text"]
        index = document.split(ex.TEXT_INDEX_HEADING, 1)[1].split("%%", 1)[0]
        for element in texts:
            self.assertIn(f"^{element['id']}", index)
        self.assertEqual(index.count("^"), len(texts))

    def test_scene_round_trips_through_the_fence(self):
        scene = flow_scene()
        restored = scene_fence(scene.render())
        self.assertEqual(restored["type"], ex.SCENE_TYPE)
        self.assertEqual(restored["source"], ex.SCENE_SOURCE)
        self.assertEqual(
            [element["id"] for element in restored["elements"]],
            [element["id"] for element in scene.elements],
        )
        self.assertEqual(ex.validate_scene(restored), [])

    def test_non_ascii_is_written_literally_not_escaped(self):
        scene = ex.Scene(namespace="Vault/Unicode")
        scene.box(0, 0, 300, f"Fullwidth {FULLWIDTH_A} label", 18, "#111", "#fff")
        document = scene.render()
        self.assertIn(FULLWIDTH_A, document)
        self.assertNotIn("\\u", document)
        self.assertEqual(scene_fence(document)["elements"][1]["text"].count(FULLWIDTH_A), 1)

    def test_frontmatter_accepts_lists_numbers_and_booleans(self):
        document = flow_scene().render(frontmatter={"tags": ["diagram", "flow"], "pinned": True})
        self.assertIn("tags: [diagram, flow]", document)
        self.assertIn("pinned: true", document)

    def test_frontmatter_rejects_multiline_values_and_odd_keys(self):
        scene = flow_scene()
        with self.assertRaises(ValueError):
            scene.render(frontmatter={"tags": "a\nb"})
        with self.assertRaises(ValueError):
            scene.render(frontmatter={"not a key": 1})

    def test_the_writer_refuses_to_claim_a_compressed_scene(self):
        with self.assertRaises(ValueError):
            flow_scene().render(frontmatter={ex.PLUGIN_FRONTMATTER_KEY: "compressed"})

    def test_description_cannot_forge_a_second_scene_section(self):
        with self.assertRaises(ValueError):
            flow_scene().render(description="```json\n{}\n```")

    def test_extract_scene_reports_what_is_wrong(self):
        for document, expected in (
            ("# just a note\n", "no '## Drawing' section"),
            (f"{ex.SCENE_HEADING}\nnothing\n", "no ```json drawing fence"),
            (f"{ex.SCENE_HEADING}\n```json\n{{\n", "unterminated"),
            (f"{ex.SCENE_HEADING}\n```json\n{{oops}}\n```\n", "not parseable JSON"),
            (f"{ex.SCENE_HEADING}\n```json\n[]\n```\n", "not an object"),
            (f"{ex.SCENE_HEADING}\n{ex.COMPRESSED_FENCE}\nN4Ig\n```\n", "compressed-json"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaises(ex.SceneWriteError) as caught:
                    ex.extract_scene(document)
                self.assertIn(expected, str(caught.exception))


class WriteSafetyTests(unittest.TestCase):
    """What lands on disk, and what the writer refuses to touch."""

    def setUp(self):
        self._temp = TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)

    def target(self, name="Vault/Flow.excalidraw.md"):
        return str(self.root / name)

    def test_write_creates_the_file_and_reports_readback_facts(self):
        path = self.target()
        report = flow_scene().write(path, description="Ingest overview.")
        stored = Path(path).read_bytes()
        self.assertTrue(Path(path).is_file())
        self.assertEqual(report.sha256, hashlib.sha256(stored).hexdigest())
        self.assertEqual(report.size, len(stored))
        self.assertFalse(report.replaced)
        self.assertEqual(report.summary["by_type"], {"arrow": 2, "rectangle": 3, "text": 5})
        self.assertEqual(report.added_ids, ())
        self.assertEqual(report.allowed_overlaps, ())

    def test_a_second_write_to_the_same_path_is_refused(self):
        path = self.target()
        flow_scene().write(path)
        before = Path(path).read_bytes()
        with self.assertRaises(ex.SceneWriteError):
            flow_scene(stages=2).write(path)
        self.assertEqual(Path(path).read_bytes(), before)

    def test_replacing_requires_the_digest_of_the_inspected_bytes(self):
        path = self.target()
        flow_scene().write(path)
        before = Path(path).read_bytes()
        with self.assertRaises(ex.SceneWriteError):
            flow_scene(stages=2).write(path, overwrite=True)
        with self.assertRaises(ex.SceneWriteError):
            flow_scene(stages=2).write(path, overwrite=True, expected_sha256="0" * 64)
        self.assertEqual(Path(path).read_bytes(), before)

    def test_a_digest_without_an_existing_file_is_refused(self):
        with self.assertRaises(ex.SceneWriteError):
            flow_scene().write(self.target("Absent.excalidraw.md"), expected_sha256="0" * 64)
        self.assertFalse((self.root / "Absent.excalidraw.md").exists())

    def test_non_markdown_and_directory_targets_are_refused(self):
        (self.root / "Dir.excalidraw.md").mkdir()
        for path in (str(self.root / "Flow.excalidraw"), str(self.root / "Dir.excalidraw.md")):
            with self.subTest(path=path), self.assertRaises(ex.SceneWriteError):
                flow_scene().write(path)

    @unittest.skipUnless(hasattr(os, "symlink"), "platform has no symlinks")
    def test_a_symlinked_target_is_refused_instead_of_written_through(self):
        real = self.root / "Real note.md"
        real.write_text("# keep me\n", encoding="utf-8")
        link = self.root / "Link.excalidraw.md"
        link.symlink_to(real)
        with self.assertRaises(ex.SceneWriteError):
            flow_scene().write(str(link), overwrite=True, expected_sha256="0" * 64)
        self.assertEqual(real.read_text(encoding="utf-8"), "# keep me\n")

    def test_a_plain_note_cannot_be_replaced_even_with_its_digest(self):
        note = self.root / "Meeting notes.md"
        body = "# Meeting notes\n\nnothing to do with drawings\n"
        note.write_text(body, encoding="utf-8")
        digest = hashlib.sha256(note.read_bytes()).hexdigest()
        with self.assertRaises(ex.SceneWriteError):
            flow_scene().write(str(note), overwrite=True, expected_sha256=digest)
        self.assertEqual(note.read_text(encoding="utf-8"), body)

    def test_a_defective_scene_writes_nothing_and_leaves_no_partial_file(self):
        scene = ex.Scene(namespace="Vault/Stack")
        scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        scene.box(10, 10, 200, "B", 16, "#111", "#fff")
        path = self.target("Stacked.excalidraw.md")
        with self.assertRaises(ex.SceneDefect) as caught:
            scene.write(path)
        self.assertTrue(caught.exception.defects)
        self.assertFalse(Path(path).exists())
        self.assertEqual(sorted(entry.name for entry in self.root.iterdir()), [])

    def test_deliberate_overlaps_are_written_only_when_asked_and_are_reported(self):
        scene = ex.Scene(namespace="Vault/Stack")
        scene.box(0, 0, 200, "A", 16, "#111", "#fff")
        scene.box(10, 10, 200, "B", 16, "#111", "#fff")
        report = scene.write(self.target("Stacked.excalidraw.md"), allow_overlaps=True)
        self.assertTrue(report.allowed_overlaps)
        for defect in report.allowed_overlaps:
            self.assertTrue(defect.startswith(ex.OVERLAP_DEFECT_PREFIX))

    def test_writing_leaves_no_temporary_files_behind(self):
        directory = self.root / "Vault"
        flow_scene().write(self.target())
        leftovers = [entry.name for entry in directory.iterdir() if entry.suffix == ".tmp"]
        self.assertEqual(leftovers, [])

    def test_writing_a_drawing_does_not_touch_neighbouring_notes(self):
        directory = self.root / "Vault"
        directory.mkdir()
        neighbours = {
            "Index.md": "# Index\n\n- [[Flow]]\n",
            "Board.canvas": '{"nodes": [], "edges": []}\n',
        }
        for name, body in neighbours.items():
            (directory / name).write_text(body, encoding="utf-8")
        before = {name: (directory / name).read_bytes() for name in neighbours}
        flow_scene().write(self.target())
        for name, payload in before.items():
            with self.subTest(neighbour=name):
                self.assertEqual((directory / name).read_bytes(), payload)

    def test_read_drawing_returns_the_digest_needed_to_replace_it(self):
        path = self.target()
        report = flow_scene().write(path)
        document, digest, scene = ex.read_drawing(path)
        self.assertEqual(digest, report.sha256)
        self.assertIn(ex.DRAWING_HEADING, document)
        self.assertEqual(ex.validate_scene(scene), [])


class DeterminismTests(unittest.TestCase):
    """Re-running a generator has to be boring: same bytes, same ids, honest diffs."""

    def setUp(self):
        self._temp = TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)

    def test_two_runs_of_the_same_generator_are_byte_identical(self):
        first = flow_scene().write(str(self.root / "a" / "Flow.excalidraw.md"), description="Flow.")
        second = flow_scene().write(str(self.root / "b" / "Flow.excalidraw.md"), description="Flow.")
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(
            Path(first.path).read_bytes(),
            Path(second.path).read_bytes(),
        )

    def test_the_output_path_does_not_leak_into_the_scene(self):
        first = flow_scene(namespace="Vault/Flow").write(str(self.root / "One.excalidraw.md"))
        second = flow_scene(namespace="Vault/Flow").write(
            str(self.root / "deep" / "Two.excalidraw.md")
        )
        self.assertEqual(first.sha256, second.sha256)

    def test_ids_do_not_depend_on_element_text(self):
        def ids(label):
            scene = ex.Scene(namespace="Vault/Flow")
            first = scene.box(0, 0, 240, label, 18, "#111", "#fff")
            second = scene.box(0, 300, 240, "B", 18, "#111", "#fff")
            scene.arrow(first, second, "x", start_side="bottom", end_side="top")
            return [element["id"] for element in scene.elements]

        self.assertEqual(ids("Ingest"), ids("Ingest, renamed and much longer"))

    def test_a_different_namespace_produces_different_ids(self):
        self.assertNotEqual(
            {element["id"] for element in flow_scene(namespace="Vault/One").elements},
            {element["id"] for element in flow_scene(namespace="Vault/Two").elements},
        )

    def test_explicit_keys_survive_a_change_in_construction_order(self):
        def ids(order):
            scene = ex.Scene(namespace="Vault/Keyed")
            for name in order:
                scene.box(0, 0, 200, name.upper(), 16, "#111", "#fff", key=name)
            return {element["id"] for element in scene.elements}

        self.assertEqual(ids(["alpha", "beta"]), ids(["beta", "alpha"]))

    def test_seed_and_nonce_are_derived_and_in_range(self):
        for element in flow_scene().elements:
            with self.subTest(element=element["type"]):
                for field in ("seed", "versionNonce"):
                    self.assertIsInstance(element[field], int)
                    self.assertGreaterEqual(element[field], 1)
                    self.assertLessEqual(element[field], 2**31 - 1)
                self.assertEqual(element["updated"], ex.ELEMENT_UPDATED)

    def test_stable_int_is_a_pure_function_of_its_parts(self):
        self.assertEqual(ex.stable_int("a", 1), ex.stable_int("a", 1))
        self.assertNotEqual(ex.stable_int("a", 1), ex.stable_int("a", 2))

    def test_regenerating_the_same_drawing_reports_an_empty_diff(self):
        path = str(self.root / "Flow.excalidraw.md")
        flow_scene().write(path)
        _, digest, _ = ex.read_drawing(path)
        report = flow_scene().write(path, overwrite=True, expected_sha256=digest)
        self.assertTrue(report.replaced)
        self.assertEqual(report.added_ids, ())
        self.assertEqual(report.removed_ids, ())
        self.assertEqual(report.binding_changes, ())

    def test_growing_a_drawing_reports_added_ids_and_keeps_the_old_ones(self):
        path = str(self.root / "Flow.excalidraw.md")
        first = flow_scene(stages=2).write(path)
        before_ids = {
            element["id"] for element in ex.read_drawing(path)[2]["elements"]
        }
        _, digest, _ = ex.read_drawing(path)
        report = flow_scene(stages=3).write(path, overwrite=True, expected_sha256=digest)
        after_ids = {element["id"] for element in ex.read_drawing(path)[2]["elements"]}
        self.assertTrue(before_ids < after_ids)
        self.assertEqual(set(report.added_ids), after_ids - before_ids)
        self.assertEqual(report.removed_ids, ())
        self.assertTrue(all(change.startswith("+") for change in report.binding_changes))
        self.assertNotEqual(report.sha256, first.sha256)

    def test_shrinking_a_drawing_reports_removed_ids_and_dropped_bindings(self):
        path = str(self.root / "Flow.excalidraw.md")
        flow_scene(stages=3).write(path)
        _, digest, _ = ex.read_drawing(path)
        report = flow_scene(stages=2).write(path, overwrite=True, expected_sha256=digest)
        self.assertTrue(report.removed_ids)
        self.assertEqual(report.added_ids, ())
        self.assertTrue(all(change.startswith("-") for change in report.binding_changes))


class PackageIntegrityTests(unittest.TestCase):
    """The package has to stand on its own, with no cross-package file dependency."""

    link_pattern = re.compile(r"\[[^\]]*\]\(([^)\s]+)")

    def documents(self):
        return [PACKAGE / "SKILL.md", PACKAGE / "references" / "workbench.md"]

    def test_the_package_ships_its_skill_reference_script_and_changelog(self):
        for relative in (
            "SKILL.md",
            "CHANGELOG.md",
            "references/workbench.md",
            "scripts/excalidraw_scene.py",
        ):
            with self.subTest(file=relative):
                self.assertTrue((PACKAGE / relative).is_file())

    def test_skill_frontmatter_names_this_package(self):
        text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        block = text.split("---\n", 2)[1]
        fields = dict(
            line.split(":", 1) for line in block.splitlines() if ":" in line and line[0].isalpha()
        )
        self.assertEqual(fields["name"].strip(), "obsidian-visualize")
        self.assertTrue(fields["description"].strip())

    def test_local_links_resolve_inside_this_package(self):
        checked = 0
        for document in self.documents():
            for target in self.link_pattern.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (document.parent / target.split("#", 1)[0]).resolve()
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(resolved.exists(), f"{target} does not exist")
                    self.assertIn(PACKAGE, resolved.parents)
                checked += 1
        self.assertGreater(checked, 0)

    def test_no_document_links_into_a_neighbouring_package(self):
        for document in self.documents():
            for target in self.link_pattern.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                with self.subTest(document=document.name, target=target):
                    self.assertNotIn("skills/obsidian-", target)

    def test_the_generator_is_standard_library_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        imports = {
            line.split()[1].split(".")[0]
            for line in source.splitlines()
            if line.startswith("import ") or line.startswith("from ")
        }
        self.assertEqual(
            imports - {"__future__"},
            {"hashlib", "json", "math", "os", "re", "tempfile", "typing", "unicodedata"},
        )

    def test_the_self_check_demo_validates(self):
        scene = ex._demo()
        self.assertEqual(scene.check(), [])
        self.assertEqual(json.loads(json.dumps(scene.to_scene()))["type"], ex.SCENE_TYPE)


if __name__ == "__main__":
    unittest.main()
