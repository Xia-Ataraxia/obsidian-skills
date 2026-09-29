"""Verify the rights ledger against actual original asset bytes.

The second class checks the other kind of referenced artifact this repository
publishes: the recorded evidence reports the verification matrix links to. A
link that resolves and a report that parses say nothing about the run the report
describes; the report's own contents are checked in ``test_contracts.py``.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/verification-matrix.md"
EVIDENCE = ROOT / "tests/evidence"
EVIDENCE_LINK_RE = re.compile(r"\]\((\.\./tests/evidence/[^)]+)\)")


class AssetRightsTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / "assets/asset-ledger.json").read_text())["assets"]

    def test_every_svg_has_one_rights_record_and_matching_bytes(self):
        paths = [row["path"] for row in self.rows]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(set(paths), {str(p.relative_to(ROOT)) for p in (ROOT / "assets").rglob("*.svg")})
        for row in self.rows:
            with self.subTest(asset=row["path"]):
                raw = (ROOT / row["path"]).read_bytes()
                self.assertEqual(len(raw), row["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
                self.assertEqual(row["rights"]["license"], "MIT")
                self.assertTrue((ROOT / row["rights"]["license_file"]).is_file())
                self.assertTrue(row["creator"])
                self.assertTrue(row["origin"])

    def test_artwork_contains_no_executable_or_external_resource(self):
        for row in self.rows:
            with self.subTest(asset=row["path"]):
                svg = ET.fromstring((ROOT / row["path"]).read_bytes())
                self.assertTrue(svg.tag.endswith("}svg"))
                for node in svg.iter():
                    self.assertNotIn(node.tag.rsplit("}", 1)[-1], {"script", "foreignObject", "image"})
                    for key, value in node.attrib.items():
                        if key.rsplit("}", 1)[-1] == "href":
                            self.assertTrue(value.startswith("#"), "External resource in original SVG")

    def test_both_readmes_reference_existing_accessible_original_images(self):
        expected = {"assets/brand/hero.svg", "assets/demo/workflow.svg"}
        for name in ("README.md", "README.ko.md"):
            images = re.findall(r'<img\s+src="([^"]+)"\s+alt="([^"]+)"', (ROOT / name).read_text())
            self.assertEqual({path for path, _ in images}, expected)
            for path, alt in images:
                self.assertTrue((ROOT / path).is_file())
                self.assertTrue(alt.strip())


class EvidenceReferenceTests(unittest.TestCase):
    """Every evidence link in the matrix resolves, and no report is unpublished."""

    def setUp(self):
        self.matrix = MATRIX.read_text("utf-8")
        self.reports = sorted(EVIDENCE.glob("*.json"))

    def test_every_matrix_evidence_link_resolves_to_a_report_that_parses(self):
        links = set(EVIDENCE_LINK_RE.findall(self.matrix))
        self.assertTrue(links, "the matrix links no recorded evidence")
        for link in sorted(links):
            with self.subTest(link=link):
                target = (MATRIX.parent / link).resolve()
                self.assertTrue(target.is_file(), "a cited report is missing")
                self.assertEqual(target.parent, EVIDENCE.resolve())
                self.assertIsInstance(json.loads(target.read_text("utf-8")), dict)

    def test_every_recorded_report_is_referenced_by_the_matrix(self):
        self.assertTrue(self.reports, "no evidence report is recorded")
        for path in self.reports:
            with self.subTest(report=path.name):
                self.assertIn(path.name, self.matrix, "a report is recorded but never published")

    def test_no_evidence_link_points_outside_the_repository(self):
        for link in sorted(set(EVIDENCE_LINK_RE.findall(self.matrix))):
            with self.subTest(link=link):
                self.assertFalse(link.startswith("/"))
                self.assertNotIn("://", link)
                target = (MATRIX.parent / link).resolve()
                self.assertTrue(target.is_relative_to(ROOT.resolve()))


if __name__ == "__main__":
    unittest.main()
