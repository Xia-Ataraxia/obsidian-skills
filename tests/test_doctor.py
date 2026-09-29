#!/usr/bin/env python3
"""Behavioural tests for the plugin/Templater diagnosis helper.

Every test here executes the real helper, ``skills/obsidian-doctor/scripts/
diagnose.py``, as a subprocess against a synthetic evidence bundle written into a
throwaway temporary directory, then asserts on the JSON it printed and the exit
code it returned. The helper is never imported, so the assertions bind to its
published command-line contract (exit codes, envelope keys, status vocabulary,
check ids) rather than to its internals, and never to instructional wording.

Scope boundary: nothing here reads a vault, a configuration folder, an Obsidian
profile, a network, or any private value. The host-shaped paths and secret-shaped
values below are fabricated placeholders, assembled from fragments so this file
never contains the literal shapes it asks the helper to withhold. They exist
only to prove the helper reports such a value by location and refuses to echo it.
A passing run means the classifier separates observed evidence from absent
evidence; it does not mean any plugin, template, or app was exercised.

Run:  python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "skills" / "obsidian-doctor" / "scripts" / "diagnose.py"

# --------------------------------------------------------------------------- #
# published contract identifiers
# --------------------------------------------------------------------------- #
EVIDENCE_SCHEMA = "obsidian-doctor/evidence@1"
DIAGNOSIS_SCHEMA = "obsidian-doctor/diagnosis@1"
CHECKS_SCHEMA = "obsidian-doctor/checks@1"
REGISTRY_FILE = "references/plugins.yaml"

CONFIRMED = "confirmed"
RULED_OUT = "ruled_out"
UNKNOWN = "unknown"
NOT_APPLICABLE = "not_applicable"
FINDING_STATUSES = frozenset({CONFIRMED, RULED_OUT, UNKNOWN, NOT_APPLICABLE})

# The exit code reports evidence sufficiency, not defect presence.
EXIT_OK = 0
EXIT_INDETERMINATE = 1
EXIT_USAGE = 2
EXIT_INPUT_ERROR = 3

ACTION_KINDS = frozenset({"observe", "consult", "propose-change"})
ACTION_MUTATES = frozenset({"no", "yes-after-human-approval"})
READ_ONLY_KINDS = frozenset({"observe", "consult"})

DIAGNOSIS_KEYS = frozenset(
    {
        "schema",
        "status",
        "fixture",
        "evidence_schema",
        "subject",
        "findings",
        "unknowns",
        "mutations_performed",
        "read_only_probes",
    }
)
SUBJECT_KEYS = frozenset(
    {"case_id", "plugin_id", "plugin_version", "min_app_version", "app_version", "template_path"}
)
FINDING_KEYS = frozenset({"id", "title", "status", "summary", "evidence", "next_actions", "docs"})
OPTIONAL_FINDING_KEYS = frozenset({"registry_lookup"})
ACTION_KEYS = frozenset({"kind", "mutates", "detail"})
REGISTRY_KEYS = frozenset({"file", "plugin_id", "keys"})
INPUT_ERROR_KEYS = frozenset(
    {"schema", "status", "fixture", "reason", "findings", "unknowns", "mutations_performed"}
)

# Check ids the package publishes. Asserted as a required subset so that adding a
# new check does not break these tests, while dropping or renaming one does.
CONTRACT_CHECK_IDS = (
    "runtime-unavailable",
    "plugin-unavailable",
    "plugin-version-mismatch",
    "templater-reference-error",
    "templater-missing-await",
    "templater-missing-output",
    "templater-partial-mutation-risk",
    "plugin-api-unavailable",
    "console-error-unclassified",
    "fixture-not-sanitized",
)

# Checks that depend on a channel the caller may simply not have supplied. When
# the channel is absent none of them may report ruled_out: unsupplied is not
# verified.
CHANNEL_DEPENDENT_IDS = tuple(i for i in CONTRACT_CHECK_IDS if i != "fixture-not-sanitized")

# --------------------------------------------------------------------------- #
# synthetic fixture material
# --------------------------------------------------------------------------- #
# Host-shaped strings are assembled from fragments, the same way the repository
# privacy scanner assembles its own patterns, so that this file never carries a
# literal account-scoped path or an address-shaped token.
_USERS = "/" + "Users" + "/"
_HOMES = "/" + "home" + "/"
_AT = "@"
_ACCOUNT = "example-user"

# A fabricated value for every key name that looks like a secret. It carries
# "synthetic", "placeholder" and "not-a-real" so no scanner can mistake it for a
# real credential.
SECRET_PLACEHOLDER = "SYNTHETIC-PLACEHOLDER-NOT-A-REAL-VALUE-0001"
SECRET_KEY_NAMES = (
    "token",
    "password",
    "passwd",
    "secret",
    "apikey",
    "api_key",
    "authorization",
    "credential",
    "private_key",
    "cookie",
    "license_key",
)

# Each pair is (label, fabricated host-shaped value). The label names the shape
# only; the assertions never depend on how the helper words its report.
HOST_SHAPED_VALUES = (
    ("macos-account-path", _USERS + _ACCOUNT + "/Vaults/SynthVault/Templates/Synth.md"),
    ("linux-account-path", _HOMES + _ACCOUNT + "/vaults/SynthVault/Templates/Synth.md"),
    ("windows-account-path", "C:\\Users\\" + _ACCOUNT + "\\SynthVault\\Templates\\Synth.md"),
    ("home-shorthand", "~/SynthVault/Templates/Synth.md"),
    ("machine-temp-path", "/var/folders/sy/nthetic/T/placeholder-capture/Synth.md"),
    ("local-file-url", "file:///SynthVault/Templates/Synth.md"),
    (
        "credential-in-url",
        "https://" + _ACCOUNT + ":" + "placeholder-pass" + _AT + "sync.invalid/endpoint",
    ),
)

VAULT_RELATIVE_TEMPLATE = "Templates/Synthetic.md"

# Synthetic Templater sources. Each isolates one documented failure mode so a
# confirmation can be attributed to exactly one check.
TEMPLATE_UNBOUND = "<% missingIdentifier %>\n"
TEMPLATE_BOUND = '<%* const noteLabel = "Synthetic"; tR += noteLabel; %>\n<% tp.date.now() %>\n'
TEMPLATE_UNAWAITED = '<%* const answer = tp.system.prompt("Synthetic label"); tR += answer; %>\n'
TEMPLATE_AWAITED = (
    '<%* const answer = await tp.system.prompt("Synthetic label"); tR += answer; %>\n'
)
TEMPLATE_DISCARDED = '<%* const answer = await tp.system.prompt("Synthetic label"); %>\n'
TEMPLATE_PROMPT_THEN_MUTATION = (
    '<%* const target = await tp.system.prompt("Synthetic target");'
    " await tp.file.rename(target); %>\n"
)
TEMPLATE_MUTATION_THEN_PROMPT = (
    '<%* await tp.file.rename("Synthetic-Renamed");'
    ' const extra = await tp.system.prompt("Synthetic extra"); tR += extra; %>\n'
)
TEMPLATE_GUARDED_BY_RETURN = (
    '<%* const target = await tp.system.prompt("Synthetic target");'
    " if (target === null) { return; } await tp.file.rename(target); %>\n"
)
TEMPLATE_THROWS_ON_CANCEL = (
    '<%* const target = await tp.system.prompt("Synthetic target", "", true);'
    " await tp.file.rename(target); %>\n"
)

RUNTIME_OBSERVED = {"app_running": True, "cli_available": True, "app_version": "1.12.7"}

UNCLASSIFIED_CONSOLE_LINE = "Synthetic subsystem QX7 reported marker 41 while indexing"
REFERENCE_ERROR_LINE = "ReferenceError: noteLabel is not defined"
API_SHAPE_ERROR_LINE = "TypeError: pluginApi.synthDoThing is not a function"


def bundle(**sections):
    """A minimal valid evidence bundle plus whatever channels the test supplies."""
    payload = {"schema": EVIDENCE_SCHEMA, "case_id": "SYN-DOCTOR-0001"}
    payload.update(sections)
    return payload


def runtime(**overrides):
    observed = dict(RUNTIME_OBSERVED)
    observed.update(overrides)
    return observed


def template(source=TEMPLATE_BOUND, path=VAULT_RELATIVE_TEMPLATE):
    section = {"path": path}
    if source is not None:
        section["source"] = source
    return section


def manifest_plugin(version="2.0.1", min_app_version="1.5.0", plugin_id="synthetic-plugin"):
    return {
        "id": plugin_id,
        "installed": True,
        "enabled": True,
        "manifest": {"id": plugin_id, "version": version, "minAppVersion": min_app_version},
    }


# Bundles reused by the cross-cutting invariant sweep. Named so a failure names
# the scenario rather than an index.
BUNDLES = {
    "no-channel-at-all": bundle(),
    "runtime-down": bundle(runtime={"app_running": False, "cli_available": False}),
    "runtime-half-observed": bundle(runtime={"app_running": True}),
    "runtime-observed": bundle(runtime=runtime()),
    "runtime-without-console-command": bundle(
        runtime=runtime(cli_commands_confirmed=["read", "search"])
    ),
    "plugin-absent": bundle(
        runtime=runtime(), plugin={"id": "synthetic-plugin", "installed": False, "enabled": False}
    ),
    "plugin-disabled": bundle(
        runtime=runtime(), plugin={"id": "synthetic-plugin", "installed": True, "enabled": False}
    ),
    "plugin-state-half-observed": bundle(
        runtime=runtime(), plugin={"id": "synthetic-plugin", "installed": True}
    ),
    "app-older-than-manifest": bundle(
        runtime=runtime(app_version="1.4.16"), plugin=manifest_plugin()
    ),
    "app-version-v-prefixed": bundle(
        runtime=runtime(app_version="v1.4.0"), plugin=manifest_plugin()
    ),
    "app-newer-double-digit-minor": bundle(
        runtime=runtime(app_version="1.10.0"), plugin=manifest_plugin(min_app_version="1.9.0")
    ),
    "app-version-shorter-but-equal": bundle(
        runtime=runtime(app_version="1.5"), plugin=manifest_plugin()
    ),
    "app-version-not-numeric": bundle(
        runtime=runtime(app_version="1.5.0-insider"), plugin=manifest_plugin()
    ),
    "app-version-missing": bundle(
        runtime={"app_running": True, "cli_available": True}, plugin=manifest_plugin()
    ),
    "reference-error-in-console": bundle(runtime=runtime(), console_errors=[REFERENCE_ERROR_LINE]),
    "reference-error-in-source": bundle(
        runtime=runtime(), template=template(TEMPLATE_UNBOUND)
    ),
    "template-fully-bound": bundle(runtime=runtime(), template=template(TEMPLATE_BOUND)),
    "async-call-unawaited": bundle(runtime=runtime(), template=template(TEMPLATE_UNAWAITED)),
    "async-call-awaited": bundle(runtime=runtime(), template=template(TEMPLATE_AWAITED)),
    "async-result-discarded": bundle(runtime=runtime(), template=template(TEMPLATE_DISCARDED)),
    "command-text-reached-note": bundle(
        runtime=runtime(),
        template=template(TEMPLATE_BOUND),
        rendered_output={"content": "---\nstatus: draft\n---\n<% tp.date.now() %>\n"},
    ),
    "prompt-before-mutation": bundle(
        runtime=runtime(), template=template(TEMPLATE_PROMPT_THEN_MUTATION)
    ),
    "mutation-before-prompt": bundle(
        runtime=runtime(), template=template(TEMPLATE_MUTATION_THEN_PROMPT)
    ),
    "cancel-guarded-by-return": bundle(
        runtime=runtime(), template=template(TEMPLATE_GUARDED_BY_RETURN)
    ),
    "cancel-raises-instead": bundle(
        runtime=runtime(), template=template(TEMPLATE_THROWS_ON_CANCEL)
    ),
    "template-named-without-source": bundle(runtime=runtime(), template=template(source=None)),
    "console-line-unclassified": bundle(
        runtime=runtime(), console_errors=[UNCLASSIFIED_CONSOLE_LINE]
    ),
    "console-entry-unreadable": bundle(runtime=runtime(), console_errors=[{"level": "error"}]),
    "console-channel-wrong-type": bundle(runtime=runtime(), console_errors=REFERENCE_ERROR_LINE),
    "console-capture-empty": bundle(runtime=runtime(), console_errors=[]),
    "console-lines-all-classified": bundle(
        runtime=runtime(), console_errors=[REFERENCE_ERROR_LINE, API_SHAPE_ERROR_LINE]
    ),
    "api-probe-missing": bundle(
        runtime=runtime(),
        plugin={
            "id": "synthetic-plugin",
            "installed": True,
            "enabled": True,
            "api_probe": {"symbol": "pluginApi.synthDoThing", "observed": "missing"},
        },
    ),
    "api-probe-indeterminate": bundle(
        runtime=runtime(),
        plugin={
            "id": "synthetic-plugin",
            "installed": True,
            "enabled": True,
            "api_probe": {"symbol": "pluginApi.synthDoThing"},
        },
    ),
    "api-probe-present": bundle(
        runtime=runtime(),
        plugin={
            "id": "synthetic-plugin",
            "installed": True,
            "enabled": True,
            "api_probe": {"symbol": "pluginApi.synthDoThing", "observed": "present"},
        },
    ),
    "unsanitized-template-path": bundle(
        runtime=runtime(), template=template(path=HOST_SHAPED_VALUES[0][1])
    ),
    "unsanitized-case-id": bundle(runtime=runtime()),
    "non-ascii-case-id": bundle(runtime=runtime()),
}
BUNDLES["unsanitized-case-id"]["case_id"] = _USERS + _ACCOUNT + "/cases/synthetic-0001"
BUNDLES["non-ascii-case-id"]["case_id"] = "SYN-검증-α-0001"


def digest_tree(root, skip_names=()):
    """Content and metadata of every entry under ``root``, for a before/after diff."""
    entries = {}
    for path in sorted(root.rglob("*")):
        if any(part in skip_names for part in path.relative_to(root).parts):
            continue
        key = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[key] = ("symlink", os.readlink(path))
        elif path.is_dir():
            stat = path.stat()
            entries[key] = ("dir", stat.st_mode, stat.st_mtime_ns)
        else:
            stat = path.stat()
            entries[key] = (
                "file",
                stat.st_size,
                stat.st_mode,
                stat.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return entries


class DoctorHelperTest(unittest.TestCase):
    """Shared plumbing plus the invariants that hold for every diagnosis run."""

    @classmethod
    def setUpClass(cls):
        if not HELPER.is_file():
            raise AssertionError(f"diagnosis helper is missing from the package: {HELPER}")

    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="obsidian-doctor-tests-")
        self.addCleanup(workspace.cleanup)
        self.workspace = Path(workspace.name)

    # -- invocation -------------------------------------------------------- #
    def run_helper(self, *args, cwd=None, script=None):
        """Run the real helper and return ``(exit_code, stdout, stderr)`` as text."""
        completed = subprocess.run(
            [sys.executable, str(script or HELPER), *args],
            cwd=str(cwd or self.workspace),
            capture_output=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        stdout = completed.stdout.decode("utf-8")
        stderr = completed.stderr.decode("utf-8")
        self.assertNotIn("Traceback", stderr, "the helper must never surface a raw exception")
        return completed.returncode, stdout, stderr

    def write_bundle(self, payload, name="evidence.json"):
        path = self.workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(copy.deepcopy(payload), indent=2), encoding="utf-8")
        return name

    def diagnose(self, payload, name="evidence.json"):
        """Diagnose one bundle, asserting the whole-envelope contract on the way."""
        relative = self.write_bundle(payload, name)
        code, stdout, stderr = self.run_helper("--fixture", relative)
        self.assertEqual(stderr, "", "a readable bundle must not produce diagnostics on stderr")
        document = self.parse_json(stdout)
        self.assertDiagnosisContract(code, document, stdout)
        return code, document, stdout

    def parse_json(self, stdout):
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as error:
            self.fail(f"stdout was not JSON ({error}): {stdout[:400]!r}")

    # -- contract assertions ----------------------------------------------- #
    def assertDiagnosisContract(self, code, document, stdout):
        self.assertEqual(set(document), DIAGNOSIS_KEYS, "unexpected diagnosis envelope key")
        self.assertEqual(document["schema"], DIAGNOSIS_SCHEMA)
        self.assertEqual(document["evidence_schema"], EVIDENCE_SCHEMA)
        self.assertIsInstance(document["fixture"], str)
        self.assertTrue(document["fixture"])

        self.assertEqual(
            document["mutations_performed"], [], "a read-only classifier may never mutate"
        )
        probes = document["read_only_probes"]
        self.assertIsInstance(probes, list)
        self.assertTrue(probes)
        self.assertEqual(len(probes), len(set(probes)))
        for probe in probes:
            self.assertIsInstance(probe, str)
            self.assertTrue(probe.strip())

        self.assertEqual(set(document["subject"]), SUBJECT_KEYS, "unexpected subject key")
        for key, value in document["subject"].items():
            with self.subTest(subject_field=key):
                self.assertTrue(value is None or isinstance(value, str))

        for finding in document["findings"]:
            self.assertFindingContract(finding)

        ids = [finding["id"] for finding in document["findings"]]
        self.assertEqual(len(ids), len(set(ids)), "a check reported twice")
        for check_id in CONTRACT_CHECK_IDS:
            self.assertIn(check_id, ids, "a published check stopped reporting")

        unknown_ids = [f["id"] for f in document["findings"] if f["status"] == UNKNOWN]
        self.assertEqual(
            [entry.split(":", 1)[0] for entry in document["unknowns"]],
            unknown_ids,
            "the unknown roll-up must list exactly the checks that stayed unknown",
        )
        expected_status = "indeterminate" if unknown_ids else "ok"
        self.assertEqual(document["status"], expected_status)
        expected_code = EXIT_INDETERMINATE if unknown_ids else EXIT_OK
        self.assertEqual(code, expected_code, "exit code must track evidence sufficiency")

        self.assertEqual(
            stdout,
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            "stdout must be one indented, non-escaped JSON document with a trailing newline",
        )

    def assertFindingContract(self, finding):
        with self.subTest(finding=finding.get("id")):
            keys = set(finding)
            self.assertTrue(FINDING_KEYS <= keys, f"missing finding keys: {FINDING_KEYS - keys}")
            self.assertFalse(
                keys - FINDING_KEYS - OPTIONAL_FINDING_KEYS, f"unexpected finding key in {keys}"
            )
            self.assertIn(finding["status"], FINDING_STATUSES)
            for field in ("id", "title", "summary"):
                self.assertIsInstance(finding[field], str)
                self.assertTrue(finding[field].strip(), f"{field} must not be blank")

            self.assertIsInstance(finding["evidence"], list)
            self.assertTrue(finding["evidence"], "no finding may assert a status with no evidence")
            for item in finding["evidence"]:
                self.assertIsInstance(item, str)
                self.assertTrue(item.strip())

            self.assertIsInstance(finding["docs"], list)
            self.assertTrue(finding["docs"], "a finding must cite the documentation it rests on")
            for url in finding["docs"]:
                self.assertTrue(url.startswith("https://"), url)

            for action in finding["next_actions"]:
                self.assertEqual(set(action), ACTION_KEYS)
                self.assertIn(action["kind"], ACTION_KINDS)
                self.assertIn(action["mutates"], ACTION_MUTATES)
                self.assertTrue(action["detail"].strip())
                if action["kind"] in READ_ONLY_KINDS:
                    self.assertEqual(
                        action["mutates"], "no", "an observe/consult step may not mutate"
                    )
                else:
                    self.assertEqual(
                        action["mutates"],
                        "yes-after-human-approval",
                        "a proposed change must require human approval",
                    )
            if finding["status"] == CONFIRMED:
                self.assertTrue(
                    finding["next_actions"], "a confirmed defect must say what to do next"
                )

            if "registry_lookup" in finding:
                lookup = finding["registry_lookup"]
                self.assertEqual(set(lookup), REGISTRY_KEYS)
                self.assertEqual(lookup["file"], REGISTRY_FILE)
                self.assertTrue(lookup["plugin_id"] is None or isinstance(lookup["plugin_id"], str))
                self.assertTrue(lookup["keys"])
                for key in lookup["keys"]:
                    self.assertIsInstance(key, str)

    # -- helpers ----------------------------------------------------------- #
    def statuses(self, document):
        return {finding["id"]: finding["status"] for finding in document["findings"]}

    def finding(self, document, check_id):
        for candidate in document["findings"]:
            if candidate["id"] == check_id:
                return candidate
        self.fail(f"{check_id} was not reported; got {sorted(self.statuses(document))}")

    def assertStatus(self, document, check_id, expected):
        self.assertEqual(self.finding(document, check_id)["status"], expected)

    def assertEvidenceMentions(self, document, check_id, needle):
        evidence = self.finding(document, check_id)["evidence"]
        self.assertTrue(
            any(needle in item for item in evidence),
            f"{check_id} evidence never names {needle!r}: {evidence}",
        )


class CheckCatalogTest(DoctorHelperTest):
    """``--list-checks`` publishes the catalogue and the exit-code contract."""

    def catalogue(self):
        code, stdout, stderr = self.run_helper("--list-checks")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        return self.parse_json(stdout)

    def test_catalogue_declares_its_schema_statuses_and_exit_codes(self):
        catalogue = self.catalogue()
        self.assertEqual(catalogue["schema"], CHECKS_SCHEMA)
        self.assertEqual(set(catalogue["statuses"]), FINDING_STATUSES)
        self.assertEqual(
            set(catalogue["exit_codes"]),
            {str(EXIT_OK), str(EXIT_INDETERMINATE), str(EXIT_USAGE), str(EXIT_INPUT_ERROR)},
        )
        for description in catalogue["exit_codes"].values():
            self.assertTrue(description.strip())

    def test_every_published_check_is_listed_once_with_its_required_evidence(self):
        checks = self.catalogue()["checks"]
        ids = [check["id"] for check in checks]
        self.assertEqual(len(ids), len(set(ids)), "duplicate check id in the catalogue")
        for check_id in CONTRACT_CHECK_IDS:
            self.assertIn(check_id, ids)
        for check in checks:
            with self.subTest(check=check["id"]):
                self.assertEqual(set(check), {"id", "title", "evidence_required"})
                self.assertTrue(check["title"].strip())
                self.assertTrue(check["evidence_required"], "a check must name its input channel")

    def test_catalogue_matches_the_checks_a_real_run_emits(self):
        """A check listed but never emitted (or emitted but unlisted) is a lie."""
        catalogue_ids = [check["id"] for check in self.catalogue()["checks"]]
        _, document, _ = self.diagnose(BUNDLES["runtime-observed"])
        self.assertEqual(catalogue_ids, [finding["id"] for finding in document["findings"]])


class RuntimeAvailabilityTest(DoctorHelperTest):
    def test_unavailable_app_and_cli_are_confirmed_from_observed_negatives(self):
        code, document, _ = self.diagnose(BUNDLES["runtime-down"])
        self.assertStatus(document, "runtime-unavailable", CONFIRMED)
        self.assertEqual(code, EXIT_OK, "complete evidence exits 0 even when a defect is confirmed")

    def test_partially_observed_runtime_stays_unknown_rather_than_available(self):
        code, document, _ = self.diagnose(BUNDLES["runtime-half-observed"])
        self.assertStatus(document, "runtime-unavailable", UNKNOWN)
        self.assertEqual(code, EXIT_INDETERMINATE)
        self.assertEqual(document["status"], "indeterminate")

    def test_both_channels_observed_available_rules_the_failure_mode_out(self):
        _, document, _ = self.diagnose(BUNDLES["runtime-observed"])
        self.assertStatus(document, "runtime-unavailable", RULED_OUT)

    def test_a_cli_without_a_console_command_is_recorded_as_a_capability_gap(self):
        _, document, _ = self.diagnose(BUNDLES["runtime-without-console-command"])
        finding = self.finding(document, "runtime-unavailable")
        self.assertEqual(finding["status"], RULED_OUT)
        self.assertGreater(
            len(finding["evidence"]),
            2,
            "a confirmed command list without a console command must be reported",
        )


class PluginAvailabilityTest(DoctorHelperTest):
    def test_absent_and_disabled_plugins_are_confirmed_separately(self):
        for name in ("plugin-absent", "plugin-disabled"):
            with self.subTest(bundle=name):
                _, document, _ = self.diagnose(BUNDLES[name])
                self.assertStatus(document, "plugin-unavailable", CONFIRMED)

    def test_half_observed_install_state_stays_unknown(self):
        code, document, _ = self.diagnose(BUNDLES["plugin-state-half-observed"])
        self.assertStatus(document, "plugin-unavailable", UNKNOWN)
        self.assertEqual(code, EXIT_INDETERMINATE)

    def test_a_plugin_scoped_finding_points_at_the_registry_entry(self):
        _, document, _ = self.diagnose(BUNDLES["plugin-absent"])
        lookup = self.finding(document, "plugin-unavailable")["registry_lookup"]
        self.assertEqual(lookup["file"], REGISTRY_FILE)
        self.assertEqual(lookup["plugin_id"], "synthetic-plugin")

    def test_enabling_a_plugin_is_proposed_as_a_human_approved_change(self):
        _, document, _ = self.diagnose(BUNDLES["plugin-absent"])
        actions = self.finding(document, "plugin-unavailable")["next_actions"]
        proposals = [a for a in actions if a["kind"] == "propose-change"]
        self.assertTrue(proposals, "a configuration change must be proposed, not performed")
        for proposal in proposals:
            self.assertEqual(proposal["mutates"], "yes-after-human-approval")


class VersionCompatibilityTest(DoctorHelperTest):
    def test_app_older_than_min_app_version_is_confirmed(self):
        _, document, _ = self.diagnose(BUNDLES["app-older-than-manifest"])
        self.assertStatus(document, "plugin-version-mismatch", CONFIRMED)
        self.assertEqual(document["subject"]["app_version"], "1.4.16")
        self.assertEqual(document["subject"]["min_app_version"], "1.5.0")
        self.assertEqual(document["subject"]["plugin_version"], "2.0.1")

    def test_a_v_prefixed_app_version_is_still_compared_numerically(self):
        _, document, _ = self.diagnose(BUNDLES["app-version-v-prefixed"])
        self.assertStatus(document, "plugin-version-mismatch", CONFIRMED)

    def test_versions_compare_componentwise_not_lexicographically(self):
        """1.10.0 satisfies 1.9.0; a string comparison would call it too old."""
        _, document, _ = self.diagnose(BUNDLES["app-newer-double-digit-minor"])
        self.assertStatus(document, "plugin-version-mismatch", RULED_OUT)

    def test_a_shorter_but_equal_version_is_not_treated_as_older(self):
        _, document, _ = self.diagnose(BUNDLES["app-version-shorter-but-equal"])
        self.assertStatus(document, "plugin-version-mismatch", RULED_OUT)

    def test_an_unparseable_or_missing_version_stays_unknown(self):
        for name in ("app-version-not-numeric", "app-version-missing"):
            with self.subTest(bundle=name):
                code, document, _ = self.diagnose(BUNDLES[name])
                self.assertStatus(document, "plugin-version-mismatch", UNKNOWN)
                self.assertEqual(code, EXIT_INDETERMINATE)

    def test_compatibility_is_not_evaluated_without_a_manifest(self):
        _, document, _ = self.diagnose(BUNDLES["plugin-absent"])
        self.assertStatus(document, "plugin-version-mismatch", NOT_APPLICABLE)


class TemplaterReferenceErrorTest(DoctorHelperTest):
    def test_a_reported_reference_error_is_confirmed_and_names_the_identifier(self):
        _, document, _ = self.diagnose(BUNDLES["reference-error-in-console"])
        self.assertStatus(document, "templater-reference-error", CONFIRMED)
        self.assertEvidenceMentions(document, "templater-reference-error", "noteLabel")

    def test_an_unbound_output_command_is_confirmed_from_the_source_alone(self):
        _, document, _ = self.diagnose(BUNDLES["reference-error-in-source"])
        self.assertStatus(document, "templater-reference-error", CONFIRMED)
        self.assertEvidenceMentions(document, "templater-reference-error", "missingIdentifier")

    def test_bound_locals_and_documented_globals_are_not_reported_as_unbound(self):
        _, document, _ = self.diagnose(BUNDLES["template-fully-bound"])
        self.assertStatus(document, "templater-reference-error", RULED_OUT)

    def test_a_named_template_without_its_source_stays_unknown_for_every_source_check(self):
        code, document, _ = self.diagnose(BUNDLES["template-named-without-source"])
        self.assertEqual(code, EXIT_INDETERMINATE)
        for check_id in (
            "templater-reference-error",
            "templater-missing-await",
            "templater-missing-output",
            "templater-partial-mutation-risk",
        ):
            with self.subTest(check=check_id):
                self.assertStatus(document, check_id, UNKNOWN)


class TemplaterAwaitTest(DoctorHelperTest):
    def test_an_unawaited_async_call_is_confirmed_and_located(self):
        _, document, _ = self.diagnose(BUNDLES["async-call-unawaited"])
        self.assertStatus(document, "templater-missing-await", CONFIRMED)
        self.assertEvidenceMentions(document, "templater-missing-await", "tp.system.prompt")

    def test_an_awaited_call_is_ruled_out(self):
        _, document, _ = self.diagnose(BUNDLES["async-call-awaited"])
        self.assertStatus(document, "templater-missing-await", RULED_OUT)

    def test_the_await_check_does_not_fire_on_an_unrelated_defect(self):
        _, document, _ = self.diagnose(BUNDLES["reference-error-in-source"])
        self.assertStatus(document, "templater-missing-await", RULED_OUT)


class TemplaterOutputTest(DoctorHelperTest):
    def test_a_prompted_value_that_is_never_emitted_is_confirmed(self):
        _, document, _ = self.diagnose(BUNDLES["async-result-discarded"])
        self.assertStatus(document, "templater-missing-output", CONFIRMED)
        self.assertEvidenceMentions(document, "templater-missing-output", "answer")

    def test_command_text_surviving_into_the_rendered_note_is_confirmed(self):
        """Read-back evidence, not a clean exit, decides whether output landed."""
        _, document, _ = self.diagnose(BUNDLES["command-text-reached-note"])
        self.assertStatus(document, "templater-missing-output", CONFIRMED)

    def test_a_value_that_reaches_the_output_string_is_ruled_out(self):
        for name in ("async-call-awaited", "template-fully-bound"):
            with self.subTest(bundle=name):
                _, document, _ = self.diagnose(BUNDLES[name])
                self.assertStatus(document, "templater-missing-output", RULED_OUT)


class TemplaterPartialMutationTest(DoctorHelperTest):
    def test_an_unguarded_prompt_before_a_rename_is_confirmed(self):
        _, document, _ = self.diagnose(BUNDLES["prompt-before-mutation"])
        finding = self.finding(document, "templater-partial-mutation-risk")
        self.assertEqual(finding["status"], CONFIRMED)
        self.assertEvidenceMentions(document, "templater-partial-mutation-risk", "tp.file.rename")

    def test_a_prompt_after_a_mutation_is_confirmed_as_an_ordering_hazard(self):
        _, document, _ = self.diagnose(BUNDLES["mutation-before-prompt"])
        self.assertStatus(document, "templater-partial-mutation-risk", CONFIRMED)

    def test_a_cancellation_guard_or_raising_prompt_rules_the_hazard_out(self):
        for name in ("cancel-guarded-by-return", "cancel-raises-instead"):
            with self.subTest(bundle=name):
                _, document, _ = self.diagnose(BUNDLES[name])
                self.assertStatus(document, "templater-partial-mutation-risk", RULED_OUT)

    def test_the_remedy_is_proposed_for_human_approval_not_applied(self):
        _, document, _ = self.diagnose(BUNDLES["prompt-before-mutation"])
        finding = self.finding(document, "templater-partial-mutation-risk")
        kinds = {action["kind"] for action in finding["next_actions"]}
        self.assertIn("propose-change", kinds)
        self.assertEqual(document["mutations_performed"], [])


class PluginApiTest(DoctorHelperTest):
    def test_a_probe_observed_missing_is_confirmed(self):
        _, document, _ = self.diagnose(BUNDLES["api-probe-missing"])
        self.assertStatus(document, "plugin-api-unavailable", CONFIRMED)
        self.assertEvidenceMentions(document, "plugin-api-unavailable", "pluginApi.synthDoThing")

    def test_a_declared_probe_with_no_result_stays_unknown(self):
        code, document, _ = self.diagnose(BUNDLES["api-probe-indeterminate"])
        self.assertStatus(document, "plugin-api-unavailable", UNKNOWN)
        self.assertEqual(code, EXIT_INDETERMINATE)

    def test_a_probe_observed_present_is_ruled_out(self):
        _, document, _ = self.diagnose(BUNDLES["api-probe-present"])
        self.assertStatus(document, "plugin-api-unavailable", RULED_OUT)

    def test_an_api_shape_console_error_is_routed_to_this_check(self):
        _, document, _ = self.diagnose(BUNDLES["console-lines-all-classified"])
        self.assertStatus(document, "plugin-api-unavailable", CONFIRMED)


class ConsoleClassificationTest(DoctorHelperTest):
    def test_an_unrecognised_console_line_stays_unknown(self):
        code, document, _ = self.diagnose(BUNDLES["console-line-unclassified"])
        self.assertStatus(document, "console-error-unclassified", UNKNOWN)
        self.assertEqual(code, EXIT_INDETERMINATE)
        self.assertEqual(document["status"], "indeterminate")
        self.assertEvidenceMentions(document, "console-error-unclassified", "QX7")

    def test_an_unrecognised_line_is_never_rounded_up_to_a_familiar_class(self):
        _, document, _ = self.diagnose(BUNDLES["console-line-unclassified"])
        statuses = self.statuses(document)
        for check_id in ("templater-reference-error", "plugin-api-unavailable"):
            with self.subTest(check=check_id):
                self.assertNotEqual(statuses[check_id], CONFIRMED)

    def test_an_unknown_line_keeps_the_case_open_even_beside_a_confirmed_defect(self):
        payload = bundle(
            runtime={"app_running": False, "cli_available": False},
            console_errors=[UNCLASSIFIED_CONSOLE_LINE],
        )
        code, document, _ = self.diagnose(payload, name="mixed.json")
        self.assertStatus(document, "runtime-unavailable", CONFIRMED)
        self.assertStatus(document, "console-error-unclassified", UNKNOWN)
        self.assertEqual(code, EXIT_INDETERMINATE, "a confirmed defect does not close an unknown")

    def test_an_entry_the_classifier_cannot_read_is_reported_by_location(self):
        _, document, _ = self.diagnose(BUNDLES["console-entry-unreadable"])
        self.assertStatus(document, "console-error-unclassified", UNKNOWN)
        self.assertEvidenceMentions(document, "console-error-unclassified", "/console_errors/0")

    def test_a_console_channel_of_the_wrong_shape_stays_unknown_and_confirms_nothing(self):
        code, document, _ = self.diagnose(BUNDLES["console-channel-wrong-type"])
        self.assertEqual(code, EXIT_INDETERMINATE)
        self.assertStatus(document, "console-error-unclassified", UNKNOWN)
        self.assertNotEqual(
            self.statuses(document)["templater-reference-error"],
            CONFIRMED,
            "a malformed channel must not be mined for a confirmation",
        )

    def test_an_empty_capture_is_bounded_rather_than_called_clean(self):
        _, document, _ = self.diagnose(BUNDLES["console-capture-empty"])
        finding = self.finding(document, "console-error-unclassified")
        self.assertEqual(finding["status"], RULED_OUT)
        self.assertGreaterEqual(
            len(finding["evidence"]),
            2,
            "an empty capture must record what it does not prove",
        )

    def test_lines_that_all_match_a_signature_leave_nothing_unclassified(self):
        _, document, _ = self.diagnose(BUNDLES["console-lines-all-classified"])
        self.assertStatus(document, "console-error-unclassified", RULED_OUT)
        self.assertStatus(document, "templater-reference-error", CONFIRMED)

    def test_a_long_console_line_is_bounded_before_it_is_quoted(self):
        long_line = "Synthetic subsystem QX7 emitted marker " + ("ZZ" * 450)
        payload = bundle(runtime=runtime(), console_errors=[long_line])
        _, document, stdout = self.diagnose(payload, name="long.json")
        self.assertNotIn(long_line, stdout, "an unbounded fixture string reached the output")
        for item in self.finding(document, "console-error-unclassified")["evidence"]:
            self.assertLess(len(item), len(long_line))

    def test_a_multiline_console_line_is_flattened_into_single_line_evidence(self):
        payload = bundle(
            runtime=runtime(), console_errors=["Synthetic line one\nSynthetic line two\tcolumn"]
        )
        _, document, _ = self.diagnose(payload, name="multiline.json")
        for item in self.finding(document, "console-error-unclassified")["evidence"]:
            with self.subTest(evidence=item[:40]):
                self.assertNotIn("\n", item)
                self.assertNotIn("\t", item)


class AbsentChannelTest(DoctorHelperTest):
    def test_an_empty_bundle_verifies_nothing_and_stays_indeterminate(self):
        code, document, _ = self.diagnose(BUNDLES["no-channel-at-all"])
        self.assertEqual(code, EXIT_INDETERMINATE)
        statuses = self.statuses(document)
        self.assertEqual(statuses["runtime-unavailable"], UNKNOWN)
        for check_id in CHANNEL_DEPENDENT_IDS:
            if check_id == "runtime-unavailable":
                continue
            with self.subTest(check=check_id):
                self.assertEqual(
                    statuses[check_id],
                    NOT_APPLICABLE,
                    "a channel that was never supplied must not be reported as ruled out",
                )

    def test_observing_one_channel_does_not_verify_the_others(self):
        _, document, _ = self.diagnose(BUNDLES["runtime-observed"])
        statuses = self.statuses(document)
        self.assertEqual(statuses["runtime-unavailable"], RULED_OUT)
        for check_id in (
            "plugin-unavailable",
            "plugin-version-mismatch",
            "templater-reference-error",
            "templater-missing-await",
            "templater-missing-output",
            "templater-partial-mutation-risk",
            "plugin-api-unavailable",
            "console-error-unclassified",
        ):
            with self.subTest(check=check_id):
                self.assertEqual(statuses[check_id], NOT_APPLICABLE)

    def test_unsupplied_and_ruled_out_are_never_the_same_answer(self):
        """A template-only bundle verifies template checks and nothing else."""
        _, document, _ = self.diagnose(BUNDLES["template-fully-bound"])
        statuses = self.statuses(document)
        self.assertEqual(statuses["templater-missing-await"], RULED_OUT)
        self.assertEqual(statuses["plugin-api-unavailable"], NOT_APPLICABLE)
        self.assertEqual(statuses["console-error-unclassified"], NOT_APPLICABLE)


class SanitizationTest(DoctorHelperTest):
    def test_every_host_shaped_value_is_reported_by_location_and_never_echoed(self):
        for label, value in HOST_SHAPED_VALUES:
            with self.subTest(shape=label):
                payload = bundle(runtime=runtime(), template=template(path=value))
                _, document, stdout = self.diagnose(payload, name=f"{label}.json")
                self.assertStatus(document, "fixture-not-sanitized", CONFIRMED)
                self.assertEvidenceMentions(document, "fixture-not-sanitized", "/template/path")
                self.assertNotIn(value, stdout, "a host-shaped fixture value reached the output")
                self.assertNotEqual(document["subject"]["template_path"], value)

    def test_every_secret_shaped_key_is_withheld_by_key_name(self):
        for key_name in SECRET_KEY_NAMES:
            with self.subTest(key=key_name):
                payload = bundle(
                    runtime=runtime(),
                    template=template(),
                    capture={key_name: SECRET_PLACEHOLDER},
                )
                _, document, stdout = self.diagnose(payload, name=f"secret-{key_name}.json")
                self.assertStatus(document, "fixture-not-sanitized", CONFIRMED)
                self.assertEvidenceMentions(
                    document, "fixture-not-sanitized", f"/capture/{key_name}"
                )
                self.assertNotIn(SECRET_PLACEHOLDER, stdout)

    def test_redaction_does_not_destroy_the_diagnosis_it_is_protecting(self):
        leaky_line = (
            "ReferenceError: synthLabel is not defined at "
            + _USERS
            + _ACCOUNT
            + "/SynthVault/Templates/Synth.md:3:12"
        )
        payload = bundle(runtime=runtime(), console_errors=[leaky_line])
        _, document, stdout = self.diagnose(payload, name="leaky-console.json")
        self.assertStatus(document, "templater-reference-error", CONFIRMED)
        self.assertStatus(document, "fixture-not-sanitized", CONFIRMED)
        self.assertNotIn(_USERS + _ACCOUNT, stdout)

    def test_a_host_shaped_case_id_is_withheld_from_the_subject(self):
        supplied = BUNDLES["unsanitized-case-id"]["case_id"]
        _, document, stdout = self.diagnose(BUNDLES["unsanitized-case-id"], name="case-id.json")
        self.assertNotIn(_USERS + _ACCOUNT, stdout)
        self.assertNotEqual(document["subject"]["case_id"], supplied)

    def test_a_sanitized_bundle_is_not_over_redacted(self):
        """A classifier that withheld everything would be useless, not private."""
        _, document, _ = self.diagnose(BUNDLES["template-fully-bound"])
        self.assertStatus(document, "fixture-not-sanitized", RULED_OUT)
        self.assertEqual(document["subject"]["template_path"], VAULT_RELATIVE_TEMPLATE)
        self.assertEqual(document["subject"]["case_id"], "SYN-DOCTOR-0001")

    def test_the_fixture_path_is_echoed_exactly_as_supplied(self):
        _, document, _ = self.diagnose(BUNDLES["runtime-observed"], name="evidence.json")
        self.assertEqual(
            document["fixture"],
            "evidence.json",
            "the helper must not resolve the supplied path against the host",
        )

    def test_a_host_shaped_fixture_path_is_withheld_from_the_envelope(self):
        relative = "./Users/" + _ACCOUNT + "/evidence.json"
        target = self.workspace / "Users" / _ACCOUNT / "evidence.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(BUNDLES["runtime-observed"]), encoding="utf-8")
        code, stdout, _ = self.run_helper("--fixture", relative)
        document = self.parse_json(stdout)
        self.assertDiagnosisContract(code, document, stdout)
        self.assertNotIn(relative, stdout)
        self.assertNotIn("/Users/" + _ACCOUNT, stdout)

    def test_a_host_shaped_fixture_path_is_withheld_from_an_input_error(self):
        relative = "./Users/" + _ACCOUNT + "/never-created.json"
        code, stdout, _ = self.run_helper("--fixture", relative)
        self.assertEqual(code, EXIT_INPUT_ERROR)
        document = self.parse_json(stdout)
        self.assertEqual(document["status"], "input_error")
        self.assertNotIn("/Users/" + _ACCOUNT, stdout)


class OutputFormatTest(DoctorHelperTest):
    def test_non_ascii_evidence_is_emitted_literally_not_escaped(self):
        _, document, stdout = self.diagnose(BUNDLES["non-ascii-case-id"], name="non-ascii.json")
        self.assertEqual(document["subject"]["case_id"], "SYN-검증-α-0001")
        self.assertIn("SYN-검증-α-0001", stdout)
        self.assertNotIn("\\u", stdout)

    def test_the_same_bundle_produces_byte_identical_output(self):
        relative = self.write_bundle(BUNDLES["app-older-than-manifest"], "repeat.json")
        first = self.run_helper("--fixture", relative)
        second = self.run_helper("--fixture", relative)
        self.assertEqual(first, second, "output must not vary with time or host state")

    def test_the_catalogue_is_also_stable_across_runs(self):
        self.assertEqual(self.run_helper("--list-checks"), self.run_helper("--list-checks"))


class InputErrorTest(DoctorHelperTest):
    """A malformed bundle is reported as an input error, never as a diagnosis."""

    def assertInputError(self, relative):
        code, stdout, _ = self.run_helper("--fixture", relative)
        self.assertEqual(code, EXIT_INPUT_ERROR)
        document = self.parse_json(stdout)
        self.assertEqual(set(document), INPUT_ERROR_KEYS, "unexpected input-error envelope key")
        self.assertEqual(document["schema"], DIAGNOSIS_SCHEMA)
        self.assertEqual(document["status"], "input_error")
        self.assertIsInstance(document["reason"], str)
        self.assertTrue(document["reason"].strip(), "an input error must say what was wrong")
        self.assertEqual(document["findings"], [])
        self.assertEqual(document["unknowns"], [])
        self.assertEqual(document["mutations_performed"], [])
        return document

    def test_unreadable_or_malformed_json_exits_with_an_input_error(self):
        cases = {
            "truncated.json": '{"schema": "obsidian-doctor/evidence@1", ',
            "empty.json": "",
            "array.json": "[]",
            "number.json": "42",
            "string.json": '"synthetic"',
            "null.json": "null",
        }
        for name, text in cases.items():
            with self.subTest(fixture=name):
                (self.workspace / name).write_text(text, encoding="utf-8")
                self.assertInputError(name)

    def test_a_bundle_of_the_wrong_schema_is_refused_rather_than_guessed(self):
        cases = {
            "no-schema.json": {"case_id": "SYN-DOCTOR-0001", "runtime": RUNTIME_OBSERVED},
            "next-schema.json": {"schema": "obsidian-doctor/evidence@2"},
            "numeric-schema.json": {"schema": 1},
            "null-schema.json": {"schema": None},
        }
        for name, payload in cases.items():
            with self.subTest(fixture=name):
                (self.workspace / name).write_text(json.dumps(payload), encoding="utf-8")
                self.assertInputError(name)

    def test_a_non_utf8_bundle_is_refused_without_an_exception(self):
        path = self.workspace / "latin1.json"
        path.write_bytes(b'{"schema": "obsidian-doctor/evidence@1", "case_id": "\xff\xfe"}')
        self.assertInputError("latin1.json")

    def test_a_missing_path_and_a_directory_are_both_input_errors(self):
        (self.workspace / "a-directory").mkdir()
        for relative in ("never-created.json", "a-directory"):
            with self.subTest(fixture=relative):
                self.assertInputError(relative)

    @unittest.skipIf(
        getattr(os, "geteuid", lambda: -1)() == 0, "root bypasses file permission checks"
    )
    def test_an_unreadable_bundle_is_an_input_error_not_a_crash(self):
        path = self.workspace / "unreadable.json"
        path.write_text(json.dumps(BUNDLES["runtime-observed"]), encoding="utf-8")
        path.chmod(0o000)
        self.addCleanup(path.chmod, 0o600)
        self.assertInputError("unreadable.json")

    def test_an_input_error_reports_no_subject_and_no_probes(self):
        (self.workspace / "array.json").write_text("[]", encoding="utf-8")
        document = self.assertInputError("array.json")
        self.assertNotIn("subject", document)
        self.assertNotIn("read_only_probes", document)


class UsageErrorTest(DoctorHelperTest):
    """An invalid command line fails on stderr and prints no diagnosis."""

    def test_every_invalid_invocation_exits_two_with_no_json_on_stdout(self):
        self.write_bundle(BUNDLES["runtime-observed"])
        invocations = {
            "no-mode": (),
            "both-modes": ("--list-checks", "--fixture", "evidence.json"),
            "unknown-flag": ("--vault", "SynthVault"),
            "fixture-without-value": ("--fixture",),
        }
        for label, args in invocations.items():
            with self.subTest(invocation=label):
                code, stdout, stderr = self.run_helper(*args)
                self.assertEqual(code, EXIT_USAGE)
                self.assertEqual(stdout, "", "a usage error must not print a diagnosis")
                self.assertTrue(stderr.strip(), "a usage error must explain itself on stderr")


class ReadOnlyBehaviourTest(DoctorHelperTest):
    """The helper reads one fixture and writes nothing, on every code path."""

    def populate(self):
        """A synthetic non-target tree plus every fixture the run will touch."""
        notes = self.workspace / "notes"
        (notes / "Templates").mkdir(parents=True)
        (notes / "nested").mkdir()
        (notes / "Welcome.md").write_text("# Synthetic Welcome\n\nkeep: true\n", encoding="utf-8")
        (notes / "Templates" / "Synthetic.md").write_text(TEMPLATE_BOUND, encoding="utf-8")
        (notes / "nested" / "keep.txt").write_text(
            "synthetic non-target payload\n", encoding="utf-8"
        )
        self.write_bundle(BUNDLES["prompt-before-mutation"])
        (self.workspace / "malformed.json").write_text("{not json", encoding="utf-8")
        (self.workspace / "a-directory").mkdir()

    def exercise(self, script=None):
        """Run every code path: diagnosis, catalogue, input error, usage error."""
        self.run_helper("--fixture", "evidence.json", script=script)
        self.run_helper("--list-checks", script=script)
        self.run_helper("--fixture", "malformed.json", script=script)
        self.run_helper("--fixture", "never-created.json", script=script)
        self.run_helper("--fixture", "a-directory", script=script)
        self.run_helper(script=script)

    def test_no_code_path_creates_changes_or_removes_a_file(self):
        self.populate()
        before = digest_tree(self.workspace)
        self.exercise()
        self.assertEqual(digest_tree(self.workspace), before, "the helper wrote to its workspace")

    def test_the_non_target_notes_survive_byte_for_byte(self):
        self.populate()
        notes = self.workspace / "notes"
        before = digest_tree(notes)
        self.exercise()
        self.assertEqual(digest_tree(notes), before)
        self.assertEqual(
            (notes / "Welcome.md").read_text(encoding="utf-8"),
            "# Synthetic Welcome\n\nkeep: true\n",
        )

    def test_the_helper_writes_nothing_beside_its_own_installed_location(self):
        """Run a copy of the real helper so the package directory is observable."""
        self.populate()
        package = self.workspace / "installed" / "scripts"
        package.mkdir(parents=True)
        copied = package / HELPER.name
        shutil.copy2(HELPER, copied)
        before = digest_tree(self.workspace, skip_names=("__pycache__",))
        self.exercise(script=copied)
        self.assertEqual(digest_tree(self.workspace, skip_names=("__pycache__",)), before)


class EnvelopeInvariantSweepTest(DoctorHelperTest):
    """Every synthetic bundle must satisfy the whole published contract."""

    def test_every_bundle_satisfies_the_envelope_and_finding_contract(self):
        for name, payload in BUNDLES.items():
            with self.subTest(bundle=name):
                # diagnose() asserts the envelope, findings, unknown roll-up,
                # exit code and serialisation contract for this bundle.
                self.diagnose(payload, name=f"{name}.json")

    def test_no_bundle_leaks_a_synthetic_host_or_secret_value(self):
        leaky = bundle(
            runtime=runtime(),
            template=template(path=HOST_SHAPED_VALUES[0][1]),
            capture={name: SECRET_PLACEHOLDER for name in SECRET_KEY_NAMES},
            console_errors=[HOST_SHAPED_VALUES[4][1], UNCLASSIFIED_CONSOLE_LINE],
        )
        _, document, stdout = self.diagnose(leaky, name="everything-leaky.json")
        self.assertStatus(document, "fixture-not-sanitized", CONFIRMED)
        for _label, value in HOST_SHAPED_VALUES[:1] + HOST_SHAPED_VALUES[4:5]:
            self.assertNotIn(value, stdout)
        self.assertNotIn(SECRET_PLACEHOLDER, stdout)


if __name__ == "__main__":
    unittest.main()
