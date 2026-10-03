#!/usr/bin/env python3
"""Generate each knowledge package's copy of the shared field contract.

`docs/contracts.md` is the single authored source. A package is installed on its
own, so it cannot read that file; it carries a byte-identical generated copy at
`skills/<name>/references/contract.md` instead. The header line is part of both
files, so the copy is the source, byte for byte.

    sync_contracts.py                 every knowledge package present
    sync_contracts.py ingest query    only the named packages
    sync_contracts.py --check [...]   write nothing; report drift

Naming packages writes those copies and no others, so writers that own
different packages can run at the same time. Run the all-package form only when
no other writer is active.

Exit codes: 0 in sync or written, 1 refused or drift found, 2 usage.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HEADER = b"<!-- generated from docs/contracts.md; do not edit -->\n"
SOURCE = "docs/contracts.md"
COPY = "references/contract.md"
KNOWLEDGE_PACKAGES = (
    "capture",
    "inbox",
    "ingest",
    "query",
    "verify",
    "audit",
    "lint",
    "status",
    "reindex",
    "refresh-context",
    "onboard",
)


class Refused(Exception):
    """The request cannot be carried out safely; nothing was written for it."""


def read_source(root):
    path = root / SOURCE
    if path.is_symlink() or not path.is_file():
        raise Refused(f"contract source is not a regular file: {SOURCE}")
    blob = path.read_bytes()
    if not blob.startswith(HEADER):
        raise Refused(f"contract source does not start with the generated-copy header: {SOURCE}")
    return blob


def present_packages(root):
    return [
        name for name in KNOWLEDGE_PACKAGES
        if (root / "skills" / name / "SKILL.md").is_file()
    ]


def destination(root, name):
    """The copy path for one package, refusing any route that leaves the package."""
    package = root / "skills" / name
    if package.is_symlink() or not package.is_dir():
        raise Refused(f"package is not present as a directory: skills/{name}")
    references = package / "references"
    if references.is_symlink() or (references.exists() and not references.is_dir()):
        raise Refused(f"references is not a plain directory: skills/{name}/references")
    target = package / COPY
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise Refused(f"contract copy is not a regular file: skills/{name}/{COPY}")
    return target


def write_copy(target, blob):
    """Replace the copy in one step, so a reader never sees a partial file."""
    target.parent.mkdir(exist_ok=True)
    handle, staged = tempfile.mkstemp(dir=target.parent, prefix=".contract-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(blob)
        os.chmod(staged, 0o644)
        os.replace(staged, target)
    except BaseException:
        if os.path.exists(staged):
            os.unlink(staged)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate skills/<name>/references/contract.md from docs/contracts.md."
    )
    parser.add_argument(
        "packages", nargs="*", metavar="package",
        help="knowledge package names; default is every knowledge package present",
    )
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 on drift")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)

    unknown = [name for name in args.packages if name not in KNOWLEDGE_PACKAGES]
    if unknown:
        print(
            "not a knowledge package: " + ", ".join(repr(name) for name in unknown)
            + ". Known: " + " ".join(KNOWLEDGE_PACKAGES),
            file=sys.stderr,
        )
        return 2

    root = args.root.resolve()
    try:
        blob = read_source(root)
        names = list(dict.fromkeys(args.packages)) or present_packages(root)
        # Resolve every destination before the first write: a refused package
        # leaves the others it was requested with untouched too.
        targets = [(name, destination(root, name)) for name in names]
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1

    drift = 0
    for name, target in targets:
        shown = f"skills/{name}/{COPY}"
        current = target.read_bytes() if target.is_file() else None
        if current == blob:
            print(f"unchanged {shown}")
        elif args.check:
            drift += 1
            state = "missing" if current is None else "differs"
            print(f"{state} {shown}", file=sys.stderr)
        else:
            write_copy(target, blob)
            print(f"written {shown}")
    if drift:
        print(f"{drift} contract copies out of sync with {SOURCE}", file=sys.stderr)
        return 1
    print(f"{len(targets)} package(s) checked against {SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
