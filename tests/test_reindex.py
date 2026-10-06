"""Behavioral reindex tests with a faithful isolated qmd CLI fixture."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/reindex/scripts/reindex.py"
SPEC = importlib.util.spec_from_file_location("reindex_under_test", SCRIPT)
REINDEX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REINDEX)


class ReindexTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="task13-reindex-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.vault = self.base / "vault"
        for root in ("10. Raw Sources", "20. Wiki", "30. Queries",
                     "40. Paper Analyses", "50. References",
                     "00. Inbox", "Personal", "Public", "Company", "memories"):
            (self.vault / root).mkdir(parents=True)
        (self.vault / "40. Paper Analyses/paper.md").write_text(
            "# Synthetic paper\n", encoding="utf-8")
        for root in ("00. Inbox", "Personal", "Public", "Company", "memories"):
            (self.vault / root / "excluded.md").write_text("# Excluded\n", encoding="utf-8")
        self.scope = {
            "schema": "reindex/scope@1",
            "index": "isolated-knowledge",
            "collection": "knowledge",
            "include_roots": [
                "10. Raw Sources", "20. Wiki", "30. Queries",
                "40. Paper Analyses", "50. References",
            ],
            "paper_analyses": "40. Paper Analyses",
        }
        self.multi_collection, self.shown_vault = False, self.vault
        self.pattern = ",".join(root + "/**/*.md" for root in self.scope["include_roots"])
        self.listed_files = ["40. Paper Analyses/paper.md"]
        self.log = self.base / "qmd-args.jsonl"
        self.marker, self.embed_fail, self.status_padding, self.trailing_collection = self.base / "derivation.marker", False, "", ""
        self.qmd = self.base / "qmd"
        self.qmd.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\nargs = sys.argv[1:]\n"
            "with open(os.environ['QMD_TEST_LOG'], 'a', encoding='utf-8') as f:\n    f.write(json.dumps(args) + '\\n')\n"
            "if args[-1:] == ['status']:\n    extra = '\\n  personal (qmd://personal/)' if os.environ.get('QMD_TEST_MULTI') == '1' else ''\n    print('Collections\\n  knowledge (qmd://knowledge/)' + extra + os.environ['QMD_TEST_PADDING'] + os.environ['QMD_TEST_TRAILING'] + '\\nDocuments\\n  Total: 6 files indexed\\n  Vectors: 9 embedded')\n"
            "elif args[-3:] == ['collection', 'show', 'knowledge']:\n    print('Path: ' + os.environ['QMD_TEST_VAULT']); print('Pattern: ' + os.environ['QMD_TEST_PATTERN'])\n"
            "elif args[-1:] == ['update']:\n    open(os.environ['QMD_TEST_MARKER'], 'w', encoding='utf-8').write('updated'); print('All collections updated')\nelif args[-2:] == ['ls', 'qmd://knowledge/']: print('\\n'.join(json.loads(os.environ['QMD_TEST_FILES'])))\n"
            "elif args[-1:] == ['embed']:\n    if os.environ.get('QMD_TEST_EMBED_FAIL') == '1': sys.exit(7)\n    print('Embeddings complete')\nelse: sys.exit(2)\n",
            encoding="utf-8",
        )
        self.qmd.chmod(self.qmd.stat().st_mode | 0o111)

    def environment(self):
        return dict(
            os.environ,
            QMD_TEST_LOG=str(self.log),
            QMD_TEST_VAULT=str(self.shown_vault),
            QMD_TEST_PATTERN=self.pattern,
            QMD_TEST_FILES=json.dumps(self.listed_files),
            QMD_TEST_MARKER=str(self.marker),
            QMD_TEST_EMBED_FAIL="1" if self.embed_fail else "0",
            QMD_TEST_MULTI="1" if self.multi_collection else "0",
            QMD_TEST_PADDING=self.status_padding,
            QMD_TEST_TRAILING=self.trailing_collection,
        )

    def run_helper(self):
        prior = dict(os.environ)
        os.environ.update(self.environment())
        try:
            return REINDEX.run(self.vault, self.scope, str(self.qmd), timeout=10)
        finally:
            os.environ.clear()
            os.environ.update(prior)

    def invocations(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_selected_collection_only_runs_update_embed_and_status(self):
        # Given / When
        report = self.run_helper()
        # Then
        self.assertEqual(report["status"], "reindexed")
        calls = self.invocations()
        self.assertEqual(len(calls), 6)
        self.assertTrue(all(call[:2] == ["--index", "isolated-knowledge"] for call in calls))
        self.assertEqual([call[-1] for call in calls], [
            "status", "knowledge", "update", "qmd://knowledge/", "embed", "status"])
        self.assertEqual(report["matched_files"], ["40. Paper Analyses/paper.md"])
        flattened = json.dumps(calls).casefold()
        self.assertNotIn("inbox", flattened)
        self.assertNotIn("personal", flattened)
        self.assertNotIn("public", flattened)
        self.assertNotIn("company", flattened)
        self.assertNotIn("memories", flattened)
        self.assertNotIn("model", flattened)

    def test_paper_analyses_is_required_and_audited(self):
        # Given
        missing = dict(self.scope, include_roots=self.scope["include_roots"][:-2] +
                       ["50. References"])
        # When / Then
        with self.assertRaises(REINDEX.Refused) as raised:
            REINDEX.run(self.vault, missing, str(self.qmd), timeout=10)
        self.assertEqual(raised.exception.code, "missing_paper_analyses")
        self.assertFalse(self.log.exists())

    def test_qmd_display_examples_are_not_index_membership(self):
        # Given: qmd status includes usage placeholders after real collection rows.
        shown = "Collection: knowledge\n  Path: " + str(self.vault) + "\n  Pattern: " + self.pattern
        status = (
            "Collections\n  knowledge (qmd://knowledge/)\n"
            "\nExamples\n  qmd get qmd://knowledge/path/to/file.md\n"
            "Tips\n  qmd context add qmd://<name>/ \"context\"\n"
        )
        # When / Then
        self.assertEqual(REINDEX.audit_preflight(self.vault, self.scope, status, shown),
                         {"40. Paper Analyses/paper.md"})

    def test_qmd_display_columns_preserve_exact_member_paths(self):
        # Given
        displayed = "1.9 KB  Oct  6 19:58  qmd://knowledge/40. Paper Analyses/paper.md\n"
        # When / Then
        self.assertEqual(REINDEX.listed_files("knowledge", displayed),
                         {"40. Paper Analyses/paper.md"})

    def test_forbidden_responsibility_root_is_refused_before_qmd(self):
        # Given
        mixed = dict(self.scope, include_roots=self.scope["include_roots"] + ["00. Inbox"])
        # When / Then
        with self.assertRaises(REINDEX.Refused) as raised:
            REINDEX.run(self.vault, mixed, str(self.qmd), timeout=10)
        self.assertEqual(raised.exception.code, "mixed_corpus")
        self.assertFalse(self.log.exists())

    def test_multi_collection_named_index_is_refused_before_update(self):
        # Given
        regular = {p.relative_to(self.vault).as_posix(): p.read_bytes()
                   for p in self.vault.rglob("*.md") if p.is_file()}
        self.multi_collection = True
        # When / Then
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "collection_not_isolated")
        self.assertEqual(len(self.invocations()), 2)
        self.log.unlink()
        self.multi_collection = False
        self.status_padding = "\n" + "x" * 5000
        self.trailing_collection = "\n  personal (qmd://personal/)"
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "collection_not_isolated")
        self.assertEqual(len(self.invocations()), 2)
        self.assertFalse(self.marker.exists())
        self.assertEqual({p.relative_to(self.vault).as_posix(): p.read_bytes()
                          for p in self.vault.rglob("*.md") if p.is_file()}, regular)

    def test_wrong_vault_prefix_and_overbroad_glob_are_refused(self):
        # Given / When / Then
        self.shown_vault = self.base / "vault-other"
        self.shown_vault.mkdir()
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "collection_root_mismatch")
        self.log.unlink()
        self.shown_vault = self.vault
        self.pattern += ",**/*.md"
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "collection_scope_mismatch")
        self.assertEqual(len(self.invocations()), 2)

    def test_actual_indexed_membership_must_equal_allowed_vault_files(self):
        # Given
        self.listed_files.append("00. Inbox/excluded.md")
        # When / Then
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "collection_membership_mismatch")
        calls = self.invocations()
        self.assertEqual(calls[-1][-2:], ["ls", "qmd://knowledge/"])
        self.assertFalse(any(call[-1:] == ["embed"] for call in calls))

    def test_expected_membership_skips_fifo_and_preserves_regular_files(self):
        # Given
        fifo = self.vault / "40. Paper Analyses/blocked.md"
        os.mkfifo(fifo)
        regular = {p.relative_to(self.vault).as_posix(): p.read_bytes()
                   for p in self.vault.rglob("*.md") if p.is_file()}
        # When
        report = self.run_helper()
        # Then
        self.assertEqual(report["matched_files"], ["40. Paper Analyses/paper.md"])
        self.assertTrue(stat.S_ISFIFO(fifo.lstat().st_mode))
        self.assertEqual({p.relative_to(self.vault).as_posix(): p.read_bytes()
                          for p in self.vault.rglob("*.md") if p.is_file()}, regular)

    def test_post_update_failures_report_possible_effects_and_preserve_sources(self):
        # Given
        scope = self.base / "scope.json"
        scope.write_text(json.dumps(self.scope), encoding="utf-8")
        regular = {p.relative_to(self.vault).as_posix(): p.read_bytes()
                   for p in self.vault.rglob("*.md") if p.is_file()}
        # When / Then
        for case in ("membership", "malformed-member", "embed"):
            with self.subTest(case=case):
                listings = {"membership": ["00. Inbox/excluded.md"],
                            "malformed-member": ["../escape.md"],
                            "embed": ["40. Paper Analyses/paper.md"]}
                self.listed_files = listings[case]
                self.embed_fail = case == "embed"
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
                     "--scope", str(scope), "--qmd", str(self.qmd)],
                    capture_output=True, text=True, timeout=10,
                    env=dict(self.environment(), PYTHONDONTWRITEBYTECODE="1"),
                )
                self.assertEqual(result.returncode, 1)
                envelope = json.loads(result.stdout)
                codes = {"membership": "collection_membership_mismatch",
                         "malformed-member": "unsafe_path", "embed": "qmd_command_failed"}
                self.assertEqual(envelope["code"], codes[case])
                self.assertEqual(envelope["mutation_state"], "possible_unconfirmed")
                self.assertEqual(envelope["mutations_performed"], [])
                effects = envelope["effects_possible"]
                self.assertEqual((len(effects), type(effects[0]), bool(effects[0]), self.scope["index"] in effects[0]), (1, str, True, True))
                self.assertEqual(self.marker.read_text(encoding="utf-8"), "updated")
                self.assertEqual({p.relative_to(self.vault).as_posix(): p.read_bytes()
                                  for p in self.vault.rglob("*.md") if p.is_file()}, regular)
                if self.log.exists():
                    self.log.unlink()

    def test_preflight_failure_reports_no_possible_effects(self):
        # Given
        self.shown_vault = self.base / "vault-other"
        self.shown_vault.mkdir()
        scope = self.base / "scope.json"
        scope.write_text(json.dumps(self.scope), encoding="utf-8")
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope), "--qmd", str(self.qmd)],
            capture_output=True, text=True, timeout=10,
            env=dict(self.environment(), PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["mutation_state"], "none")
        self.assertEqual(envelope["effects_possible"], [])
        self.assertFalse(self.marker.exists())

    def test_malformed_include_root_is_structured_cli_refusal_without_qmd(self):
        # Given
        malformed = dict(self.scope, include_roots=[{}])
        scope = self.base / "malformed.json"
        scope.write_text(json.dumps(malformed), encoding="utf-8")
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope), "--qmd", str(self.qmd)],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 1)
        envelope = json.loads(result.stdout)
        self.assertEqual((envelope["status"], envelope["code"]),
                         ("refused", "invalid_input"))
        self.assertEqual(envelope["mutations_performed"], [])
        self.assertFalse(self.log.exists())

    def test_missing_qmd_reports_unavailable_not_success(self):
        # Given
        scope = self.base / "scope.json"
        scope.write_text(json.dumps(self.scope), encoding="utf-8")
        # When
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--vault", str(self.vault),
             "--scope", str(scope), "--qmd", str(self.base / "absent-qmd")],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        # Then
        self.assertEqual(result.returncode, 1)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["status"], "unavailable")
        self.assertNotEqual(envelope["status"], "reindexed")

    def test_nonzero_and_hung_qmd_are_not_success(self):
        # Given
        self.qmd.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
        self.qmd.chmod(0o755)
        # When / Then: nonzero
        with self.assertRaises(REINDEX.Refused) as raised:
            self.run_helper()
        self.assertEqual(raised.exception.code, "qmd_preflight_failed")
        # Given: a command that never returns and does not depend on timing luck.
        self.qmd.write_text("#!/usr/bin/env python3\nwhile True:\n    pass\n", encoding="utf-8")
        self.qmd.chmod(0o755)
        # When / Then: bounded timeout
        with self.assertRaises(REINDEX.Refused) as raised:
            REINDEX.run(self.vault, self.scope, str(self.qmd), timeout=1)
        self.assertEqual(raised.exception.code, "hung_command")

    def test_script_parses_with_python38_grammar(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 8))
        self.assertTrue(tree.body)


if __name__ == "__main__":
    unittest.main()
