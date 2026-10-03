#!/usr/bin/env python3
"""Refresh one isolated qmd named index after auditing its sole collection.

Python >=3.8, standard library only.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

FORBIDDEN = ("inbox", "personal", "public", "company", "memories", "memory")


class Refused(Exception):
    """The selected corpus or qmd index is not safely isolated."""

    def __init__(self, code: str, detail: str,
                 effects_possible: Optional[List[str]] = None) -> None:
        super().__init__(detail)
        self.code = code
        self.effects_possible = [] if effects_possible is None else effects_possible


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read scope JSON") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "scope must be an object")
    return value


def text(value, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or "\x00" in value
            or any(ord(char) < 32 for char in value)):
        raise Refused("invalid_input", label + " must be nonempty text")
    return value


def relative(value: str) -> str:
    text(value, "path")
    parts = value.split("/")
    if ("\\" in value or ":" in value
            or any(part in ("", ".", "..") or part.startswith(".") for part in parts)):
        raise Refused("unsafe_path", "path must be a literal visible vault-relative route")
    return value


def target(root: Path, value: str) -> Path:
    path = root
    for part in relative(value).split("/"):
        path = path / part
        if path.is_symlink():
            raise Refused("unsafe_path", "symlink in corpus route")
    return path


def parse_scope(value: dict) -> dict:
    required = {"schema", "index", "collection", "include_roots", "paper_analyses"}
    if set(value) != required or value["schema"] != "reindex/scope@1":
        raise Refused("invalid_input", "unsupported reindex scope")
    text(value["index"], "index")
    text(value["collection"], "collection")
    roots = value["include_roots"]
    if (not isinstance(roots, list) or not roots
            or any(not isinstance(root, str) for root in roots)):
        raise Refused("invalid_input", "include_roots must be unique literal paths")
    if len(roots) != len(set(roots)):
        raise Refused("invalid_input", "include_roots must be unique literal paths")
    for root in roots:
        relative(root)
        lowered = root.casefold()
        if any(token in lowered.split("/")[-1] for token in FORBIDDEN):
            raise Refused("mixed_corpus", "forbidden responsibility root in selected corpus")
    paper = relative(value["paper_analyses"])
    if paper not in roots:
        raise Refused("missing_paper_analyses", "Paper Analyses must be included explicitly")
    return value


def bounded(value: str) -> str:
    return value if len(value) <= 4000 else value[:3999] + "\u2026"


def invoke(command: List[str], timeout: int) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
    except subprocess.TimeoutExpired as exc:
        raise Refused("hung_command", "qmd exceeded the bounded timeout") from exc
    except OSError as exc:
        raise Refused("qmd_unavailable", "qmd could not be executed") from exc
    return result.returncode, result.stdout, result.stderr


def command(qmd: str, index: str, *parts: str) -> List[str]:
    return [qmd, "--index", index] + list(parts)


def visible_markdown(root: Path, included: List[str]) -> set:
    found = set()
    for name in included:
        selected = target(root, name)
        for parent, directories, filenames in os.walk(str(selected), followlinks=False):
            base = Path(parent)
            directories[:] = sorted(
                item for item in directories
                if not item.startswith(".") and not (base / item).is_symlink()
            )
            for filename in filenames:
                path = base / filename
                if (filename.startswith(".") or path.is_symlink()
                        or not path.is_file() or path.suffix != ".md"):
                    continue
                found.add(path.relative_to(root).as_posix())
    return found


def show_fields(shown: str) -> Tuple[str, str]:
    values = {}
    for line in shown.splitlines():
        for key in ("Path", "Pattern"):
            prefix = key + ":"
            if line.startswith(prefix):
                if key in values:
                    raise Refused("collection_scope_mismatch",
                                  "collection show repeated " + key)
                values[key] = line[len(prefix):].strip()
    if set(values) != {"Path", "Pattern"}:
        raise Refused("collection_scope_mismatch",
                      "collection show must expose exact Path and Pattern fields")
    return values["Path"], values["Pattern"]


def audit_preflight(root: Path, scope: dict, status: str, shown: str) -> set:
    names = set(re.findall(r"qmd://([^/\s]+)/", status))
    if names != {scope["collection"]}:
        raise Refused("collection_not_isolated",
                      "named index must expose exactly the selected collection")
    shown_path, shown_pattern = show_fields(shown)
    try:
        configured_root = Path(shown_path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise Refused("collection_root_mismatch",
                      "collection root cannot be resolved") from exc
    if configured_root != root.resolve(strict=True):
        raise Refused("collection_root_mismatch", "collection show did not name the selected vault")
    if any(token in shown_pattern for token in ("{", "}")):
        raise Refused("collection_scope_mismatch", "brace-expanded collection masks are refused")
    patterns = {item.strip() for item in shown_pattern.split(",") if item.strip()}
    expected = {included + "/**/*.md" for included in scope["include_roots"]}
    if patterns != expected:
        raise Refused("collection_scope_mismatch",
                      "collection mask must equal the approved responsibility roots")
    return visible_markdown(root, scope["include_roots"])


def listed_files(collection: str, output: str) -> set:
    found = set()
    prefix = "qmd://" + collection + "/"
    for raw in output.splitlines():
        line = raw.strip().lstrip("- ").strip()
        if not line:
            continue
        if line.startswith(prefix):
            candidate = line[len(prefix):]
        else:
            match = re.match(r"^(.*?\.md)(?:\s{2,}.*)?$", line)
            if not match:
                continue
            candidate = match.group(1)
        found.add(relative(candidate))
    return found


def run(root: Path, scope: dict, qmd: Optional[str] = None, timeout: int = 1800) -> dict:
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise Refused("missing_vault", "vault is not an existing plain directory")
    scope = parse_scope(scope)
    for included in scope["include_roots"]:
        if not target(root, included).is_dir():
            raise Refused("missing_root", "included responsibility root is absent")
    executable = qmd or shutil.which("qmd")
    if not executable:
        return {
            "schema": "reindex/result@1", "status": "unavailable",
            "reason": "qmd executable not found", "commands": [],
            "readbacks": [], "mutations_performed": [],
        }
    commands = [
        command(executable, scope["index"], "status"),
        command(executable, scope["index"], "collection", "show", scope["collection"]),
    ]
    readbacks = []
    preflight_outputs = []
    for item in commands:
        code, stdout, stderr = invoke(item, timeout)
        preflight_outputs.append((stdout, stderr))
        readbacks.append({"command": item, "exit_code": code,
                          "stdout": bounded(stdout), "stderr": bounded(stderr)})
        if code != 0:
            raise Refused("qmd_preflight_failed", "qmd preflight returned nonzero")
    expected_files = audit_preflight(
        root, scope, preflight_outputs[0][0], preflight_outputs[1][0])
    effects_possible = []
    for parts in (("update",), ("ls", "qmd://" + scope["collection"] + "/"),
                  ("embed",), ("status",)):
        item = command(executable, scope["index"], *parts)
        commands.append(item)
        attempted_effects = list(effects_possible)
        if parts[0] in ("update", "embed"):
            possible = "qmd derivations may have changed for named index " + scope["index"]
            if possible not in attempted_effects:
                attempted_effects.append(possible)
        try:
            code, stdout, stderr = invoke(item, timeout)
        except Refused as exc:
            raise Refused(exc.code, str(exc), attempted_effects) from exc
        readbacks.append({"command": item, "exit_code": code,
                          "stdout": bounded(stdout), "stderr": bounded(stderr)})
        if code != 0:
            raise Refused("qmd_command_failed",
                          "qmd " + parts[0] + " returned nonzero", attempted_effects)
        effects_possible = attempted_effects
        if parts[0] == "ls":
            try:
                actual_files = listed_files(scope["collection"], stdout)
            except Refused as exc:
                raise Refused(exc.code, str(exc), effects_possible) from exc
            if actual_files != expected_files:
                raise Refused("collection_membership_mismatch",
                              "indexed files differ from approved vault membership",
                              effects_possible)
    return {
        "schema": "reindex/result@1", "status": "reindexed",
        "index": scope["index"], "collection": scope["collection"],
        "include_roots": scope["include_roots"],
        "paper_analyses": scope["paper_analyses"],
        "matched_files": sorted(expected_files),
        "commands": commands, "readbacks": readbacks,
        "limitations": [
            "Document and vector counts are separate observations.",
            "Index success does not verify source quality or runtime query relevance.",
        ],
        "mutations_performed": ["qmd derivations for named index " + scope["index"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--qmd")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        result = run(args.vault, load(args.scope), args.qmd, args.timeout_seconds)
    except Refused as exc:
        status = "unavailable" if exc.code == "qmd_unavailable" else "refused"
        print(json.dumps({"schema": "reindex/error@1", "status": status,
                          "code": exc.code, "error": str(exc),
                          "mutations_performed": [],
                          "mutation_state": (
                              "possible_unconfirmed" if exc.effects_possible else "none"),
                          "effects_possible": exc.effects_possible}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "reindexed" else 1


if __name__ == "__main__":
    sys.exit(main())
