#!/usr/bin/env python3
"""Behavioral tests for the audit package."""
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
SCRIPT = REPO / "skills" / "audit" / "scripts" / "audit.py"
FIXTURE = REPO / "tests" / "fixtures" / "verify" / "vault"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "vault"
        shutil.copytree(FIXTURE, self.root)

    def invoke(
        self, request: dict, approval: Optional[dict] = None
    ) -> subprocess.CompletedProcess:
        request_path = Path(self.temporary.name) / "audit-request.json"
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
            approval_path = Path(self.temporary.name) / "audit-approval.json"
            approval_path.write_text(json.dumps(approval), encoding="utf-8")
            command.extend(["--approval", str(approval_path)])
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )

    def request(self) -> dict:
        return {
            "schema": "audit/request@1",
            "scope": ["Wiki", "Personas"],
            "sample": ["Wiki/Attention.md", "Personas/Analyst.md"],
            "sample_method": "Explicit risk sample selected for this test.",
            "limits": ["Two selected notes; no exhaustive review."],
            "previous_report": "Reports/previous-audit.json",
            "report_path": "Reports/current-audit.json",
        }

    def test_report_states_scope_sample_limits_without_pseudo_score(self) -> None:
        completed = self.invoke(self.request())

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["scope"], ["Wiki", "Personas"])
        self.assertEqual(
            report["sample"],
            ["Wiki/Attention.md", "Personas/Analyst.md"],
        )
        self.assertGreaterEqual(len(report["limits"]), 2)
        self.assertIn("category_counts", report)
        self.assertIn("comparison", report)
        self.assertNotIn("score", report)
        self.assertNotIn("grade", report)
        self.assertEqual(report["mutations_performed"], [])

    def test_unapproved_report_proposal_writes_nothing(self) -> None:
        report_path = self.root / "Reports" / "current-audit.json"
        sampled_before = sha256(self.root / "Wiki" / "Attention.md")

        completed = self.invoke(self.request())

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse(report_path.exists())
        self.assertEqual(sha256(self.root / "Wiki" / "Attention.md"), sampled_before)

    def test_link_resolution_removes_only_a_literal_markdown_suffix(self) -> None:
        for name in ("Random", "System", "Item"):
            (self.root / "Wiki" / (name + ".md")).write_text(
                "---\ntype: wiki\n---\n# " + name + "\n",
                encoding="utf-8",
            )
        (self.root / "Wiki" / "Source.md").write_text(
            "---\ntype: wiki\n---\n# Source\n"
            "[[Wiki/Random.md]] [[Wiki/System.md]] [[Wiki/Item]] "
            "[[Wiki/Missing.md]] [[Wiki/Absent]]\n",
            encoding="utf-8",
        )
        request = self.request()
        request["scope"] = ["Wiki/Source.md"]
        request["sample"] = ["Wiki/Source.md"]
        request.pop("previous_report")
        request.pop("report_path")

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        broken = [
            finding["detail"]
            for finding in report["findings"]
            if finding["category"] == "broken_link"
        ]
        self.assertEqual(broken, ["Wiki/Missing.md", "Wiki/Absent"])

    def test_recursive_scope_rejects_nonregular_markdown_entries(self) -> None:
        pipe = self.root / "Wiki" / "Pipe.md"
        os.mkfifo(pipe)
        source = self.root / "Wiki" / "Pipe source.md"
        source.write_text(
            "---\ntype: wiki\n---\n# Pipe source\n"
            "[[Wiki/Pipe]] [[Wiki/Missing]]\n",
            encoding="utf-8",
        )
        source_before = sha256(source)
        request = self.request()
        request["scope"] = ["Wiki"]
        request["sample"] = ["Wiki/Pipe source.md"]
        request.pop("previous_report")
        request.pop("report_path")

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertNotIn("Wiki/Pipe.md", report["resolved_scope_notes"])
        broken = [
            finding["detail"]
            for finding in report["findings"]
            if finding["category"] == "broken_link"
        ]
        self.assertEqual(broken, ["Wiki/Pipe", "Wiki/Missing"])
        self.assertEqual(report["mutations_performed"], [])
        self.assertEqual(sha256(source), source_before)
        self.assertFalse(pipe.is_file())

    def test_approved_save_creates_only_the_report(self) -> None:
        request = self.request()
        proposed = self.invoke(request)
        self.assertEqual(proposed.returncode, 0, proposed.stdout + proposed.stderr)
        item = json.loads(proposed.stdout)["proposals"][0]
        note_hashes = {
            path: sha256(self.root / path)
            for path in ("Wiki/Attention.md", "Personas/Analyst.md")
        }
        approval = {
            "approval_state": "approved",
            "approval_effect": ["create"],
            "approval_scope": [item["path"]],
            "approval_basis": "Approved exact audit report for this test.",
            "approval_preimage": {item["path"]: "absent"},
            "approval_proposal": {item["path"]: item["proposal_sha256"]},
        }

        completed = self.invoke(request, approval)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "saved")
        self.assertEqual(report["mutations_performed"], ["Reports/current-audit.json"])
        self.assertTrue((self.root / "Reports" / "current-audit.json").is_file())
        for path, expected in note_hashes.items():
            self.assertEqual(sha256(self.root / path), expected)

    def test_sample_outside_scope_is_refused(self) -> None:
        request = self.request()
        request["scope"] = ["Wiki"]
        request["sample"] = ["Personas/Analyst.md"]

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["code"], "sample_outside_scope")


if __name__ == "__main__":
    unittest.main()
