#!/usr/bin/env python3
"""Static package-identity, resource-closure and privacy tests.

Scope boundary: every assertion in this module is about the bytes checked into
this repository. Nothing here loads a skill into a runtime, reaches a network,
reads a profile, or proves that Obsidian, a plugin, or a marketplace accepted
anything. A passing run means the packages are internally consistent and agree
with the declared release identity -- not that a runtime installed them. 0.3.0
is a public prerelease. Its two verified native installs and fresh-loads are
historical: Claude Code in an isolated project scope, at the immutable v0.1.0
tag, and Hermes Agent across five generic operator profiles, at the corrected
c22ce26 revision and operator-reported. No
assertion here observed either one; Codex, GJC and Grok remain unverified.

Run:  python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
INSTALL_SH = REPO / "install.sh"
PUBLICATION_CANARY = REPO / "tests" / "evidence" / "publication-canary.json"

# Directories that are private working state, not publishable content. They are
# excluded from every scan in this module; the exclusion itself is asserted.
PRIVATE_DIRS = frozenset(
    {".git", ".gjc", ".venv", ".test-output", "__pycache__", "node_modules"}
)

# Agent Skills frontmatter keys this repository allows. A key outside this set
# is either a typo or an undeclared coupling between packages.
ALLOWED_FRONTMATTER_KEYS = frozenset(
    {"name", "description", "license", "allowed-tools", "metadata"}
)

# Frontmatter keys that would turn a standalone package into a router, a
# dispatcher, or a dependent of another package. AGENTS.md forbids all of them.
FORBIDDEN_FRONTMATTER_KEYS = frozenset(
    {
        "dependencies",
        "depends_on",
        "requires",
        "skills",
        "router",
        "dispatch",
        "dispatcher",
        "entrypoint",
        "extends",
        "imports",
    }
)

# Agent Skills limits: one lowercase path segment, and a description a host can
# hold in its skill index.
NAME_SEGMENT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024

FENCE_RE = re.compile(r"^```.*?^```", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)

TEXT_SUFFIXES = frozenset(
    {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".svg", ".base", ".canvas", ""}
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def declared_packages() -> list:
    """The nine package names install.sh declares, read from the installer."""
    match = re.search(r"^PACKAGE_SKILLS='([^']*)'", INSTALL_SH.read_text("utf-8"), re.M)
    if match is None:
        raise AssertionError("install.sh no longer declares PACKAGE_SKILLS")
    return match.group(1).split()


def knowledge_packages() -> list:
    """The eleven knowledge package names install.sh declares."""
    match = re.search(r"^KNOWLEDGE_SKILLS='([^']*)'", INSTALL_SH.read_text("utf-8"), re.M)
    if match is None:
        raise AssertionError("install.sh no longer declares KNOWLEDGE_SKILLS")
    return match.group(1).split()


def present_packages() -> list:
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


def public_files() -> list:
    """Every readable file that would ship, private working state excluded."""
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = sorted(d for d in dirnames if d not in PRIVATE_DIRS)
        for filename in sorted(filenames):
            found.append(Path(dirpath) / filename)
    return found


def package_files(package: Path) -> list:
    """Every shipped file in one package; private working state excluded."""
    found = []
    for dirpath, dirnames, filenames in os.walk(package):
        dirnames[:] = sorted(d for d in dirnames if d not in PRIVATE_DIRS)
        for filename in sorted(filenames):
            found.append(Path(dirpath) / filename)
    return found


def read_text(path: Path):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def prose_only(markdown: str) -> str:
    """Markdown with fenced blocks and inline code removed.

    Links inside a code span are syntax examples, not resource references.
    """
    return INLINE_CODE_RE.sub(" ", FENCE_RE.sub(" ", markdown))


def frontmatter(path: Path) -> dict:
    match = FRONTMATTER_RE.match(path.read_text("utf-8"))
    if match is None:
        raise AssertionError(f"{path} has no --- delimited YAML frontmatter block")
    loaded = yaml.safe_load(match.group(1))
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path} frontmatter is {type(loaded).__name__}, not a mapping")
    return loaded


def load_json(path: Path):
    return json.loads(path.read_text("utf-8"))


# --------------------------------------------------------------------------- #
# privacy scanner
# --------------------------------------------------------------------------- #
# The literals below are assembled from fragments so that this file does not
# contain the very strings it forbids, which would make the scanner flag itself.
_USERS = "/" + "Users" + "/"
_HOMES = "/" + "home" + "/"

# Placeholder names that are obviously invented. A synthetic example path is not
# a host leak; a real account name is.
SYNTHETIC_ACCOUNTS = frozenset({"example-user", "username", "user", "you", "<user>", "USER"})

# A value carrying one of these markers is a documented placeholder, not a
# credential, however long or opaque it looks.
PLACEHOLDER_MARKERS = ("placeholder", "example", "synthetic", "redact", "not-a-real", "dummy")

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|authorization|private[_-]?key)"
    r"\s*[:=]\s*[\"']?([A-Za-z0-9/+_-]{16,})"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ACCOUNT_PATH_RE = re.compile(
    "(?:" + re.escape(_USERS) + "|" + re.escape(_HOMES) + r")([A-Za-z0-9._-]+)"
)


def host_identity_leaks(text: str) -> list:
    """Reasons ``text`` would publish this workstation's identity or a secret."""
    reasons = []

    home = str(Path.home())
    if home and home not in ("/", "/root") and home in text:
        reasons.append("absolute home-directory path of the current host")

    account = getpass.getuser()
    if account and len(account) >= 3 and account not in SYNTHETIC_ACCOUNTS:
        if re.search(r"\b" + re.escape(account) + r"\b", text):
            reasons.append("current host account name")

    for match in ACCOUNT_PATH_RE.finditer(text):
        if match.group(1) not in SYNTHETIC_ACCOUNTS:
            reasons.append(f"account-scoped absolute path for {match.group(1)!r}")

    for match in EMAIL_RE.finditer(text):
        reasons.append(f"email address {match.group(0)!r}")

    for match in SECRET_ASSIGNMENT_RE.finditer(text):
        value = match.group(2)
        if not any(marker in value.lower() for marker in PLACEHOLDER_MARKERS):
            reasons.append(f"credential-shaped assignment to {match.group(1)!r}")

    return reasons


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
class DeclaredPackagesTest(unittest.TestCase):
    """The installer's declared set and the checkout must agree exactly."""

    def setUp(self):
        self.declared = declared_packages()

    def test_installer_declares_nine_unique_legal_names(self):
        self.assertEqual(len(self.declared), 9, self.declared)
        self.assertEqual(len(set(self.declared)), 9, "duplicate name in PACKAGE_SKILLS")
        for name in self.declared:
            with self.subTest(package=name):
                self.assertRegex(name, NAME_SEGMENT_RE)
                self.assertLessEqual(len(name), MAX_NAME_LEN)

    def test_every_declared_package_ships_a_skill_file(self):
        missing = [n for n in self.declared if not (SKILLS_DIR / n / "SKILL.md").is_file()]
        self.assertEqual(missing, [], f"declared but not installable from this checkout: {missing}")

    def test_installer_declares_the_eleven_knowledge_names_without_a_native_prefix(self):
        knowledge = knowledge_packages()
        self.assertEqual(
            sorted(knowledge),
            sorted(
                "capture inbox ingest query verify audit lint status reindex "
                "refresh-context onboard".split()
            ),
        )
        self.assertEqual(len(set(knowledge)), len(knowledge), "duplicate knowledge name")
        self.assertEqual(set(knowledge) & set(self.declared), set())
        for name in knowledge:
            with self.subTest(package=name):
                self.assertRegex(name, NAME_SEGMENT_RE)
                self.assertFalse(name.startswith("obsidian-"), "knowledge names carry no prefix")

    def test_no_undeclared_package_directory_exists(self):
        """Native packages all exist; a knowledge package may be absent, never unnamed."""
        knowledge = set(knowledge_packages())
        present = present_packages()
        self.assertEqual([n for n in present if n not in knowledge], sorted(self.declared))
        for name in present:
            with self.subTest(package=name):
                self.assertTrue((SKILLS_DIR / name / "SKILL.md").is_file())

    def test_twenty_packages(self):
        """Nine native plus eleven knowledge: one directory, one listing, one owner each."""
        knowledge = knowledge_packages()
        twenty = sorted(self.declared + knowledge)
        self.assertEqual(len(set(twenty)), 20, twenty)
        self.assertEqual(present_packages(), twenty)
        for name in twenty:
            with self.subTest(package=name):
                self.assertTrue((SKILLS_DIR / name / "SKILL.md").is_file())

        for label, metadata in (
            ("claude plugin", load_json(REPO / ".claude-plugin" / "plugin.json")["metadata"]),
            (
                "claude marketplace",
                load_json(REPO / ".claude-plugin" / "marketplace.json")["plugins"][0]["metadata"],
            ),
        ):
            with self.subTest(manifest=label):
                self.assertEqual(sorted(metadata["packages"]), sorted(self.declared))
                self.assertEqual(sorted(metadata["knowledgePackages"]), sorted(knowledge))

        sys.path.insert(0, str(REPO / "scripts"))
        from audit_inventory import audit

        inventory = load_json(REPO / "source-inventory.json")
        self.assertEqual(audit(inventory, REPO), [])
        self.assertEqual(
            sorted(feature["package"] for feature in inventory["features"].values()),
            ["skills/" + name for name in twenty],
        )
        self.assertEqual(
            {unit["package"] for unit in inventory["units"] if unit["class"] == "functional"},
            set(self.declared),
        )
        self.assertEqual(
            sorted(row["package"] for row in inventory["knowledge_capabilities"]),
            sorted(knowledge),
        )

    def test_repository_ships_no_callable_root_skill(self):
        self.assertFalse((REPO / "SKILL.md").exists(), "a root SKILL.md would be a router")
        for name in self.declared + knowledge_packages():
            package = SKILLS_DIR / name
            if not package.is_dir():
                continue
            nested = [p for p in package.rglob("SKILL.md") if p.parent != package]
            with self.subTest(package=name):
                self.assertEqual(nested, [], "a package holds exactly one SKILL.md")


class FrontmatterTest(unittest.TestCase):
    """Frontmatter is real YAML and carries a usable, self-contained identity."""

    def setUp(self):
        self.skills = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        if not self.skills:
            self.fail("no packages found under skills/")

    def test_frontmatter_parses_and_declares_name_and_description(self):
        for path in self.skills:
            with self.subTest(package=path.parent.name):
                data = frontmatter(path)
                self.assertIn("name", data)
                self.assertIn("description", data)
                self.assertIsInstance(data["name"], str)
                self.assertIsInstance(data["description"], str)
                self.assertTrue(data["description"].strip())

    def test_declared_name_matches_the_owning_directory(self):
        for path in self.skills:
            with self.subTest(package=path.parent.name):
                self.assertEqual(frontmatter(path)["name"], path.parent.name)

    def test_name_is_one_lowercase_path_segment_within_the_length_limit(self):
        for path in self.skills:
            with self.subTest(package=path.parent.name):
                name = frontmatter(path)["name"]
                self.assertRegex(name, NAME_SEGMENT_RE)
                self.assertLessEqual(len(name), MAX_NAME_LEN)

    def test_description_is_single_line_and_within_the_index_limit(self):
        for path in self.skills:
            with self.subTest(package=path.parent.name):
                description = frontmatter(path)["description"]
                self.assertNotIn("\n", description)
                self.assertLessEqual(
                    len(description),
                    MAX_DESCRIPTION_LEN,
                    f"{len(description)} chars exceeds the {MAX_DESCRIPTION_LEN}-char limit",
                )

    def test_frontmatter_carries_no_unknown_or_coupling_key(self):
        for path in self.skills:
            with self.subTest(package=path.parent.name):
                keys = set(frontmatter(path))
                self.assertEqual(keys & FORBIDDEN_FRONTMATTER_KEYS, set())
                self.assertEqual(
                    keys - ALLOWED_FRONTMATTER_KEYS,
                    set(),
                    "unrecognised frontmatter key",
                )

    def test_declared_license_and_version_match_the_shipped_manifests(self):
        plugin = load_json(REPO / ".claude-plugin" / "plugin.json")
        for path in self.skills:
            data = frontmatter(path)
            with self.subTest(package=path.parent.name):
                if "license" in data:
                    self.assertEqual(data["license"], plugin["license"])
                metadata = data.get("metadata")
                if isinstance(metadata, dict) and "version" in metadata:
                    self.assertEqual(str(metadata["version"]), plugin["version"])


class PackageIdentityTest(unittest.TestCase):
    """One identity per feature, and one release identity across the manifests."""

    def test_declared_skill_names_are_unique(self):
        names = [frontmatter(p)["name"] for p in sorted(SKILLS_DIR.glob("*/SKILL.md"))]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual(duplicates, [])

    def test_no_package_reaches_into_a_sibling_package(self):
        for package in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
            for path in package_files(package):
                text = read_text(path) if path.suffix == ".md" else None
                if text is None:
                    continue
                for target in MD_LINK_RE.findall(prose_only(text)):
                    with self.subTest(file=str(path.relative_to(REPO)), link=target):
                        self.assertNotRegex(
                            target,
                            r"\.\./obsidian-",
                            "a package must not link into a sibling package",
                        )

    def test_release_identity_agrees_across_installer_and_manifests(self):
        installer = INSTALL_SH.read_text("utf-8")
        pkg_name = re.search(r"^PKG_NAME=(\S+)", installer, re.M).group(1)
        pkg_version = re.search(r"^PKG_VERSION=(\S+)", installer, re.M).group(1)
        pkg_license = re.search(r"^PKG_LICENSE=(\S+)", installer, re.M).group(1)
        pkg_status = re.search(r"^PKG_STATUS=(\S+)", installer, re.M).group(1)

        claude_plugin = load_json(REPO / ".claude-plugin" / "plugin.json")
        codex_plugin = load_json(REPO / ".codex-plugin" / "plugin.json")
        claude_market = load_json(REPO / ".claude-plugin" / "marketplace.json")
        agents_market = load_json(REPO / ".agents" / "plugins" / "marketplace.json")

        for label, value in (
            ("claude plugin", claude_plugin["name"]),
            ("codex plugin", codex_plugin["name"]),
            ("claude marketplace", claude_market["name"]),
            ("agents marketplace", agents_market["name"]),
        ):
            with self.subTest(manifest=label):
                self.assertEqual(value, pkg_name)

        self.assertEqual(claude_plugin["version"], pkg_version)
        self.assertEqual(codex_plugin["version"], pkg_version)
        self.assertEqual(claude_plugin["license"], pkg_license)

        for label, manifest in (("claude", claude_market), ("agents", agents_market)):
            with self.subTest(marketplace=label):
                entries = manifest["plugins"]
                self.assertEqual(len(entries), 1, "one plugin identity per marketplace")
                self.assertEqual(entries[0]["name"], pkg_name)

        # The release identity moves with the shipped tree so that installed hosts
        # see an upgrade; the immutable historical tag keeps its own version.
        # Installer and manifests must not disagree about either.
        pkg_tag_version = re.search(r"^PKG_TAG_VERSION=(\S+)", installer, re.M).group(1)
        self.assertEqual(pkg_version, "0.3.0")
        self.assertEqual(pkg_tag_version, "0.1.0")
        self.assertNotEqual(pkg_version, pkg_tag_version)
        self.assertEqual(pkg_status, "prerelease")
        self.assertEqual(claude_plugin["metadata"]["releaseStatus"], pkg_status)
        self.assertEqual(claude_market["version"], pkg_version)
        self.assertEqual(
            claude_market["plugins"][0]["metadata"]["releaseStatus"], pkg_status
        )

    def test_every_manifest_names_the_collection_and_lists_only_existing_packages(self):
        """A manifest may not advertise a package this checkout cannot install."""
        manifests = {
            "claude plugin": REPO / ".claude-plugin" / "plugin.json",
            "claude marketplace": REPO / ".claude-plugin" / "marketplace.json",
            "codex plugin": REPO / ".codex-plugin" / "plugin.json",
            "agents marketplace": REPO / ".agents" / "plugins" / "marketplace.json",
        }
        loaded = {}
        for label, path in manifests.items():
            with self.subTest(manifest=label):
                loaded[label] = load_json(path)
                self.assertIn("secondbrain-skills", json.dumps(loaded[label]))

        knowledge = set(knowledge_packages())
        present = present_packages()
        for label, metadata in (
            ("claude plugin", loaded["claude plugin"]["metadata"]),
            ("claude marketplace", loaded["claude marketplace"]["plugins"][0]["metadata"]),
        ):
            with self.subTest(manifest=label):
                self.assertEqual(metadata["collection"], "secondbrain-skills")
                self.assertEqual(
                    sorted(metadata["packages"]), [n for n in present if n not in knowledge]
                )
                self.assertEqual(
                    sorted(metadata["knowledgePackages"]), [n for n in present if n in knowledge]
                )
                self.assertEqual(metadata["packageCount"], len(metadata["packages"]))

    def test_manifest_prose_states_the_prerelease_and_its_verified_install_boundary(self):
        """No manifest may still read as unreleased or claim a blanket install."""
        claude = load_json(REPO / ".claude-plugin" / "plugin.json")
        codex = load_json(REPO / ".codex-plugin" / "plugin.json")
        market = load_json(REPO / ".claude-plugin" / "marketplace.json")
        prose = {
            "claude description": claude["description"],
            "codex description": codex["description"],
            "codex longDescription": codex["interface"]["longDescription"],
            "claude marketplace description": market["description"],
        }
        for label, text in prose.items():
            with self.subTest(field=label):
                self.assertNotIn("unreleased", text)
                self.assertIn("public prerelease", text)

        for label, text in (
            ("claude description", prose["claude description"]),
            ("codex longDescription", prose["codex longDescription"]),
        ):
            with self.subTest(field=label):
                self.assertIn("Claude Code", text)
                self.assertIn("isolated project scope", text)
                self.assertIn("unverified", text)


class RecordedEvidenceProvenanceTest(unittest.TestCase):
    """A recorded result has to say who observed it, and at which revision.

    The publication report now mixes two kinds of claim: canaries this repository
    ran itself, and an install an operator ran on their own profiles and relayed.
    A reader cannot weigh either one without being told which it is, so the
    distinction is recorded as data rather than left to prose. Nothing here
    re-observes any run; these are consistency checks over text already written.
    """

    def setUp(self):
        self.report = load_json(PUBLICATION_CANARY)
        self.installer = INSTALL_SH.read_text("utf-8")

    def sections(self) -> dict:
        return {
            name: value
            for name, value in self.report.items()
            if isinstance(value, dict) and name != "reporters"
        }

    def installer_value(self, name: str) -> str:
        match = re.search(rf"^{name}=(\S+)", self.installer, re.M)
        if match is None:
            raise AssertionError(f"install.sh no longer declares {name}")
        return match.group(1)

    def test_every_recorded_section_names_a_declared_reporter(self):
        reporters = self.report["reporters"]
        self.assertTrue({"leader", "operator"} <= set(reporters), sorted(reporters))
        for label, description in reporters.items():
            with self.subTest(reporter=label):
                self.assertTrue(description.strip())
        for name, section in self.sections().items():
            with self.subTest(section=name):
                self.assertIn(section.get("reportedBy"), reporters)

    def test_an_operator_section_never_reads_as_something_observed_here(self):
        operator = {
            name: section
            for name, section in self.sections().items()
            if section["reportedBy"] == "operator"
        }
        self.assertTrue(operator, "the operator evidence is no longer recorded")
        for name, section in operator.items():
            with self.subTest(section=name):
                limitations = section["limitations"]
                self.assertTrue(
                    any("Operator-reported" in entry for entry in limitations),
                    "an operator section must say it was not observed here",
                )

    def test_the_installer_and_the_report_agree_on_the_two_revisions(self):
        """Each recorded result stays bound to the revision it was observed at.

        The tag, the historical Hermes install and the current recommended source
        are three separate facts. The recommended pin moves with each release;
        the recorded runs never move with it.
        """
        pin = self.installer_value("PKG_PIN")
        hermes_pin = self.installer_value("PKG_HERMES_PIN")
        tag_pin = self.installer_value("PKG_TAG_PIN")
        for label, commit in (
            ("PKG_PIN", pin),
            ("PKG_HERMES_PIN", hermes_pin),
            ("PKG_TAG_PIN", tag_pin),
        ):
            with self.subTest(pin=label):
                self.assertRegex(commit, COMMIT_RE)
        self.assertNotEqual(pin, tag_pin, "the tag is never the recommended source")
        self.assertNotEqual(hermes_pin, tag_pin, "the correction has to be its own revision")

        self.assertEqual(self.report["publication"]["commit"], tag_pin)
        self.assertEqual(self.report["nativeCanary"]["commit"], tag_pin)
        self.assertEqual(self.report["hermesNative"]["commit"], hermes_pin)
        tagged = self.report["taggedRelease"]
        self.assertEqual(tagged["commit"], tag_pin)
        self.assertEqual(tagged["correctedAt"], hermes_pin)


    def test_the_tagged_release_is_recorded_as_unusable_and_never_retagged(self):
        tagged = self.report["taggedRelease"]
        self.assertIs(tagged["retagged"], False)
        self.assertIs(tagged["usableForFullHermesInstall"], False)
        self.assertTrue(tagged["findings"], "a refusal has to name what it found")
        for finding in tagged["findings"]:
            with self.subTest(finding=finding[:40]):
                self.assertTrue(finding.strip())

    def test_the_operator_install_records_counts_rather_than_identities(self):
        hermes = self.report["hermesNative"]
        install = hermes["install"]
        for key in ("packages", "profiles", "units", "safe"):
            with self.subTest(count=key):
                self.assertNotIsInstance(install[key], bool)
                self.assertIsInstance(install[key], int)
        self.assertEqual(install["packages"], len(declared_packages()))
        self.assertEqual(install["units"], install["packages"] * install["profiles"])
        self.assertEqual(install["safe"], install["units"], "a unit short of SAFE is not SAFE")
        self.assertIs(install["forceUsed"], False)
        # A profile is reported as a count and a generic word, never as a name,
        # a path or an account.
        for text in (hermes["scope"], install["unit"]):
            with self.subTest(text=text):
                for forbidden in ("/", "@", "~", "\\"):
                    self.assertNotIn(forbidden, text)

    def test_a_fresh_session_claim_stays_inside_what_it_exercised(self):
        sessions = self.report["hermesNative"]["freshSessions"]
        self.assertIsInstance(sessions["count"], int)
        self.assertNotIsInstance(sessions["count"], bool)
        self.assertIs(sessions["appVaultAccountOrNetworkOperation"], False)
        invoked = sessions["skillsInvoked"]
        untouched = sessions["skillsNotInvoked"]
        declared = declared_packages()
        self.assertTrue(invoked, "a fresh-load claim has to name what it loaded")
        self.assertTrue(untouched, "the packages never invoked are a claim of their own")
        self.assertEqual(set(invoked) & set(untouched), set(), "a package is one or the other")
        self.assertEqual(
            sorted(invoked + untouched),
            sorted(declared),
            "every installed package is either invoked or explicitly not claimed",
        )


class ResourceClosureTest(unittest.TestCase):
    """A package copied on its own must not point at anything it did not bring.

    install.sh copies ``skills/<name>`` and nothing else, so a relative link that
    resolves outside the package is dangling in every installed copy.
    """

    def relative_links(self):
        for package in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
            for path in package_files(package):
                text = read_text(path) if path.suffix == ".md" else None
                if text is None:
                    continue
                for target in MD_LINK_RE.findall(prose_only(text)):
                    if target.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    base = target.split("#", 1)[0]
                    if not base:
                        continue
                    yield package, path, target, base

    def test_every_relative_link_resolves_inside_its_own_package(self):
        for package, path, target, base in self.relative_links():
            resolved = (path.parent / base).resolve()
            with self.subTest(file=str(path.relative_to(REPO)), link=target):
                self.assertTrue(
                    str(resolved).startswith(str(package.resolve()) + os.sep),
                    f"{target} escapes {package.name}",
                )
                self.assertTrue(resolved.exists(), f"{target} does not exist")

    def test_no_link_targets_an_absolute_or_host_local_location(self):
        for _package, path, target, _base in self.relative_links():
            with self.subTest(file=str(path.relative_to(REPO)), link=target):
                self.assertFalse(target.startswith("/"), "absolute path target")
                self.assertNotIn("file://", target.lower())

    def test_every_shipped_resource_is_referenced_by_its_package(self):
        """A reference or script nobody names is dead weight in every install."""
        standalone = {"SKILL.md", "CHANGELOG.md", "PROVENANCE.md", "LICENSE", "NOTICE"}
        for package in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
            files = package_files(package)
            for resource in files:
                if resource.name in standalone:
                    continue
                relative = resource.relative_to(package).as_posix()
                # A file naming its own path does not make it referenced.
                corpus = "\n".join(
                    text
                    for text in (read_text(p) for p in files if p != resource)
                    if text is not None
                )
                with self.subTest(resource=f"{package.name}/{relative}"):
                    self.assertIn(relative, corpus, "shipped but never referenced")


class PublicTreePrivacyTest(unittest.TestCase):
    """Nothing publishable may carry this workstation's identity or a secret."""

    def setUp(self):
        self.files = public_files()

    def test_the_scan_actually_covers_the_publishable_tree(self):
        readable = [p for p in self.files if read_text(p) is not None]
        self.assertGreaterEqual(len(readable), 15, "scan collected implausibly few files")
        names = {p.name for p in self.files}
        self.assertIn("install.sh", names)
        self.assertIn("SKILL.md", names)

    def test_private_working_directories_are_excluded_from_the_scan(self):
        scanned = {p for p in self.files}
        for private in PRIVATE_DIRS:
            candidate = REPO / private
            if not candidate.exists():
                continue
            with self.subTest(directory=private):
                leaked = [p for p in scanned if candidate in p.parents]
                self.assertEqual(leaked, [], f"{private} must never be scanned or shipped")

    def test_no_public_file_leaks_host_identity_or_a_credential(self):
        for path in self.files:
            text = read_text(path)
            if text is None:
                continue
            reasons = host_identity_leaks(text)
            with self.subTest(file=str(path.relative_to(REPO))):
                self.assertEqual(reasons, [], "; ".join(reasons))

    def test_the_scanner_rejects_a_synthetic_leak(self):
        """Negative control: a scanner that flags nothing would pass vacuously."""
        account = getpass.getuser()
        samples = [
            str(Path.home() / "vaults" / "private.md"),
            _USERS + "realaccount/Vaults/Notes",
            "contact: " + "someone" + "@" + "example.org",
            "api_key: " + "A1b2C3d4E5f6G7h8I9j0K1l2",
        ]
        if account and len(account) >= 3 and account not in SYNTHETIC_ACCOUNTS:
            samples.append(f"owner {account} ran this")
        for sample in samples:
            with self.subTest(sample=sample[:24]):
                self.assertNotEqual(host_identity_leaks(sample), [])

    def test_the_scanner_accepts_documented_placeholders(self):
        for sample in (
            "token: <your-placeholder-token-here>",
            _USERS + "example-user/Vaults/Demo",
            "password: PLACEHOLDER-NOT-A-REAL-VALUE",
        ):
            with self.subTest(sample=sample[:24]):
                self.assertEqual(host_identity_leaks(sample), [])

    def test_private_working_state_is_ignored_by_version_control(self):
        rules = {
            line.strip()
            for line in (REPO / ".gitignore").read_text("utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        for private in (".gjc", ".venv"):
            with self.subTest(directory=private):
                self.assertTrue(
                    any(private in rule for rule in rules),
                    f"{private} must be gitignored, not publishable",
                )

    def test_the_scan_never_leaves_the_repository_tree(self):
        for path in self.files:
            self.assertTrue(str(path).startswith(str(REPO) + os.sep))


# Two HIGH-severity rules of the Hermes Agent skills guard (tools/skills_guard.py,
# observed in Hermes v0.21.5). A HIGH finding gives a package a "caution" verdict,
# and Hermes refuses to install a community-source package with that verdict, so
# one match blocks the whole package from `hermes skills install`. Both rules
# matched harmless 0.2.0 text (an exclamation mark shown as inline code, and an
# environment copy for a subprocess) and blocked four packages. The expressions
# below are the guard's own, so a match here is a match there.
HERMES_INLINE_SHELL_EXEC_RE = re.compile(r"!`[^`\s][^`\n]*`")
HERMES_PYTHON_OS_ENVIRON_RE = re.compile(r"^[^#\n]*os\.environ\b(?!\s*\.get\s*\()", re.M)


def hermes_blocking_findings(rel: str, text: str) -> list:
    """``file:line rule`` for each Hermes HIGH rule match in one shipped file."""
    rules = [("inline_shell_exec", HERMES_INLINE_SHELL_EXEC_RE)]
    if rel.endswith(".py"):
        rules.append(("python_os_environ", HERMES_PYTHON_OS_ENVIRON_RE))
    found = []
    for name, pattern in rules:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append(f"{rel}:{line} {name}: {match.group(0).strip()[:80]}")
    return found


class HermesSkillsGuardTest(unittest.TestCase):
    """No shipped package may trip a Hermes skills-guard rule that blocks install."""

    def test_no_package_file_matches_a_hermes_install_blocking_rule(self):
        scanned = 0
        findings = []
        for path in package_files(SKILLS_DIR):
            try:
                text = path.read_text("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            scanned += 1
            findings += hermes_blocking_findings(path.relative_to(REPO).as_posix(), text)
        self.assertGreater(scanned, 100, "scan collected implausibly few files")
        self.assertEqual(findings, [], "\n" + "\n".join(findings))

    def test_the_rules_flag_the_shapes_that_blocked_0_2_0(self):
        """Negative control: rules that flag nothing would pass vacuously."""
        bang = "!"
        tick = "`"
        blocked = {
            "a.md": "prefixed with " + tick + bang + tick + ": the target -- see `SKILL.md`",
            "b.md": "`=`, " + tick + bang + tick + ", `%`",
            "c.py": "env=dict(os." + "environ, LANG='C'),",
            "d.py": "x = os." + "environ['HOME']",
        }
        for rel, text in blocked.items():
            with self.subTest(sample=rel):
                self.assertNotEqual(hermes_blocking_findings(rel, text), [])

    def test_the_rules_accept_the_0_2_1_rewordings(self):
        for rel, text in {
            "a.md": "prefixed with an exclamation mark, as in `![[Note Name]]`: the target",
            "b.md": "`=`, `` ! ``, `%`, `!=`",
            "c.py": "# os." + "environ is never copied\nvalue = os." + "environ.get('X')",
            "d.md": "os." + "environ in prose is not Python",
        }.items():
            with self.subTest(sample=rel):
                self.assertEqual(hermes_blocking_findings(rel, text), [])


if __name__ == "__main__":
    unittest.main()
