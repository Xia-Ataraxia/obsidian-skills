#!/usr/bin/env python3
"""Review selected claim ranges and gate one append-only verification record."""
import argparse
import json
from pathlib import Path
from typing import List, Optional

from verify_core import run
from verify_io import Refused, load


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--write-disabled", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.vault.absolute()
        if root.is_symlink() or not root.is_dir():
            raise Refused("missing_vault", "vault is not an existing plain directory")
        result = run(
            root,
            load(args.request),
            load(args.approval) if args.approval else None,
            args.write_disabled,
        )
    except (Refused, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        code = exc.code if isinstance(exc, Refused) else "io_error"
        print(json.dumps({"schema": "verify/error@1", "status": "refused", "code": code}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
