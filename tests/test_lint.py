#!/usr/bin/env python3
"""Behavioral tests for the lint package."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "lint" / "scripts" / "lint.py"
FIXTURE = REPO / "tests" / "fixtures" / "verify" / "vault"
CROSS_VAULT = REPO / "tests" / "fixtures" / "verify" / "cross-vault"


def hashes(root: Path) -> dict:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class LintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "vault"
        shutil.copytree(FIXTURE, self.root)

    def invoke(
        self, request: dict, approval: Optional[dict] = None
    ) -> subprocess.CompletedProcess:
        request_path = Path(self.temporary.name) / "lint-request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            "--vault",
            str(self.root),
            "--request",
            str(request_path),
        ]
        if approval is not None:
            approval_path = Path(self.temporary.name) / "lint-approval.json"
            approval_path.write_text(json.dumps(approval), encoding="utf-8")
            command.extend(["--approval", str(approval_path)])
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )

    def request(self, mode: str = "report") -> dict:
        return {
            "schema": "lint/request@1",
            "mode": mode,
            "scope": ["Wiki", "Personas"],
            "required_properties": ["type", "created_by", "authorship"],
            "derived_index": "Indexes/Knowledge.md",
            "boundaries": [
                {
                    "name": "persona-to-personal-people",
                    "root": "Personas",
                    "forbidden_roots": ["People"],
                }
            ],
        }

    def test_report_mode_checks_all_categories_and_writes_nothing(self) -> None:
        before = hashes(self.root)

        completed = self.invoke(self.request())

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["mode"], "report")
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(result["note_patch_proposals"], [])
        self.assertEqual(
            set(result["checks"]),
            {
                "structure",
                "citations",
                "properties",
                "index",
                "broken_link",
                "orphan_link",
                "persona_boundary",
            },
        )
        self.assertIn(
            "persona_boundary",
            {finding["category"] for finding in result["findings"]},
        )
        self.assertEqual(hashes(self.root), before)

    def test_cross_vault_link_without_target_is_limited_and_unconfirmed(self) -> None:
        request = self.request()
        request["scope"] = ["Personas"]
        before = hashes(self.root)

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "limited")
        self.assertFalse(result["cross_vault"]["permission_confirmed"])
        self.assertFalse(result["cross_vault"]["checked"])
        self.assertTrue(result["cross_vault"]["blocks_fix"])
        self.assertEqual(result["cross_vault"]["links_encountered"], 1)
        self.assertNotIn("cross_vault_link", result["checks"])
        self.assertEqual(len(result["derived_index_proposals"]), 1)
        self.assertEqual(result["note_patch_proposals"], [])
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(hashes(self.root), before)

    def test_single_note_scope_does_not_read_unrelated_note_bodies(self) -> None:
        (self.root / "People" / "Unreadable.md").write_bytes(b"\xff")
        before = hashes(self.root)
        request = self.request()
        request["scope"] = ["Wiki/Focus.md"]

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["checked_notes"], ["Wiki/Focus.md"])
        self.assertEqual(
            {finding["path"] for finding in result["findings"]},
            {"Indexes/Knowledge.md", "Wiki/Focus.md"},
        )
        self.assertFalse(result["cross_vault"]["checked"])
        self.assertFalse(result["cross_vault"]["blocks_fix"])
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(hashes(self.root), before)

    def test_link_resolution_removes_only_an_exact_markdown_suffix(self) -> None:
        for name in ("System", "Random", "Item"):
            (self.root / "Wiki" / (name + ".md")).write_text(
                "---\ntype: wiki\ncreated_by: agent\nauthorship: agent\n---\n# " + name + "\n",
                encoding="utf-8",
            )
        (self.root / "Wiki" / "Source.md").write_text(
            "---\ntype: wiki\ncreated_by: agent\nauthorship: agent\n---\n"
            "# Source\n\n[[System]] [[Random.md]] [[Item]] [[Missing.md]]\n",
            encoding="utf-8",
        )
        request = self.request()
        request["scope"] = ["Wiki/Source.md"]

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        broken = [
            finding["detail"]
            for finding in result["findings"]
            if finding["category"] == "broken_link"
        ]
        self.assertEqual(broken, ["Missing.md"])

    def test_recursive_scope_rejects_nonregular_markdown_entries(self) -> None:
        pipe = self.root / "Wiki" / "Pipe.md"
        os.mkfifo(pipe)
        (self.root / "Wiki" / "Pipe source.md").write_text(
            "---\ntype: wiki\ncreated_by: agent\nauthorship: agent\n---\n"
            "# Pipe source\n\n[[Wiki/Pipe]] [[Wiki/Missing]]\n",
            encoding="utf-8",
        )
        before = hashes(self.root)
        request = self.request()
        request["scope"] = ["Wiki"]

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertNotIn("Wiki/Pipe.md", result["checked_notes"])
        broken = [
            finding["detail"]
            for finding in result["findings"]
            if finding["category"] == "broken_link"
        ]
        self.assertEqual(broken, ["Wiki/Pipe", "Wiki/Missing"])
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(hashes(self.root), before)
        self.assertFalse(pipe.is_file())

    def test_fix_mode_changes_only_the_derived_index(self) -> None:
        request = self.request("report")
        request["scope"] = ["Wiki"]
        proposed = self.invoke(request)
        self.assertEqual(proposed.returncode, 0, proposed.stdout + proposed.stderr)
        item = json.loads(proposed.stdout)["derived_index_proposals"][0]
        before = hashes(self.root)
        approval = {
            "approval_state": "approved",
            "approval_effect": [item["effect"]],
            "approval_scope": [item["path"]],
            "approval_basis": "Approved exact derived-index fix for this test.",
            "approval_preimage": {item["path"]: item["preimage"]},
            "approval_proposal": {item["path"]: item["proposal_sha256"]},
        }
        request["mode"] = "fix"

        completed = self.invoke(request, approval)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "fixed")
        self.assertEqual(result["mutations_performed"], ["Indexes/Knowledge.md"])
        after = hashes(self.root)
        changed = sorted(path for path in after if before.get(path) != after[path])
        self.assertEqual(changed, ["Indexes/Knowledge.md"])

    def test_unconfirmed_cross_vault_target_reports_limit_and_blocks_fix(self) -> None:
        request = self.request("fix")
        request["cross_vault"] = {
            "target_name": "research",
            "target_root": str(CROSS_VAULT),
            "permission_state": "requested",
            "permission_basis": "",
        }
        before = hashes(self.root)

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "limited")
        self.assertFalse(result["cross_vault"]["permission_confirmed"])
        self.assertTrue(result["limits"])
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(hashes(self.root), before)

    def test_confirmed_cross_vault_target_is_checked_by_name(self) -> None:
        request = self.request()
        request["cross_vault"] = {
            "target_name": "research",
            "target_root": str(CROSS_VAULT),
            "permission_state": "approved",
            "permission_basis": "Approved exact test target read.",
        }

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["cross_vault"]["permission_confirmed"])
        self.assertTrue(result["cross_vault"]["checked"])
        self.assertEqual(result["cross_vault"]["target_name"], "research")
        self.assertIn("cross_vault_link", result["checks"])
        self.assertNotIn(
            "cross_vault_link",
            {finding["category"] for finding in result["findings"]},
        )


if __name__ == "__main__":
    unittest.main()
