#!/usr/bin/env python3
"""Behavioral tests for the verify package."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "verify" / "scripts" / "verify.py"
FIXTURE = REPO / "tests" / "fixtures" / "verify" / "vault"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "vault"
        shutil.copytree(FIXTURE, self.root)

    def invoke(
        self, request: dict, approval: Optional[dict] = None
    ) -> subprocess.CompletedProcess:
        request_path = Path(self.temporary.name) / "request.json"
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
            approval_path = Path(self.temporary.name) / "approval.json"
            approval_path.write_text(json.dumps(approval), encoding="utf-8")
            command.extend(["--approval", str(approval_path)])
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def request(self, reviewed: bool, verdict: str) -> dict:
        return {
            "schema": "verify/request@1",
            "page": "Wiki/Attention.md",
            "manifest": [
                "Wiki/Attention.md",
                "Wiki/Focus.md",
                "Raw/Attention study.md",
            ],
            "claims": [
                {
                    "id": "attention-limited",
                    "start_line": 11,
                    "end_line": 11,
                    "reviewed": reviewed,
                    "verdict": verdict,
                    "counterpart": "",
                    "evidence": [],
                    "new_evidence": [],
                }
            ],
            "record_target": "Wiki/Attention.md",
        }

    def test_unreviewed_claim_stays_unverified_and_writes_nothing(self) -> None:
        before = sha256(self.root / "Wiki" / "Attention.md")

        completed = self.invoke(self.request(False, "unverified"))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["claims"][0]["status"], "unverified")
        self.assertFalse(result["claims"][0]["reviewed"])
        self.assertEqual(result["mutations_performed"], [])
        self.assertEqual(sha256(self.root / "Wiki" / "Attention.md"), before)

    def test_resolution_without_new_evidence_is_refused(self) -> None:
        request = self.request(True, "resolved")
        request["claims"][0]["counterpart"] = "Wiki/Focus.md"

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["code"], "new_evidence_required")

    def test_counterpart_must_be_in_manifest(self) -> None:
        request = self.request(True, "disputed")
        request["claims"][0]["counterpart"] = "Wiki/Missing.md"

        completed = self.invoke(request)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["code"], "manifest_required")

    def test_approved_record_appends_only_to_reviewed_page(self) -> None:
        request = self.request(True, "resolved")
        claim = request["claims"][0]
        claim["counterpart"] = "Wiki/Focus.md"
        claim["evidence"] = [{"path": "Wiki/Focus.md", "start_line": 9, "end_line": 9}]
        claim["new_evidence"] = [
            {"path": "Raw/Attention study.md", "start_line": 9, "end_line": 9}
        ]
        proposed = self.invoke(request)
        self.assertEqual(proposed.returncode, 0, proposed.stdout + proposed.stderr)
        item = json.loads(proposed.stdout)["proposals"][0]
        before = {
            path: sha256(self.root / path)
            for path in (
                "Wiki/Attention.md",
                "Wiki/Focus.md",
                "Raw/Attention study.md",
            )
        }
        approval = {
            "approval_state": "approved",
            "approval_effect": ["update"],
            "approval_scope": [item["path"]],
            "approval_basis": "Approved exact verification record for this test.",
            "approval_preimage": {item["path"]: item["preimage"]},
            "approval_proposal": {item["path"]: item["proposal_sha256"]},
        }

        completed = self.invoke(request, approval)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["mutations_performed"], ["Wiki/Attention.md"])
        self.assertNotEqual(sha256(self.root / "Wiki/Attention.md"), before["Wiki/Attention.md"])
        self.assertEqual(sha256(self.root / "Wiki/Focus.md"), before["Wiki/Focus.md"])
        self.assertEqual(
            sha256(self.root / "Raw/Attention study.md"),
            before["Raw/Attention study.md"],
        )


if __name__ == "__main__":
    unittest.main()
