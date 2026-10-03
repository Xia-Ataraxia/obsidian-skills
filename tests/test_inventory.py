"""Behavioural tests for the source inventory and its audit.

Two halves. The first exercises `audit()` against synthetic manifests and
synthetic source checkouts, so every failure mode has a test that actually fails
when the check is removed. The second asserts properties of the real
`source-inventory.json` that a reviewer would otherwise have to check by hand.
"""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_inventory  # noqa: E402
from audit_inventory import audit  # noqa: E402

MANIFEST_PATH = ROOT / "source-inventory.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

COPYRIGHT = "Copyright (c) 2099 Example Holder"
NOTICE_TEXT = (
    "Synthetic notice\n\n"
    f"{COPYRIGHT}\n\n"
    f"{audit_inventory.PERMISSION_SENTENCE}\n"
    "copies or substantial portions of the Software.\n"
)
FEATURE_NAMES = {
    "F01": "markdown",
    "F02": "bases",
    "F03": "canvas",
    "F04": "mermaid",
    "F05": "visualize",
    "F06": "cli",
    "F07": "clipper",
    "F08": "doctor",
    "F09": "sync",
}


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SyntheticAuditTest(unittest.TestCase):
    """Every audit rule, exercised through a manifest that is valid until mutated."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.root = base / "repo"
        self.unlicensed = base / "unlicensed-checkout"
        self.licensed = base / "licensed-checkout"

        # Repository tree: nine package directories, one target per functional unit.
        for feature, name in FEATURE_NAMES.items():
            (self.root / f"skills/obsidian-{name}").mkdir(parents=True)
            self._write(self.root / f"skills/obsidian-{name}/SKILL.md", f"# {feature}\n")
        self._write(self.root / "NOTICE", NOTICE_TEXT)
        self._write(self.root / "AGENTS.md", "# contract\n")

        # Source checkouts. The mixed file carries three units; the others one each.
        self.source_bodies = {
            "pkg/mixed.md": "routes and a shared section\n",
            "pkg/single-canvas.md": "canvas behaviour\n",
            "pkg/single-mermaid.md": "mermaid behaviour\n",
            "pkg/single-visualize.md": "visualize behaviour\n",
            "pkg/single-cli.md": "cli behaviour\n",
            "pkg/single-clipper.md": "clipper behaviour\n",
            "pkg/single-doctor.md": "doctor behaviour\n",
            "pkg/single-sync.md": "sync behaviour\n",
        }
        for path, body in self.source_bodies.items():
            self._write(self.unlicensed / path, body)
        self._write(self.unlicensed / "ignored/skip.md", "out of scope\n")
        self.licensed_bodies = {
            "lib/imported.md": "imported markdown recipe\n",
            "LICENSE": f"MIT\n\n{COPYRIGHT}\n",
        }
        for path, body in self.licensed_bodies.items():
            self._write(self.licensed / path, body)

        self.data = self._manifest()
        self.roots = {"unlicensed": self.unlicensed, "licensed": self.licensed}

    def _write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _file_row(self, file_id, source, path, body, rights, kind, units):
        return {
            "id": file_id,
            "source": source,
            "path": path,
            "sha256": _digest(body),
            "bytes": len(body.encode("utf-8")),
            "rights": rights,
            "kind": kind,
            "expected_units": units,
        }

    def _unit(self, unit_id, file_id, unit, owner, **kwargs):
        row = {
            "id": unit_id,
            "file": file_id,
            "unit": unit,
            "class": "functional" if owner else "supporting",
            "owner": owner,
            "disposition": kwargs.pop("disposition", "reimplemented"),
            "behavior": kwargs.pop("behavior", "behaviour statement"),
        }
        if owner:
            name = FEATURE_NAMES[owner]
            target = kwargs.pop("target", f"skills/obsidian-{name}/SKILL.md")
            row["target"] = target
            row["package"] = f"obsidian-{name}"
            row["verification"] = kwargs.pop("verification", [f"{target}#verification"])
        row.update(kwargs)
        return row

    def _manifest(self):
        single = {
            "pkg/single-canvas.md": ("S03", "F03"),
            "pkg/single-mermaid.md": ("S04", "F04"),
            "pkg/single-visualize.md": ("S05", "F05"),
            "pkg/single-cli.md": ("S06", "F06"),
            "pkg/single-clipper.md": ("S07", "F07"),
            "pkg/single-doctor.md": ("S08", "F08"),
            "pkg/single-sync.md": ("S09", "F09"),
        }
        files = [
            self._file_row(
                "M01", "unlicensed", "pkg/mixed.md", self.source_bodies["pkg/mixed.md"],
                "evidence-only", "mixed-route-and-section",
                ["route:markdown", "route:bases", "section:shared-contract"],
            )
        ]
        units = [
            self._unit("u-mixed-markdown", "M01", "route:markdown", "F01"),
            self._unit("u-mixed-bases", "M01", "route:bases", "F02"),
            self._unit(
                "u-mixed-shared", "M01", "section:shared-contract", None,
                target="AGENTS.md",
            ),
        ]
        for path, (file_id, owner) in single.items():
            files.append(
                self._file_row(
                    file_id, "unlicensed", path, self.source_bodies[path],
                    "evidence-only", "single-feature", [f"whole:{owner}"],
                )
            )
            units.append(self._unit(f"u-{file_id}", file_id, f"whole:{owner}", owner))
        files.append(
            self._file_row(
                "L01", "licensed", "lib/imported.md",
                self.licensed_bodies["lib/imported.md"], "mit-import", "single-feature",
                ["whole:imported-recipe"],
            )
        )
        units.append(
            self._unit(
                "u-imported", "L01", "whole:imported-recipe", "F01",
                disposition="imported",
            )
        )
        files.append(
            self._file_row(
                "L02", "licensed", "LICENSE", self.licensed_bodies["LICENSE"],
                "mit-notice", "rights-evidence", ["whole:notice"],
            )
        )
        units.append(
            self._unit("u-notice", "L02", "whole:notice", None, disposition="imported",
                       target="NOTICE")
        )
        return {
            "schema_version": audit_inventory.SCHEMA_VERSION,
            "features": {
                feature: {"name": name, "package": f"skills/obsidian-{name}"}
                for feature, name in FEATURE_NAMES.items()
            },
            "sources": {
                "unlicensed": {
                    "name": "unlicensed-source",
                    "revision": "a" * 40,
                    "license": {"spdx": None, "evidence": "no licence file at this revision"},
                    "coverage_roots": ["pkg"],
                    "partition": True,
                },
                "licensed": {
                    "name": "licensed-source",
                    "revision": "b" * 40,
                    "license": {
                        "spdx": "MIT",
                        "file": "LICENSE",
                        "copyright": COPYRIGHT,
                        "evidence": "root LICENSE carries the full MIT text",
                    },
                    "coverage_roots": ["lib"],
                    "partition": True,
                },
            },
            "files": files,
            "units": units,
            "excluded": [
                {
                    "source": "unlicensed",
                    "patterns": ["ignored/**"],
                    "reason": "out of scope for the nine features",
                }
            ],
        }

    def _audit(self, data=None, with_sources=True):
        return audit(
            data or self.data, self.root, self.roots if with_sources else None
        )

    # --- the baseline must be clean, or no negative test below proves anything ---

    def test_valid_manifest_has_no_errors(self):
        self.assertEqual([], self._audit())

    def test_valid_mixed_split_is_accepted(self):
        """One source file, two different owners plus a shared supporting unit."""
        mixed = [unit for unit in self.data["units"] if unit["file"] == "M01"]
        self.assertEqual(3, len(mixed))
        self.assertEqual({"F01", "F02"}, {u["owner"] for u in mixed if u["owner"]})
        self.assertEqual(
            1, sum(1 for u in mixed if u["class"] == "supporting")
        )
        self.assertEqual([], self._audit())

    # --- required negative tests ---

    def test_duplicate_unit_is_rejected(self):
        data = copy.deepcopy(self.data)
        duplicate = copy.deepcopy(data["units"][0])
        duplicate["id"] = "u-mixed-markdown-copy"
        data["units"].append(duplicate)
        data["files"][0]["expected_units"].append("route:markdown")
        errors = self._audit(data)
        self.assertIn("duplicate responsibility unit: ('M01', 'route:markdown')", errors)

    def test_duplicate_stable_unit_id_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][1]["id"] = data["units"][0]["id"]
        self.assertIn(
            f"duplicate stable unit ID: {data['units'][0]['id']}", self._audit(data)
        )

    def test_missing_owner_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["owner"] = None
        errors = self._audit(data)
        self.assertIn(
            "missing or invalid single owner: ('M01', 'route:markdown')", errors
        )

    def test_owner_outside_the_nine_features_is_rejected(self):
        """An out-of-range owner is not a tenth feature; it leaves its feature uncovered."""
        data = copy.deepcopy(self.data)
        for unit in data["units"]:
            if unit["owner"] == "F01":
                unit["owner"] = "F10"
        errors = self._audit(data)
        self.assertIn(
            "missing or invalid single owner: ('M01', 'route:markdown')", errors
        )
        self.assertIn(
            "missing or invalid single owner: ('L01', 'whole:imported-recipe')", errors
        )
        self.assertIn("uncovered feature owners: ['F01']", errors)

    def test_feature_with_no_functional_unit_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"] = [u for u in data["units"] if u["owner"] != "F09"]
        data["files"] = [f for f in data["files"] if f["id"] != "S09"]
        errors = self._audit(data)
        self.assertIn("uncovered feature owners: ['F09']", errors)

    def test_missing_unit_declared_by_its_file_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"] = [u for u in data["units"] if u["unit"] != "route:bases"]
        errors = self._audit(data)
        self.assertIn("unit inventory mismatch: M01", errors)
        self.assertIn("uncovered feature owners: ['F02']", errors)

    def test_unit_absent_from_its_file_declaration_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["files"][0]["expected_units"].remove("section:shared-contract")
        self.assertIn("unit inventory mismatch: M01", self._audit(data))

    def test_source_file_with_no_unit_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"] = [u for u in data["units"] if u["file"] != "S08"]
        data["files"] = [
            dict(f, expected_units=[]) if f["id"] == "S08" else f for f in data["files"]
        ]
        errors = self._audit(data)
        self.assertIn("uncovered source file: S08", errors)

    def test_hash_tamper_is_detected(self):
        data = copy.deepcopy(self.data)
        data["files"][0]["sha256"] = _digest("a different body")
        self.assertIn("source digest mismatch: M01", self._audit(data))

    def test_byte_count_tamper_is_detected(self):
        data = copy.deepcopy(self.data)
        data["files"][0]["bytes"] = data["files"][0]["bytes"] + 1
        self.assertIn("source byte-count mismatch: M01", self._audit(data))

    def test_malformed_digest_is_rejected_without_a_checkout(self):
        data = copy.deepcopy(self.data)
        data["files"][0]["sha256"] = "NOTAHASH"
        self.assertIn(
            "missing or malformed digest: M01", self._audit(data, with_sources=False)
        )

    def test_source_path_must_be_a_canonical_relative_path(self):
        for unsafe in ("", "./pkg/mixed.md", "pkg/../pkg/mixed.md", "/etc/hostname"):
            with self.subTest(path=unsafe):
                data = copy.deepcopy(self.data)
                data["files"][0]["path"] = unsafe
                self.assertIn("unsafe or missing source path: M01", self._audit(data))

    def test_unsafe_source_path_is_never_read_from_outside_the_checkout(self):
        outside = self.root.parent / "outside/secret.md"
        self._write(outside, "a file that belongs to no checkout\n")
        data = copy.deepcopy(self.data)
        data["files"][0]["path"] = str(outside)
        errors = self._audit(data)
        self.assertIn("unsafe or missing source path: M01", errors)
        self.assertNotIn("source digest mismatch: M01", errors)
        self.assertNotIn("source byte-count mismatch: M01", errors)

    def test_supporting_unit_may_not_carry_an_owner(self):
        data = copy.deepcopy(self.data)
        unit = next(u for u in data["units"] if u["unit"] == "section:shared-contract")
        unit["owner"] = "F01"
        self.assertIn(
            "supporting unit has functional owner: ('M01', 'section:shared-contract')",
            self._audit(data),
        )

    def test_functional_target_outside_the_owning_package_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = "skills/obsidian-bases/SKILL.md"
        data["units"][0]["verification"] = ["skills/obsidian-bases/SKILL.md"]
        self.assertIn(
            "target outside owning package: ('M01', 'route:markdown')", self._audit(data)
        )

    def test_missing_target_file_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = "skills/obsidian-markdown/ABSENT.md"
        self.assertIn("missing target: ('M01', 'route:markdown')", self._audit(data))

    def test_functional_target_escaping_its_package_by_traversal_is_rejected(self):
        """The path starts with the owning package and still lands in another one."""
        target = "skills/obsidian-markdown/../obsidian-bases/SKILL.md"
        self.assertTrue(target.startswith("skills/obsidian-markdown/"))
        self.assertTrue((self.root / target).exists())
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = target
        errors = self._audit(data)
        self.assertIn("unsafe target path: ('M01', 'route:markdown')", errors)

    def test_absolute_functional_target_is_rejected(self):
        """An absolute target silently discards the repository root it is joined to."""
        target = str((self.root / "skills/obsidian-markdown/SKILL.md").resolve())
        self.assertTrue(Path(target).is_absolute())
        self.assertTrue((self.root / target).exists())
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = target
        self.assertIn(
            "unsafe target path: ('M01', 'route:markdown')", self._audit(data)
        )

    def test_functional_target_reached_through_an_escaping_symlink_is_rejected(self):
        """A link inside the package that resolves out of the repository."""
        outside = self.root.parent / "outside/leaked.md"
        self._write(outside, "material that is not in this repository\n")
        link = self.root / "skills/obsidian-markdown/LEAK.md"
        link.symlink_to(outside)
        self.assertTrue(link.exists())
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = "skills/obsidian-markdown/LEAK.md"
        data["units"][0]["verification"] = ["skills/obsidian-markdown/LEAK.md#anchor"]
        errors = self._audit(data)
        self.assertIn("unsafe target path: ('M01', 'route:markdown')", errors)
        self.assertIn(
            "unsafe verification reference: ('M01', 'route:markdown') "
            "-> skills/obsidian-markdown/LEAK.md#anchor",
            errors,
        )

    def test_functional_target_symlinked_into_another_package_is_rejected(self):
        """A link that stays in the repository but leaves the package it is owned by."""
        link = self.root / "skills/obsidian-markdown/BASES.md"
        link.symlink_to(self.root / "skills/obsidian-bases/SKILL.md")
        self.assertTrue(link.exists())
        data = copy.deepcopy(self.data)
        data["units"][0]["target"] = "skills/obsidian-markdown/BASES.md"
        self.assertIn(
            "target outside owning package: ('M01', 'route:markdown')", self._audit(data)
        )

    def test_supporting_target_outside_the_repository_is_rejected(self):
        outside = self.root.parent / "outside/notes.md"
        self._write(outside, "a file this repository does not own\n")
        self.assertTrue((self.root / "../outside/notes.md").exists())
        data = copy.deepcopy(self.data)
        unit = next(u for u in data["units"] if u["unit"] == "section:shared-contract")
        unit["target"] = "../outside/notes.md"
        self.assertIn(
            "unsafe target path: ('M01', 'section:shared-contract')", self._audit(data)
        )

    def test_missing_verification_mapping_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["verification"] = []
        self.assertIn(
            "missing verification mapping: ('M01', 'route:markdown')", self._audit(data)
        )

    def test_unresolved_verification_reference_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["verification"] = ["tests/test_absent.py::case"]
        self.assertIn(
            "unresolved verification reference: ('M01', 'route:markdown') "
            "-> tests/test_absent.py::case",
            self._audit(data),
        )

    def test_verification_reference_outside_the_repository_is_rejected(self):
        outside = self.root.parent / "outside/evidence.md"
        self._write(outside, "evidence that is not in this repository\n")
        data = copy.deepcopy(self.data)
        data["units"][0]["verification"] = ["../outside/evidence.md#case"]
        self.assertIn(
            "unsafe verification reference: ('M01', 'route:markdown') "
            "-> ../outside/evidence.md#case",
            self._audit(data),
        )

    def test_import_from_an_unlicensed_source_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["disposition"] = "imported"
        self.assertIn(
            "imported unit on non-copyable source: ('M01', 'route:markdown')",
            self._audit(data),
        )

    def test_copy_rights_on_an_unlicensed_source_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["files"][0]["rights"] = "mit-import"
        self.assertIn("rights claim exceeds source licence evidence: M01", self._audit(data))

    def test_not_adopted_functional_unit_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["disposition"] = "not-adopted"
        self.assertIn(
            "functional unit cannot be not-adopted: ('M01', 'route:markdown')",
            self._audit(data),
        )

    def test_not_adopted_supporting_unit_needs_a_reason(self):
        data = copy.deepcopy(self.data)
        unit = next(u for u in data["units"] if u["unit"] == "section:shared-contract")
        unit["disposition"] = "not-adopted"
        self.assertIn(
            "not-adopted unit needs a reason: ('M01', 'section:shared-contract')",
            self._audit(data),
        )

    def test_unit_may_not_compose_its_own_owner(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["composes"] = ["F01"]
        self.assertIn(
            "unit composes its own owner: ('M01', 'route:markdown')", self._audit(data)
        )

    def test_exclusion_overlapping_an_inventoried_file_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["excluded"][0]["patterns"] = ["pkg/**"]
        errors = self._audit(data)
        self.assertIn("exclusion overlaps inventoried file: pkg/** -> pkg/mixed.md", errors)

    def test_stale_exclusion_pattern_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["excluded"][0]["patterns"] = ["never/**"]
        self.assertIn("stale exclusion pattern: unlicensed -> never/**", self._audit(data))

    def test_file_in_a_coverage_root_must_be_inventoried(self):
        self._write(self.unlicensed / "pkg/forgotten.md", "a route nobody recorded\n")
        errors = self._audit()
        self.assertIn(
            "uninventoried file in coverage root: unlicensed -> pkg/forgotten.md", errors
        )

    def test_file_outside_every_rule_breaks_the_partition(self):
        self._write(self.unlicensed / "stray/extra.md", "neither inventoried nor excluded\n")
        self.assertIn(
            "unpartitioned source file: unlicensed -> stray/extra.md", self._audit()
        )

    def test_notice_must_carry_the_upstream_copyright_line(self):
        self._write(self.root / "NOTICE", audit_inventory.PERMISSION_SENTENCE + "\n")
        self.assertIn("NOTICE is missing the copyright line for licensed", self._audit())

    def test_notice_must_carry_the_permission_notice(self):
        self._write(self.root / "NOTICE", COPYRIGHT + "\n")
        self.assertIn("NOTICE is missing the MIT permission notice", self._audit())

    def test_missing_notice_file_is_rejected_when_material_was_copied(self):
        (self.root / "NOTICE").unlink()
        self.assertIn("copied licensed material requires a NOTICE file", self._audit())

    def test_licensed_source_without_a_copyright_line_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["sources"]["licensed"]["license"].pop("copyright")
        self.assertIn("licensed source needs an exact copyright line: licensed", self._audit(data))

    def test_inexact_revision_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["sources"]["unlicensed"]["revision"] = "main"
        self.assertIn(
            "source needs an exact 40-character revision: unlicensed", self._audit(data)
        )

    def test_missing_feature_package_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["features"]["F09"]["package"] = "skills/obsidian-absent"
        errors = self._audit(data)
        self.assertIn("missing feature package: F09 -> skills/obsidian-absent", errors)

    def test_feature_package_reached_by_traversal_is_rejected(self):
        """Ownership is only real if the package itself is a canonical repository path."""
        package = "skills/obsidian-doctor/../obsidian-sync"
        self.assertTrue((self.root / package).is_dir())
        data = copy.deepcopy(self.data)
        data["features"]["F09"]["package"] = package
        self.assertIn(
            f"unsafe feature package path: F09 -> {package}", self._audit(data)
        )

    def test_two_features_declaring_the_same_package_are_rejected(self):
        """A package holds one feature; an identical declaration is still a collision."""
        data = copy.deepcopy(self.data)
        shared = data["features"]["F01"]["package"]
        data["features"]["F09"]["package"] = shared
        # Follow F09's unit into the shared directory, so doubled ownership is the
        # only fault left for the audit to report.
        unit = next(u for u in data["units"] if u["owner"] == "F09")
        unit["target"] = f"{shared}/SKILL.md"
        unit["verification"] = [f"{shared}/SKILL.md#verification"]
        self.assertEqual(["feature package shared by F01 and F09"], self._audit(data))

    def test_two_features_aliased_onto_one_package_by_a_symlink_are_rejected(self):
        """Two distinct repository paths that resolve to one directory are one package."""
        alias = "skills/obsidian-alias"
        owned = self.data["features"]["F09"]["package"]
        (self.root / alias).symlink_to(self.root / owned, target_is_directory=True)
        self.assertNotEqual(alias, owned)
        self.assertTrue((self.root / alias).is_dir())
        self.assertEqual((self.root / alias).resolve(), (self.root / owned).resolve())
        data = copy.deepcopy(self.data)
        data["features"]["F08"]["package"] = alias
        # F08's unit follows the alias, so the aliased directory is the only fault.
        unit = next(u for u in data["units"] if u["owner"] == "F08")
        unit["target"] = f"{alias}/SKILL.md"
        unit["verification"] = [f"{alias}/SKILL.md#verification"]
        self.assertEqual(["feature package shared by F08 and F09"], self._audit(data))

    # --- one owning package per capability unit ---

    def test_unit_naming_two_owners_is_rejected_by_unit_id(self):
        for field, value in (("owner", ["F01", "F02"]),
                             ("package", ["obsidian-markdown", "obsidian-bases"])):
            data = copy.deepcopy(self.data)
            data["units"][0][field] = value
            with self.subTest(field=field):
                self.assertIn(
                    "unit must map to exactly one owning package: u-mixed-markdown",
                    self._audit(data),
                )

    def test_functional_unit_without_an_owning_package_is_rejected(self):
        data = copy.deepcopy(self.data)
        del data["units"][0]["package"]
        self.assertIn("missing owning package: u-mixed-markdown", self._audit(data))

    def test_owning_package_must_be_the_package_of_the_owner(self):
        data = copy.deepcopy(self.data)
        data["units"][0]["package"] = "obsidian-bases"
        self.assertIn(
            "owning package is not the package of its owner: u-mixed-markdown",
            self._audit(data),
        )

    def test_supporting_unit_may_not_carry_an_owning_package(self):
        data = copy.deepcopy(self.data)
        data["units"][2]["package"] = "obsidian-markdown"
        self.assertIn(
            "supporting unit has an owning package: u-mixed-shared", self._audit(data)
        )

    def test_owner_declared_twice_in_the_manifest_text_is_reported_not_resolved(self):
        """A plain JSON parse keeps the second owner and hides that there were two."""
        text = json.dumps(self.data).replace(
            '"owner": "F01"', '"owner": "F02", "owner": "F01"', 1
        )
        self.assertEqual(self.data, json.loads(text), "the injection must be invisible to json")
        data, problems = audit_inventory.load_manifest(text)
        self.assertEqual(self.data, data)
        self.assertEqual(["duplicate owner declared for unit: u-mixed-markdown"], problems)
        self.assertEqual(([]), audit_inventory.load_manifest(json.dumps(self.data))[1])

    def test_knowledge_feature_owns_only_its_own_package(self):
        (self.root / "skills/ingest").mkdir()
        data = copy.deepcopy(self.data)
        data["features"]["K03"] = {"name": "ingest", "package": "skills/ingest"}
        self.assertEqual([], self._audit(data))
        data["features"]["K03"]["package"] = "skills/obsidian-markdown"
        self.assertIn("knowledge feature K03 must own skills/ingest", self._audit(data))

    def test_feature_outside_the_native_and_knowledge_registries_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["features"]["K12"] = {"name": "extra", "package": "skills/obsidian-sync"}
        self.assertTrue(
            any(e.startswith("feature registry must declare exactly") for e in self._audit(data))
        )

    def test_wrong_schema_version_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["schema_version"] = 1
        self.assertIn(
            f"schema_version must be {audit_inventory.SCHEMA_VERSION}", self._audit(data)
        )


class RealManifestTest(unittest.TestCase):
    """Properties of the shipped inventory that a reviewer should not have to hand-check."""

    def test_real_manifest_passes_the_audit(self):
        self.assertEqual([], audit(MANIFEST, ROOT))

    def test_every_feature_owns_at_least_one_unit_and_no_unit_has_two_owners(self):
        owners = {}
        for unit in MANIFEST["units"]:
            if unit["class"] != "functional":
                continue
            self.assertIsInstance(unit["owner"], str, unit["id"])
            owners.setdefault(unit["owner"], []).append(unit["id"])
        self.assertEqual(set(MANIFEST["features"]), set(owners))

    def test_every_functional_unit_names_the_one_package_of_its_owner(self):
        checked = 0
        for unit in MANIFEST["units"]:
            if unit["class"] != "functional":
                self.assertNotIn("package", unit, unit["id"])
                continue
            package = MANIFEST["features"][unit["owner"]]["package"]
            self.assertEqual(f"skills/{unit['package']}", package, unit["id"])
            self.assertTrue((ROOT / package / "SKILL.md").is_file(), unit["id"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_the_audit_command_refuses_an_injected_duplicate_owner_by_unit_id(self):
        """The shipped manifest, copied and tampered, through the real command."""
        text = MANIFEST_PATH.read_text(encoding="utf-8")
        unit = next(u for u in MANIFEST["units"] if u["class"] == "functional")
        needle = f'"id": "{unit["id"]}"'
        owner = f'"owner": "{unit["owner"]}"'
        start = text.index(needle)
        at = text.index(owner, start)
        other = next(f for f in sorted(MANIFEST["features"]) if f != unit["owner"])
        tampered = {
            "repeated key": text[:at] + f'"owner": "{other}", ' + text[at:],
            "owner list": text[:at] + f'"owner": ["{unit["owner"]}", "{other}"]'
            + text[at + len(owner):],
        }
        script = ROOT / "scripts" / "audit_inventory.py"
        with tempfile.TemporaryDirectory() as tmp:
            for label, body in {"untouched": text, **tampered}.items():
                manifest = Path(tmp) / f"{label.replace(' ', '-')}.json"
                manifest.write_text(body, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(script), "--manifest", str(manifest)],
                    cwd=tmp, capture_output=True, text=True, timeout=60,
                )
                with self.subTest(manifest=label):
                    if label == "untouched":
                        self.assertEqual(0, result.returncode, result.stderr)
                        continue
                    self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                    self.assertIn(unit["id"], result.stderr)
                    self.assertNotIn("inventory:", result.stdout)

    def test_single_feature_files_hold_one_unit_and_mixed_files_hold_several(self):
        counts = {}
        for unit in MANIFEST["units"]:
            counts[unit["file"]] = counts.get(unit["file"], 0) + 1
        for row in MANIFEST["files"]:
            count = counts.get(row["id"], 0)
            if row["kind"] == "single-feature":
                self.assertEqual(1, count, f"{row['id']} is single-feature")
            elif row["kind"].startswith("mixed"):
                self.assertGreater(count, 1, f"{row['id']} is mixed but has one unit")

    def test_mixed_files_are_split_by_owner_not_collapsed(self):
        """A mixed file must expose more than one distinct responsibility holder."""
        by_file = {}
        for unit in MANIFEST["units"]:
            by_file.setdefault(unit["file"], []).append(unit)
        for row in MANIFEST["files"]:
            if not row["kind"].startswith("mixed"):
                continue
            units = by_file[row["id"]]
            holders = {unit["owner"] or "supporting" for unit in units}
            self.assertGreater(len(holders), 1, f"{row['id']} collapses its mixed content")

    def test_every_digest_is_lowercase_hex_and_every_source_path_is_unique(self):
        seen = set()
        for row in MANIFEST["files"]:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$", row["id"])
            key = (row["source"], row["path"])
            self.assertNotIn(key, seen, row["id"])
            seen.add(key)

    def test_no_unit_from_the_unlicensed_source_claims_an_import(self):
        unlicensed = {
            row["id"]
            for row in MANIFEST["files"]
            if not (MANIFEST["sources"][row["source"]]["license"] or {}).get("spdx")
        }
        self.assertTrue(unlicensed)
        for unit in MANIFEST["units"]:
            if unit["file"] in unlicensed:
                self.assertNotEqual("imported", unit["disposition"], unit["id"])

    def test_public_artifacts_leak_no_private_identifier(self):
        forbidden = [
            ".gjc",
            "/Users/",
            "/home/",
            "seeon-backups",
            "private-inventory",
            "neutral-app",
            "OBSIDIAN_SYNC_REMOTE_HOST=",
            "exec-plan",
        ]
        for name in ("source-inventory.json", "PROVENANCE.md", "NOTICE"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, f"{name} leaks {marker!r}")

    def test_declared_source_digests_match_a_supplied_checkout(self):
        """Opt-in: point the two environment variables at read-only checkouts."""
        supplied = {
            "craft": os.environ.get("OBSIDIAN_SKILLS_CRAFT_SOURCE"),
            "upstream": os.environ.get("OBSIDIAN_SKILLS_UPSTREAM_SOURCE"),
        }
        roots = {name: Path(path) for name, path in supplied.items() if path}
        if not roots:
            self.skipTest(
                "set OBSIDIAN_SKILLS_CRAFT_SOURCE and/or "
                "OBSIDIAN_SKILLS_UPSTREAM_SOURCE to a read-only source checkout to "
                "verify the recorded digests; audit_inventory.py takes the same paths "
                "as --craft-source/--upstream-source"
            )
        checked = 0
        for row in MANIFEST["files"]:
            root = roots.get(row["source"])
            if root is None:
                continue
            blob = (root / row["path"]).read_bytes()
            self.assertEqual(row["sha256"], hashlib.sha256(blob).hexdigest(), row["id"])
            self.assertEqual(row["bytes"], len(blob), row["id"])
            checked += 1
        self.assertGreater(checked, 0)
        self.assertEqual([], audit(MANIFEST, ROOT, roots))


if __name__ == "__main__":
    unittest.main()
