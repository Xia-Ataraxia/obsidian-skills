import io
import importlib.util
import json
import sys
import threading
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "ingest" / "scripts" / "youtube-transcript-extract.py"
spec = importlib.util.spec_from_file_location("youtube_transcript_extract", SCRIPT)
assert spec is not None
assert spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class YoutubeTranscriptExtractTest(unittest.TestCase):
    def test_parse_video_id_watch_url(self):
        video_id, canonical = mod.parse_video_id("https://www.youtube.com/watch?v=ShYKkPPhOoc")
        self.assertEqual(video_id, "ShYKkPPhOoc")
        self.assertEqual(canonical, "https://www.youtube.com/watch?v=ShYKkPPhOoc")

    def test_parse_video_id_youtu_be(self):
        video_id, canonical = mod.parse_video_id("https://youtu.be/tWxyohJIEeA")
        self.assertEqual(video_id, "tWxyohJIEeA")
        self.assertEqual(canonical, "https://www.youtube.com/watch?v=tWxyohJIEeA")

    def test_parse_video_id_short_and_embed_urls(self):
        for raw in (
            "https://www.youtube.com/shorts/tWxyohJIEeA?feature=share",
            "https://www.youtube.com/embed/tWxyohJIEeA",
        ):
            video_id, canonical = mod.parse_video_id(raw)
            self.assertEqual(video_id, "tWxyohJIEeA")
            self.assertEqual(canonical, "https://www.youtube.com/watch?v=tWxyohJIEeA")

    def test_extract_transcript_and_frontmatter(self):
        markdown = """---\ntitle: \"Demo\"\nlanguage: \"en\"\n---\n\nIntro\n\n## Transcript\n\nhello world\n"""
        self.assertEqual(mod.parse_frontmatter(markdown)["title"], "Demo")
        self.assertEqual(mod.parse_frontmatter(markdown)["language"], "en")
        self.assertEqual(mod.extract_transcript(markdown), "hello world")
        self.assertEqual(mod.word_count(markdown), 2)

    def test_transcript_parser_keeps_real_boundaries(self):
        markdown = """---
title: "Demo"
---

# Transcript

not the transcript section

## Transcript

only these words count

### A subsection remains transcript text

## Resources

trailing metadata must not count
"""
        self.assertEqual(
            mod.extract_transcript(markdown),
            "only these words count\n\n### A subsection remains transcript text",
        )
        # The whitespace-based diagnostic includes the Markdown heading marker.
        self.assertEqual(mod.word_count(markdown), 10)
        self.assertEqual(mod.word_count("metadata-only response with many words"), 0)

    def test_transcript_parser_ignores_headings_inside_fences(self):
        markdown = """## Transcript

opening words

```markdown
## Resources
```

closing words

## Resources

metadata must not count
"""
        self.assertEqual(
            mod.extract_transcript(markdown),
            "opening words\n\n```markdown\n## Resources\n```\n\nclosing words",
        )

    def test_missing_and_short_transcript_are_distinct(self):
        status, reason = mod.transcript_status("## Description\n\nmetadata only")
        self.assertEqual(status, "missing")
        self.assertIn("transcript", reason)

        short = "## Transcript\n\none short sentence"
        self.assertTrue(mod.transcript_is_usable(short))
        self.assertEqual(mod.word_count(short), 3)
        self.assertEqual(mod.transcript_diagnostic(short)["completeness"], "unknown")

    def test_error_and_challenge_shells_are_not_transcript_evidence(self):
        shells = (
            "## Transcript\n\nNo transcript available.",
            "## Transcript\n\nError: failed to load transcript.",
            "## Transcript\n\nPlease verify you are human before continuing.",
        )
        for shell in shells:
            with self.subTest(shell=shell):
                self.assertFalse(mod.transcript_is_usable(shell))

    def test_run_defuddle_returns_diagnostic_when_executable_is_missing(self):
        with mock.patch.object(mod.subprocess, "run", side_effect=FileNotFoundError):
            markdown, diagnostic = mod.run_defuddle("https://www.youtube.com/watch?v=ShYKkPPhOoc", 17)

        self.assertEqual(markdown, "")
        self.assertEqual(diagnostic, "defuddle not installed")

    def test_run_defuddle_returns_diagnostic_when_timed_out(self):
        timeout = mod.subprocess.TimeoutExpired("defuddle", 17)
        with mock.patch.object(mod.subprocess, "run", side_effect=timeout):
            markdown, diagnostic = mod.run_defuddle("https://www.youtube.com/watch?v=ShYKkPPhOoc", 17)

        self.assertEqual(markdown, "")
        self.assertIn("TimeoutExpired:", diagnostic)

    def test_fetch_gateway_overlaps_requests_and_preserves_url_priority_for_ties(self):
        barrier = threading.Barrier(3, timeout=2)
        second_done = threading.Event()
        third_done = threading.Event()
        completion_order = []

        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return self.body.encode()

        def urlopen(request, timeout):
            self.assertEqual(timeout, 17)
            index = next(i for i, url in enumerate(urls) if request.full_url == url)
            barrier.wait()
            if index == 0:
                self.assertTrue(second_done.wait(2))
            elif index == 1:
                self.assertTrue(third_done.wait(2))
            completion_order.append(index)
            if index == 2:
                third_done.set()
            elif index == 1:
                second_done.set()
            return Response(f"## Transcript\n\ncandidate-{index} equal words")

        video_id = "ShYKkPPhOoc"
        urls = [
            f"https://defuddle.md/http://www.youtube.com/watch?v={video_id}",
            f"https://defuddle.md/www.youtube.com/watch?v={video_id}",
            f"https://defuddle.md/https://www.youtube.com/watch?v={video_id}",
        ]
        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=urlopen):
            markdown, errors = mod.fetch_gateway(video_id, 17)

        self.assertEqual(completion_order, [2, 1, 0])
        self.assertEqual(markdown, "## Transcript\n\ncandidate-0 equal words")
        self.assertEqual(errors, "")

    def test_fetch_gateway_rejects_shells_and_orders_diagnostics(self):
        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return self.body.encode()

        def urlopen(request, timeout):
            self.assertEqual(timeout, 9)
            if "/http://" in request.full_url:
                raise TimeoutError("first")
            if "/https://" in request.full_url:
                return Response("## Transcript\n\nJust a moment")
            return Response("## Transcript\n\nsuccessful short transcript")

        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=urlopen):
            markdown, errors = mod.fetch_gateway("ShYKkPPhOoc", 9)

        self.assertEqual(markdown, "## Transcript\n\nsuccessful short transcript")
        first_position = errors.index("TimeoutError: first")
        third_position = errors.index("challenge marker: just a moment")
        self.assertLess(first_position, third_position)

    def test_fetch_gateway_returns_no_transcript_when_all_requests_fail(self):
        barrier = threading.Barrier(3, timeout=2)
        observed_timeouts = []
        observed_lock = threading.Lock()

        def urlopen(_request, timeout):
            with observed_lock:
                observed_timeouts.append(timeout)
            barrier.wait()
            raise ConnectionError("offline")

        with mock.patch.object(mod.urllib.request, "urlopen", side_effect=urlopen):
            markdown, errors = mod.fetch_gateway("ShYKkPPhOoc", 23)

        self.assertEqual(markdown, "")
        self.assertEqual(observed_timeouts, [23, 23, 23])
        self.assertEqual(errors.count("ConnectionError: offline"), 3)

    def test_main_accepts_short_transcript_and_keeps_video_id_diagnostic(self):
        markdown = "---\ntitle: Demo\n---\n\n## Transcript\n\nshort evidence"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.md"
            metadata = Path(directory) / "capture.json"
            with mock.patch.object(mod, "run_defuddle", return_value=(markdown, "")), \
                mock.patch.object(mod, "fetch_gateway") as gateway, \
                mock.patch.object(mod, "choose_metadata", return_value=("Demo", "", "", {})):
                with redirect_stdout(io.StringIO()):
                    result = mod.main(
                        [
                            "https://www.youtube.com/watch?v=ShYKkPPhOoc",
                            "--output",
                            str(output),
                            "--metadata-output",
                            str(metadata),
                        ]
                    )

            self.assertEqual(result, 0)
            gateway.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), markdown)
            evidence = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(evidence["video_id"], "ShYKkPPhOoc")
            self.assertEqual(evidence["word_count"], 2)
            self.assertEqual(evidence["completeness"], "unknown")

    def test_main_uses_gateway_after_missing_transcript(self):
        gateway_markdown = "## Transcript\n\nshort fallback evidence"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.md"
            with mock.patch.object(mod, "run_defuddle", return_value=("## Description\n\nmetadata", "")), \
                mock.patch.object(
                    mod,
                    "fetch_gateway",
                    return_value=(gateway_markdown, "https://defuddle.md/http://...: TimeoutError"),
                ) as gateway, \
                mock.patch.object(mod, "choose_metadata", return_value=("", "", "", {})):
                with redirect_stdout(io.StringIO()):
                    result = mod.main(
                        [
                            "ShYKkPPhOoc",
                            "--output",
                            str(output),
                            "--timeout",
                            "13",
                        ]
                    )

            self.assertEqual(result, 0)
            gateway.assert_called_once_with("ShYKkPPhOoc", 13)
            self.assertEqual(output.read_text(encoding="utf-8"), gateway_markdown)


if __name__ == "__main__":
    unittest.main()
