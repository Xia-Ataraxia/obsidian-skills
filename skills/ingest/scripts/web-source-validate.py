#!/usr/bin/env python3
"""Inspect bounded web-source evidence for readable content and access errors.

The script is intentionally dependency-free so it can run inside Hermes/bstack
without package setup. It reports extraction, URL-identity, and optional coverage
signals; it does not validate a vault note or its admission.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from pathlib import Path
from typing import Iterable

SECTION_RE = re.compile(r"^##\s+(Content|Transcript|README)\s*$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-z0-9가-힣]+")

BLOCK_MARKERS = [
    "access denied",
    "403 forbidden",
    "forbidden",
    "not authorized",
    "unauthorized",
    "request blocked",
    "temporarily blocked",
    "just a moment",
    "checking your browser",
    "verify you are human",
    "captcha",
    "cloudflare",
    "akamai",
    "perimeterx",
    "datadome",
    "bot detection",
    "enable javascript",
    "please enable cookies",
    "login required",
    "sign in to continue",
    "subscribe to continue",
    "paywall",
    "__cf_chl_",
    "cf-browser-verification",
    "sec-if-cpt-container",
]
BAD_URL_CHARS = set("`$();|&\n\r")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + 5 :]


def extract_content_section(text: str) -> str:
    body = strip_frontmatter(text)
    match = SECTION_RE.search(body)
    if not match:
        return body.strip()
    start = match.end()
    next_heading = HEADING_RE.search(body, start)
    end = next_heading.start() if next_heading else len(body)
    return body[start:end].strip()


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def find_markers(text: str) -> list[str]:
    low = text.lower()
    return [marker for marker in BLOCK_MARKERS if marker in low]


def _youtube_video_id(parsed: urllib.parse.ParseResult) -> str:
    host = (parsed.hostname or "").lower().rstrip(".")
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]
    query_id = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
    if query_id:
        return query_id
    for prefix in ("/shorts/", "/embed/"):
        if parsed.path.startswith(prefix):
            return parsed.path[len(prefix) :].split("/")[0]
    return ""


def source_identity(source_url: str, *, source_type: str = "") -> dict:
    """Inspect URL identity without requiring a note field or vault schema."""
    identity = {
        "provided": bool(source_url),
        "canonical_url": source_url,
        "host": "",
        "youtube_id_resolved": False,
        "errors": [],
    }
    if not source_url:
        return identity
    if any(char in source_url for char in BAD_URL_CHARS):
        identity["errors"].append("source_url_contains_forbidden_characters")
        return identity
    try:
        parsed = urllib.parse.urlparse(source_url)
    except ValueError:
        identity["errors"].append("source_url_invalid")
        return identity
    host = (parsed.hostname or "").lower().rstrip(".")
    identity["host"] = host
    if parsed.scheme not in {"http", "https"}:
        identity["errors"].append("source_url_scheme_not_http")
    if not host:
        identity["errors"].append("source_url_host_missing")
    if identity["errors"]:
        return identity

    if host in YOUTUBE_HOSTS:
        candidate = _youtube_video_id(parsed)
        if source_type.lower() == "video" and not YOUTUBE_ID_RE.fullmatch(candidate):
            identity["errors"].append("youtube_video_id_missing_or_invalid")
        elif YOUTUBE_ID_RE.fullmatch(candidate):
            identity["canonical_url"] = f"https://www.youtube.com/watch?v={candidate}"
            identity["youtube_id_resolved"] = True
    return identity


def validate(
    text: str,
    *,
    min_words: int | None = None,
    expected: Iterable[str] = (),
    source_url: str = "",
    source_type: str = "",
) -> dict:
    section = extract_content_section(text)
    words = count_words(section)
    markers = find_markers(section)
    expected_terms = [term.strip() for term in expected if term.strip()]
    section_low = section.lower()
    missing_expected = [term for term in expected_terms if term.lower() not in section_low]
    identity = source_identity(source_url, source_type=source_type)
    coverage_warnings: list[str] = []
    if min_words is not None and words < min_words:
        coverage_warnings.append(
            f"word_count_below_advisory_floor:{words}<{min_words}"
        )
    passed = (
        bool(section)
        and not markers
        and not missing_expected
        and not identity["errors"]
    )
    reasons: list[str] = []
    if not section:
        reasons.append("content_section_empty")
    if markers:
        reasons.append("blocked_or_challenge_markers:" + ",".join(markers))
    if missing_expected:
        reasons.append("missing_expected_terms:" + ",".join(missing_expected))
    if identity["errors"]:
        reasons.append("source_identity_invalid:" + ",".join(identity["errors"]))
    return {
        "passed": passed,
        "word_count": words,
        "min_words": min_words,
        "markers": markers,
        "missing_expected_terms": missing_expected,
        "source_identity": identity,
        "coverage_warnings": coverage_warnings,
        "reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect bounded web-source evidence")
    parser.add_argument("--file", required=True, help="Markdown or text file to validate")
    parser.add_argument("--source-url", default="", help="Original source URL to identity-check")
    parser.add_argument(
        "--source-type",
        default="",
        help="Optional evidence class; video enables YouTube ID checking",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=None,
        help="Optional advisory coverage floor; never proves completeness",
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="Coverage anchor that must appear in the content section; repeatable",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human text")
    args = parser.parse_args(argv)

    path = Path(args.file)
    text = path.read_text(encoding="utf-8")
    result = validate(
        text,
        min_words=args.min_words,
        expected=args.expect,
        source_url=args.source_url,
        source_type=args.source_type,
    )
    result.update({"file": str(path), "source_url": args.source_url, "source_type": args.source_type})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["passed"]:
        print(f"web-source-validate: OK word_count={result['word_count']} source_type={args.source_type}")
        for warning in result["coverage_warnings"]:
            print(f"- warning: {warning}")
    else:
        print("web-source-validate: FAIL")
        for reason in result["reasons"]:
            print(f"- {reason}")
        for warning in result["coverage_warnings"]:
            print(f"- warning: {warning}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
