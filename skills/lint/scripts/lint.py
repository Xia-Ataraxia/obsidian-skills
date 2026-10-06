#!/usr/bin/env python3
"""Run bounded vault lint and optionally apply one approved derived-index fix."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import List, Optional

from lint_core import analyze
from lint_scan import Refused, digest, route, text


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("invalid_input", "cannot read JSON input") from exc
    if not isinstance(value, dict):
        raise Refused("invalid_input", "JSON input must be an object")
    return value


def authorize(approval: dict, item: dict) -> None:
    required = {
        "approval_state",
        "approval_effect",
        "approval_scope",
        "approval_basis",
        "approval_preimage",
        "approval_proposal",
    }
    if not isinstance(approval, dict) or set(approval) != required:
        raise Refused("invalid_input", "approval fields are invalid")
    path = item["path"]
    if (
        approval["approval_state"] not in ("approved", "partially-approved")
        or not isinstance(approval["approval_effect"], list)
        or item["effect"] not in approval["approval_effect"]
        or not isinstance(approval["approval_scope"], list)
        or path not in approval["approval_scope"]
        or not isinstance(approval["approval_preimage"], dict)
        or approval["approval_preimage"].get(path) != item["preimage"]
        or not isinstance(approval["approval_proposal"], dict)
        or approval["approval_proposal"].get(path) != item["proposal_sha256"]
    ):
        raise Refused("approval_required", "approval does not bind the exact index proposal")
    text(approval["approval_basis"], "approval_basis")


def publish(root: Path, item: dict) -> None:
    destination = route(root, item["path"])
    current = destination.read_bytes() if destination.is_file() else None
    preimage = "absent" if current is None else digest(current)
    if preimage != item["preimage"] or (destination.exists() and not destination.is_file()):
        raise Refused("stale_approval", "derived index preimage changed")
    if not destination.parent.is_dir():
        raise Refused("missing_parent", "derived index parent must already exist")
    content = item["content"].encode("utf-8")
    handle, staged = tempfile.mkstemp(prefix=".lint-", dir=str(destination.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, 0o644 if current is None else destination.stat().st_mode & 0o777)
        if current is None:
            os.link(staged, str(destination))
        else:
            os.replace(staged, str(destination))
        if destination.read_bytes() != content:
            raise Refused("readback_failed", "derived index readback differs")
    finally:
        if os.path.exists(staged):
            os.unlink(staged)


def run(root: Path, request: dict, approval: Optional[dict] = None) -> dict:
    result = analyze(root, request)
    proposals = result["derived_index_proposals"]
    if result["mode"] == "fix":
        if result["cross_vault"]["blocks_fix"]:
            return result
        if proposals:
            if approval is None:
                raise Refused("approval_required", "fix mode needs exact index approval")
            authorize(approval, proposals[0])
            publish(root, proposals[0])
            result["mutations_performed"].append(proposals[0]["path"])
            result["status"] = "fixed"
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.vault.absolute()
        if root.is_symlink() or not root.is_dir():
            raise Refused("missing_vault", "vault is not an existing plain directory")
        result = run(root, load(args.request), load(args.approval) if args.approval else None)
    except (Refused, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        code = exc.code if isinstance(exc, Refused) else "io_error"
        print(json.dumps({"schema": "lint/error@1", "status": "refused", "code": code}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
