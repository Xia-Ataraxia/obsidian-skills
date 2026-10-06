"""Functional source-evidence regressions; these do not admit native notes."""
import importlib.util
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "skills" / "ingest"
SCRIPT = PACKAGE / "scripts" / "web-source-validate.py"
spec = importlib.util.spec_from_file_location("web_source_validate_metadata_contract", SCRIPT)
assert spec is not None
assert spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class SourceEvidenceContractTest(unittest.TestCase):
    def test_youtube_url_identity_accepts_canonical_and_public_variants(self):
        for source_url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ):
            with self.subTest(source_url=source_url):
                result = validator.validate(
                    "## Transcript\n\nObserved transcript excerpt.",
                    source_url=source_url,
                    source_type="video",
                )
                self.assertTrue(result["passed"])
                identity = result["source_identity"]
                self.assertTrue(identity["youtube_id_resolved"])
                self.assertEqual(
                    identity["canonical_url"],
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                )

    def test_source_evidence_result_does_not_claim_note_admission(self):
        result = validator.validate(
            "## Content\n\nReadable article evidence.",
            source_url="https://example.com/article",
            source_type="article",
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["source_identity"]["host"], "example.com")
        note_admission_keys = {
            "admitted",
            "created_by",
            "folder",
            "path",
            "retention",
            "status",
            "template",
            "template_id",
            "type",
        }
        self.assertFalse(note_admission_keys.intersection(result))

    def test_source_failure_remains_extraction_evidence_not_note_admission(self):
        result = validator.validate(
            "## Content\n\nAccess Denied. Checking your browser.",
            source_url="https://example.com/article",
            source_type="article",
        )
        self.assertFalse(result["passed"])
        self.assertIn("access denied", result["markers"])
        self.assertNotIn("admitted", result)


if __name__ == "__main__":
    unittest.main()
