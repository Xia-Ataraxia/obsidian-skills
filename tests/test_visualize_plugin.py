"""Plugin-first source checks; no test here executes Obsidian or renders a PNG."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.test_visualize import ex, flow_scene

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills" / "obsidian-visualize"
sys.path.insert(0, str(PACKAGE / "scripts"))
spec = importlib.util.spec_from_file_location("visualize_import", PACKAGE / "scripts" / "import_scene.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class PluginImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "Flow.excalidraw"
        self.target = self.root / "Flow.excalidraw.md"
        self.scene = flow_scene().to_scene()

    def source_bytes(self, scene=None):
        raw = json.dumps(self.scene if scene is None else scene, ensure_ascii=False).encode()
        self.source.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_import_preserves_full_scene_ids_unknown_fields_and_inline_assets(self):
        scene = copy.deepcopy(self.scene)
        scene["customEnvelope"] = {"user": "keep"}
        scene["files"]["image"] = {"id": "image", "mimeType": "image/png",
                                    "dataURL": "data:image/png;base64,AA==", "created": 1}
        scene["elements"][0]["customData"] = {"note": "retain"}
        image = copy.deepcopy(scene["elements"][0])
        image.update({"id": "image-element", "type": "image", "fileId": "image",
                      "boundElements": None, "backgroundColor": "transparent"})
        scene["elements"].append(image)
        digest = self.source_bytes(scene)
        before = self.source.read_bytes()
        report = adapter.import_scene(str(self.source), str(self.target), digest)
        document, actual_digest, actual = ex.read_drawing(str(self.target))
        self.assertEqual(actual, scene)
        self.assertEqual(actual_digest, report.sha256)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertIn("excalidraw-plugin: parsed", document)
        for element in scene["elements"]:
            if element["type"] == "text":
                self.assertIn("^" + element["id"], document)

    def test_index_uses_original_text_without_changing_scene_payload(self):
        text = next(element for element in self.scene["elements"] if element["type"] == "text")
        text.pop("rawText")
        text["originalText"] = "Original unwrapped text"
        digest = self.source_bytes()
        adapter.import_scene(str(self.source), str(self.target), digest)
        document, _, scene = ex.read_drawing(str(self.target))
        self.assertIn("Original unwrapped text ^" + text["id"], document)
        self.assertEqual(scene, self.scene)

    def test_deleted_text_tombstones_remain_in_scene_without_an_index_entry(self):
        text = next(element for element in self.scene["elements"] if element["type"] == "text")
        text["isDeleted"] = True
        digest = self.source_bytes()
        adapter.import_scene(str(self.source), str(self.target), digest)
        document, _, scene = ex.read_drawing(str(self.target))
        self.assertEqual(scene, self.scene)
        self.assertNotIn("^" + text["id"], document)

    def test_null_raw_text_falls_back_but_empty_raw_text_is_preserved(self):
        texts = [element for element in self.scene["elements"] if element["type"] == "text"]
        texts[0]["rawText"] = None
        texts[0]["originalText"] = "Original fallback"
        texts[1]["rawText"] = ""
        texts[1]["originalText"] = "Must not replace empty raw text"
        digest = self.source_bytes()
        adapter.import_scene(str(self.source), str(self.target), digest)
        index = self.target.read_text().split("## Text Elements\n", 1)[1].split("\n\n%%", 1)[0]
        self.assertIn("Original fallback ^" + texts[0]["id"], index)
        self.assertIn(" ^" + texts[1]["id"], index)
        self.assertNotIn("Must not replace empty raw text", index)

    def test_late_concurrent_write_survives_atomic_replace_preparation(self):
        flow_scene().write(str(self.target))
        _, digest, _ = ex.read_drawing(str(self.target))
        original_fsync = ex.os.fsync
        concurrent = b"Concurrent user bytes.\n"

        def edit_after_temp_flush(handle):
            original_fsync(handle)
            self.target.write_bytes(concurrent)

        with patch.object(ex.os, "fsync", side_effect=edit_after_temp_flush):
            with self.assertRaises(ex.SceneWriteError):
                flow_scene(stages=2).write(str(self.target), overwrite=True,
                                          expected_sha256=digest)
        self.assertEqual(self.target.read_bytes(), concurrent)

    def test_replacement_keeps_existing_digest_case_and_whitespace_contract(self):
        flow_scene().write(str(self.target))
        _, digest, _ = ex.read_drawing(str(self.target))
        report = flow_scene().write(str(self.target), overwrite=True,
                                    expected_sha256=" " + digest.upper() + " ")
        self.assertEqual(report.sha256, digest)

    def test_collision_preserves_user_document_and_non_target(self):
        digest = self.source_bytes()
        self.target.write_text("User note and assets.\n")
        other = self.root / "Control.md"
        other.write_text("Untouched.\n")
        with self.assertRaises(adapter.drawing.SceneWriteError):
            adapter.import_scene(str(self.source), str(self.target), digest)
        self.assertEqual(self.target.read_text(), "User note and assets.\n")
        self.assertEqual(other.read_text(), "Untouched.\n")

    def test_changed_preimage_creates_nothing(self):
        digest = self.source_bytes()
        self.source.write_text("Concurrent edit.\n")
        with self.assertRaises(adapter.drawing.SceneWriteError):
            adapter.import_scene(str(self.source), str(self.target), digest)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.source.read_text(), "Concurrent edit.\n")

    def test_skeleton_pending_mermaid_and_missing_image_refuse(self):
        scenes = []
        skeleton = copy.deepcopy(self.scene)
        del skeleton["elements"][0]["version"]
        scenes.append(skeleton)
        pending = copy.deepcopy(self.scene)
        pending["pendingMermaid"] = "flowchart LR\n A --> B"
        scenes.append(pending)
        missing = copy.deepcopy(self.scene)
        image = copy.deepcopy(missing["elements"][0])
        image.update({"id": "new-image", "type": "image", "fileId": "missing",
                      "boundElements": None, "backgroundColor": "transparent"})
        missing["elements"].append(image)
        scenes.append(missing)
        for scene in scenes:
            with self.subTest(input=scene):
                digest = self.source_bytes(scene)
                with self.assertRaises((adapter.drawing.SceneWriteError, adapter.drawing.SceneDefect)):
                    adapter.import_scene(str(self.source), str(self.target), digest)
                self.assertFalse(self.target.exists())

    def test_symlink_path_does_not_write_its_target(self):
        digest = self.source_bytes()
        actual = self.root / "Actual.excalidraw.md"
        actual.write_text("Keep.\n")
        self.target.symlink_to(actual)
        with self.assertRaises(adapter.drawing.SceneWriteError):
            adapter.import_scene(str(self.source), str(self.target), digest)
        self.assertEqual(actual.read_text(), "Keep.\n")

    def test_symlink_source_is_refused_without_creating_target(self):
        real_source = self.root / "Real.excalidraw"
        raw = json.dumps(self.scene, ensure_ascii=False).encode()
        real_source.write_bytes(raw)
        alias = self.root / "Alias.excalidraw"
        alias.symlink_to(real_source)
        with self.assertRaises(adapter.drawing.SceneWriteError):
            adapter.import_scene(str(alias), str(self.target), hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.target.exists())
        self.assertEqual(real_source.read_bytes(), raw)

    def test_cli_import_materializes_a_valid_plugin_document(self):
        digest = self.source_bytes()
        completed = subprocess.run(
            [sys.executable, str(PACKAGE / "scripts" / "import_scene.py"),
             "--source", str(self.source), "--target", str(self.target),
             "--expected-source-sha256", digest],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["sha256"],
                         hashlib.sha256(self.target.read_bytes()).hexdigest())
        self.assertEqual(ex.extract_scene(self.target.read_text()), self.scene)


class PluginToolTests(unittest.TestCase):
    def test_additive_source_map_keeps_one_owner_and_the_exact_notice(self):
        mapping = json.loads((PACKAGE / "source-map.json").read_text())
        self.assertEqual(mapping["owner"], "F05")
        self.assertEqual(mapping["package"], PACKAGE.name)
        self.assertEqual(len(mapping["revision"]), 40)
        self.assertEqual(len({row["path"] for row in mapping["files"]}), len(mapping["files"]))
        for row in mapping["files"]:
            self.assertEqual(len(row["sha256"]), 64)
            self.assertGreater(row["bytes"], 0)
            if row["target"] is not None:
                target = (PACKAGE / row["target"]).resolve()
                self.assertIn(PACKAGE.resolve(), target.parents)
                self.assertTrue(target.is_file())
        license_row = next(row for row in mapping["files"] if row["path"] == "LICENSE")
        notice = (PACKAGE / "NOTICE").read_bytes()
        self.assertEqual(hashlib.sha256(notice).hexdigest(), license_row["sha256"])
        self.assertEqual(len(notice), license_row["bytes"])

    def test_native_content_contract_preservation_and_conflict_tests(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for optional plugin tooling tests")
        completed = subprocess.run(
            [node, "--test", str(ROOT / "tests" / "fixtures" / "visualize-workbench.cjs")],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_read_only_inspect_lint_and_malformed_refusals(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            drawing = root / "Flow.excalidraw.md"
            flow_scene().write(str(drawing))
            before = drawing.read_bytes()
            node = shutil.which("node")
            self.assertIsNotNone(node)
            script = PACKAGE / "scripts" / "inspect.mjs"
            for command in ("inspect", "lint"):
                result = subprocess.run([node, str(script), command, str(drawing)],
                                        cwd=ROOT, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(drawing.read_bytes(), before)
            invalid = root / "Bad.excalidraw"
            for payload in ("null", '{"type":"excalidraw","elements":[null]}',
                            '{"type":"excalidraw","elements":[{"type":"text","x":"bad"}]}'):
                invalid.write_text(payload)
                result = subprocess.run([node, str(script), "lint", str(invalid)],
                                        cwd=ROOT, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(invalid.read_text(), payload)
            compressed = root / "Compressed.excalidraw.md"
            compressed.write_text("## Drawing\n```compressed-json\nnot-a-codec-fixture\n```\n")
            result = subprocess.run([node, str(script), "inspect", str(compressed)],
                                    cwd=ROOT, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
