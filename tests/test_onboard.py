"""Behavioral onboarding regressions using original synthetic schema-v1 inputs."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/onboard/scripts/onboard.py"
FIXTURE = ROOT / "tests/fixtures/onboard"
SPEC = importlib.util.spec_from_file_location("onboard_under_test", SCRIPT)
ONBOARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ONBOARD
SPEC.loader.exec_module(ONBOARD)


def snapshot(path):
    """Observe names, bytes, modes and link targets without following links."""
    result = {}
    if not path.exists():
        return result
    for item in path.rglob("*"):
        name = item.relative_to(path).as_posix()
        mode = item.lstat().st_mode
        if item.is_symlink():
            result[name] = ("link", os.readlink(item), mode)
        elif item.is_dir():
            result[name] = ("directory", mode)
        else:
            result[name] = ("file", item.read_bytes(), mode)
    return result


class OnboardTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="onboard-tests-")
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name).resolve()
        self.source = self.base / "source"
        shutil.copytree(FIXTURE, self.source)
        self.candidate = self.source / "candidates"
        self.target = self.base / "vault"

    def cli(self, role="knowledge", *arguments, expected=0):
        command = [sys.executable, "-B", str(SCRIPT), "--candidate", str(self.candidate),
                   "--role", role, "--target", str(self.target)] + list(arguments)
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return json.loads(completed.stdout if expected == 0 else completed.stderr)

    def existing(self):
        self.target.mkdir()
        (self.target / "User.md").write_bytes(b"---\nauthorship: user\n---\nUntouched.\n")
        settings = self.target / ".obsidian"
        settings.mkdir()
        (settings / "app.json").write_bytes(
            b'{\r\n  "unknown" : {"nested": [1, 2]},\r\n'
            b'  "newFileLocation" : "root"\r\n}\r\n')
        (self.target / "User-link.md").symlink_to("User.md")

    def approved(self, selection=None):
        selection_path = self.base / "selection.json"
        selection_path.write_text(json.dumps(selection or {
            ".obsidian/app.json": ["newFileLocation"]}), encoding="utf-8")
        preview = self.cli("knowledge", "--preview", "--select", str(selection_path))
        preview["approval_state"] = "approved"
        preview["approval_basis"] = "Synthetic owner approved this exact fixture diff."
        preview["approval_effect"] = sorted({
            "create" if c["before"] is None else "update" for c in preview["changes"]
        })
        approval = self.base / "approval.json"
        approval.write_text(json.dumps(preview), encoding="utf-8")
        return approval, preview

    def test_fresh_personal_when_target_absent(self):
        # Given: an absent isolated target, with no counterpart.
        # When: initialize the personal role through its real CLI.
        result = self.cli("personal")
        # Then: every manifest entry matches materialized bytes and names.
        self.assertEqual(result["mode"], "fresh")
        self.assertTrue((self.target / "15. Work/Placement.md").is_file())
        self.assertFalse((self.target / "20. Wiki").exists())
        self.assert_manifest()

    def test_fresh_knowledge_when_target_empty(self):
        # Given
        self.target.mkdir()
        # When
        self.cli()
        # Then
        self.assertTrue((self.target / "20. Wiki/Placement.md").is_file())
        self.assertFalse((self.target / "15. Work").exists())
        self.assert_manifest()

    def assert_manifest(self):
        manifest = json.loads((self.target / "candidate-manifest.json").read_bytes())
        actual = snapshot(self.target)
        expected_files = {f["path"] for f in manifest["files"]} | {"candidate-manifest.json"}
        self.assertEqual({n for n, v in actual.items() if v[0] == "file"}, expected_files)
        self.assertEqual({n for n, v in actual.items() if v[0] == "directory"},
                         set(manifest["folders"]))
        for row in manifest["files"]:
            data = (self.target / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            self.assertEqual(len(data), row["size"])

    def test_additive_when_exact_key_diff_approved(self):
        # Given
        self.existing()
        approval, _ = self.approved()
        before = snapshot(self.target)
        # When
        result = self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        # Then: only one value's bytes changed, not unknown keys or CRLF formatting.
        after = snapshot(self.target)
        original = before.pop(".obsidian/app.json")[1]
        changed = after.pop(".obsidian/app.json")[1]
        self.assertEqual(before, after)
        self.assertEqual(changed, original.replace(b'"root"', b'"folder"'))
        self.assertEqual(result["changed"], [".obsidian/app.json"])

    def test_existing_when_no_approval_refused_without_writes(self):
        # Given
        self.existing()
        before = snapshot(self.target)
        # When
        self.cli(expected=1)
        # Then
        self.assertEqual(snapshot(self.target), before)

    def test_preview_when_target_absent_has_no_effect(self):
        # Given: absent target.
        # When
        result = self.cli("knowledge", "--preview")
        # Then
        self.assertEqual(result["approval_state"], "not-requested")
        self.assertFalse(self.target.exists())

    def test_rerun_when_fresh_result_complete_has_zero_diffs(self):
        # Given
        self.cli()
        before = snapshot(self.target)
        # When
        result = self.cli()
        # Then
        self.assertEqual(result["diff_count"], 0)
        self.assertEqual(snapshot(self.target), before)

    def test_rerun_when_approved_diff_already_applied_has_zero_diffs(self):
        # Given
        self.existing()
        approval, _ = self.approved()
        self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        before = snapshot(self.target)
        # When
        result = self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        # Then
        self.assertEqual(result["diff_count"], 0)
        self.assertEqual(snapshot(self.target), before)

    def test_missing_key_when_selected_preserves_all_existing_bytes(self):
        # Given
        self.existing()
        original = (self.target / ".obsidian/app.json").read_bytes()
        approval, _ = self.approved({".obsidian/app.json": ["newFileFolderPath"]})
        # When
        self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        # Then: removing only the approved insertion recovers the original bytes.
        after = (self.target / ".obsidian/app.json").read_bytes()
        self.assertEqual(after.replace(b', "newFileFolderPath": "00. Inbox"', b""), original)

    def test_missing_setting_when_creation_approved_contains_only_selected_keys(self):
        # Given
        self.existing()
        approval, _ = self.approved({".obsidian/daily-notes.json": ["folder"]})
        before = snapshot(self.target)
        # When
        self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        # Then
        self.assertEqual(json.loads((self.target / ".obsidian/daily-notes.json").read_bytes()),
                         {"folder": "00. Inbox"})
        after = snapshot(self.target)
        after.pop(".obsidian/daily-notes.json")
        self.assertEqual(after, before)

    def test_setting_when_number_equals_boolean_still_applies_correct_json_type(self):
        # Given: Python equality considers 0 equal to False; JSON types are distinct.
        self.existing()
        daily = self.target / ".obsidian/daily-notes.json"
        daily.write_bytes(b'{"autorun": 0, "unknown": "keep"}\n')
        approval, _ = self.approved({".obsidian/daily-notes.json": ["autorun"]})
        # When
        self.cli("knowledge", "--mode", "additive", "--approval", str(approval))
        # Then
        self.assertEqual(daily.read_bytes(), b'{"autorun": false, "unknown": "keep"}\n')

    def test_malformed_manifest_when_invalid_json_has_no_writes(self):
        # Given
        (self.candidate / "knowledge.json").write_bytes(b'{"role":')
        # When
        self.cli(expected=1)
        # Then
        self.assertFalse(self.target.exists())

    def test_manifest_when_paths_or_schema_invalid_has_no_writes(self):
        # Given
        path = self.candidate / "knowledge.json"
        original = json.loads(path.read_bytes())
        invalid = ("../escape.md", "/escape.md", "./file.md", "a//b", "a\\b",
                   ".env", ".git/config", "candidate-manifest.json",
                   "90. Settings/04 Index/folder-structure.json", "20. Wiki")
        for destination in invalid:
            with self.subTest(destination=destination):
                document = copy.deepcopy(original)
                document["files"][0]["path"] = destination
                path.write_text(json.dumps(document), encoding="utf-8")
                # When
                self.cli(expected=1)
                # Then
                self.assertFalse(self.target.exists())

    def test_source_when_missing_even_other_role_native_asset_has_no_writes(self):
        # Given
        path = self.candidate / "common/native.json"
        native = json.loads(path.read_bytes())
        native["files"][0]["roles"] = ["personal"]
        path.write_text(json.dumps(native), encoding="utf-8")
        (self.source / ".obsidian/core-plugins.json").unlink()
        # When
        self.cli(expected=1)
        # Then
        self.assertFalse(self.target.exists())

    def test_json_when_duplicate_keys_or_nonfinite_refused(self):
        # Given
        path = self.candidate / "knowledge.json"
        for blob in (b'{"role":"knowledge","role":"personal"}',
                     b'{"schema_version":NaN}'):
            with self.subTest(blob=blob):
                path.write_bytes(blob)
                # When
                self.cli(expected=1)
                # Then
                self.assertFalse(self.target.exists())

    def test_target_when_symlink_ancestor_refused(self):
        # Given
        outside = self.base / "outside"
        outside.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        self.target = alias / "vault"
        before = snapshot(outside)
        # When
        self.cli(expected=1)
        # Then
        self.assertEqual(snapshot(outside), before)

    def test_target_when_parent_absent_never_creates_outside_target(self):
        # Given: creating the missing parent would be a write outside the target.
        parent = self.base / "missing-parent"
        self.target = parent / "vault"
        # When
        self.cli(expected=1)
        # Then
        self.assertFalse(parent.exists())

    def test_preview_when_empty_selection_does_not_select_all_settings(self):
        # Given: an explicit empty selection, not an omitted selection.
        self.existing()
        selection = self.base / "selection.json"
        selection.write_bytes(b"{}")
        before = snapshot(self.target)
        # When
        result = self.cli("knowledge", "--preview", "--select", str(selection))
        # Then
        self.assertEqual(result["changes"], [])
        self.assertEqual(snapshot(self.target), before)

    def test_source_when_internal_symlink_refused(self):
        # Given
        path = self.candidate / "common/sample.md"
        path.unlink()
        path.symlink_to("../knowledge/placement.md")
        # When
        self.cli(expected=1)
        # Then
        self.assertFalse(self.target.exists())

    def test_target_when_hardlinked_setting_refused(self):
        # Given
        self.existing()
        protected = self.base / "protected.json"
        os.link(self.target / ".obsidian/app.json", protected)
        before = snapshot(self.target)
        # When
        self.cli("knowledge", "--preview", expected=1)
        # Then
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(protected.read_bytes(), before[".obsidian/app.json"][1])

    def test_approval_when_stale_preimage_refused_before_any_write(self):
        # Given
        self.existing()
        approval, _ = self.approved({
            ".obsidian/app.json": ["newFileLocation"],
            ".obsidian/daily-notes.json": ["folder"],
        })
        (self.target / ".obsidian/daily-notes.json").write_bytes(b'{"folder":"user"}\n')
        before = snapshot(self.target)
        # When
        self.cli("knowledge", "--mode", "additive", "--approval", str(approval), expected=1)
        # Then
        self.assertEqual(snapshot(self.target), before)

    def test_approval_when_extra_formatting_or_scope_refused(self):
        # Given
        self.existing()
        approval, original = self.approved()
        for kind in ("format", "scope", "effect", "digest", "basis", "key", "state"):
            with self.subTest(kind=kind):
                value = copy.deepcopy(original)
                if kind == "format":
                    value["changes"][0]["after"] = value["changes"][0]["after"].replace("\r\n", "\n")
                elif kind == "scope":
                    value["approval_scope"].append("User.md")
                elif kind == "effect":
                    value["approval_effect"] = ["delete"]
                elif kind == "digest":
                    value["candidate_sha256"] = "0" * 64
                elif kind == "basis":
                    value["approval_basis"] = ""
                elif kind == "key":
                    value["changes"][0]["keys"] = ["unknown"]
                else:
                    value["approval_state"] = "not-requested"
                approval.write_text(json.dumps(value), encoding="utf-8")
                before = snapshot(self.target)
                # When
                self.cli("knowledge", "--mode", "additive", "--approval", str(approval), expected=1)
                # Then
                self.assertEqual(snapshot(self.target), before)

    def test_resume_when_repeated_interruptions_preserves_complete_files(self):
        # Given: an actual file-publication seam that interrupts before linking a file.
        original_link = os.link
        for filename in ("core-plugins.json", "Placement.md"):
            def interrupt(source, destination, *args, **kwargs):
                if destination == filename:
                    raise KeyboardInterrupt()
                return original_link(source, destination, *args, **kwargs)
            # When: each interruption leaves only complete exclusive files.
            with patch.object(ONBOARD.os, "link", side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    ONBOARD.run(self.candidate, "knowledge", self.target)
            # Then
            self.assertTrue((self.target / "candidate-manifest.json").is_file())
            self.assertEqual(list(self.target.rglob(".onboard-*")), [])
        result = self.cli("knowledge", "--mode", "resume")
        self.assertGreater(result["diff_count"], 0)
        self.assert_manifest()
        self.assertEqual(self.cli()["diff_count"], 0)

    def test_resume_when_completed_file_changed_refused_without_replacement(self):
        # Given
        self.cli()
        (self.target / "README.md").write_bytes(b"User edit.\n")
        before = snapshot(self.target)
        # When
        self.cli("knowledge", "--mode", "resume", expected=1)
        # Then
        self.assertEqual(snapshot(self.target), before)

    def test_resume_when_empty_folder_missing_reports_real_directory_diff(self):
        # Given
        self.cli()
        (self.target / "00. Inbox").rmdir()
        # When
        result = self.cli("knowledge", "--mode", "resume")
        # Then
        self.assertEqual(result["changed"], ["00. Inbox"])
        self.assertEqual(result["diff_count"], 1)
        self.assertTrue((self.target / "00. Inbox").is_dir())

    def test_approval_when_interrupted_batch_resumes_exact_postimages(self):
        # Given
        self.existing()
        _, approved = self.approved({
            ".obsidian/app.json": ["newFileLocation"],
            ".obsidian/daily-notes.json": ["folder"],
        })
        original_link = os.link
        def interrupt(source, destination, *args, **kwargs):
            if destination == "daily-notes.json":
                raise KeyboardInterrupt()
            return original_link(source, destination, *args, **kwargs)
        # When
        with patch.object(ONBOARD.os, "link", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                ONBOARD.run(self.candidate, "knowledge", self.target, "additive", approved)
        # Then: completed update remains valid; reapplication creates only the pending file.
        result = ONBOARD.run(self.candidate, "knowledge", self.target, "additive", approved)
        self.assertEqual(result["changed"], [".obsidian/daily-notes.json"])
        self.assertEqual(ONBOARD.run(self.candidate, "knowledge", self.target,
                                    "additive", approved)["diff_count"], 0)

    def test_candidate_when_instruction_like_content_is_not_executed(self):
        # Given: the synthetic body contains a traversal/command instruction.
        outside = self.base / "outside"
        outside.write_bytes(b"Protected.")
        # When
        self.cli()
        # Then
        self.assertEqual((self.target / "README.md").read_bytes(),
                         (self.candidate / "common/sample.md").read_bytes())
        self.assertEqual(outside.read_bytes(), b"Protected.")

    def test_python_when_parsed_under_38_grammar(self):
        # Given: product code, not a runtime compatibility shim.
        source = SCRIPT.read_text(encoding="utf-8")
        # When
        tree = ast.parse(source, feature_version=(3, 8))
        # Then
        self.assertIsInstance(tree, ast.Module)


if __name__ == "__main__":
    unittest.main()
