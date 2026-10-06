#!/usr/bin/env python3
"""Import an inspected full .excalidraw scene into a NEW plugin Markdown drawing.

Standard library only. Existing drawings are updated through the native plugin
workbench, never replaced by this adapter. Skeletons and pending Mermaid input
are not full scenes: use the deterministic generator or the plugin's addMermaid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

import excalidraw_scene as drawing


def import_scene(source: str, target: str, expected_source_sha256: str,
                 allow_overlaps: bool = False) -> drawing.WriteReport:
    """Preserve the full scene and assets, producing its native text index."""
    if not source.endswith(".excalidraw") or not target.endswith(".excalidraw.md"):
        raise drawing.SceneWriteError("explicit .excalidraw source and .excalidraw.md target required")
    for path in (source, target):
        absolute = os.path.abspath(path)
        if os.path.realpath(absolute) != absolute:
            raise drawing.SceneWriteError("symlink paths are refused")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_source_sha256):
        raise drawing.SceneWriteError("inspected source SHA-256 required")
    with open(source, "rb") as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != expected_source_sha256:
        raise drawing.SceneWriteError("source preimage changed")
    scene = json.loads(raw.decode("utf-8"))
    defects = drawing.validate_scene(scene)
    hard = [defect for defect in defects if not defect.startswith(drawing.OVERLAP_DEFECT_PREFIX)]
    overlaps = [defect for defect in defects if defect.startswith(drawing.OVERLAP_DEFECT_PREFIX)]
    if hard or overlaps and not allow_overlaps:
        raise drawing.SceneDefect(hard + ([] if allow_overlaps else overlaps))
    if "pendingMermaid" in scene:
        raise drawing.SceneWriteError("pending Mermaid is not a normalized scene")
    for element in scene["elements"]:
        version = element.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise drawing.SceneWriteError("full elements with version are required; skeleton input refused")
        if element["type"] == "image" and element.get("fileId") not in scene["files"]:
            raise drawing.SceneWriteError("image asset missing from full exported scene")
    for file_id, asset in scene["files"].items():
        if (not isinstance(asset, dict) or asset.get("id") != file_id
                or not isinstance(asset.get("dataURL"), str)
                or not asset["dataURL"].startswith("data:")
                or not isinstance(asset.get("mimeType"), str)):
            raise drawing.SceneWriteError("full embedded image data required")
    document = drawing.render_drawing(scene)
    # Plugin serialization indexes raw/original text, not its visually wrapped
    # display text. Keep the original scene payload itself unchanged.
    entries = []
    for element in scene["elements"]:
        if element["type"] != "text" or element.get("isDeleted"):
            continue
        body = next(element[key] for key in ("rawText", "originalText", "text")
                    if element.get(key) is not None)
        if not isinstance(body, str):
            raise drawing.SceneWriteError("raw/original text must be a string")
        entries.append(f"{body} ^{element['id']}")
    index = "\n\n".join(entries)
    start = document.index(drawing.TEXT_INDEX_HEADING) + len(drawing.TEXT_INDEX_HEADING) + 1
    end = document.index("\n\n%%\n", start)
    document = document[:start] + index + document[end:]
    with open(source, "rb") as stream:
        if stream.read() != raw:
            raise drawing.SceneWriteError("source changed during import preparation")
    return drawing._write_drawing(
        target, document, scene, allowed_overlaps=tuple(overlaps) if allow_overlaps else ()
    )


def main() -> int:
    """Run the explicit new-file import and print the materialized receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--allow-overlaps", action="store_true")
    args = parser.parse_args()
    try:
        report = import_scene(args.source, args.target, args.expected_source_sha256,
                              args.allow_overlaps)
    except (OSError, ValueError, drawing.SceneWriteError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report._asdict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
