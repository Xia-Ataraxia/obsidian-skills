"""Behavioral status tests over an isolated synthetic vault."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/status/scripts/status.py"
FIXTURE = ROOT / "tests/fixtures/status"
SPEC = importlib.util.spec_from_file_location("status_under_test", SCRIPT)
STATUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATUS)


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = ("link", os.readlink(path), mode)
        elif path.is_dir():
            result[name] = ("dir", mode, path.stat().st_mtime_ns)
        else:
            result[name] = (
                "file", mode, path.stat().st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return result


class StatusTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="task13-status-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.vault = self.base / "vault"
        shutil.copytree(FIXTURE / "vault", self.vault)
        self.scope = json.loads((FIXTURE / "scope.json").read_text(encoding="utf-8"))

    def test_status_counts_real_roots_without_any_write(self):
        # Given
        before = snapshot(self.vault)
        # When
        report = STATUS.run(self.vault, self.scope, now=2000000000)
        # Then
        self.assertEqual(snapshot(self.vault), before)
        self.assertEqual(report["mutations_performed"], [])
        roots = {item["name"]: item for item in report["roots"]}
        self.assertEqual(roots["questions"]["markdown_files"], 2)
        self.assertEqual(roots["questions"]["properties"]["purpose"], 1)
        self.assertEqual(roots["personas"]["properties"]["source_locator"], 0)
        self.assertEqual(report["inbox"]["markdown_files"], 1)

    def test_paper_hubs_and_files_are_distinct_counts(self):
        # Given / When
        paper = STATUS.run(self.vault, self.scope)["paper_analyses"]
        # Then
        self.assertEqual(paper["top_level_directories"], 2)
        self.assertEqual(paper["root_markdown_files"], 4)
        self.assertEqual(paper["markdown_files"], 7)
        self.assertEqual(paper["paper_hub_files"], 3)
        self.assertEqual(paper["unique_source_identities"], 2)
        self.assertEqual(paper["duplicate_identity_hub_files"], 1)
        self.assertEqual(paper["hub_files_missing_source_identity"], 0)
        self.assertNotEqual(paper["top_level_directories"], paper["markdown_files"])

    def test_report_exposes_machine_semantics_for_presence_limits(self):
        # Given / When
        semantics = STATUS.run(self.vault, self.scope)["semantics"]
        # Then
        self.assertEqual(semantics, {
            "property_presence_only": True,
            "quality_assessed": False,
            "purpose_fulfillment_assessed": False,
            "paper_hubs_deduplicated_by_source_identity": True,
            "note_body_read": False,
        })

    def test_valid_frontmatter_does_not_require_reading_note_body(self):
        # Given
        path = self.vault / "20. Wiki/Questions/binary-body.md"
        path.write_bytes(b'---\npurpose: "Bounded"\n---\n\xff\xfe')
        # When
        report = STATUS.run(self.vault, self.scope)
        # Then
        questions = next(item for item in report["roots"] if item["name"] == "questions")
        self.assertEqual(questions["markdown_files"], 3)
        self.assertEqual(questions["properties"]["purpose"], 2)
        self.assertFalse(report["semantics"]["note_body_read"])

    def test_missing_or_symlinked_root_is_refused(self):
        # Given
        outside = self.base / "outside"
        outside.mkdir()
        (self.vault / "alias").symlink_to(outside, target_is_directory=True)
        cases = [
            dict(self.scope, inbox="Missing"),
            dict(self.scope, inbox="alias"),
            dict(self.scope, inbox="../outside"),
        ]
        before = snapshot(self.vault)
        # When / Then
        for scope in cases:
            with self.subTest(scope=scope["inbox"]):
                with self.assertRaises(STATUS.Refused):
                    STATUS.run(self.vault, scope)
                self.assertEqual(snapshot(self.vault), before)

    def test_unterminated_frontmatter_is_not_silently_counted(self):
        # Given
        broken = self.vault / "20. Wiki/Questions/broken.md"
        broken.write_text("---\npurpose: unfinished\n", encoding="utf-8")
        # When / Then
        with self.assertRaises(STATUS.Refused) as raised:
            STATUS.run(self.vault, self.scope)
        self.assertEqual(raised.exception.code, "invalid_note")

    def test_malformed_property_element_is_structured_cli_refusal_without_writes(self):
        # Given
        malformed = dict(self.scope, properties=[{}])
        scope = self.base / "malformed.json"
        scope.write_text(json.dumps(malformed), encoding="utf-8")
        before = snapshot(self.vault)
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope)],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 1)
        envelope = json.loads(result.stdout)
        self.assertEqual((envelope["status"], envelope["code"]),
                         ("refused", "invalid_input"))
        self.assertEqual(envelope["mutations_performed"], [])
        self.assertEqual(snapshot(self.vault), before)

    def test_cli_outputs_json_and_leaves_fixture_unchanged(self):
        # Given
        before = snapshot(self.vault)
        scope = self.base / "scope.json"
        scope.write_text(json.dumps(self.scope), encoding="utf-8")
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope)],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "observed")
        self.assertEqual(snapshot(self.vault), before)

    def test_cli_skips_fifo_and_preserves_regular_files(self):
        # Given
        fifo = self.vault / "20. Wiki/Questions/blocked.md"
        os.mkfifo(fifo)
        regular = {
            path.relative_to(self.vault).as_posix(): path.read_bytes()
            for path in self.vault.rglob("*.md") if path.is_file()
        }
        scope = self.base / "scope.json"
        scope.write_text(json.dumps(self.scope), encoding="utf-8")
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope)],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        questions = next(item for item in report["roots"] if item["name"] == "questions")
        self.assertEqual(questions["markdown_files"], 2)
        self.assertTrue(stat.S_ISFIFO(fifo.lstat().st_mode))
        self.assertEqual({
            path.relative_to(self.vault).as_posix(): path.read_bytes()
            for path in self.vault.rglob("*.md") if path.is_file()
        }, regular)

    def test_script_parses_with_python38_grammar(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 8))
        self.assertTrue(tree.body)


if __name__ == "__main__":
    unittest.main()
