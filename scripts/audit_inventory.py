#!/usr/bin/env python3
"""Audit the source inventory: responsibility units, rights, and exact source checkouts.

The manifest (`source-inventory.json`) is a double-entry record. Every source file
declares the responsibility units it contains, and every unit declares the feature
that owns the adopted behaviour in this repository. This script checks that the two
halves agree, that rights claims match the licence evidence of their source, and --
when a read-only checkout of a source is supplied -- that the recorded digests and
the inventory's coverage of that checkout are exact.

Every repository path a manifest entry names -- a feature package, a unit target,
a verification reference -- must be a canonical relative path that resolves,
through symlinks, to a real location inside this repository; a functional target
must in addition resolve inside the package of the feature that owns it.

Every functional unit maps to exactly one owning package. It names one owning
feature and, in `package`, the package directory that feature declares. A unit
that names several owners, names its owner twice, or names a package other than
its owner's is refused by unit ID.
"""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[1]
FEATURES = {f"F{i:02}" for i in range(1, 10)}
KNOWLEDGE_PACKAGES = (
    "capture", "inbox", "ingest", "query", "verify", "audit", "lint", "status",
    "reindex", "refresh-context", "onboard",
)
KNOWLEDGE_FEATURES = {
    f"K{i:02}": name for i, name in enumerate(KNOWLEDGE_PACKAGES, start=1)
}
OWNER_KEYS = {"owner", "package"}
CLASSES = {"functional", "supporting"}
DISPOSITIONS = {"imported", "reimplemented", "not-adopted"}
RIGHTS = {"mit-import", "mit-notice", "mit-reference", "evidence-only"}
COPYABLE_RIGHTS = {"mit-import", "mit-notice"}
SCHEMA_VERSION = 3
HEX = set("0123456789abcdef")
PERMISSION_SENTENCE = (
    "The above copyright notice and this permission notice shall be included in all"
)


def _matches(pattern, path):
    """Match a POSIX-relative path against an exclusion pattern.

    `dir/**` matches the directory and everything under it; anything else is an
    fnmatch glob on the whole path.
    """
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def _verification_path(entry):
    """The repository path a verification reference points at, without its anchor."""
    return entry.split("#", 1)[0].split("::", 1)[0].strip()


def _canonical_relative(path):
    """The canonical relative POSIX path `path` names, or None when it is unsafe.

    Only a plain relative path built from real segments is canonical. Absolute
    paths, Windows drive and UNC paths, backslash separators, empty segments and
    `.` or `..` segments are all rejected, so no manifest entry can name a
    location by traversal or by anchoring itself outside the tree it belongs to.
    """
    if not isinstance(path, str) or not path or "\\" in path:
        return None
    if PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute():
        return None
    if any(part in ("", ".", "..") for part in path.split("/")):
        return None
    return PurePosixPath(path)


def _repo_path(root, path):
    """Resolve a declared repository path. Returns `(resolved, problem)`.

    `problem` is "unsafe" when the path is not canonical or when resolving it --
    through symlinks -- lands outside `root`, "missing" when nothing exists at
    the resolved location, and None when the path names a real file or directory
    strictly inside the repository. Containment is decided after resolution:
    `Path.exists()` and a lexical prefix test both accept a symlink that points
    out of the repository.
    """
    relative = _canonical_relative(path)
    if relative is None:
        return None, "unsafe"
    base = Path(root).resolve()
    resolved = (base / relative).resolve()
    if base not in resolved.parents:
        return None, "unsafe"
    if not resolved.exists():
        return None, "missing"
    return resolved, None


def load_manifest(text):
    """Parse a manifest. Returns `(data, problems)`.

    `json.loads` keeps the last of two equal keys and drops the first without a
    word, so a unit that declares its owner twice would otherwise be read as a
    unit with one owner. Repeated keys are reported instead of resolved.
    """
    problems = []

    def pairs_hook(pairs):
        row = dict(pairs)
        seen = set()
        for key, _value in pairs:
            if key in seen:
                label = row.get("id") if isinstance(row.get("id"), str) else "<no id>"
                if key in OWNER_KEYS:
                    problems.append(f"duplicate owner declared for unit: {label}")
                else:
                    problems.append(f"duplicate key {key!r} in manifest object: {label}")
            seen.add(key)
        return row

    return json.loads(text, object_pairs_hook=pairs_hook), problems


def _walk(source_root):
    return sorted(
        str(path.relative_to(source_root).as_posix())
        for path in source_root.rglob("*")
        if path.is_file()
    )


def audit(data, root=ROOT, source_roots=None):
    errors = []
    root = Path(root)
    source_roots = source_roots or {}

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    features = data["features"]
    declared = set(features)
    if not FEATURES <= declared or declared - FEATURES - set(KNOWLEDGE_FEATURES):
        errors.append(
            f"feature registry must declare exactly {sorted(FEATURES)}"
            f" and at most the knowledge features {sorted(KNOWLEDGE_FEATURES)}"
        )
    packages = {}
    package_dirs = {}
    package_names = {}
    for feature, row in sorted(features.items()):
        package = row.get("package")
        if not row.get("name") or not package:
            errors.append(f"incomplete feature registry entry: {feature}")
            continue
        if isinstance(package, str):
            package_names[feature] = package.rsplit("/", 1)[-1]
        if feature in KNOWLEDGE_FEATURES and package != f"skills/{KNOWLEDGE_FEATURES[feature]}":
            errors.append(
                f"knowledge feature {feature} must own skills/{KNOWLEDGE_FEATURES[feature]}"
            )
        directory, problem = _repo_path(root, package)
        if problem == "unsafe":
            errors.append(f"unsafe feature package path: {feature} -> {package}")
        elif directory is None or not directory.is_dir():
            errors.append(f"missing feature package: {feature} -> {package}")
        else:
            package_dirs[feature] = directory
        identity = directory if directory is not None else package
        if identity in packages:
            errors.append(f"feature package shared by {packages[identity]} and {feature}")
            package_names.pop(packages[identity], None)
            package_names.pop(feature, None)
        packages[identity] = feature

    sources = data["sources"]
    licensed = {
        name for name, row in sources.items() if (row.get("license") or {}).get("spdx")
    }
    for name, row in sorted(sources.items()):
        if not row.get("revision") or len(row["revision"]) != 40:
            errors.append(f"source needs an exact 40-character revision: {name}")
        if not (row.get("license") or {}).get("evidence"):
            errors.append(f"source needs licence evidence: {name}")
        if name in licensed and not row["license"].get("copyright"):
            errors.append(f"licensed source needs an exact copyright line: {name}")

    files = {row["id"]: row for row in data["files"]}
    if len(files) != len(data["files"]):
        errors.append("duplicate source file ID")
    seen_paths = set()
    for file_id, row in sorted(files.items()):
        path = row.get("path", "")
        if _canonical_relative(path) is None:
            errors.append(f"unsafe or missing source path: {file_id}")
        key = (row.get("source"), path)
        if key in seen_paths:
            errors.append(f"duplicate source path: {file_id}")
        seen_paths.add(key)
        if row.get("source") not in sources:
            errors.append(f"unknown source: {file_id}")
        digest = row.get("sha256") or ""
        if len(digest) != 64 or set(digest) - HEX:
            errors.append(f"missing or malformed digest: {file_id}")
        if not isinstance(row.get("bytes"), int) or row["bytes"] <= 0:
            errors.append(f"missing byte count: {file_id}")
        if row.get("rights") not in RIGHTS:
            errors.append(f"unknown rights class: {file_id}")
        elif row["rights"] != "evidence-only" and row.get("source") not in licensed:
            errors.append(f"rights claim exceeds source licence evidence: {file_id}")

    covered = set()
    owners = set()
    keys = set()
    unit_ids = set()
    for unit in data["units"]:
        key = (unit.get("file"), unit.get("unit"))
        if key in keys:
            errors.append(f"duplicate responsibility unit: {key}")
        keys.add(key)
        unit_id = unit.get("id")
        if not unit_id:
            errors.append(f"missing stable unit ID: {key}")
        elif unit_id in unit_ids:
            errors.append(f"duplicate stable unit ID: {unit_id}")
        unit_ids.add(unit_id)
        row = files.get(unit.get("file"))
        if row is None:
            errors.append(f"unknown source file: {unit.get('file')}")
        covered.add(unit.get("file"))
        if not unit.get("behavior"):
            errors.append(f"missing behavior description: {key}")
        disposition = unit.get("disposition")
        if disposition not in DISPOSITIONS:
            errors.append(f"unknown disposition: {key}")
        if disposition == "imported" and row is not None:
            if row.get("rights") not in COPYABLE_RIGHTS:
                errors.append(f"imported unit on non-copyable source: {key}")
        label = unit_id or key
        if any(isinstance(unit.get(field), (list, dict)) for field in OWNER_KEYS):
            errors.append(f"unit must map to exactly one owning package: {label}")
            continue
        for composed in unit.get("composes", []):
            if composed not in declared:
                errors.append(f"unknown composed feature: {key}")
            if composed == unit.get("owner"):
                errors.append(f"unit composes its own owner: {key}")
        if unit.get("class") == "functional":
            owner = unit.get("owner")
            if owner not in declared:
                errors.append(f"missing or invalid single owner: {key}")
            else:
                owners.add(owner)
                if not unit.get("package"):
                    errors.append(f"missing owning package: {label}")
                elif owner in package_names and unit["package"] != package_names[owner]:
                    errors.append(f"owning package is not the package of its owner: {label}")
            target = unit.get("target")
            resolved, problem = _repo_path(root, target)
            if not target or problem == "missing":
                errors.append(f"missing target: {key}")
            elif problem:
                errors.append(f"unsafe target path: {key}")
            elif owner in package_dirs and package_dirs[owner] not in resolved.parents:
                errors.append(f"target outside owning package: {key}")
            verification = unit.get("verification") or []
            if not verification:
                errors.append(f"missing verification mapping: {key}")
            for entry in verification:
                reference = _verification_path(entry)
                found, problem = _repo_path(root, reference)
                if reference and problem == "unsafe":
                    errors.append(f"unsafe verification reference: {key} -> {entry}")
                elif found is None:
                    errors.append(f"unresolved verification reference: {key} -> {entry}")
            if disposition == "not-adopted":
                errors.append(f"functional unit cannot be not-adopted: {key}")
        elif unit.get("class") == "supporting":
            if unit.get("owner") is not None:
                errors.append(f"supporting unit has functional owner: {key}")
            if unit.get("package") is not None:
                errors.append(f"supporting unit has an owning package: {label}")
            target = unit.get("target")
            if target:
                resolved, problem = _repo_path(root, target)
                if problem == "unsafe":
                    errors.append(f"unsafe target path: {key}")
                elif resolved is None:
                    errors.append(f"missing target: {key}")
            if disposition == "not-adopted" and not unit.get("reason"):
                errors.append(f"not-adopted unit needs a reason: {key}")
        else:
            errors.append(f"unknown unit class: {key}")

    for file_id in sorted(files.keys() - covered):
        errors.append(f"uncovered source file: {file_id}")
    if FEATURES - owners:
        errors.append(f"uncovered feature owners: {sorted(FEATURES - owners)}")

    for file_id, row in sorted(files.items()):
        expected = set(row.get("expected_units", []))
        actual = {unit for source, unit in keys if source == file_id}
        if expected != actual:
            errors.append(f"unit inventory mismatch: {file_id}")

    inventoried = {}
    for row in files.values():
        inventoried.setdefault(row.get("source"), set()).add(row.get("path"))
    excluded = data.get("excluded", [])
    for entry in excluded:
        source = entry.get("source")
        patterns = entry.get("patterns") or []
        if source not in sources:
            errors.append(f"unknown source in exclusion: {source}")
        if not patterns or not entry.get("reason"):
            errors.append(f"incomplete exclusion entry: {source} {patterns[:1]}")
        for pattern in patterns:
            for path in sorted(inventoried.get(source, ())):
                if _matches(pattern, path):
                    errors.append(f"exclusion overlaps inventoried file: {pattern} -> {path}")

    for name, source_root in sorted(source_roots.items()):
        source_root = Path(source_root)
        if name not in sources:
            errors.append(f"checkout supplied for unknown source: {name}")
            continue
        if not source_root.is_dir():
            errors.append(f"source checkout is not a directory: {name}")
            continue
        present = _walk(source_root)
        for row in sorted(
            (r for r in files.values() if r.get("source") == name),
            key=lambda r: r["id"],
        ):
            if _canonical_relative(row.get("path")) is None:
                continue  # already reported as an unsafe or missing source path
            path = source_root / row["path"]
            if not path.is_file():
                errors.append(f"source file missing from checkout: {row['id']}")
                continue
            blob = path.read_bytes()
            if hashlib.sha256(blob).hexdigest() != row["sha256"]:
                errors.append(f"source digest mismatch: {row['id']}")
            if len(blob) != row.get("bytes"):
                errors.append(f"source byte-count mismatch: {row['id']}")
        for pattern in (p for entry in excluded if entry.get("source") == name
                        for p in entry.get("patterns", [])):
            if not any(_matches(pattern, path) for path in present):
                errors.append(f"stale exclusion pattern: {name} -> {pattern}")
        for coverage_root in sources[name].get("coverage_roots", []):
            under = [p for p in present if _matches(coverage_root.rstrip("/") + "/**", p)]
            if not under:
                errors.append(f"empty coverage root: {name} -> {coverage_root}")
            for path in under:
                if path not in inventoried.get(name, ()):
                    errors.append(f"uninventoried file in coverage root: {name} -> {path}")
        if sources[name].get("partition"):
            patterns = [p for entry in excluded if entry.get("source") == name
                        for p in entry.get("patterns", [])]
            for path in present:
                if path in inventoried.get(name, ()):
                    continue
                if not any(_matches(pattern, path) for pattern in patterns):
                    errors.append(f"unpartitioned source file: {name} -> {path}")

    if any(row.get("rights") in COPYABLE_RIGHTS for row in files.values()):
        notice = root / "NOTICE"
        if not notice.is_file():
            errors.append("copied licensed material requires a NOTICE file")
        else:
            text = notice.read_text(encoding="utf-8")
            if PERMISSION_SENTENCE not in text:
                errors.append("NOTICE is missing the MIT permission notice")
            for name in sorted(licensed):
                copyright_line = sources[name]["license"].get("copyright")
                if copyright_line and copyright_line not in text:
                    errors.append(f"NOTICE is missing the copyright line for {name}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "source-inventory.json")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--craft-source", type=Path)
    parser.add_argument("--upstream-source", type=Path)
    args = parser.parse_args()
    supplied = (("craft", args.craft_source), ("upstream", args.upstream_source))
    sources = {name: path for name, path in supplied if path}
    try:
        data, errors = load_manifest(args.manifest.read_text(encoding="utf-8"))
        errors += audit(data, args.root, sources)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"inventory error: {type(exc).__name__}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"{len(errors)} inventory errors", file=sys.stderr)
        return 1
    functional = sum(1 for unit in data["units"] if unit["class"] == "functional")
    print(
        f"inventory: {len(data['files'])} source files, {len(data['units'])} units "
        f"({functional} functional, {len(data['units']) - functional} supporting), "
        f"{len({unit['package'] for unit in data['units'] if unit['class'] == 'functional'})} "
        f"owning packages, one per functional unit; digests and coverage checked for "
        f"{len(sources)} supplied checkout(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
