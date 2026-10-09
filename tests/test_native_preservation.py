"""Real CLI preservation cases over disposable copies, not native behavior QA."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "source-inventory.json").read_text(encoding="utf-8"))
FIRST_UNIT = "craft-skill-route-markdown"


class NativePreservationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native-preservation-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(
            ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        self.data = copy.deepcopy(MANIFEST)

    def run_cli(self, text=None):
        manifest = self.root / "source-inventory.json"
        manifest.write_text(
            json.dumps(self.data) if text is None else text, encoding="utf-8",
        )
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/audit_inventory.py"),
             "--root", str(self.root), "--manifest", str(manifest)],
            capture_output=True, text=True, timeout=30,
        )

    def assert_refused(self, result, identity):
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(identity, result.stderr)
        self.assertNotIn("unmapped=0", result.stdout)
        self.assertNotIn("inventory:", result.stdout)

    def test_untampered_real_copy_has_complete_structural_mapping(self):
        result = self.run_cli()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("15 knowledge capabilities", result.stdout)
        self.assertIn("24 total owning packages", result.stdout)
        self.assertIn("unmapped=0", result.stdout)

    def test_directory_cannot_replace_functional_target_file(self):
        path = self.root / "skills/obsidian-visualize/scripts/excalidraw_scene.py"
        path.unlink()
        path.mkdir()
        result = self.run_cli()
        self.assert_refused(result, "craft-skill-req-python-generator")
        self.assertIn("target is not a file", result.stderr)

    def test_directory_cannot_replace_verification_file(self):
        path = self.root / "tests/test_visualize.py"
        path.unlink()
        path.mkdir()
        result = self.run_cli()
        self.assert_refused(result, "craft-skill-req-python-generator")
        self.assertIn("verification is not a file", result.stderr)

    def test_directory_cannot_replace_supporting_target_file(self):
        path = self.root / "docs/security-and-privacy.md"
        path.unlink()
        path.mkdir()
        result = self.run_cli()
        self.assert_refused(result, "craft-skill-req-vault-root")
        self.assertIn("target is not a file", result.stderr)

    def test_package_directory_does_not_replace_entrypoint_file(self):
        path = self.root / "skills/obsidian-markdown/SKILL.md"
        path.unlink()
        path.mkdir()
        result = self.run_cli()
        self.assert_refused(result, FIRST_UNIT)
        self.assertIn("feature entrypoint not-file: F01", result.stderr)

    def test_duplicate_expected_units_alone_is_rejected(self):
        self.data["files"][0]["expected_units"].append("route:markdown-note-prose")
        result = self.run_cli()
        self.assert_refused(result, "C01")
        self.assertIn("duplicate expected_units", result.stderr)

    def test_duplicate_composes_alone_is_rejected(self):
        unit = next(u for u in self.data["units"] if u["id"] == "craft-skill-route-sync-state")
        unit["composes"].append("F09")
        result = self.run_cli()
        self.assert_refused(result, unit["id"])
        self.assertIn("duplicate composes", result.stderr)

    def test_coordinated_same_count_substitution_is_rejected(self):
        self.data["units"][0]["id"] = "replacement-markdown"
        self.data["units"][0]["unit"] = "route:replacement-markdown"
        self.data["files"][0]["expected_units"][0] = "route:replacement-markdown"
        self.assertEqual(len(MANIFEST["units"]), len(self.data["units"]))
        result = self.run_cli()
        self.assert_refused(result, FIRST_UNIT)
        self.assertIn("unexpected native unit: replacement-markdown", result.stderr)

    def test_deleted_mapping_names_the_frozen_unit(self):
        self.data["units"].pop(0)
        result = self.run_cli()
        self.assert_refused(result, FIRST_UNIT)
        self.assertIn("missing native unit", result.stderr)

    def test_coordinated_source_record_deletion_is_rejected(self):
        self.data["files"] = [f for f in self.data["files"] if f["id"] != "C01"]
        self.data["units"] = [u for u in self.data["units"] if u["file"] != "C01"]
        result = self.run_cli()
        self.assert_refused(result, "C01")
        self.assertIn(FIRST_UNIT, result.stderr)

    def test_changed_recorded_obligation_is_not_identity_preservation(self):
        self.data["units"][0]["behavior"] = "A different obligation."
        result = self.run_cli()
        self.assert_refused(result, FIRST_UNIT)
        self.assertIn("native unit identity changed", result.stderr)

    def test_coordinated_contract_tamper_cannot_redefine_the_baseline(self):
        path = self.root / "assets/native-preservation.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["units"][0]["id"] = "replacement-markdown"
        self.data["units"][0]["id"] = "replacement-markdown"
        path.write_text(json.dumps(contract), encoding="utf-8")
        result = self.run_cli()
        self.assert_refused(result, "native preservation contract authentication failed")

    def test_missing_knowledge_row_is_rejected(self):
        self.data["knowledge_capabilities"].pop(9)
        result = self.run_cli()
        self.assert_refused(result, "K-10")
        self.assertIn("missing knowledge capability", result.stderr)

    def test_deleting_knowledge_feature_and_row_does_not_hide_the_gap(self):
        del self.data["features"]["K10"]
        self.data["knowledge_capabilities"].pop(9)
        result = self.run_cli()
        self.assert_refused(result, "K-10")

    def test_knowledge_row_has_one_matching_owner(self):
        self.data["knowledge_capabilities"][0]["owner"] = "K02"
        result = self.run_cli()
        self.assert_refused(result, "K-01")
        self.assertIn("knowledge owner mismatch", result.stderr)

    def test_duplicate_knowledge_row_is_rejected(self):
        self.data["knowledge_capabilities"].append(copy.deepcopy(self.data["knowledge_capabilities"][0]))
        result = self.run_cli()
        self.assert_refused(result, "K-01")
        self.assertIn("duplicate knowledge capability", result.stderr)

    def test_changed_knowledge_target_bytes_require_a_refreshed_binding(self):
        path = self.root / "skills/refresh-context/SKILL.md"
        path.write_bytes(path.read_bytes() + b"\n")
        result = self.run_cli()
        self.assert_refused(result, "K-10")
        self.assertIn("knowledge target digest mismatch", result.stderr)

    def test_malformed_lists_are_diagnostics_not_success(self):
        self.data["files"][0]["expected_units"] = "route:markdown-note-prose"
        self.data["units"][0]["composes"] = {"F09": True}
        result = self.run_cli()
        self.assert_refused(result, "C01")
        self.assertIn(FIRST_UNIT, result.stderr)
        self.assertIn("invalid string list", result.stderr)

    def test_unrecognized_transfer_rights_are_not_an_implicit_grant(self):
        self.data["files"][0]["rights"] = "local-transfer-unconfirmed"
        result = self.run_cli()
        self.assert_refused(result, "C01")
        self.assertIn("unknown rights class", result.stderr)

    def test_malformed_json_has_no_success_summary(self):
        result = self.run_cli(text="{")
        self.assertEqual(2, result.returncode)
        self.assert_refused(result, "inventory error: JSONDecodeError")

    def test_cli_has_no_native_contract_bypass_option(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/audit_inventory.py"),
             "--native-contract", str(self.root / "assets/native-preservation.json")],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(2, result.returncode)
        self.assert_refused(result, "--native-contract")


if __name__ == "__main__":
    unittest.main()
