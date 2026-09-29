#!/usr/bin/env python3
"""Read-only classifier for Obsidian plugin and Templater failure evidence.

The script never touches an Obsidian installation, a vault, a configuration
folder, or any host profile.  Its only input is one sanitized evidence fixture
whose path the caller passes explicitly on the command line.  Nothing is
written, reloaded, reset, enabled, or disabled: the output is a diagnosis plus
next actions that a human still has to authorize and perform.

Contract summary (the authoritative copy lives in ../SKILL.md):

  usage: diagnose.py (--fixture PATH | --list-checks)

  exit 0  every check reached a determinate state              (status "ok")
  exit 1  at least one check stayed "unknown" for lack of data (status "indeterminate")
  exit 2  invalid command line (argparse; message on stderr, no JSON)
  exit 3  fixture missing, unreadable, or not a valid evidence bundle
          (status "input_error", JSON envelope still printed on stdout)

The exit code reports *evidence sufficiency*, not whether defects were found.
A run that confirms three defects from complete evidence exits 0.  Read
``findings[].status`` to learn what was actually wrong.

Stdlib only.  Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

EVIDENCE_SCHEMA = "obsidian-doctor/evidence@1"
DIAGNOSIS_SCHEMA = "obsidian-doctor/diagnosis@1"
CHECKS_SCHEMA = "obsidian-doctor/checks@1"

REGISTRY_FILE = "references/plugins.yaml"
MAX_EVIDENCE_CHARS = 300
REDACTED = "<redacted: host-specific value withheld from output>"

# Statuses a single check can report.
CONFIRMED = "confirmed"          # evidence supports the failure mode
RULED_OUT = "ruled_out"          # evidence was present and contradicts it
UNKNOWN = "unknown"              # the channel exists but the signal is missing
NOT_APPLICABLE = "not_applicable"  # the caller did not supply that channel at all

# --------------------------------------------------------------------------
# Documentation anchors.  Every URL below was read while authoring this file;
# none of them is inferred from a command name.
# --------------------------------------------------------------------------
DOC_MANIFEST = "https://docs.obsidian.md/Reference/Manifest"
DOC_PLUGIN_ANATOMY = "https://docs.obsidian.md/Plugins/Getting+started/Anatomy+of+a+plugin"
DOC_COMMUNITY_PLUGINS = "https://help.obsidian.md/community-plugins"
DOC_CONFIG_FOLDER = "https://help.obsidian.md/configuration-folder"
DOC_DATA_STORAGE = "https://help.obsidian.md/data-storage"
DOC_TP_SYNTAX = "https://silentvoid13.github.io/Templater/syntax.html"
DOC_TP_EXECUTION = "https://silentvoid13.github.io/Templater/commands/execution-command.html"
DOC_TP_SYSTEM = "https://silentvoid13.github.io/Templater/internal-functions/internal-modules/system-module.html"
DOC_TP_FILE = "https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html"

# --------------------------------------------------------------------------
# Templater surface facts, each taken from the module page cited beside it.
# --------------------------------------------------------------------------
# Documented with `await` in every official example -> must be awaited.
ASYNC_TEMPLATER_CALLS: Tuple[str, ...] = (
    "tp.system.prompt",
    "tp.system.suggester",
    "tp.system.multi_suggester",
    "tp.file.create_new",
    "tp.file.exists",
    "tp.file.include",
    "tp.file.move",
    "tp.file.rename",
)
# Calls that open a modal and return null when the user cancels (the
# `throw_on_cancel` argument defaults to false on all three).
INTERACTIVE_CALLS: Tuple[str, ...] = (
    "tp.system.prompt",
    "tp.system.suggester",
    "tp.system.multi_suggester",
)
# Zero-based index of `throw_on_cancel` in each interactive signature.
THROW_ON_CANCEL_ARG_INDEX: Dict[str, int] = {
    "tp.system.prompt": 2,
    "tp.system.suggester": 2,
    "tp.system.multi_suggester": 2,
}
# Calls that change the vault as a side effect of rendering.
MUTATING_CALLS: Tuple[str, ...] = (
    "tp.file.rename",
    "tp.file.move",
    "tp.file.create_new",
)

# Identifiers that legitimately resolve inside a Templater command, so a bare
# occurrence of one is not an unbound reference.  `app` and `moment` are called
# out by the execution-command page; the rest are JavaScript globals.
KNOWN_GLOBALS = frozenset(
    """
    tp app moment window document globalThis console process require
    Math JSON Date String Number Boolean Array Object RegExp Promise Map Set
    WeakMap WeakSet Symbol BigInt Intl Error TypeError RangeError
    parseInt parseFloat isNaN isFinite encodeURIComponent decodeURIComponent
    undefined null true false this arguments NaN Infinity
    """.split()
)

TEMPLATER_COMMAND_RE = re.compile(r"<%([*_\-]*)(.*?)[_\-]?%>", re.DOTALL)
DECLARATION_RE = re.compile(r"\b(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)")
PARAM_LIST_RE = re.compile(r"\bfunction\s*[A-Za-z_$][\w$]*?\s*\(([^)]*)\)")
LEADING_IDENT_RE = re.compile(r"^(?:await\s+)?([A-Za-z_$][\w$]*)")
REFERENCE_ERROR_RE = re.compile(r"ReferenceError:\s*([A-Za-z_$][\w$]*)\s+is not defined")
NOT_A_FUNCTION_RE = re.compile(r"TypeError:.*?\bis not a function\b")
UNDEFINED_READ_RE = re.compile(
    r"TypeError:\s*Cannot read propert(?:y|ies) of (?:undefined|null)"
)

# The console signatures this package is able to classify, paired with the check
# that owns each one.  A captured line matching none of them is reported as
# unclassified and stays `unknown`: an unfamiliar message is never rounded up to
# the nearest familiar one, and it is never "cleared" by a reload or a reset.
CLASSIFIED_ERROR_SIGNATURES: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("templater-reference-error", REFERENCE_ERROR_RE),
    ("plugin-api-unavailable", NOT_A_FUNCTION_RE),
    ("plugin-api-unavailable", UNDEFINED_READ_RE),
)
# How many unclassified lines are quoted before the rest are counted instead.
MAX_REPORTED_UNCLASSIFIED = 5

# Host-profile markers.  A fixture value matching any of these is treated as
# unsanitized: it is reported by location only and never echoed.
HOST_LEAK_PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("home-directory path", re.compile(r"(?:^|[\s\"'(=])~/")),
    ("macOS user path", re.compile(r"/Users/[^/\s\"']+")),
    ("Linux user path", re.compile(r"/home/[^/\s\"']+")),
    ("Windows user path", re.compile(r"[A-Za-z]:\\+Users\\+[^\\\s\"']+", re.IGNORECASE)),
    ("macOS temp path", re.compile(r"/var/folders/[^\s\"']+")),
    ("file:// URL", re.compile(r"file://", re.IGNORECASE)),
    ("credential embedded in URL", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
)
SECRET_KEY_TOKENS: Tuple[str, ...] = (
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

# Read-only CLI probes this package is willing to name.  Anything outside this
# list is described as "confirm against `obsidian help` first" rather than
# asserted to exist.
CLI_READ_ONLY_PROBES: Tuple[str, ...] = (
    "obsidian help",
    "obsidian dev:errors",
    "obsidian dev:console level=error",
    "obsidian read path=<vault-relative-path>",
)


# ==========================================================================
# Sanitization helpers
# ==========================================================================
def host_leak_reasons(value: str) -> List[str]:
    """Return the names of every host-profile marker present in ``value``."""
    return [label for label, pattern in HOST_LEAK_PATTERNS if pattern.search(value)]


def safe_text(value: Optional[str], limit: int = MAX_EVIDENCE_CHARS) -> str:
    """Bound and sanitize a fixture-derived string before emitting it."""
    if value is None:
        return ""
    text = str(value)
    if host_leak_reasons(text):
        return REDACTED
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 1] + "\u2026"
    return text


def safe_path(value: Any) -> Optional[str]:
    """Echo a vault-relative path, or redact anything that names the host."""
    if not isinstance(value, str) or not value:
        return None
    if host_leak_reasons(value):
        return REDACTED
    return value


def walk_strings(node: Any, pointer: str = "") -> Iterable[Tuple[str, str, Any]]:
    """Yield ``(json_pointer, key_name, value)`` for every scalar in the bundle."""
    if isinstance(node, dict):
        for key, child in node.items():
            child_pointer = f"{pointer}/{key}"
            if isinstance(child, (dict, list)):
                yield from walk_strings(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(node, list):
        for index, child in enumerate(node):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from walk_strings(child, child_pointer)
            else:
                yield child_pointer, "", child


# ==========================================================================
# Version helpers
# ==========================================================================
def parse_version(value: Any) -> Optional[Tuple[int, ...]]:
    """Parse a plain dotted numeric version, else return None (stays unknown)."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    if not text:
        return None
    parts = text.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def compare_versions(left: Tuple[int, ...], right: Tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    padded_left = left + (0,) * (width - len(left))
    padded_right = right + (0,) * (width - len(right))
    if padded_left < padded_right:
        return -1
    if padded_left > padded_right:
        return 1
    return 0


# ==========================================================================
# Templater source analysis
# ==========================================================================
class TemplaterCommand:
    """One `<% ... %>` or `<%* ... %>` command lifted out of a template."""

    __slots__ = ("flags", "body", "start", "end", "is_execution")

    def __init__(self, flags: str, body: str, start: int, end: int) -> None:
        self.flags = flags
        self.body = body
        self.start = start
        self.end = end
        self.is_execution = "*" in flags


class TemplaterCall:
    """One `tp.<module>.<fn>(` call site inside a template."""

    __slots__ = ("name", "start", "awaited", "args")

    def __init__(self, name: str, start: int, awaited: bool, args: List[str]) -> None:
        self.name = name
        self.start = start
        self.awaited = awaited
        self.args = args


def scan_commands(source: str) -> List[TemplaterCommand]:
    commands: List[TemplaterCommand] = []
    for match in TEMPLATER_COMMAND_RE.finditer(source):
        commands.append(
            TemplaterCommand(match.group(1), match.group(2), match.start(), match.end())
        )
    return commands


def split_top_level_args(source: str, open_paren: int) -> Tuple[List[str], int]:
    """Split the argument list that starts at ``open_paren``.

    Returns ``(args, index_after_closing_paren)``.  Returns ``([], -1)`` when the
    parentheses never balance, which keeps a malformed template from raising.
    """
    depth = 0
    args: List[str] = []
    current: List[str] = []
    quote: Optional[str] = None
    escaped = False
    index = open_paren
    length = len(source)
    while index < length:
        char = source[index]
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'`":
            quote = char
            current.append(char)
            index += 1
            continue
        if char in "([{":
            depth += 1
            if depth == 1 and char == "(":
                index += 1
                continue
            current.append(char)
            index += 1
            continue
        if char in ")]}":
            depth -= 1
            if depth == 0 and char == ")":
                tail = "".join(current).strip()
                if tail or args:
                    args.append(tail)
                return args, index + 1
            current.append(char)
            index += 1
            continue
        if char == "," and depth == 1:
            args.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    return [], -1


def scan_calls(source: str, names: Sequence[str]) -> List[TemplaterCall]:
    """Find every call to one of ``names``, longest name first so that
    ``tp.system.multi_suggester`` is not mistaken for ``tp.system.suggester``."""
    calls: List[TemplaterCall] = []
    claimed: List[Tuple[int, int]] = []
    for name in sorted(names, key=len, reverse=True):
        pattern = re.compile(re.escape(name) + r"\s*\(")
        for match in pattern.finditer(source):
            start = match.start()
            if any(low <= start < high for low, high in claimed):
                continue
            # Reject a longer member chain such as `tp.file.renamed(`.
            if start > 0 and (source[start - 1].isalnum() or source[start - 1] in "_$."):
                continue
            args, after = split_top_level_args(source, match.end() - 1)
            claimed.append((start, after if after > start else match.end()))
            prefix = source[max(0, start - 12) : start]
            calls.append(TemplaterCall(name, start, prefix.rstrip().endswith("await"), args))
    calls.sort(key=lambda call: call.start)
    return calls


def declared_identifiers(source: str) -> set:
    names = set(DECLARATION_RE.findall(source))
    for params in PARAM_LIST_RE.findall(source):
        for param in params.split(","):
            cleaned = param.strip().split("=")[0].strip()
            if cleaned and re.fullmatch(r"[A-Za-z_$][\w$]*", cleaned):
                names.add(cleaned)
    return names


def unbound_interpolations(source: str) -> List[str]:
    """Bare identifiers used in output commands with no binding anywhere."""
    commands = scan_commands(source)
    bound = declared_identifiers(source)
    unbound: List[str] = []
    for command in commands:
        if command.is_execution:
            continue
        body = command.body.strip()
        if not body:
            continue
        match = LEADING_IDENT_RE.match(body)
        if not match:
            continue
        identifier = match.group(1)
        if identifier in KNOWN_GLOBALS or identifier in bound:
            continue
        if identifier not in unbound:
            unbound.append(identifier)
    return unbound


ASSIGNMENT_RE = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*((?:await\s+)?tp\.[A-Za-z_.]+)\s*\("
)


def discarded_bindings(source: str) -> List[str]:
    """Variables bound from an asynchronous `tp.` call and then never referenced.

    Per the execution-command page a `<%* ... %>` block emits nothing by itself,
    so a value only reaches the note through `tR` or an output command.  A
    binding that is never mentioned again after its declaration reaches neither,
    and never reaches the vault either: the work the user was prompted for is
    thrown away.  A binding that is passed on to another call still counts as
    used, because its effect lands somewhere observable.
    """
    discarded: List[str] = []
    for command in scan_commands(source):
        if not command.is_execution:
            continue
        for match in ASSIGNMENT_RE.finditer(command.body):
            name, callee = match.group(1), match.group(2)
            if callee.replace("await", "").strip() not in ASYNC_TEMPLATER_CALLS:
                continue
            occurrences = len(re.findall(r"\b" + re.escape(name) + r"\b", source))
            if occurrences > 1:
                continue
            if name not in discarded:
                discarded.append(name)
    return discarded


def cancellation_exposure(source: str) -> List[str]:
    """Describe every way a cancelled prompt can leave the vault half-changed."""
    interactive = scan_calls(source, INTERACTIVE_CALLS)
    mutating = scan_calls(source, MUTATING_CALLS)
    problems: List[str] = []
    if not interactive or not mutating:
        return problems

    first_mutation = mutating[0]
    later_prompts = [call for call in interactive if call.start > first_mutation.start]
    if later_prompts:
        problems.append(
            "{first} runs before {later}; Templater has no rollback, so cancelling the "
            "later prompt leaves the earlier vault change applied".format(
                first=first_mutation.name,
                later=", ".join(sorted({call.name for call in later_prompts})),
            )
        )

    earlier_prompts = [call for call in interactive if call.start < first_mutation.start]
    for call in earlier_prompts:
        index = THROW_ON_CANCEL_ARG_INDEX.get(call.name)
        throws_on_cancel = (
            index is not None
            and len(call.args) > index
            and call.args[index].strip() == "true"
        )
        if throws_on_cancel:
            continue
        between = source[call.start : first_mutation.start]
        if re.search(r"\b(?:return|throw)\b", between):
            continue
        problems.append(
            "{name} defaults throw_on_cancel to false and returns null on cancel, and no "
            "return/throw guard separates it from {mutation}; the null flows into a vault "
            "mutation".format(name=call.name, mutation=first_mutation.name)
        )
    return problems


# ==========================================================================
# Finding construction
# ==========================================================================
def make_finding(
    check_id: str,
    title: str,
    status: str,
    summary: str,
    evidence: Sequence[str] = (),
    next_actions: Sequence[Dict[str, str]] = (),
    docs: Sequence[str] = (),
    registry_lookup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    finding: Dict[str, Any] = {
        "id": check_id,
        "title": title,
        "status": status,
        "summary": summary,
        "evidence": list(evidence),
        "next_actions": [dict(action) for action in next_actions],
        "docs": list(docs),
    }
    if registry_lookup is not None:
        finding["registry_lookup"] = registry_lookup
    return finding


def observe(detail: str) -> Dict[str, str]:
    return {"kind": "observe", "mutates": "no", "detail": detail}


def consult(detail: str) -> Dict[str, str]:
    return {"kind": "consult", "mutates": "no", "detail": detail}


def propose_change(detail: str) -> Dict[str, str]:
    """A source or setting change the human must review, approve, and apply."""
    return {"kind": "propose-change", "mutates": "yes-after-human-approval", "detail": detail}


def registry_pointer(plugin_id: Optional[str], keys: Sequence[str]) -> Dict[str, Any]:
    return {
        "file": REGISTRY_FILE,
        "plugin_id": plugin_id,
        "keys": list(keys),
    }


# ==========================================================================
# Checks
# ==========================================================================
def check_runtime_unavailable(fixture: Dict[str, Any]) -> Dict[str, Any]:
    runtime = fixture.get("runtime")
    docs = [DOC_COMMUNITY_PLUGINS]
    actions = [
        observe("Run `obsidian help` and record the command catalog it actually prints."),
        observe(
            "If the app bridge answers nothing, report the capability gap; do not "
            "substitute a filesystem write for the missing command."
        ),
    ]
    if not isinstance(runtime, dict):
        return make_finding(
            "runtime-unavailable",
            "Obsidian runtime or CLI bridge unavailable",
            UNKNOWN,
            "No `runtime` section was supplied, so runtime availability is unknown.",
            ["fixture has no `runtime` object"],
            actions,
            docs,
        )

    app_running = runtime.get("app_running")
    cli_available = runtime.get("cli_available")
    evidence: List[str] = [
        f"runtime.app_running = {json.dumps(app_running)}",
        f"runtime.cli_available = {json.dumps(cli_available)}",
    ]
    confirmed_parts: List[str] = []
    if app_running is False:
        confirmed_parts.append("the Obsidian app is reported as not running")
    if cli_available is False:
        confirmed_parts.append("the `obsidian` executable is reported as unavailable")

    confirmed_commands = runtime.get("cli_commands_confirmed")
    if isinstance(confirmed_commands, list):
        names = [str(item) for item in confirmed_commands]
        evidence.append("confirmed commands: " + (", ".join(names) if names else "(none)"))
        if "dev:errors" not in names and "dev:console" not in names:
            evidence.append(
                "no console-error command confirmed; console evidence must come from the "
                "Developer Tools console instead"
            )

    if confirmed_parts:
        return make_finding(
            "runtime-unavailable",
            "Obsidian runtime or CLI bridge unavailable",
            CONFIRMED,
            "Live diagnosis is blocked because " + " and ".join(confirmed_parts) + ".",
            evidence,
            actions,
            docs,
        )
    if app_running is None or cli_available is None:
        return make_finding(
            "runtime-unavailable",
            "Obsidian runtime or CLI bridge unavailable",
            UNKNOWN,
            "Runtime availability was not fully observed; it stays unknown.",
            evidence,
            actions,
            docs,
        )
    return make_finding(
        "runtime-unavailable",
        "Obsidian runtime or CLI bridge unavailable",
        RULED_OUT,
        "The app and the `obsidian` executable were both observed as available.",
        evidence,
        [observe("Proceed to the read-only evidence capture steps.")],
        docs,
    )


def check_plugin_unavailable(fixture: Dict[str, Any]) -> Dict[str, Any]:
    plugin = fixture.get("plugin")
    docs = [DOC_COMMUNITY_PLUGINS, DOC_CONFIG_FOLDER]
    if not isinstance(plugin, dict):
        return make_finding(
            "plugin-unavailable",
            "Plugin not installed or not enabled",
            NOT_APPLICABLE,
            "No plugin subject was supplied, so this case is not plugin-scoped.",
            ["fixture has no `plugin` object"],
            (),
            docs,
        )

    plugin_id = plugin.get("id") if isinstance(plugin.get("id"), str) else None
    installed = plugin.get("installed")
    enabled = plugin.get("enabled")
    evidence = [
        f"plugin.id = {json.dumps(plugin_id)}",
        f"plugin.installed = {json.dumps(installed)}",
        f"plugin.enabled = {json.dumps(enabled)}",
    ]
    actions = [
        observe(
            "Confirm the vault's real configuration folder name before looking for the "
            "plugin directory; `.obsidian` is only the default and can be overridden."
        ),
        observe(
            "Read `<config-folder>/plugins/<plugin-id>/manifest.json` and record `id`, "
            "`version`, and `minAppVersion`."
        ),
        propose_change(
            "Enabling or installing a plugin changes the vault configuration; leave that "
            "to the vault owner in Settings and re-capture evidence afterwards."
        ),
    ]
    reasons: List[str] = []
    if installed is False:
        reasons.append("the plugin directory was not found")
    if enabled is False:
        reasons.append("the plugin is installed but disabled")
    if reasons:
        return make_finding(
            "plugin-unavailable",
            "Plugin not installed or not enabled",
            CONFIRMED,
            "Every downstream symptom is explained by availability: "
            + " and ".join(reasons)
            + ".",
            evidence,
            actions,
            docs,
            registry_pointer(plugin_id, ["repo", "docs"]),
        )
    if installed is None or enabled is None:
        return make_finding(
            "plugin-unavailable",
            "Plugin not installed or not enabled",
            UNKNOWN,
            "Install/enable state was not observed; it stays unknown.",
            evidence,
            actions,
            docs,
            registry_pointer(plugin_id, ["repo", "docs"]),
        )
    return make_finding(
        "plugin-unavailable",
        "Plugin not installed or not enabled",
        RULED_OUT,
        "The plugin was observed installed and enabled.",
        evidence,
        [observe("Continue to version and API checks.")],
        docs,
        registry_pointer(plugin_id, ["repo", "docs"]),
    )


def check_version_mismatch(fixture: Dict[str, Any]) -> Dict[str, Any]:
    plugin = fixture.get("plugin")
    runtime = fixture.get("runtime") if isinstance(fixture.get("runtime"), dict) else {}
    docs = [DOC_MANIFEST, DOC_COMMUNITY_PLUGINS]
    if not isinstance(plugin, dict) or not isinstance(plugin.get("manifest"), dict):
        return make_finding(
            "plugin-version-mismatch",
            "Installed plugin version incompatible with the running app",
            NOT_APPLICABLE,
            "No plugin manifest was supplied, so compatibility was not evaluated.",
            ["fixture has no `plugin.manifest` object"],
            [observe("Capture `manifest.json` for the plugin and re-run.")],
            docs,
        )

    manifest = plugin["manifest"]
    plugin_id = manifest.get("id") or plugin.get("id")
    plugin_id = plugin_id if isinstance(plugin_id, str) else None
    app_version_raw = runtime.get("app_version")
    min_app_raw = manifest.get("minAppVersion")
    plugin_version_raw = manifest.get("version")
    evidence = [
        f"runtime.app_version = {json.dumps(app_version_raw)}",
        f"manifest.minAppVersion = {json.dumps(min_app_raw)}",
        f"manifest.version = {json.dumps(plugin_version_raw)}",
    ]
    lookup = registry_pointer(plugin_id, ["known_versions", "failure_signatures"])
    actions = [
        consult(
            "Look the installed version up in "
            + REGISTRY_FILE
            + " under `known_versions`; treat any version with no recorded evidence as "
            "untested rather than as working."
        ),
        observe(
            "Read the app version from Obsidian's About pane and record it as an observed "
            "value; do not infer it from a plugin."
        ),
    ]

    app_version = parse_version(app_version_raw)
    min_app = parse_version(min_app_raw)
    if app_version is None or min_app is None:
        missing = []
        if app_version is None:
            missing.append("a plain numeric app version")
        if min_app is None:
            missing.append("a plain numeric manifest minAppVersion")
        return make_finding(
            "plugin-version-mismatch",
            "Installed plugin version incompatible with the running app",
            UNKNOWN,
            "Compatibility stays unknown: " + " and ".join(missing) + " was not available.",
            evidence,
            actions,
            docs,
            lookup,
        )

    if compare_versions(app_version, min_app) < 0:
        return make_finding(
            "plugin-version-mismatch",
            "Installed plugin version incompatible with the running app",
            CONFIRMED,
            "The running app is older than the plugin's declared `minAppVersion`, which "
            "is the documented minimum required Obsidian version.",
            evidence,
            actions
            + [
                propose_change(
                    "Either update Obsidian or install a plugin release whose "
                    "`minAppVersion` the app satisfies; both are vault-owner decisions."
                )
            ],
            docs,
            lookup,
        )
    return make_finding(
        "plugin-version-mismatch",
        "Installed plugin version incompatible with the running app",
        RULED_OUT,
        "The running app satisfies the manifest's declared `minAppVersion`.",
        evidence,
        actions,
        docs,
        lookup,
    )


def _console_errors(fixture: Dict[str, Any]) -> Optional[List[str]]:
    raw = fixture.get("console_errors")
    if raw is None:
        return None
    if not isinstance(raw, list):
        return []
    messages: List[str] = []
    for item in raw:
        if isinstance(item, str):
            messages.append(item)
        elif isinstance(item, dict) and isinstance(item.get("message"), str):
            messages.append(item["message"])
    return messages


def _console_lines(raw: Sequence[Any]) -> Tuple[List[str], List[str]]:
    """Split a raw console channel into readable lines and unreadable entries.

    ``_console_errors`` drops anything it cannot read, which is the right
    behaviour for a signature match but hides a malformed capture.  This helper
    keeps the dropped entries so the unclassified check can report them as a gap
    in the evidence rather than as a clean console.
    """
    readable: List[str] = []
    unreadable: List[str] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            readable.append(item)
        elif isinstance(item, dict) and isinstance(item.get("message"), str):
            readable.append(item["message"])
        else:
            unreadable.append(
                f"/console_errors/{index} is neither a string nor an object with a "
                "string `message`, so that line could not be classified"
            )
    return readable, unreadable


def _template_source(fixture: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Return ``(state, source)`` where state is absent / missing-source / ok."""
    template = fixture.get("template")
    if not isinstance(template, dict):
        return "absent", None
    source = template.get("source")
    if not isinstance(source, str):
        return "missing-source", None
    return "ok", source


def check_templater_reference_error(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_TP_SYNTAX, DOC_TP_EXECUTION]
    state, source = _template_source(fixture)
    errors = _console_errors(fixture)
    registry = registry_pointer("templater-obsidian", ["failure_signatures"])
    actions = [
        observe(
            "Capture the exact console line from Obsidian's Developer Tools console "
            "(Cmd-Option-I on macOS, Ctrl+Shift+I elsewhere) before changing anything."
        ),
        propose_change(
            "Bind the identifier inside a `<%* ... %>` execution block and emit it through "
            "`tR +=`, then have the template owner apply and re-render the template."
        ),
    ]

    if state == "absent" and errors is None:
        return make_finding(
            "templater-reference-error",
            "Templater command references an unbound identifier",
            NOT_APPLICABLE,
            "Neither template source nor console output was supplied.",
            ["fixture has no `template` and no `console_errors`"],
            (),
            docs,
            registry,
        )
    if state == "missing-source":
        return make_finding(
            "templater-reference-error",
            "Templater command references an unbound identifier",
            UNKNOWN,
            "A template was named but its source was not supplied, so the identifier "
            "bindings could not be checked.",
            ["fixture has `template` without a string `template.source`"],
            actions,
            docs,
            registry,
        )

    evidence: List[str] = []
    reported: List[str] = []
    for message in errors or []:
        match = REFERENCE_ERROR_RE.search(message)
        if match:
            reported.append(match.group(1))
            evidence.append("console: " + safe_text(message))

    static_unbound = unbound_interpolations(source) if source is not None else []
    for identifier in static_unbound:
        evidence.append(
            f"`<% {identifier} %>` has no const/let/var/function binding in the template "
            "and is not a documented Templater or JavaScript global"
        )

    if reported or static_unbound:
        names = sorted(set(reported) | set(static_unbound))
        return make_finding(
            "templater-reference-error",
            "Templater command references an unbound identifier",
            CONFIRMED,
            "Templater evaluates a `<% ... %>` command as a JavaScript expression, so an "
            "identifier with no binding throws and aborts the render. Unbound: "
            + ", ".join(names)
            + ".",
            evidence,
            actions,
            docs,
            registry,
        )
    return make_finding(
        "templater-reference-error",
        "Templater command references an unbound identifier",
        RULED_OUT,
        "No unbound identifier was reported by the console or found in the template.",
        evidence or ["no ReferenceError in console output; every command root is bound"],
        [observe("Keep the console capture with the case record.")],
        docs,
        registry,
    )


def check_templater_missing_await(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_TP_EXECUTION, DOC_TP_SYSTEM, DOC_TP_FILE]
    state, source = _template_source(fixture)
    registry = registry_pointer("templater-obsidian", ["api_surface", "failure_signatures"])
    if state == "absent":
        return make_finding(
            "templater-missing-await",
            "Asynchronous Templater call used without await",
            NOT_APPLICABLE,
            "No template source was supplied.",
            ["fixture has no `template`"],
            (),
            docs,
            registry,
        )
    if state == "missing-source":
        return make_finding(
            "templater-missing-await",
            "Asynchronous Templater call used without await",
            UNKNOWN,
            "A template was named but its source was not supplied.",
            ["fixture has `template` without a string `template.source`"],
            [observe("Capture the template body verbatim and re-run.")],
            docs,
            registry,
        )

    assert source is not None
    missing = [call for call in scan_calls(source, ASYNC_TEMPLATER_CALLS) if not call.awaited]
    if missing:
        evidence = [
            f"`{call.name}(` at character offset {call.start} is not preceded by `await`"
            for call in missing
        ]
        return make_finding(
            "templater-missing-await",
            "Asynchronous Templater call used without await",
            CONFIRMED,
            "These calls are documented as asynchronous; without `await` the template "
            "receives a pending Promise instead of the value, so the rendered note shows "
            "`[object Promise]` or an empty slot while the side effect races the render.",
            evidence,
            [
                propose_change(
                    "Add `await` at each listed call site inside a `<%* ... %>` block and "
                    "re-render against a throwaway target the vault owner nominates."
                ),
                observe("Re-read the rendered note after the change; a clean exit is not proof."),
            ],
            docs,
            registry,
        )
    return make_finding(
        "templater-missing-await",
        "Asynchronous Templater call used without await",
        RULED_OUT,
        "Every documented asynchronous Templater call in this template is awaited.",
        ["all async `tp.` call sites carry `await`"],
        (),
        docs,
        registry,
    )


def check_templater_missing_output(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_TP_EXECUTION]
    state, source = _template_source(fixture)
    registry = registry_pointer("templater-obsidian", ["api_surface", "failure_signatures"])
    if state == "absent":
        return make_finding(
            "templater-missing-output",
            "Execution block computes a value it never emits",
            NOT_APPLICABLE,
            "No template source was supplied.",
            ["fixture has no `template`"],
            (),
            docs,
            registry,
        )
    if state == "missing-source":
        return make_finding(
            "templater-missing-output",
            "Execution block computes a value it never emits",
            UNKNOWN,
            "A template was named but its source was not supplied.",
            ["fixture has `template` without a string `template.source`"],
            [observe("Capture the template body verbatim and re-run.")],
            docs,
            registry,
        )

    assert source is not None
    discarded = discarded_bindings(source)
    evidence: List[str] = []
    unrendered = False
    rendered = fixture.get("rendered_output")
    if isinstance(rendered, dict) and isinstance(rendered.get("content"), str):
        if "<%" in rendered["content"]:
            unrendered = True
            evidence.append(
                "rendered output still contains a literal `<%` command, so the command "
                "text reached the note instead of a value: either Templater never "
                "processed the file or the render aborted partway"
            )
    if discarded or unrendered:
        evidence.extend(
            f"`{name}` is bound from an asynchronous `tp.` call and never referenced "
            "again, so it reaches neither `tR` nor the vault"
            for name in discarded
        )
        return make_finding(
            "templater-missing-output",
            "Execution block computes a value it never emits",
            CONFIRMED,
            "A `<%* ... %>` execution block emits nothing on its own; a value only appears "
            "in the note when it is appended to the `tR` output string or read back by an "
            "output command.",
            evidence,
            [
                propose_change(
                    "Append the computed value to `tR` (or read it back through a `<% var %>` "
                    "output command) and let the template owner re-render."
                ),
                observe("Read the rendered note back and confirm the value materialized."),
            ],
            docs,
            registry,
        )
    return make_finding(
        "templater-missing-output",
        "Execution block computes a value it never emits",
        RULED_OUT,
        "Every value bound from an asynchronous call is emitted.",
        evidence or ["no discarded async binding found"],
        (),
        docs,
        registry,
    )


def check_templater_partial_mutation(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_TP_SYSTEM, DOC_TP_FILE, DOC_TP_EXECUTION]
    state, source = _template_source(fixture)
    registry = registry_pointer("templater-obsidian", ["failure_signatures"])
    if state == "absent":
        return make_finding(
            "templater-partial-mutation-risk",
            "Cancelled prompt can leave a half-applied rename or move",
            NOT_APPLICABLE,
            "No template source was supplied.",
            ["fixture has no `template`"],
            (),
            docs,
            registry,
        )
    if state == "missing-source":
        return make_finding(
            "templater-partial-mutation-risk",
            "Cancelled prompt can leave a half-applied rename or move",
            UNKNOWN,
            "A template was named but its source was not supplied.",
            ["fixture has `template` without a string `template.source`"],
            [observe("Capture the template body verbatim and re-run.")],
            docs,
            registry,
        )

    assert source is not None
    problems = cancellation_exposure(source)
    if problems:
        return make_finding(
            "templater-partial-mutation-risk",
            "Cancelled prompt can leave a half-applied rename or move",
            CONFIRMED,
            "`tp.file.rename` and `tp.file.move` change the vault as the template renders "
            "and are not undone when a later step fails, so an interactive template must "
            "collect and validate every answer before the first mutation.",
            problems,
            [
                propose_change(
                    "Gather all prompt/suggester answers first, return early on a null "
                    "answer (or pass throw_on_cancel = true), and perform rename/move only "
                    "after every value is validated."
                ),
                observe(
                    "After any cancelled run, read the note back by its expected path and "
                    "by its previous path: a rename that already landed leaves the note "
                    "under the new name with unrendered body text, and a move whose target "
                    "folder does not exist leaves it under the old path. Record whichever "
                    "path actually resolves, and treat 'the command returned' as no "
                    "evidence at all."
                ),
            ],
            docs,
            registry,
        )
    return make_finding(
        "templater-partial-mutation-risk",
        "Cancelled prompt can leave a half-applied rename or move",
        RULED_OUT,
        "No interactive prompt precedes an unguarded vault mutation in this template.",
        ["no prompt-before-mutation ordering hazard found"],
        (),
        docs,
        registry,
    )


def check_plugin_api_unavailable(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_PLUGIN_ANATOMY, DOC_MANIFEST]
    plugin = fixture.get("plugin") if isinstance(fixture.get("plugin"), dict) else {}
    plugin_id = plugin.get("id") if isinstance(plugin.get("id"), str) else None
    probe = plugin.get("api_probe") if isinstance(plugin.get("api_probe"), dict) else None
    errors = _console_errors(fixture)
    registry = registry_pointer(plugin_id, ["api_surface", "known_versions"])
    actions = [
        observe(
            "Probe the symbol with a read-only expression only. A probe that assigns, "
            "saves settings, reloads, or resets state is a mutation, not a diagnosis."
        ),
        consult(
            "Compare the symbol against the plugin's published API documentation recorded "
            "in " + REGISTRY_FILE + "; an undocumented internal is not a stable contract."
        ),
    ]

    signature_hits = [
        message
        for message in errors or []
        if NOT_A_FUNCTION_RE.search(message) or UNDEFINED_READ_RE.search(message)
    ]

    if probe is None and errors is None:
        return make_finding(
            "plugin-api-unavailable",
            "Plugin API symbol missing at the installed version",
            NOT_APPLICABLE,
            "Neither an API probe result nor console output was supplied.",
            ["fixture has no `plugin.api_probe` and no `console_errors`"],
            (),
            docs,
            registry,
        )

    evidence: List[str] = []
    observed = None
    if probe is not None:
        observed = probe.get("observed")
        symbol = probe.get("symbol")
        evidence.append(
            "api_probe: symbol={symbol} observed={observed}".format(
                symbol=json.dumps(symbol if isinstance(symbol, str) else None),
                observed=json.dumps(observed),
            )
        )
    for message in signature_hits:
        evidence.append("console: " + safe_text(message))

    if observed == "missing" or signature_hits:
        return make_finding(
            "plugin-api-unavailable",
            "Plugin API symbol missing at the installed version",
            CONFIRMED,
            "The call site expects a symbol the installed build does not expose, so the "
            "caller must be rewritten against the API the installed version documents.",
            evidence,
            actions
            + [
                propose_change(
                    "Rewrite the call site against the documented API of the installed "
                    "version, or have the vault owner install a version that documents the "
                    "expected symbol."
                )
            ],
            docs,
            registry,
        )
    if probe is not None and observed not in ("present", "missing"):
        return make_finding(
            "plugin-api-unavailable",
            "Plugin API symbol missing at the installed version",
            UNKNOWN,
            "An API probe was declared but reported no determinate result.",
            evidence,
            actions,
            docs,
            registry,
        )
    return make_finding(
        "plugin-api-unavailable",
        "Plugin API symbol missing at the installed version",
        RULED_OUT,
        "No missing-symbol evidence was found in the probe or the console output.",
        evidence or ["no API-shape error signature in console output"],
        (),
        docs,
        registry,
    )


def check_console_unclassified(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_COMMUNITY_PLUGINS, DOC_PLUGIN_ANATOMY]
    plugin = fixture.get("plugin") if isinstance(fixture.get("plugin"), dict) else {}
    plugin_id = plugin.get("id") if isinstance(plugin.get("id"), str) else None
    registry = registry_pointer(plugin_id, ["failure_signatures", "known_versions"])
    actions = [
        consult(
            "Look the line up verbatim under `failure_signatures` for this plugin in "
            + REGISTRY_FILE
            + ", then in the plugin's own published issue tracker or release notes recorded "
            "there. An absent signature means untested, not benign."
        ),
        observe(
            "Keep the line verbatim with the case record and report it as unclassified. Do "
            "not map it onto the nearest familiar class, and do not reload, disable, "
            "reinstall, or reset anything to make it disappear: that destroys the evidence "
            "without explaining the failure."
        ),
    ]

    raw = fixture.get("console_errors")
    if raw is None:
        return make_finding(
            "console-error-unclassified",
            "Console error matches no signature this package can classify",
            NOT_APPLICABLE,
            "No console capture was supplied, so there was nothing to classify.",
            ["fixture has no `console_errors`"],
            (),
            docs,
            registry,
        )
    if not isinstance(raw, list):
        return make_finding(
            "console-error-unclassified",
            "Console error matches no signature this package can classify",
            UNKNOWN,
            "The console channel was supplied in a shape this classifier cannot read, so "
            "whether it holds an unclassified error stays unknown.",
            [f"`console_errors` is {type(raw).__name__}, not a list"],
            [observe("Re-capture `console_errors` as a list of strings or objects and re-run.")],
            docs,
            registry,
        )

    readable, unreadable = _console_lines(raw)
    unclassified = [
        line
        for line in readable
        if not any(pattern.search(line) for _, pattern in CLASSIFIED_ERROR_SIGNATURES)
    ]

    if unclassified or unreadable:
        evidence = list(unreadable)
        for line in unclassified[:MAX_REPORTED_UNCLASSIFIED]:
            evidence.append("unclassified console line: " + safe_text(line))
        remainder = len(unclassified) - MAX_REPORTED_UNCLASSIFIED
        if remainder > 0:
            evidence.append(f"{remainder} further unclassified line(s) not quoted here")
        return make_finding(
            "console-error-unclassified",
            "Console error matches no signature this package can classify",
            UNKNOWN,
            "The capture holds at least one line that matches none of the signatures this "
            "package records, so its cause stays unknown and the case is not closed by the "
            "determinate findings alone.",
            evidence,
            actions,
            docs,
            registry,
        )

    if not readable:
        return make_finding(
            "console-error-unclassified",
            "Console error matches no signature this package can classify",
            RULED_OUT,
            "The capture carried no error line, so no line went unclassified.",
            [
                "`console_errors` is empty",
                "an empty capture bounds what was observed in that window; it is not proof "
                "that the runtime is clean, and it never substitutes for the rendered or "
                "read-back evidence a defect claim needs",
            ],
            [
                observe(
                    "State the capture window alongside the empty result, and rely on "
                    "template, manifest, or readback evidence for any claim about behaviour."
                )
            ],
            docs,
            registry,
        )

    matched = sorted(
        {
            owner
            for line in readable
            for owner, pattern in CLASSIFIED_ERROR_SIGNATURES
            if pattern.search(line)
        }
    )
    return make_finding(
        "console-error-unclassified",
        "Console error matches no signature this package can classify",
        RULED_OUT,
        "Every captured line matched a recorded signature, so each one is owned by a "
        "named check rather than left unexplained.",
        [f"{len(readable)} captured line(s) matched: " + ", ".join(matched)],
        (),
        docs,
        registry,
    )


def check_fixture_sanitized(fixture: Dict[str, Any]) -> Dict[str, Any]:
    docs = [DOC_DATA_STORAGE, DOC_CONFIG_FOLDER]
    problems: List[str] = []
    for pointer, key, value in walk_strings(fixture):
        lowered = key.lower()
        if any(token in lowered for token in SECRET_KEY_TOKENS):
            problems.append(f"{pointer}: key name suggests a secret; value withheld")
            continue
        if isinstance(value, str):
            for reason in host_leak_reasons(value):
                problems.append(f"{pointer}: {reason}; value withheld")
    if problems:
        return make_finding(
            "fixture-not-sanitized",
            "Fixture carries host-specific or secret-looking values",
            CONFIRMED,
            "The bundle was not sanitized before it was handed over. The offending values "
            "are reported by location only and are never echoed into this output.",
            problems,
            [
                propose_change(
                    "Replace each listed value with a vault-relative path or a placeholder "
                    "in the source fixture, then re-run."
                ),
                observe("Do not attach the raw bundle to a report or an issue as-is."),
            ],
            docs,
        )
    return make_finding(
        "fixture-not-sanitized",
        "Fixture carries host-specific or secret-looking values",
        RULED_OUT,
        "No host path, home-directory reference, or secret-looking key was found.",
        ["fixture scan found no host-specific or secret-looking value"],
        (),
        docs,
    )


CHECKS: Tuple[Tuple[str, str, Tuple[str, ...], Any], ...] = (
    (
        "runtime-unavailable",
        "Obsidian runtime or CLI bridge unavailable",
        ("runtime.app_running", "runtime.cli_available", "runtime.cli_commands_confirmed"),
        check_runtime_unavailable,
    ),
    (
        "plugin-unavailable",
        "Plugin not installed or not enabled",
        ("plugin.id", "plugin.installed", "plugin.enabled"),
        check_plugin_unavailable,
    ),
    (
        "plugin-version-mismatch",
        "Installed plugin version incompatible with the running app",
        ("runtime.app_version", "plugin.manifest.minAppVersion", "plugin.manifest.version"),
        check_version_mismatch,
    ),
    (
        "templater-reference-error",
        "Templater command references an unbound identifier",
        ("template.source", "console_errors"),
        check_templater_reference_error,
    ),
    (
        "templater-missing-await",
        "Asynchronous Templater call used without await",
        ("template.source",),
        check_templater_missing_await,
    ),
    (
        "templater-missing-output",
        "Execution block computes a value it never emits",
        ("template.source", "rendered_output.content"),
        check_templater_missing_output,
    ),
    (
        "templater-partial-mutation-risk",
        "Cancelled prompt can leave a half-applied rename or move",
        ("template.source",),
        check_templater_partial_mutation,
    ),
    (
        "plugin-api-unavailable",
        "Plugin API symbol missing at the installed version",
        ("plugin.api_probe", "console_errors"),
        check_plugin_api_unavailable,
    ),
    (
        "console-error-unclassified",
        "Console error matches no signature this package can classify",
        ("console_errors",),
        check_console_unclassified,
    ),
    (
        "fixture-not-sanitized",
        "Fixture carries host-specific or secret-looking values",
        ("<entire bundle>",),
        check_fixture_sanitized,
    ),
)


# ==========================================================================
# Envelope assembly
# ==========================================================================
def build_subject(fixture: Dict[str, Any]) -> Dict[str, Any]:
    runtime = fixture.get("runtime") if isinstance(fixture.get("runtime"), dict) else {}
    plugin = fixture.get("plugin") if isinstance(fixture.get("plugin"), dict) else {}
    manifest = plugin.get("manifest") if isinstance(plugin.get("manifest"), dict) else {}
    template = fixture.get("template") if isinstance(fixture.get("template"), dict) else {}
    case_id = fixture.get("case_id")
    return {
        "case_id": safe_text(case_id) or None,
        "plugin_id": plugin.get("id") if isinstance(plugin.get("id"), str) else None,
        "plugin_version": manifest.get("version")
        if isinstance(manifest.get("version"), str)
        else None,
        "min_app_version": manifest.get("minAppVersion")
        if isinstance(manifest.get("minAppVersion"), str)
        else None,
        "app_version": runtime.get("app_version")
        if isinstance(runtime.get("app_version"), str)
        else None,
        "template_path": safe_path(template.get("path")),
    }


def error_envelope(fixture_path: str, reason: str) -> Dict[str, Any]:
    return {
        "schema": DIAGNOSIS_SCHEMA,
        "status": "input_error",
        "fixture": safe_path(fixture_path) or REDACTED,
        "reason": reason,
        "findings": [],
        "unknowns": [],
        "mutations_performed": [],
    }


def diagnose(fixture: Dict[str, Any], fixture_path: str) -> Dict[str, Any]:
    findings = [handler(fixture) for _, _, _, handler in CHECKS]
    unknowns = [
        f"{finding['id']}: {finding['summary']}"
        for finding in findings
        if finding["status"] == UNKNOWN
    ]
    status = "indeterminate" if unknowns else "ok"
    return {
        "schema": DIAGNOSIS_SCHEMA,
        "status": status,
        "fixture": safe_path(fixture_path) or REDACTED,
        "evidence_schema": fixture.get("schema"),
        "subject": build_subject(fixture),
        "findings": findings,
        "unknowns": unknowns,
        "mutations_performed": [],
        "read_only_probes": list(CLI_READ_ONLY_PROBES),
    }


def checks_catalog() -> Dict[str, Any]:
    return {
        "schema": CHECKS_SCHEMA,
        "statuses": [CONFIRMED, RULED_OUT, UNKNOWN, NOT_APPLICABLE],
        "exit_codes": {
            "0": "ok - no check stayed unknown",
            "1": "indeterminate - at least one check stayed unknown",
            "2": "usage error - invalid command line, message on stderr, no JSON",
            "3": "input_error - fixture missing, unreadable, or not an evidence bundle",
        },
        "checks": [
            {"id": check_id, "title": title, "evidence_required": list(required)}
            for check_id, title, required, _ in CHECKS
        ],
    }


def emit(document: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")


def load_fixture(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "fixture file does not exist at the supplied path"
    except IsADirectoryError:
        return None, "the supplied path is a directory, not an evidence bundle"
    except PermissionError:
        return None, "the fixture file exists but is not readable"
    except UnicodeDecodeError:
        return None, "the fixture file is not valid UTF-8"
    except json.JSONDecodeError as exc:
        return None, f"the fixture file is not valid JSON (line {exc.lineno}, column {exc.colno})"
    except OSError as exc:
        return None, f"the fixture file could not be read ({exc.strerror or 'OS error'})"

    if not isinstance(payload, dict):
        return None, "the fixture must be a JSON object"
    schema = payload.get("schema")
    if schema != EVIDENCE_SCHEMA:
        return None, (
            f"unsupported evidence schema {json.dumps(schema)}; expected "
            f"{json.dumps(EVIDENCE_SCHEMA)}"
        )
    return payload, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diagnose.py",
        description=(
            "Classify Obsidian plugin and Templater failure evidence from one sanitized "
            "fixture. Read-only: no vault, configuration folder, or plugin state is "
            "discovered, read, or changed."
        ),
        epilog=(
            "Exit codes: 0 every check determinate, 1 at least one check unknown, "
            "2 usage error, 3 fixture unreadable or wrong schema. The exit code reports "
            "evidence sufficiency, not whether defects were found."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--fixture",
        metavar="PATH",
        help="path to a sanitized " + EVIDENCE_SCHEMA + " JSON bundle",
    )
    mode.add_argument(
        "--list-checks",
        action="store_true",
        help="print the check catalog and the exit-code contract, then exit 0",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        emit(checks_catalog())
        return 0

    fixture, reason = load_fixture(args.fixture)
    if fixture is None:
        emit(error_envelope(args.fixture, reason or "unreadable fixture"))
        return 3

    document = diagnose(fixture, args.fixture)
    emit(document)
    return 1 if document["status"] == "indeterminate" else 0


if __name__ == "__main__":
    sys.exit(main())
