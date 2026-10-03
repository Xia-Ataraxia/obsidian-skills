#!/usr/bin/env python3
"""Deterministic YouTube transcript extractor for Ataraxia ingest.

Attempts, in order:
1. Local Defuddle CLI against the canonical YouTube URL.
2. Public Defuddle markdown gateway: https://defuddle.md/www.youtube.com/watch?v=<id>
3. Metadata-only diagnostics via YouTube oEmbed / yt-dlp for blocker reporting.

The script never fabricates transcript text. A transcript is accepted only when a
bounded ``## Transcript`` section contains readable text rather than an error or
challenge shell. Word counts are observations for diagnostics, not completeness
proofs or admission thresholds.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

BAD_URL_CHARS = set("`$();|&\n\r")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
MAX_GATEWAY_WORKERS = 3
TRANSCRIPT_HEADING_RE = re.compile(r"^[ \t]*##[ \t]+Transcript[ \t]*$", re.IGNORECASE)
SECTION_HEADING_RE = re.compile(r"^[ \t]*##[ \t]+")
ERROR_SHELL_RE = re.compile(
    r"^(?:error\b|failed\b|failure\b|unable to\b|could not\b|couldn't\b|"
    r"no transcript\b|transcript unavailable\b|transcript (?:is )?not available\b|"
    r"video unavailable\b|this video is unavailable\b|"
    r"failed to (?:load|fetch|extract|retrieve)\b)",
    re.IGNORECASE,
)
NO_TRANSCRIPT_MARKERS = (
    "no transcript available",
    "no transcript is available",
    "transcript unavailable",
    "transcript not available",
    "captions unavailable",
    "captions are unavailable",
)
CHALLENGE_MARKERS = (
    "access denied",
    "403 forbidden",
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
    "sign in to confirm",
    "subscribe to continue",
    "paywall",
)


@dataclass
class ExtractionResult:
    ok: bool
    method: str
    canonical_url: str
    video_id: str
    title: str = ""
    channel: str = ""
    language: str = ""
    word_count: int = 0
    output_path: str = ""
    error: str = ""
    diagnostics: Optional[dict] = None
    completeness: str = "unknown"


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def parse_video_id(raw: str) -> tuple[str, str]:
    if not raw:
        fail("empty URL/video id")
    raw = raw.strip()
    if raw.lower().startswith(("http://", "https://")):
        if any(ch in raw for ch in BAD_URL_CHARS):
            fail("URL contains forbidden shell/control characters")
        parsed = urllib.parse.urlparse(raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host not in YOUTUBE_HOSTS:
            fail(f"not a supported YouTube host: {host}")
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        else:
            qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            video_id = (qs.get("v") or [""])[0]
            if not video_id:
                for prefix in ("/shorts/", "/embed/"):
                    if parsed.path.startswith(prefix):
                        video_id = parsed.path[len(prefix) :].split("/")[0]
                        break
    else:
        video_id = raw
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
        fail(f"invalid YouTube video id: {video_id!r}")
    return video_id, f"https://www.youtube.com/watch?v={video_id}"


def word_count(markdown: str) -> int:
    return len(re.findall(r"\S+", extract_transcript(markdown)))


def extract_transcript(markdown: str) -> str:
    """Return only the top-level transcript section, excluding later sections.

    A line-oriented parser keeps headings in fenced examples from becoming section
    boundaries and prevents similarly named headings from widening the evidence.
    """
    start: Optional[int] = None
    fence: Optional[str] = None
    offset = 0
    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        fence_match = re.match(r"^[ \t]*(```+|~~~+)", content)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            offset += len(line)
            continue
        if fence is not None:
            offset += len(line)
            continue
        if start is None:
            if TRANSCRIPT_HEADING_RE.fullmatch(content):
                start = offset + len(line)
        elif SECTION_HEADING_RE.match(content):
            return markdown[start:offset].strip()
        offset += len(line)
    return markdown[start:].strip() if start is not None else ""


def transcript_status(markdown: str) -> tuple[str, str]:
    """Classify transcript evidence without making a completeness claim."""
    transcript = extract_transcript(markdown)
    if not transcript:
        return "missing", "transcript section missing or empty"
    normalized = re.sub(r"\s+", " ", transcript).strip().lower()
    for marker in NO_TRANSCRIPT_MARKERS:
        if marker in normalized:
            return "missing", f"no-transcript marker: {marker}"
    for marker in CHALLENGE_MARKERS:
        if marker in normalized:
            return "challenge", f"challenge marker: {marker}"
    if ERROR_SHELL_RE.search(normalized):
        return "error", "error shell"
    return "valid", ""


def transcript_is_usable(markdown: str) -> bool:
    return transcript_status(markdown)[0] == "valid"


def transcript_diagnostic(markdown: str) -> dict[str, object]:
    status, reason = transcript_status(markdown)
    count = word_count(markdown)
    diagnostic: dict[str, object] = {
        "status": status,
        "words": count,
        "word_count": count,
        "completeness": "unknown",
    }
    if reason:
        diagnostic["reason"] = reason
    return diagnostic


def parse_frontmatter(markdown: str) -> dict:
    if not markdown.startswith("---\n"):
        return {}
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return {}
    raw = markdown[4:end]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        key, val = line.split(":", 1)
        val = val.strip().strip('"')
        data[key.strip()] = val
    return data


def run_defuddle(canonical_url: str, timeout: int) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(prefix="ingest-defuddle-", suffix=".md", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        try:
            proc = subprocess.run(
                ["defuddle", "parse", canonical_url, "--md", "-o", str(tmp_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return "", "defuddle not installed"
        except subprocess.TimeoutExpired as exc:
            return "", f"TimeoutExpired: {exc}"
        markdown = tmp_path.read_text(encoding="utf-8", errors="replace") if tmp_path.exists() else ""
        return markdown, (proc.stdout + proc.stderr).strip()
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def fetch_gateway(video_id: str, timeout: int) -> tuple[str, str]:
    """Fetch Defuddle's public markdown gateway.

    For YouTube watch pages, the HTTPS target can return embed-only markdown while the
    HTTP target currently returns the transcript. Try both and keep the richer result.
    This is still Defuddle output; do not fabricate or synthesize transcript text.
    """
    urls = [
        f"https://defuddle.md/http://www.youtube.com/watch?v={video_id}",
        f"https://defuddle.md/www.youtube.com/watch?v={video_id}",
        f"https://defuddle.md/https://www.youtube.com/watch?v={video_id}",
    ]
    best = ""
    errors: list[str] = []

    def fetch(url: str) -> tuple[str, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                markdown = response.read().decode("utf-8", "replace")
            return markdown, ""
        except Exception as exc:  # network diagnostics only; no fallback fabrication
            return "", f"{url}: {type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=MAX_GATEWAY_WORKERS) as executor:
        results = list(executor.map(fetch, urls))

    best_words = -1
    for url, (markdown, error) in zip(urls, results):
        if error:
            errors.append(error)
            continue
        status, reason = transcript_status(markdown)
        if status != "valid":
            errors.append(f"{url}: {reason or status}")
            continue
        candidate_words = word_count(markdown)
        if candidate_words > best_words:
            best = markdown
            best_words = candidate_words
    return best, "; ".join(errors)


def fetch_oembed(canonical_url: str, timeout: int) -> dict:
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(canonical_url, safe="")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def fetch_ytdlp(canonical_url: str, timeout: int) -> dict:
    try:
        proc = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--no-warnings", canonical_url],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            return {"error": proc.stderr.strip() or proc.stdout.strip()}
        data = json.loads(proc.stdout)
        return {k: data.get(k) for k in ("title", "channel", "uploader", "upload_date", "duration", "language")}
    except FileNotFoundError:
        return {"error": "yt-dlp not installed"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def choose_metadata(markdown: str, canonical_url: str, timeout: int) -> tuple[str, str, str, dict]:
    fm = parse_frontmatter(markdown)
    oembed = fetch_oembed(canonical_url, timeout)
    ytdlp = fetch_ytdlp(canonical_url, timeout)
    title = fm.get("title") or ytdlp.get("title") or oembed.get("title") or ""
    channel = ytdlp.get("channel") or ytdlp.get("uploader") or oembed.get("author_name") or ""
    language = fm.get("language") or ytdlp.get("language") or ""
    return title, channel, language, {"frontmatter": fm, "oembed": oembed, "yt_dlp": ytdlp}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract YouTube transcript markdown with deterministic fallbacks.")
    parser.add_argument("url_or_id", help="YouTube watch/shorts/youtu.be URL or video id")
    parser.add_argument("-o", "--output", required=True, help="Output markdown path")
    parser.add_argument("--metadata-output", help="Optional JSON metadata/result path")
    parser.add_argument("--timeout", type=int, default=60, help="Per-attempt timeout seconds")
    args = parser.parse_args(argv)

    video_id, canonical_url = parse_video_id(args.url_or_id)
    diagnostics: dict[str, object] = {"completeness": "unknown"}

    cli_markdown, cli_error = run_defuddle(canonical_url, args.timeout)
    cli_status, cli_reason = transcript_status(cli_markdown)
    cli_diagnostic = transcript_diagnostic(cli_markdown)
    cli_diagnostic["stderr"] = cli_error[-1000:]
    diagnostics["defuddle_cli"] = cli_diagnostic

    markdown = cli_markdown if cli_status == "valid" else ""
    method = "defuddle-cli" if cli_status == "valid" else "none"
    failure_reasons: list[str] = []
    if cli_status != "valid":
        failure_reasons.append(f"defuddle-cli: {cli_reason or cli_status}")

    if not markdown:
        gateway_markdown, gateway_error = fetch_gateway(video_id, args.timeout)
        gateway_status, gateway_reason = transcript_status(gateway_markdown)
        gateway_diagnostic = transcript_diagnostic(gateway_markdown)
        gateway_diagnostic["error"] = gateway_error[-1000:]
        diagnostics["defuddle_md_gateway"] = gateway_diagnostic
        if gateway_status == "valid":
            markdown = gateway_markdown
            method = "defuddle-md-gateway"
        else:
            failure_reasons.append(f"defuddle-md-gateway: {gateway_reason or gateway_status}")
            if gateway_error:
                failure_reasons.append(gateway_error)

    metadata_markdown = markdown or cli_markdown
    wc = word_count(markdown)
    title, channel, language, meta_diag = choose_metadata(metadata_markdown, canonical_url, args.timeout)
    diagnostics.update(meta_diag)

    out = Path(args.output)
    result = ExtractionResult(
        ok=bool(markdown),
        method=method,
        canonical_url=canonical_url,
        video_id=video_id,
        title=title,
        channel=channel,
        language=language,
        word_count=wc,
        completeness="unknown",
        output_path=str(out),
        diagnostics=diagnostics,
    )

    if not result.ok:
        result.error = "; ".join(failure_reasons) or "no usable transcript"
        if args.metadata_output:
            Path(args.metadata_output).write_text(
                json.dumps(asdict(result), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    if args.metadata_output:
        Path(args.metadata_output).write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
