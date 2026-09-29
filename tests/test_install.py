#!/usr/bin/env python3
"""Black-box tests for install.sh.

Every invocation runs with ``HOME`` and ``TMPDIR`` pointed at a throwaway
directory, so ``--scope user`` can never resolve to the real profile. Two
fixtures are used:

* a *sandbox checkout* -- install.sh and its copier, scripts/install_packages.py,
  copied next to synthetic packages named after the nine declarations, so copy
  behaviour is tested without depending on the real packages or on any lane
  still authoring them;
* the *real checkout*, exercised only by read-only commands.

Races are reproduced, not awaited. The check-then-use windows live inside the
copier, and the installer carries no hook a test could pause it with -- test
machinery has no place in the program that writes to a consumer's filesystem.
``CopierAnchoringTest`` therefore drives the copier's own functions and performs
the interference between the exact two calls it belongs between. No test depends
on winning a race, and none skips itself for losing one.

What these tests do not claim: that a runtime discovered, loaded, or executed a
copied package. A directory copy is a filesystem fact, not an install. The one
native install and fresh-load that has been verified -- Claude Code, isolated
project scope only, from a clone of the published 0.1.0 prerelease tag -- was
performed by hand outside this suite. Every other runtime's install is
unverified, and nothing here executes a runtime CLI to change that.

Run:  python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO / "install.sh"
COPIER = REPO / "scripts" / "install_packages.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "neutral-vault" / "fixture.json"

OK = 0
REFUSED = 1
USAGE_ERROR = 2

COMMAND_ALIASES = frozenset({"help", "-h", "--help"})


def installer_source() -> str:
    return INSTALL_SH.read_text("utf-8")


def declared_packages() -> list:
    return re.search(r"^PACKAGE_SKILLS='([^']*)'", installer_source(), re.M).group(1).split()


def known_runtimes() -> list:
    return re.search(r"^KNOWN_RUNTIMES='([^']*)'", installer_source(), re.M).group(1).split()


def release_status() -> str:
    return re.search(r"^PKG_STATUS=(\S+)", installer_source(), re.M).group(1)


def release_pin() -> str:
    return re.search(r"^PKG_PIN=(\S+)", installer_source(), re.M).group(1)


def route_kinds() -> dict:
    """runtime id -> declared route kind, read from the installer's route table."""
    body = re.search(r"route_load\(\) \{(.*?)\n\}\n", installer_source(), re.S).group(1)
    kinds = {}
    for runtime in known_runtimes():
        arm = re.search(
            r"^\s*" + re.escape(runtime) + r"\)\n(.*?)\n\s*;;",
            body,
            re.S | re.M,
        )
        if arm:
            kind = re.search(r"R_KIND='([^']+)'", arm.group(1))
            if kind:
                kinds[runtime] = kind.group(1)
    return kinds


def accepted_options() -> set:
    """Long/short options the argument loop actually accepts."""
    loop = re.search(r'while \[ "\$#" -gt 0 \]; do(.*?)\ndone\n', installer_source(), re.S)
    found = set()
    for label in re.findall(r"^\s{4}(-[^)]*)\)", loop.group(1), re.M):
        for token in label.split("|"):
            token = token.strip()
            if token.endswith("=*"):
                token = token[:-2]
            if token.startswith("-"):
                found.add(token)
    return found


def accepted_commands() -> set:
    match = re.search(r"^  ([a-z|]+)\) COMMAND=\$1; shift ;;", installer_source(), re.M)
    return set(match.group(1).split("|"))


def load_copier():
    """The copier as a module, loaded from the path install.sh actually runs."""
    spec = importlib.util.spec_from_file_location("obsidian_skills_copier", COPIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root: Path) -> dict:
    """relative path -> (kind, digest-or-target, permission bits)."""
    state = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        for name in sorted(dirnames) + sorted(filenames):
            path = here / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                state[relative] = ("symlink", os.readlink(path), None)
            elif path.is_dir():
                state[relative] = ("dir", None, path.stat().st_mode & 0o777)
            elif not path.is_file():
                # A FIFO, socket or device node. Never read it: opening a FIFO
                # for reading blocks until somebody opens the write end.
                state[relative] = ("special", None, path.stat().st_mode & 0o777)
            else:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                state[relative] = ("file", digest, path.stat().st_mode & 0o777)
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
    return state


class InstallerHarness(unittest.TestCase):
    """Shared sandbox: a synthetic checkout plus an isolated HOME."""

    maxDiff = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obsidian-skills-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.tmpdir = self.tmp / "tmpdir"
        self.home.mkdir()
        self.tmpdir.mkdir()
        self.packages = declared_packages()

    # -- sandbox construction ------------------------------------------------
    def make_sandbox(self, skip_skill_md=()) -> Path:
        checkout = self.tmp / "checkout"
        (checkout / "skills").mkdir(parents=True)
        (checkout / "scripts").mkdir(parents=True)
        shutil.copy2(INSTALL_SH, checkout / "install.sh")
        os.chmod(checkout / "install.sh", 0o755)
        # install.sh resolves its copier from its own checkout, so a sandbox
        # checkout is only a checkout once the copier is in it too.
        shutil.copy2(COPIER, checkout / "scripts" / COPIER.name)
        for name in self.packages:
            self.make_package(checkout / "skills" / name, name, name in skip_skill_md)
        return checkout

    def make_package(self, root: Path, name: str, skip_skill_md: bool = False):
        (root / "references" / "nested").mkdir(parents=True)
        (root / "assets").mkdir()
        (root / "scripts").mkdir()
        if not skip_skill_md:
            (root / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Synthetic sandbox package.\n---\n\n"
                f"# {name}\n\nSee [guide](references/guide.md).\n",
                encoding="utf-8",
            )
        (root / "references" / "guide.md").write_text(f"# {name} guide\n", encoding="utf-8")
        (root / "references" / "nested" / "deep.md").write_text("nested\n", encoding="utf-8")
        (root / "assets" / "with space.json").write_text('{"synthetic": true}\n', encoding="utf-8")
        script = root / "scripts" / "tool.py"
        script.write_text("#!/usr/bin/env python3\nprint('synthetic')\n", encoding="utf-8")
        os.chmod(script, 0o755)

    # -- invocation ----------------------------------------------------------
    def run_installer(self, *args, checkout=None, cwd=None):
        script = (checkout or REPO) / "install.sh"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmpdir),
            "LC_ALL": "C",
        }
        self.assertNotEqual(env["HOME"], os.path.expanduser("~"), "HOME must be disposable")
        return subprocess.run(
            ["/bin/sh", str(script), *args],
            cwd=str(cwd or self.tmp),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def relax(self, path: Path):
        """Make a deliberately read-only directory removable again at teardown."""
        if path.is_dir():
            os.chmod(path, 0o755)

    def assert_refused(self, result, *needles):
        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        for needle in needles:
            self.assertIn(needle, result.stdout + result.stderr)

    def assert_usage_error(self, result):
        self.assertEqual(result.returncode, USAGE_ERROR, result.stdout + result.stderr)
        self.assertIn("USAGE ERROR", result.stderr)


class DocumentedSurfaceTest(InstallerHarness):
    """The help text and the implementation must describe the same surface."""

    def test_help_documents_every_option_the_parser_accepts(self):
        help_text = self.run_installer("--help").stdout
        options_block = help_text.split("OPTIONS", 1)[1].split("BEHAVIOUR", 1)[0]
        documented = set(re.findall(r"(?<![\w-])(--?[a-z][a-z-]*)", options_block))
        self.assertEqual(
            accepted_options() - documented, set(), "accepted but undocumented option"
        )
        self.assertEqual(
            documented - accepted_options(), set(), "documented but unaccepted option"
        )

    def test_help_documents_every_dispatchable_command(self):
        help_text = self.run_installer("--help").stdout
        commands_block = help_text.split("COMMANDS", 1)[1].split("OPTIONS", 1)[0]
        documented = set(re.findall(r"^  ([a-z]+)", commands_block, re.M))
        self.assertEqual(accepted_commands() - COMMAND_ALIASES, documented)

    def test_every_documented_option_is_accepted_at_runtime(self):
        checkout = self.make_sandbox()
        probes = {
            "--runtime": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                          "--scope", "user"],
            "--skill": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                        "--scope", "user"],
            "--scope": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                        "--scope", "user"],
            "--project-root": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                               "--scope", "project", "--project-root", str(self.tmp / "proj")],
            "--apply": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                        "--scope", "user", "--apply"],
            "--dry-run": ["copy", "--runtime", "cursor", "--skill", self.packages[0],
                          "--scope", "user", "--dry-run"],
            "--help": ["--help"],
            "-h": ["-h"],
        }
        (self.tmp / "proj").mkdir()
        for option, argv in probes.items():
            with self.subTest(option=option):
                result = self.run_installer(*argv, checkout=checkout)
                self.assertNotIn("unknown option", result.stderr)
                self.assertNotEqual(result.returncode, USAGE_ERROR, result.stderr)
            shutil.rmtree(self.home, ignore_errors=True)
            self.home.mkdir(exist_ok=True)

    def test_equals_form_of_every_value_option_is_accepted(self):
        checkout = self.make_sandbox()
        result = self.run_installer(
            "copy",
            "--runtime=cursor",
            f"--skill={self.packages[0]}",
            "--scope=user",
            checkout=checkout,
        )
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn("Dry run only", result.stdout)


class ReadOnlyCommandTest(InstallerHarness):
    """routes / skills / native report the real checkout without writing."""

    def test_no_arguments_prints_help_and_succeeds(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn("USAGE", result.stdout)

    def test_unknown_command_is_a_usage_error(self):
        self.assert_usage_error(self.run_installer("instal"))

    def test_option_before_command_is_a_usage_error(self):
        self.assert_usage_error(self.run_installer("--runtime", "cursor"))

    def test_routes_reports_every_known_runtime_and_its_kind(self):
        result = self.run_installer("routes")
        self.assertEqual(result.returncode, OK, result.stderr)
        for runtime, kind in route_kinds().items():
            with self.subTest(runtime=runtime):
                self.assertIn(runtime, result.stdout)
                self.assertIn(kind, result.stdout)

    def test_routes_reports_the_prerelease_status_and_the_one_verified_install(self):
        """The status line must not read as unreleased or as a blanket no-install."""
        result = self.run_installer("routes")
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertEqual(release_status(), "prerelease")
        self.assertIn("prerelease", result.stdout)
        self.assertNotIn("unreleased", result.stdout)
        self.assertIn("Claude Code only", result.stdout)
        self.assertIn("isolated project", result.stdout)
        self.assertIn("native installs remain unverified", result.stdout)
        self.assertIn("Cursor and Agent Skills have no native", result.stdout)
        self.assertIn("directory-copy behavior was tested separately", result.stdout)
        self.assertIn("Local-source routes require a clone pinned", result.stdout)

    def test_native_scopes_the_verified_install_to_claude_and_no_other_runtime(self):
        """Only claude may report a verified install; the rest stay unverified."""
        claude = self.run_installer("native", "--runtime", "claude")
        self.assertEqual(claude.returncode, OK, claude.stderr)
        self.assertIn("fresh-loaded", claude.stdout)
        self.assertIn("isolated project scope only", claude.stdout)
        self.assertIn("still unverified", claude.stdout)
        self.assertNotIn("Route confirmed is not install verified", claude.stdout)
        self.assertNotIn("No native route exists to verify", claude.stdout)

        kinds = route_kinds()
        for runtime in known_runtimes():
            if runtime == "claude":
                continue
            with self.subTest(runtime=runtime):
                result = self.run_installer("native", "--runtime", runtime)
                self.assertEqual(result.returncode, OK, result.stderr)
                self.assertNotIn("fresh-loaded", result.stdout)
                if kinds[runtime] == "skill-directory":
                    self.assertIn("No native route exists to verify", result.stdout)
                    self.assertNotIn(
                        "Route confirmed is not install verified", result.stdout
                    )
                else:
                    self.assertIn(
                        "Route confirmed is not install verified", result.stdout
                    )
                    self.assertNotIn("No native route exists to verify", result.stdout)

    def test_native_without_a_plugin_route_reports_directory_copy_only(self):
        """skill-directory runtimes have no native route to call verified at all."""
        bare = [r for r, k in route_kinds().items() if k == "skill-directory"]
        self.assertTrue(bare, "the route table must still declare a skill-directory kind")
        for runtime in bare:
            with self.subTest(runtime=runtime):
                result = self.run_installer("native", "--runtime", runtime)
                self.assertEqual(result.returncode, OK, result.stderr)
                self.assertIn("UNSUPPORTED", result.stdout)
                self.assertIn("No native route exists to verify", result.stdout)
                self.assertIn("only supported route", result.stdout)
                self.assertIn("a filesystem fact, not an", result.stdout)
                self.assertIn("is itself unverified", result.stdout)

    def test_native_marks_the_local_path_as_not_the_verified_pin(self):
        """A local marketplace source is this checkout, not the verified revision."""
        pin = release_pin()
        self.assertRegex(pin, r"^[0-9a-f]{40}$")
        offered = 0
        for runtime in known_runtimes():
            result = self.run_installer("native", "--runtime", runtime)
            self.assertEqual(result.returncode, OK, result.stderr)
            with self.subTest(runtime=runtime):
                if str(REPO) not in result.stdout:
                    # No local source was offered, so no pin caveat is claimed.
                    self.assertNotIn("not by itself the verified revision", result.stdout)
                    continue
                offered += 1
                self.assertIn("from a local checkout", result.stdout)
                self.assertIn("not by itself the verified revision", result.stdout)
                self.assertIn("checked out at the public", result.stdout)
                self.assertIn(pin, result.stdout)
                self.assertIn(
                    "A checkout at any other revision, or one carrying local",
                    result.stdout,
                )
        self.assertTrue(offered, "at least one runtime must offer a local source")

    def test_routes_resolves_user_directories_from_the_overridden_home(self):
        result = self.run_installer("routes")
        self.assertIn(str(self.home), result.stdout)
        self.assertNotIn(os.path.expanduser("~") + "/.claude", result.stdout)

    def test_routes_and_skills_reject_options(self):
        for argv in (["routes", "--runtime", "cursor"], ["skills", "--apply"]):
            with self.subTest(argv=argv):
                self.assert_usage_error(self.run_installer(*argv))

    def test_skills_reports_a_state_for_every_declared_package(self):
        result = self.run_installer("skills")
        self.assertEqual(result.returncode, OK, result.stderr)
        for name in self.packages:
            with self.subTest(package=name):
                self.assertRegex(result.stdout, rf"\[(present|BROKEN |absent )\] {name}\b")
        installable = len([n for n in self.packages if (REPO / "skills" / n / "SKILL.md").is_file()])
        self.assertIn(f"{installable} of {len(self.packages)}", result.stdout)

    def test_native_refuses_an_unknown_runtime_without_guessing(self):
        result = self.run_installer("native", "--runtime", "not-a-runtime")
        self.assert_refused(result, "REFUSED", "not-a-runtime")
        for runtime in known_runtimes():
            self.assertIn(runtime, result.stderr)

    def test_native_requires_a_runtime(self):
        self.assert_usage_error(self.run_installer("native"))

    def test_native_rejects_copy_only_options(self):
        for argv in (
            ["native", "--runtime", "claude", "--skill", "obsidian-markdown"],
            ["native", "--runtime", "claude", "--apply"],
            ["native", "--runtime", "claude", "--scope", "user"],
            ["native", "--runtime", "claude", "--project-root", "."],
        ):
            with self.subTest(argv=argv):
                self.assert_usage_error(self.run_installer(*argv))

    def test_native_reports_the_declared_route_kind_for_every_runtime(self):
        for runtime, kind in route_kinds().items():
            with self.subTest(runtime=runtime, kind=kind):
                result = self.run_installer("native", "--runtime", runtime)
                self.assertEqual(result.returncode, OK, result.stderr)
                self.assertIn(kind, result.stdout)
                # A printed command line is indented and starts with a binary.
                offered = re.findall(
                    r"^ {4,}(\S+) (?:plugin|skills) \S+", result.stdout, re.M
                )
                if kind == "skill-directory":
                    self.assertIn("UNSUPPORTED", result.stdout)
                    self.assertEqual(
                        offered, [], "a directory copy must not be offered as a plugin route"
                    )
                else:
                    self.assertNotIn("UNSUPPORTED", result.stdout)
                    self.assertTrue(offered, "a native route must print its own commands")

    def test_read_only_commands_write_nothing_into_the_disposable_home(self):
        before = snapshot(self.home)
        for argv in (["routes"], ["skills"], ["native", "--runtime", "claude"], ["--help"]):
            self.run_installer(*argv)
        self.assertEqual(snapshot(self.home), before)


class SelectionValidationTest(InstallerHarness):
    """Skill, scope and runtime validation happens before anything is planned."""

    def setUp(self):
        super().setUp()
        self.checkout = self.make_sandbox()

    def copy(self, *args):
        return self.run_installer("copy", *args, checkout=self.checkout)

    def test_illegal_skill_names_are_refused_as_path_escapes(self):
        illegal = [
            "../evil",
            "nested/name",
            "..",
            ".",
            "Obsidian-Markdown",
            "-leading",
            "trailing-",
            "double--dash",
            "under_score",
            "back\\slash",
            "a" * 65,
        ]
        for name in illegal:
            with self.subTest(skill=name):
                result = self.copy("--runtime", "cursor", "--skill", name, "--scope", "user")
                self.assert_refused(result, "REFUSED")
                self.assertFalse((self.home / ".cursor").exists())

    def test_undeclared_but_legal_skill_name_is_refused(self):
        result = self.copy("--runtime", "cursor", "--skill", "obsidian-unknown", "--scope", "user")
        self.assert_refused(result, "REFUSED", "obsidian-unknown")

    def test_unknown_runtime_is_refused_before_any_selection_work(self):
        result = self.copy("--runtime", "vscode", "--skill", "all", "--scope", "user")
        self.assert_refused(result, "REFUSED", "vscode")

    def test_missing_selection_or_scope_is_a_usage_error(self):
        for argv in (
            ["--runtime", "cursor", "--scope", "user"],
            ["--runtime", "cursor", "--skill", "all"],
            ["--skill", "all", "--scope", "user"],
        ):
            with self.subTest(argv=argv):
                self.assert_usage_error(self.copy(*argv))

    def test_invalid_scope_is_a_usage_error(self):
        result = self.copy("--runtime", "cursor", "--skill", "all", "--scope", "global")
        self.assert_usage_error(result)

    def test_option_without_its_value_is_a_usage_error(self):
        for option in ("--runtime", "--skill", "--scope", "--project-root"):
            with self.subTest(option=option):
                self.assert_usage_error(self.copy(option))

    def test_project_scope_refuses_a_root_that_does_not_exist(self):
        before = snapshot(self.tmp)
        result = self.copy(
            "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.tmp / "absent"),
        )
        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        self.assertFalse((self.tmp / "absent").exists(), "the root must not be created")
        self.assertEqual(snapshot(self.tmp), before)

    def test_a_missing_project_root_is_refused_out_loud(self):
        """A silent exit 1 would be indistinguishable from a crash.

        ``phys_dir`` must absorb its own failure; a bare
        ``_pr=$(phys_dir ...)`` under ``set -e`` kills the shell before the
        ``|| refuse ...`` message can run.
        """
        result = self.copy(
            "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.tmp / "absent"),
        )
        self.assert_refused(result, "REFUSED", "absent")

    def test_an_explicitly_empty_project_root_is_a_usage_error(self):
        """'' names no destination, and must not quietly become the cwd.

        Treating an empty value as "not given" left PROJECT_ROOT at its default,
        so ``--scope project --project-root '' --apply`` wrote into whatever
        directory the command happened to run from.
        """
        for form in (["--project-root", ""], ["--project-root="]):
            with self.subTest(form=" ".join(form)):
                before = snapshot(self.tmp)
                result = self.run_installer(
                    "copy", "--runtime", "cursor", "--skill", "all",
                    "--scope", "project", *form, "--apply",
                    checkout=self.checkout, cwd=self.tmp,
                )
                self.assert_usage_error(result)
                self.assertFalse((self.tmp / ".cursor").exists(), "the cwd was used as a root")
                self.assertEqual(snapshot(self.tmp), before, "nothing may be written")

    def test_project_root_is_rejected_for_user_scope(self):
        result = self.copy(
            "--runtime", "cursor", "--skill", "all",
            "--scope", "user", "--project-root", str(self.tmp),
        )
        self.assert_usage_error(result)

    def test_all_cannot_be_mixed_with_named_packages(self):
        result = self.copy(
            "--runtime", "cursor", "--skill", "all", "--skill", self.packages[0],
            "--scope", "user",
        )
        self.assert_usage_error(result)

    def test_an_exact_option_given_twice_with_different_values_is_refused(self):
        for option, values in (
            ("--runtime", ("cursor", "claude")),
            ("--scope", ("user", "project")),
            ("--project-root", (str(self.tmp), str(self.tmp / "other"))),
        ):
            with self.subTest(option=option):
                argv = ["--runtime", "cursor", "--skill", "all", "--scope", "user"]
                argv += [option, values[0], option, values[1]]
                self.assert_usage_error(self.copy(*argv))

    def test_an_exact_option_repeated_with_the_same_value_is_accepted(self):
        result = self.copy(
            "--runtime", "cursor", "--runtime", "cursor",
            "--skill", self.packages[0], "--scope", "user",
        )
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)

    def test_project_scope_refuses_the_checkout_itself(self):
        result = self.copy(
            "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.checkout),
        )
        self.assert_refused(result, "REFUSED")
        self.assertFalse((self.checkout / ".cursor").exists())

    def test_repeated_selection_of_one_package_is_deduplicated(self):
        name = self.packages[0]
        result = self.copy(
            "--runtime", "cursor", "--skill", name, "--skill", name, "--scope", "user"
        )
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn("1 copyable, 0 refused.", result.stdout)

    def test_all_selects_every_declared_package(self):
        result = self.copy("--runtime", "cursor", "--skill", "all", "--scope", "user")
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn(f"{len(self.packages)} copyable, 0 refused.", result.stdout)

    def test_a_package_without_skill_md_is_reported_missing_and_blocks_the_run(self):
        broken = self.packages[2]
        checkout = self.tmp / "broken-checkout"
        shutil.copytree(self.checkout, checkout)
        (checkout / "skills" / broken / "SKILL.md").unlink()
        result = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user", "--apply",
            checkout=checkout,
        )
        self.assert_refused(result, "MISSING", broken)
        self.assertFalse((self.home / ".cursor").exists(), "nothing may be written")


class DryRunTest(InstallerHarness):
    """Dry run is the default and never touches the filesystem."""

    def setUp(self):
        super().setUp()
        self.checkout = self.make_sandbox()

    def test_default_run_writes_nothing_and_says_so(self):
        before = snapshot(self.home)
        result = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user",
            checkout=self.checkout,
        )
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse((self.home / ".cursor").exists())

    def test_explicit_dry_run_flag_matches_the_default(self):
        default = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user",
            checkout=self.checkout,
        )
        explicit = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user", "--dry-run",
            checkout=self.checkout,
        )
        self.assertEqual(default.stdout, explicit.stdout)
        self.assertEqual(snapshot(self.home), {})

    def test_apply_combined_with_dry_run_is_a_usage_error_in_either_order(self):
        """Letting the last flag win would make writing depend on argument order."""
        before = snapshot(self.home)
        for tail in (("--apply", "--dry-run"), ("--dry-run", "--apply")):
            with self.subTest(order=tail):
                result = self.run_installer(
                    "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user",
                    *tail, checkout=self.checkout,
                )
                self.assert_usage_error(result)
                self.assertEqual(snapshot(self.home), before)

    def test_dry_run_reports_collisions_without_resolving_them(self):
        target = self.home / ".cursor" / "skills"
        target.mkdir(parents=True)
        occupied = target / self.packages[0]
        occupied.mkdir()
        (occupied / "keep.md").write_text("user content\n", encoding="utf-8")
        before = snapshot(self.home)

        result = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all", "--scope", "user",
            checkout=self.checkout,
        )
        self.assert_refused(result, "COLLISION", self.packages[0])
        self.assertEqual(snapshot(self.home), before)


class ApplyTest(InstallerHarness):
    """--apply copies whole packages and leaves everything else alone."""

    def setUp(self):
        super().setUp()
        self.checkout = self.make_sandbox()

    def apply(self, *args, **kwargs):
        return self.run_installer("copy", *args, "--apply", checkout=self.checkout, **kwargs)

    def test_every_runtime_applies_only_below_its_documented_project_route(self):
        routes = {"claude": ".claude/skills", "codex": ".agents/skills",
                  "gjc": ".gjc/skills", "grok": ".grok/skills",
                  "hermes": ".hermes/skills", "cursor": ".cursor/skills",
                  "agent-skills": ".agents/skills"}
        self.assertEqual(set(routes), set(known_runtimes()))
        for runtime, route in routes.items():
            with self.subTest(runtime=runtime):
                project = self.tmp / ("consumer-" + runtime)
                project.mkdir()
                config = project / "settings.json"
                config.write_text('{"preserve":true}')
                result = self.apply("--runtime", runtime, "--skill", self.packages[0],
                                    "--scope", "project", "--project-root", str(project))
                self.assertEqual(result.returncode, OK, result.stderr)
                self.assertEqual(snapshot(project / route / self.packages[0]),
                                 snapshot(self.checkout / "skills" / self.packages[0]))
                self.assertEqual(config.read_text(), '{"preserve":true}')

    def test_apply_copies_the_complete_package_tree_byte_for_byte(self):
        name = self.packages[0]
        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assertEqual(result.returncode, OK, result.stderr)

        source = self.checkout / "skills" / name
        destination = self.home / ".cursor" / "skills" / name
        self.assertTrue(destination.is_dir())
        self.assertEqual(snapshot(destination), snapshot(source))

    def test_apply_creates_only_the_destination_root_it_announced(self):
        name = self.packages[0]
        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        created = set(snapshot(self.home))
        self.assertIn("created", result.stdout)
        expected_roots = {".cursor", ".cursor/skills", f".cursor/skills/{name}"}
        self.assertTrue(expected_roots.issubset(created))
        outside = {path for path in created if not path.startswith(".cursor")}
        self.assertEqual(outside, set())

    def test_apply_selects_only_the_named_packages(self):
        chosen = self.packages[:2]
        self.apply(
            "--runtime", "cursor",
            "--skill", chosen[0], "--skill", chosen[1],
            "--scope", "user",
        )
        installed = sorted(p.name for p in (self.home / ".cursor" / "skills").iterdir())
        self.assertEqual(installed, sorted(chosen))

    def test_one_collision_refuses_the_whole_selection(self):
        first, second = self.packages[0], self.packages[1]
        root = self.home / ".cursor" / "skills"
        root.mkdir(parents=True)
        (root / first).mkdir()
        (root / first / "user.md").write_text("do not touch\n", encoding="utf-8")
        before = snapshot(self.home)

        result = self.apply(
            "--runtime", "cursor", "--skill", first, "--skill", second, "--scope", "user"
        )
        self.assert_refused(result, "COLLISION")
        self.assertEqual(snapshot(self.home), before, "partial application is forbidden")
        self.assertFalse((root / second).exists(), "the clean package must not be copied")

    def test_a_plain_file_at_a_destination_is_a_collision(self):
        name = self.packages[0]
        root = self.home / ".cursor" / "skills"
        root.mkdir(parents=True)
        (root / name).write_text("a file, not a package\n", encoding="utf-8")
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assert_refused(result, "COLLISION")
        self.assertEqual(snapshot(self.home), before)

    def test_a_symlink_at_a_destination_is_refused_and_its_target_untouched(self):
        name = self.packages[0]
        root = self.home / ".cursor" / "skills"
        root.mkdir(parents=True)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "user.md").write_text("owned by the user\n", encoding="utf-8")
        (root / name).symlink_to(elsewhere)
        before_home = snapshot(self.home)
        before_target = snapshot(elsewhere)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assert_refused(result, "COLLISION", "symlink")
        self.assertEqual(snapshot(self.home), before_home)
        self.assertEqual(snapshot(elsewhere), before_target)
        self.assertEqual(sorted(p.name for p in elsewhere.iterdir()), ["user.md"])

    def test_a_dangling_symlink_at_a_destination_is_refused(self):
        name = self.packages[0]
        root = self.home / ".cursor" / "skills"
        root.mkdir(parents=True)
        (root / name).symlink_to(self.tmp / "never-created")
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assert_refused(result, "COLLISION", "dangling symlink")
        self.assertEqual(snapshot(self.home), before)
        self.assertTrue((root / name).is_symlink())
        self.assertFalse((root / name).exists())

    def test_a_destination_root_occupied_by_a_file_is_refused(self):
        name = self.packages[0]
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor" / "skills").write_text("not a directory\n", encoding="utf-8")
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        self.assertEqual(snapshot(self.home), before)

    def test_a_symlinked_destination_root_is_refused_and_left_untouched(self):
        """A symlinked root escapes the approved root, so it must be refused.

        Resolving the root and the destination's parent separately makes the two
        agree on the link *target*: both become ``physical``, containment passes,
        and the write lands outside the directory the user named. The approved
        root for ``--scope user`` is HOME, so a link out of HOME is an escape
        however consistently it resolves.
        """
        name = self.packages[0]
        physical = self.tmp / "physical-skills"
        physical.mkdir()
        (physical / "owned-by-someone-else.md").write_text("keep\n", encoding="utf-8")
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor" / "skills").symlink_to(physical)
        before_home = snapshot(self.home)
        before_target = snapshot(physical)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assert_refused(result, "REFUSED", "symlink")
        self.assertFalse((physical / name).exists(), "the write escaped the approved root")
        self.assertEqual(snapshot(physical), before_target, "the link target was modified")
        self.assertEqual(snapshot(self.home), before_home)
        self.assertTrue(
            (self.home / ".cursor" / "skills").is_symlink(),
            "the pre-existing link must be preserved, not replaced",
        )
        self.assertEqual(
            os.readlink(self.home / ".cursor" / "skills"), str(physical),
            "the link target must not be rewritten",
        )

    def test_an_intermediate_symlink_on_the_route_is_refused(self):
        """The escape can sit above the skill root, not only at it."""
        name = self.packages[0]
        outside = self.tmp / "outside-home"
        (outside / "skills").mkdir(parents=True)
        (outside / "skills" / "neighbour.md").write_text("not ours\n", encoding="utf-8")
        (self.home / ".cursor").symlink_to(outside)
        before_home = snapshot(self.home)
        before_outside = snapshot(outside)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assert_refused(result, "REFUSED", "symlink")
        self.assertFalse((outside / "skills" / name).exists())
        self.assertEqual(snapshot(outside), before_outside)
        self.assertEqual(snapshot(self.home), before_home)
        self.assertTrue((self.home / ".cursor").is_symlink())

    def test_a_symlinked_route_component_is_refused_even_when_it_points_inside(self):
        """Fail closed: the rule is 'no symlink below the approved root'.

        Allowing a link whose target happens to resolve inside would make the
        decision depend on a value the link's owner controls, and a link can be
        repointed between the check and the write.
        """
        name = self.packages[0]
        inside = self.home / "real-skills"
        inside.mkdir()
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor" / "skills").symlink_to(inside)
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assert_refused(result, "REFUSED", "symlink")
        self.assertEqual(snapshot(self.home), before)

    def test_a_project_scope_symlinked_route_is_refused(self):
        """The approved root for project scope is --project-root, not its links."""
        name = self.packages[0]
        project = self.tmp / "consumer-project"
        project.mkdir()
        escape = self.tmp / "escape-target"
        escape.mkdir()
        (project / ".cursor").mkdir()
        (project / ".cursor" / "skills").symlink_to(escape)
        before_escape = snapshot(escape)

        result = self.apply(
            "--runtime", "cursor", "--skill", name,
            "--scope", "project", "--project-root", str(project),
        )

        self.assert_refused(result, "REFUSED", "symlink")
        self.assertEqual(snapshot(escape), before_escape)
        self.assertFalse((escape / name).exists())

    def test_generated_caches_are_never_shipped_into_a_destination(self):
        """__pycache__ and friends are build residue, not package content."""
        name = self.packages[0]
        source = self.checkout / "skills" / name
        cache = source / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "tool.cpython-314.pyc").write_bytes(b"\x00compiled\n")
        (source / ".DS_Store").write_bytes(b"\x00finder\n")
        source_before = snapshot(source)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)

        destination = self.home / ".cursor" / "skills" / name
        shipped = sorted(snapshot(destination))
        self.assertNotIn("scripts/__pycache__", shipped)
        self.assertNotIn(".DS_Store", shipped)
        self.assertEqual(
            [p for p in shipped if p.endswith(".pyc")], [], "a compiled cache was shipped"
        )
        self.assertTrue((destination / "SKILL.md").is_file(), "real content must still arrive")
        self.assertEqual(
            snapshot(source), source_before, "the checkout's own cache must be left alone"
        )

    def test_an_unreadable_member_rolls_back_only_its_own_package(self):
        """Partial failure must not leave a half-copied package loadable."""
        good, broken = self.packages[0], self.packages[1]
        locked = self.checkout / "skills" / broken / "references" / "nested"
        os.chmod(locked, 0o000)
        self.addCleanup(os.chmod, locked, 0o755)

        result = self.apply(
            "--runtime", "cursor", "--skill", good, "--skill", broken, "--scope", "user"
        )

        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        self.assertIn("Stopped after", result.stdout)
        root = self.home / ".cursor" / "skills"
        self.assertTrue((root / good / "SKILL.md").is_file(), "a verified package must be kept")
        self.assertFalse((root / broken).exists(), "the failed package must be rolled back")
        self.assertEqual(sorted(p.name for p in root.iterdir()), [good])

    def test_a_readback_failure_rolls_back_the_reservation(self):
        """An entry the readback cannot prove identical is a failure, not a pass."""
        name = self.packages[0]
        fifo = self.checkout / "skills" / name / "pipe"
        os.mkfifo(fifo)
        self.addCleanup(fifo.unlink, missing_ok=True)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        self.assertIn("readback failed", result.stdout)
        root = self.home / ".cursor" / "skills"
        self.assertFalse((root / name).exists(), "an unverified package must not survive")
        self.assertEqual(list(root.iterdir()), [])

    def test_a_destination_root_that_cannot_be_reserved_writes_nothing(self):
        """A reservation that fails with no claimant is reported, not guessed at."""
        name = self.packages[0]
        root = self.home / ".cursor" / "skills"
        root.mkdir(parents=True)
        os.chmod(root, stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, root, 0o755)
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assertEqual(result.returncode, REFUSED, result.stdout + result.stderr)
        self.assertIn("NO RESERVE", result.stdout)
        self.assertEqual(snapshot(self.home), before)

    def test_a_cache_under_a_read_only_source_directory_is_never_shipped(self):
        """Nothing generated is copied, so no prune step can fail unnoticed.

        The cache sits in a source directory the destination must reproduce as
        read-only. Copying it and pruning afterwards would leave the residue in
        place -- and the readback used to exclude exactly those paths, so it
        would have reported success over it.
        """
        name = self.packages[0]
        source = self.checkout / "skills" / name
        cache = source / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "tool.cpython-314.pyc").write_bytes(b"\x00compiled\n")
        os.chmod(source / "scripts", 0o555)
        self.addCleanup(os.chmod, source / "scripts", 0o755)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")
        destination = self.home / ".cursor" / "skills" / name
        self.addCleanup(self.relax, destination / "scripts")

        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        shipped = snapshot(destination)
        self.assertNotIn("scripts/__pycache__", shipped)
        self.assertEqual([p for p in shipped if p.endswith(".pyc")], [])
        self.assertEqual(shipped["scripts"][2], 0o555, "source permissions must be reproduced")
        self.assertTrue((destination / "SKILL.md").is_file(), "real content must still arrive")

    def test_a_symlinked_source_package_is_refused(self):
        """A linked package is not this checkout's content, so it is not copied."""
        name, other = self.packages[0], self.packages[1]
        source = self.checkout / "skills" / name
        shutil.rmtree(source)
        source.symlink_to(self.checkout / "skills" / other)
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assert_refused(result, "SRC LINK", "symlink")
        self.assertEqual(snapshot(self.home), before, "nothing may be written")
        self.assertTrue(source.is_symlink(), "the link must be left exactly as it is")

    def test_copy_refuses_when_its_copier_is_missing_instead_of_falling_back(self):
        """There is no unanchored fallback to fall back to."""
        name = self.packages[0]
        (self.checkout / "scripts" / COPIER.name).unlink()
        before = snapshot(self.home)

        result = self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assert_refused(result, "REFUSED", "copier is missing")
        self.assertEqual(snapshot(self.home), before, "nothing may be written")

    def test_project_scope_writes_only_under_the_named_project_root(self):
        name = self.packages[0]
        project = self.tmp / "consumer"
        (project / "notes").mkdir(parents=True)
        (project / "notes" / "keep.md").write_text("user note\n", encoding="utf-8")
        home_before = snapshot(self.home)

        result = self.apply(
            "--runtime", "cursor", "--skill", name,
            "--scope", "project", "--project-root", str(project),
        )
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertTrue((project / ".cursor" / "skills" / name / "SKILL.md").is_file())
        self.assertEqual((project / "notes" / "keep.md").read_text("utf-8"), "user note\n")
        self.assertEqual(snapshot(self.home), home_before, "user scope must stay untouched")

    def test_apply_never_writes_outside_the_destination_root(self):
        name = self.packages[0]
        neighbour = self.tmp / "neighbour"
        neighbour.mkdir()
        (neighbour / "untouched.md").write_text("neighbour\n", encoding="utf-8")
        checkout_before = snapshot(self.checkout)
        neighbour_before = snapshot(neighbour)

        self.apply("--runtime", "cursor", "--skill", name, "--scope", "user")

        self.assertEqual(snapshot(self.checkout), checkout_before, "source must not change")
        self.assertEqual(snapshot(neighbour), neighbour_before)


class CopierAnchoringTest(unittest.TestCase):
    """The copier's anchoring and rollback guarantees, driven directly.

    These are the branches a concurrent process reaches: a route component
    replaced between the check and the create, a reservation renamed away after
    its content was verified, content planted inside a reservation, a
    destination claimed before the reservation could take it. From outside the
    process they can only be reached by racing the copy -- which is exactly what
    made the previous test skip itself whenever it lost. Calling the copier's own
    functions puts the interference between the two calls it belongs between,
    with no hook in the shipped program and no timing dependency at all.
    """

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.copier = load_copier()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obsidian-skills-copier-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.anchor = self.tmp / "anchor"
        self.anchor.mkdir()

    # -- fixtures ------------------------------------------------------------
    def open_dir(self, path: Path) -> int:
        fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, fd)
        return fd

    def make_source(self) -> Path:
        source = self.tmp / "source"
        (source / "references").mkdir(parents=True)
        (source / "SKILL.md").write_text("---\nname: pkg\n---\n", encoding="utf-8")
        (source / "references" / "guide.md").write_text("guide\n", encoding="utf-8")
        return source

    def reserve(self, root: Path, name: str):
        """Claim and hold a reservation exactly as ``install_one`` does."""
        root_fd = self.open_dir(root)
        os.mkdir(name, 0o700, dir_fd=root_fd)
        reservation_fd = self.copier.open_dir_at(name, root_fd)
        self.addCleanup(os.close, reservation_fd)
        return root_fd, reservation_fd, self.copier.ident(os.fstat(reservation_fd))

    def filled_reservation(self):
        """A complete reservation, ready for somebody else to interfere with."""
        root = self.anchor / "skills"
        root.mkdir()
        source_fd = self.open_dir(self.make_source())
        root_fd, reservation_fd, reservation_ident = self.reserve(root, "pkg")
        created = []
        self.copier.copy_tree(source_fd, reservation_fd, "", created, [])
        self.assertTrue((root / "pkg" / "SKILL.md").is_file(), "the copy must have landed")
        return root, root_fd, source_fd, reservation_fd, reservation_ident, created

    # -- the branches --------------------------------------------------------
    def test_creating_the_route_refuses_a_component_that_became_a_symlink(self):
        """The create walks handles, so a swapped component cannot redirect it."""
        outside = self.tmp / "outside"
        outside.mkdir()
        (self.anchor / ".cursor").mkdir()
        anchor_fd = self.open_dir(self.anchor)
        route = [".cursor", "skills"]

        root_fd, _made = self.copier.open_route(anchor_fd, route, str(self.anchor), create=False)
        self.assertIsNone(root_fd, "the destination root must still be missing")

        # Between the check and the create, the checked component is replaced.
        (self.anchor / ".cursor").rmdir()
        (self.anchor / ".cursor").symlink_to(outside)

        with self.assertRaises(self.copier.Refused) as caught:
            self.copier.open_route(anchor_fd, route, str(self.anchor), create=True)

        self.assertIn("symlink", str(caught.exception))
        self.assertFalse((outside / "skills").exists(), "the create followed a swapped link")
        self.assertTrue((self.anchor / ".cursor").is_symlink(), "the link must be left as it is")

    def test_a_reservation_replaced_after_the_copy_is_reported_not_deleted(self):
        """A foreign directory at the published name is reported, never removed.

        The readback still passes here -- it reads the reservation through the
        handle this run holds -- so the only thing that can catch the swap is
        comparing the published name against that handle's identity. A recursive
        delete of the path would destroy somebody else's directory.
        """
        root, root_fd, _src, reservation_fd, reservation_ident, created = self.filled_reservation()
        marker = "FOREIGN CONTENT, NOT OURS TO DELETE\n"
        (root / "pkg").rename(root / "stolen")
        (root / "pkg").mkdir()
        (root / "pkg" / "foreign.md").write_text(marker, encoding="utf-8")

        emptied = self.copier.rollback(reservation_fd, created)
        outcome = self.copier.release_reservation(root_fd, "pkg", reservation_ident, emptied)

        self.assertTrue(emptied, "this run's own entries stay reachable through the handle")
        self.assertEqual(outcome, "replaced")
        self.assertEqual(sorted(p.name for p in (root / "pkg").iterdir()), ["foreign.md"])
        self.assertEqual((root / "pkg" / "foreign.md").read_text("utf-8"), marker)
        self.assertEqual(
            sorted(p.name for p in (root / "stolen").iterdir()), [],
            "an unverified copy must not survive under any name",
        )

    def test_content_planted_in_a_reservation_stops_the_rollback(self):
        """Only recorded entries are removed, so planted content survives."""
        root, root_fd, _src, reservation_fd, reservation_ident, created = self.filled_reservation()
        marker = "SOMEBODY ELSE WROTE THIS\n"
        (root / "pkg" / "planted.md").write_text(marker, encoding="utf-8")

        emptied = self.copier.rollback(reservation_fd, created)
        outcome = self.copier.release_reservation(root_fd, "pkg", reservation_ident, emptied)

        self.assertTrue(emptied, "recorded entries must still be removed")
        self.assertEqual(outcome, "left-behind")
        self.assertEqual(
            sorted(p.name for p in (root / "pkg").iterdir()), ["planted.md"],
            "planted content must survive and this run's copy must not",
        )
        self.assertEqual((root / "pkg" / "planted.md").read_text("utf-8"), marker)

    def test_a_destination_claimed_before_the_reservation_is_left_untouched(self):
        """Atomic no-replace publication never merges into a claimed path."""
        root = self.anchor / "skills"
        root.mkdir()
        root_fd = self.open_dir(root)
        claimed = root / "pkg"
        claimed.mkdir()
        marker = "FOREIGN CONTENT, NOT OURS TO DELETE\n"
        (claimed / "foreign.md").write_text(marker, encoding="utf-8")
        source_fd = self.open_dir(self.make_source())

        reported = io.StringIO()
        with contextlib.redirect_stdout(reported):
            published, reason = self.copier.install_one(
                root_fd, "pkg", source_fd, os.fstat(source_fd), str(claimed)
            )

        self.assertFalse(published)
        self.assertIn("claimed by something else", reason)
        self.assertIn("NOT OURS", reported.getvalue())
        self.assertEqual(sorted(p.name for p in claimed.iterdir()), ["foreign.md"])
        self.assertEqual((claimed / "foreign.md").read_text("utf-8"), marker)

    def test_public_name_is_absent_until_verified_atomic_publication(self):
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        publish = self.copier.publish_exclusive

        def inspect_then_publish(fd, staged, name):
            self.assertFalse((self.anchor / name).exists())
            self.assertEqual((self.anchor / staged / "SKILL.md").read_bytes(),
                             (self.tmp / "source" / "SKILL.md").read_bytes())
            publish(fd, staged, name)

        with patch.object(self.copier, "publish_exclusive", inspect_then_publish):
            with contextlib.redirect_stdout(io.StringIO()):
                success, reason = self.copier.install_one(
                    root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertTrue(success, reason)
        self.assertEqual(sorted(p.name for p in self.anchor.iterdir()), ["pkg"])

    def test_inner_source_symlink_cannot_export_foreign_content(self):
        source = self.make_source()
        foreign = self.tmp / "foreign.md"
        foreign.write_text("do not export")
        (source / "references" / "link.md").symlink_to(foreign)
        root_fd, source_fd = self.open_dir(self.anchor), self.open_dir(source)
        with contextlib.redirect_stdout(io.StringIO()):
            success, reason = self.copier.install_one(
                root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertFalse(success)
        self.assertIn("source symlink", reason)
        self.assertFalse((self.anchor / "pkg").exists())
        self.assertEqual(foreign.read_text(), "do not export")

    def test_publication_failure_quarantines_staging_without_public_write(self):
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        with patch.object(self.copier, "publish_exclusive", side_effect=OSError("unavailable")):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                success, reason = self.copier.install_one(
                    root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertFalse(success)
        self.assertIn("exclusive publication failed", reason)
        self.assertIn("LEFT BEHIND", output.getvalue())
        self.assertFalse((self.anchor / "pkg").exists())
        staging = list(self.anchor.iterdir())
        self.assertEqual(len(staging), 1)
        self.assertFalse((staging[0] / "SKILL.md").exists())
        self.assertTrue((staging[0] / "SKILL.unpublished").is_file())

    def test_interruption_before_publication_quarantines_retained_staging(self):
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        with patch.object(self.copier, "publish_exclusive", side_effect=self.copier.Interrupted(15)):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(self.copier.Interrupted):
                    self.copier.install_one(
                        root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertFalse((self.anchor / "pkg").exists())
        self.assertFalse(list(self.anchor.glob("*/SKILL.md")))

    def test_interruption_cannot_publish_partial_package(self):
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        with patch.object(self.copier, "copy_tree", side_effect=self.copier.Interrupted(15)):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(self.copier.Interrupted):
                    self.copier.install_one(
                        root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertFalse((self.anchor / "pkg").exists())
        self.assertIn("private staging rolled back", output.getvalue())

    def test_interrupted_copy_quarantines_staging_when_cleanup_is_incomplete(self):
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        copy = self.copier.copy_tree

        def copy_then_interrupt(*args):
            copy(*args)
            raise self.copier.Interrupted(15)

        with patch.object(self.copier, "copy_tree", side_effect=copy_then_interrupt):
            with patch.object(self.copier, "rollback", return_value=False):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    with self.assertRaises(self.copier.Interrupted):
                        self.copier.install_one(
                            root_fd, "pkg", source_fd, os.fstat(source_fd), str(self.anchor / "pkg"))
        self.assertFalse((self.anchor / "pkg").exists())
        staging = list(self.anchor.iterdir())
        self.assertEqual(len(staging), 1)
        self.assertFalse((staging[0] / "SKILL.md").exists())
        self.assertTrue((staging[0] / "SKILL.unpublished").exists())
        self.assertIn("private staging retained", output.getvalue())

    def test_incomplete_cleanup_names_the_staging_it_actually_retained(self):
        """Cleanup that cannot finish leaves staging, so staging is what is named.

        Nothing is published before the readback passes, so the public
        destination either does not exist or was created by somebody else.
        Naming it as the thing to remove points at nothing or at another
        process's directory, while the copied content that really survives goes
        unnamed and stays callable.
        """
        from unittest.mock import patch
        root_fd = self.open_dir(self.anchor)
        source_fd = self.open_dir(self.make_source())
        destination = self.anchor / "pkg"
        failed = self.copier.VerifyFailed("content differs at SKILL.md")

        # An incomplete rollback is the one outcome that keeps copied content.
        with patch.object(self.copier, "verify_package", side_effect=failed):
            with patch.object(self.copier, "rollback", return_value=False):
                with contextlib.redirect_stdout(io.StringIO()) as reported:
                    published, reason = self.copier.install_one(
                        root_fd, "pkg", source_fd, os.fstat(source_fd), str(destination))

        self.assertFalse(published)
        self.assertIn("readback failed", reason)
        self.assertFalse(destination.exists(), "nothing may be published")

        retained = list(self.anchor.iterdir())
        self.assertEqual(len(retained), 1, retained)
        staging = retained[0]
        self.assertTrue(staging.name.startswith(".obsidian-stage-"), staging.name)
        self.assertFalse((staging / "SKILL.md").exists(),
                         "retained staging must not stay callable")
        self.assertTrue((staging / "SKILL.unpublished").is_file())

        named = [line for line in reported.getvalue().splitlines() if "LEFT BEHIND" in line]
        self.assertEqual(len(named), 1, reported.getvalue())
        self.assertEqual(named[0].split()[:3], ["LEFT", "BEHIND", staging.name],
                         "the report must name what survived")
        self.assertIn("nothing was published to %s" % destination, named[0])

    def test_the_readback_rejects_a_generated_entry_in_the_destination(self):
        """Caches are never copied, so one in the destination is a failure.

        The old readback excluded exactly these paths on both sides, so residue
        a failed prune left behind could not make it disagree with itself.
        """
        root, _root_fd, source_fd, reservation_fd, _ident, _created = self.filled_reservation()
        cache = root / "pkg" / "__pycache__"
        cache.mkdir()
        (cache / "tool.cpython-314.pyc").write_bytes(b"\x00compiled\n")

        with self.assertRaises(self.copier.VerifyFailed) as caught:
            self.copier.verify_package(source_fd, reservation_fd)

        self.assertIn("unexpected entry", str(caught.exception))
        self.assertIn("__pycache__", str(caught.exception))


class CopierEntryPointTest(unittest.TestCase):
    """The copier's own entry point: its startup gates and its signal report.

    Both branches sit outside the package loop -- one before any package work is
    possible, one after the run has already stopped -- so they are driven
    through ``main`` itself. Signalling a subprocess would decide by timing
    which branch was taken; here the state that follows is the evidence.
    """

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.copier = load_copier()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obsidian-skills-copier-main-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "checkout"
        self.source = self.repo / "skills"
        (self.source / "pkg").mkdir(parents=True)
        (self.source / "pkg" / "SKILL.md").write_text(
            "---\nname: pkg\n---\n", encoding="utf-8")
        self.anchor = self.tmp / "anchor"
        self.anchor.mkdir()
        # main() installs its own INT/TERM handlers; the suite gets its own back.
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous = signal.getsignal(signum)
            if previous is not None:
                self.addCleanup(signal.signal, signum, previous)

    def argv(self):
        return [
            "--repo", str(self.repo),
            "--source", str(self.source),
            "--anchor", str(self.anchor),
            "--anchor-kind", "project",
            "--route", ".cursor/skills",
            "--scope", "project",
            "--runtime", "cursor",
            "--label", "Cursor",
            "--kind", "skill-directory",
            "--prog", "install.sh",
            "--package", "obsidian-skills",
            "--mode", "apply",
            "pkg",
        ]

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = self.copier.main(argv)
        return status, out.getvalue(), err.getvalue()

    def assert_nothing_was_written(self):
        self.assertEqual(list(self.anchor.iterdir()), [],
                         "a refusal before the run may not create the route")
        self.assertFalse((self.anchor / ".cursor").exists())

    # -- startup gates -------------------------------------------------------
    def test_a_platform_without_anchored_calls_refuses_before_writing(self):
        """Without dir_fd-anchored calls there is no safe copy, so none starts."""
        from unittest.mock import patch
        unreached = AssertionError("publication must not be reached")
        with patch.object(self.copier, "O_DIRECTORY", 0), \
                patch.object(self.copier, "publish_exclusive", side_effect=unreached):
            status, _out, err = self.run_main(self.argv())

        self.assertEqual(status, REFUSED)
        self.assertIn("REFUSED:", err)
        self.assertIn("directory handles", err)
        self.assert_nothing_was_written()

    def test_a_missing_publication_primitive_refuses_before_writing(self):
        """The atomic no-replace rename is resolved before any destination work.

        Resolving it late would mean a route created, a reservation filled and a
        readback passed before the run discovered it cannot publish safely.
        """
        from unittest.mock import patch
        unavailable = OSError("atomic no-replace publication is unavailable")
        unreached = AssertionError("publication must not be reached")
        with patch.object(self.copier, "publication_primitive", side_effect=unavailable), \
                patch.object(self.copier, "publish_exclusive", side_effect=unreached):
            status, _out, err = self.run_main(self.argv())

        self.assertEqual(status, REFUSED)
        self.assertIn("atomic no-replace publication is unavailable", err)
        self.assert_nothing_was_written()

    # -- the interrupted-run report ------------------------------------------
    def test_a_signal_reports_what_may_remain_instead_of_a_clean_rollback(self):
        """The handler main() installs turns a real signal into the exit report.

        The report has to survive on its own: by the time it is printed the run
        cannot know whether cleanup finished, and packages published earlier in
        the same run are still published.
        """
        from unittest.mock import patch

        def signalled_run(_args):
            os.kill(os.getpid(), signal.SIGTERM)
            raise AssertionError("SIGTERM did not stop the run")

        with patch.object(self.copier, "run", signalled_run):
            status, _out, err = self.run_main(self.argv())

        self.assertEqual(status, 128 + signal.SIGTERM)
        self.assertIn("interrupted by signal %d" % signal.SIGTERM, err)
        self.assertIn("complete packages may remain published", err)
        self.assertIn("cleanup may be incomplete", err)
        self.assertNotIn("rolled back", err)


class DisposableRollbackTest(InstallerHarness):
    """Simulation evidence only, per docs/cutover.md.

    A disposable consumer project is created from the synthetic neutral vault,
    a copy is applied into it, the exact previous configuration revision is
    restored, and the packages the installer created are removed. The vault must
    return to its exact pre-install state without any note being rewritten.
    This exercises pointer restoration and non-target preservation; it is not a
    canary, a deployment, or evidence about a real vault.
    """

    def setUp(self):
        super().setUp()
        self.checkout = self.make_sandbox()
        self.fixture = json.loads(FIXTURE.read_text("utf-8"))
        self.vault = self.tmp / "neutral-vault"
        vault_spec = self.fixture["vault"]
        for relative, content in vault_spec["files"].items():
            path = self.vault / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.config = self.vault / vault_spec["config"]["path"]
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.approved = vault_spec["config"]["approved_revision"]
        self.drifted = vault_spec["config"]["drifted_revision"]
        self.config.write_text(self.approved, encoding="utf-8")
        self.notes = sorted(vault_spec["files"])

    def test_install_then_exact_restore_returns_the_vault_to_its_prior_state(self):
        before = snapshot(self.vault)
        self.assertNotIn(".cursor", before)

        result = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.vault), "--apply",
            checkout=self.checkout,
        )
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)

        after_install = snapshot(self.vault)
        created = set(after_install) - set(before)
        self.assertTrue(created, "the apply must have created something")
        self.assertTrue(
            all(path.split("/")[0] == ".cursor" for path in created),
            f"apply touched paths outside the skill root: {sorted(created)}",
        )
        for path in before:
            with self.subTest(path=path):
                self.assertEqual(after_install[path], before[path], "non-target changed")

        # A configuration revision is rolled forward, then rolled back to the
        # exact approved bytes. Notes are never part of a rollback.
        self.config.write_text(self.drifted, encoding="utf-8")
        self.assertNotEqual(self.config.read_text("utf-8"), self.approved)
        self.config.write_text(self.approved, encoding="utf-8")
        shutil.rmtree(self.vault / ".cursor")

        self.assertEqual(snapshot(self.vault), before, "rollback was not exact")
        self.assertEqual(self.config.read_text("utf-8"), self.approved)

    def test_rollback_restores_configuration_without_rewriting_notes(self):
        note_digests = {
            relative: hashlib.sha256((self.vault / relative).read_bytes()).hexdigest()
            for relative in self.notes
        }
        self.config.write_text(self.drifted, encoding="utf-8")
        self.config.write_text(self.approved, encoding="utf-8")

        for relative, digest in note_digests.items():
            with self.subTest(note=relative):
                current = hashlib.sha256((self.vault / relative).read_bytes()).hexdigest()
                self.assertEqual(current, digest, "a rollback must never touch user content")
        self.assertEqual(self.config.read_text("utf-8"), self.approved)

    def test_a_second_apply_over_an_installed_vault_is_refused(self):
        first = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.vault), "--apply",
            checkout=self.checkout,
        )
        self.assertEqual(first.returncode, OK, first.stderr)
        after_first = snapshot(self.vault)

        second = self.run_installer(
            "copy", "--runtime", "cursor", "--skill", "all",
            "--scope", "project", "--project-root", str(self.vault), "--apply",
            checkout=self.checkout,
        )
        self.assert_refused(second, "COLLISION")
        self.assertEqual(snapshot(self.vault), after_first, "a re-run must not overwrite")


if __name__ == "__main__":
    unittest.main()
