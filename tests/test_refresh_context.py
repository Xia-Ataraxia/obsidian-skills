"""Behavioral refresh-context tests over exact disposable snapshots."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/refresh-context/scripts/refresh_context.py"
SPEC = importlib.util.spec_from_file_location("refresh_context_under_test", SCRIPT)
REFRESH = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPT.parent))
try:
    SPEC.loader.exec_module(REFRESH)
finally:
    sys.path.pop(0)
SNAPSHOT_IO = sys.modules["snapshot_io"]


class RefreshContextTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="task13-refresh-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.vault = self.base / "vault"
        (self.vault / "Policy").mkdir(parents=True)
        (self.vault / "Derived").mkdir()
        (self.vault / "Me.md").write_text("# Owner\nCurrent intent.\n", encoding="utf-8")
        (self.vault / "Policy/Rules.md").write_text(
            "# Policy\nDerived files never replace sources.\n", encoding="utf-8")
        (self.vault / "Derived/agent.md").write_text(
            "# Old agent context\n", encoding="utf-8")
        (self.vault / "Derived/search.md").write_text(
            "# Old search context\n", encoding="utf-8")
        self.request = {
            "schema": "refresh-context/request@1",
            "sources": [
                {"name": "owner", "kind": "me", "path": "Me.md"},
                {"name": "rules", "kind": "policy", "path": "Policy/Rules.md"},
            ],
            "snapshots": [
                {"name": "agent", "path": "Derived/agent.md",
                 "content": "# Proposed agent context\n"},
                {"name": "search", "path": "Derived/search.md",
                 "content": "# Proposed search context\n"},
            ],
            "counterpart_vault": str(self.base / "missing-counterpart"),
        }

    def bytes(self):
        return {path.relative_to(self.vault).as_posix(): path.read_bytes()
                for path in self.vault.rglob("*") if path.is_file()}

    def approval(self, planned, state="approved", selected=None):
        items = planned["snapshots"]
        paths = [item["path"] for item in items] if selected is None else selected
        return {
            "approval_state": state,
            "approval_effect": sorted({item["effect"] for item in items if item["path"] in paths}),
            "approval_scope": paths,
            "approval_basis": "Synthetic owner approved these exact snapshot bytes.",
            "approval_preimage": {
                item["path"]: item["preimage"] for item in items if item["path"] in paths
            },
            "approval_proposal": {
                item["path"]: item["proposal_sha256"]
                for item in items if item["path"] in paths
            },
        }

    def test_proposal_rereads_sources_and_writes_nothing(self):
        # Given
        before = self.bytes()
        # When
        planned = REFRESH.run(self.vault, self.request)
        # Then
        self.assertEqual(self.bytes(), before)
        self.assertEqual(planned["mutations_performed"], [])
        self.assertEqual({source["kind"] for source in planned["sources"]}, {"me", "policy"})
        self.assertTrue(all(source["sha256"].startswith("sha256:") for source in planned["sources"]))
        self.assertEqual(planned["counterpart_status"], "absent-allowed")

    def test_partial_approval_changes_only_approved_snapshot(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        approval = self.approval(
            planned, state="partially-approved", selected=["Derived/agent.md"])
        before = self.bytes()
        # When
        result = REFRESH.run(self.vault, self.request, approval)
        # Then
        after = self.bytes()
        self.assertEqual(result["mutations_performed"], ["Derived/agent.md"])
        self.assertEqual(after["Derived/agent.md"], b"# Proposed agent context\n")
        self.assertEqual(after["Derived/search.md"], before["Derived/search.md"])
        self.assertEqual(after["Me.md"], before["Me.md"])
        self.assertEqual(after["Policy/Rules.md"], before["Policy/Rules.md"])

    def test_full_approval_changes_every_named_snapshot_only(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        before = self.bytes()
        # When
        result = REFRESH.run(self.vault, self.request, self.approval(planned))
        # Then
        after = self.bytes()
        self.assertEqual(set(result["mutations_performed"]),
                         {"Derived/agent.md", "Derived/search.md"})
        self.assertEqual(after["Me.md"], before["Me.md"])
        self.assertEqual(after["Policy/Rules.md"], before["Policy/Rules.md"])

    def test_rejection_changes_nothing(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        rejected = self.approval(planned, state="rejected", selected=[])
        before = self.bytes()
        # When
        result = REFRESH.run(self.vault, self.request, rejected)
        # Then
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(self.bytes(), before)

    def test_stale_source_or_snapshot_refuses_every_write(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        approval = self.approval(planned)
        cases = ["source", "snapshot"]
        # When / Then
        for case in cases:
            with self.subTest(case=case):
                self.setUp()
                planned = REFRESH.run(self.vault, self.request)
                approval = self.approval(planned)
                if case == "source":
                    (self.vault / "Me.md").write_text("# Owner\nConcurrent edit.\n", encoding="utf-8")
                    expected = "stale_approval"
                else:
                    (self.vault / "Derived/agent.md").write_text(
                        "# Concurrent snapshot edit\n", encoding="utf-8")
                    expected = "stale_approval"
                before = self.bytes()
                with self.assertRaises(REFRESH.Refused) as raised:
                    REFRESH.run(self.vault, self.request, approval)
                self.assertEqual(raised.exception.code, expected)
                self.assertEqual(self.bytes(), before)

    def test_unknown_scope_and_source_snapshot_overlap_are_refused(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        unknown = self.approval(planned)
        unknown["approval_scope"].append("Derived/unknown.md")
        overlap = copy.deepcopy(self.request)
        overlap["snapshots"][0]["path"] = "Me.md"
        before = self.bytes()
        # When / Then
        with self.assertRaises(REFRESH.Refused):
            REFRESH.run(self.vault, self.request, unknown)
        with self.assertRaises(REFRESH.Refused):
            REFRESH.run(self.vault, overlap)
        self.assertEqual(self.bytes(), before)

    def test_malformed_approval_scope_is_structured_cli_refusal_without_writes(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        approval = self.approval(
            planned, state="partially-approved", selected=["Derived/agent.md"])
        approval["approval_scope"] = [{}]
        request_path = self.base / "request.json"
        approval_path = self.base / "approval.json"
        request_path.write_text(json.dumps(self.request), encoding="utf-8")
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        before = self.bytes()
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--request", str(request_path), "--approval", str(approval_path)],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        envelope = json.loads(result.stdout)
        self.assertEqual(
            (envelope["schema"], envelope["status"], envelope["code"]),
            ("refresh-context/error@1", "refused", "invalid_input"),
        )
        self.assertEqual(envelope["mutations_performed"], [])
        self.assertEqual(self.bytes(), before)

    def test_missing_counterpart_does_not_block_standalone_apply(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        approval = self.approval(
            planned, state="partially-approved", selected=["Derived/search.md"])
        # When
        result = REFRESH.run(self.vault, self.request, approval)
        # Then
        self.assertEqual(result["counterpart_status"], "absent-allowed")
        self.assertEqual(result["status"], "applied")

    def test_repeated_mid_batch_interruptions_restore_every_snapshot(self):
        # Given
        planned = REFRESH.run(self.vault, self.request)
        approval = self.approval(planned)
        before = self.bytes()
        real_replace = SNAPSHOT_IO.os.replace
        # When / Then: two independent interrupted attempts both roll back.
        for attempt in range(2):
            calls = {"count": 0}

            def interrupt_second(source, destination):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise KeyboardInterrupt()
                return real_replace(source, destination)

            with self.subTest(attempt=attempt):
                with patch.object(SNAPSHOT_IO.os, "replace", side_effect=interrupt_second):
                    with self.assertRaises(REFRESH.Refused) as raised:
                        REFRESH.run(self.vault, self.request, approval)
                self.assertEqual(raised.exception.code, "application_interrupted")
                self.assertEqual(self.bytes(), before)

    def test_script_parses_with_python38_grammar(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 8))
        self.assertTrue(tree.body)


if __name__ == "__main__":
    unittest.main()
