import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "ingest" / "scripts" / "web-source-validate.py"
spec = importlib.util.spec_from_file_location("web_source_validate", SCRIPT)
assert spec is not None
assert spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class WebSourceValidateTest(unittest.TestCase):
    def test_extracts_content_section_and_checks_source_identity(self):
        body = " ".join(["real transcript body"] * 8)
        markdown = f"## Transcript\n\n{body}\n"
        result = mod.validate(
            markdown,
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            source_type="video",
            expected=["real transcript"],
        )
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["source_identity"]["canonical_url"],
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.assertTrue(result["source_identity"]["youtube_id_resolved"])

    def test_youtube_short_variants_canonicalize_without_a_note_field(self):
        for url in (
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ):
            with self.subTest(url=url):
                identity = mod.source_identity(url, source_type="video")
                self.assertEqual(
                    identity["canonical_url"],
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                )
                self.assertTrue(identity["youtube_id_resolved"])

    def test_rejects_challenge_page_even_with_words(self):
        body = "Access Denied. Checking your browser. " + " filler" * 100
        markdown = f"## Content\n\n{body}\n"
        result = mod.validate(markdown)
        self.assertFalse(result["passed"])
        self.assertIn("access denied", result["markers"])

    def test_rejects_empty_extraction(self):
        result = mod.validate("## Transcript\n\n## Extraction Evidence\n\nmethod: defuddle")
        self.assertFalse(result["passed"])
        self.assertIn("content_section_empty", result["reasons"])

    def test_rejects_invalid_source_identity_without_note_schema(self):
        result = mod.validate(
            "## Content\n\nReadable source text.",
            source_url="file:///private/source",
        )
        self.assertFalse(result["passed"])
        self.assertIn("source_url_scheme_not_http", result["source_identity"]["errors"])

    def test_does_not_apply_template_or_frontmatter_gates(self):
        markdown = (
            '---\n'
            'custom: "{{literal}}" and "quoted"\n'
            '---\n\n'
            "## Content\n\n"
            "The source body may contain {{literal}} as observed text.\n"
        )
        result = mod.validate(markdown)
        self.assertTrue(result["passed"])

    def test_extracts_readme_section_for_github(self):
        markdown = "## Repository Metadata\n\nCloudflare challenge marker outside target section.\n\n## README\n\n" + "github readme architecture command " * 20
        result = mod.validate(markdown, expected=["architecture"])
        self.assertTrue(result["passed"])

    def test_word_floor_is_advisory_not_a_completeness_proof(self):
        result = mod.validate("## Transcript\n\nshort excerpt", min_words=100)
        self.assertTrue(result["passed"])
        self.assertEqual(result["word_count"], 2)
        self.assertEqual(
            result["coverage_warnings"],
            ["word_count_below_advisory_floor:2<100"],
        )

    def test_cli_returns_nonzero_for_missing_expected_term(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".md") as f:
            f.write("## Content\n\n" + "alpha beta gamma " * 30)
            f.flush()
            code = mod.main(["--file", f.name, "--source-type", "article", "--expect", "needle"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
