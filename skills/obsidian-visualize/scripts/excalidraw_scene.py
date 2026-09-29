#!/usr/bin/env python3
"""Deterministic stdlib builder for Obsidian Excalidraw drawings.

An ``.excalidraw.md`` drawing is a file, not a live plugin object: YAML
frontmatter, a human-readable ``## Text Elements`` index, and one fenced JSON
scene. This module measures text, computes geometry, builds that scene, validates
it as pure JSON, and writes the native Obsidian Markdown wrapper.

Design contract:

* **Deterministic.** No clock, no PRNG, no process entropy. Element ids, ``seed``
  and ``versionNonce`` derive from ``(namespace, element kind, creation order,
  optional caller key)``, so re-running the same generator produces a
  byte-identical file. Ids do not depend on text, so relabelling a card keeps its
  id stable and the diff small.
* **Unicode-aware.** Advance width comes from ``unicodedata`` east-asian width
  plus a zero-width class for combining marks and format characters, so Hangul,
  CJK, kana, NFD sequences and emoji lay out without clipping.
* **Finite geometry.** Every coordinate and extent is checked for a real, finite
  value at construction time, not after the file is written.
* **Non-destructive.** A new drawing is created atomically and exclusively.
  Replacing an existing drawing requires ``overwrite=True`` *and* the sha256 of
  the exact bytes the caller inspected; the writer then diffs element ids and
  arrow bindings, replaces atomically, and reads the file back before returning.

What this module cannot do: it cannot prove the drawing renders. There is no
rasteriser and no SVG here, and an SVG built from the same data would not be
evidence that the Excalidraw plugin parses the file. Static validation
(:func:`validate_scene`) and rendered QA are separate gates; see ``../SKILL.md``
for the rendered-QA step and for how to report a drawing that was validated but
could not be rendered.

Typical use::

    from excalidraw_scene import Scene

    scene = Scene(namespace="Systems/Ingest Overview")
    ingest = scene.box(0, 0, 260, "Ingest\\ncollect raw events", 20, "#0369a1", "#ffffff")
    store = scene.box(420, 0, 260, "Store\\nappend to log", 20, "#334155", "#ffffff")
    scene.arrow(ingest, store, "events")
    defects = scene.check()
    assert not defects, defects
    report = scene.write("Systems/Ingest Overview.excalidraw.md")

Self-check: ``python3 excalidraw_scene.py`` builds a demo scene, validates it,
writes it into two temp directories, and asserts the two files are identical.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import unicodedata
from typing import Any, NamedTuple

# --------------------------------------------------------------------------- #
# Scene-level constants
# --------------------------------------------------------------------------- #

SCENE_TYPE = "excalidraw"
SCENE_VERSION = 2
SCENE_SOURCE = "https://github.com/zsviczian/obsidian-excalidraw-plugin"

PLUGIN_FRONTMATTER_KEY = "excalidraw-plugin"
PLUGIN_FRONTMATTER_VALUE = "parsed"

DRAWING_HEADING = "# Excalidraw Data"
TEXT_INDEX_HEADING = "## Text Elements"
SCENE_HEADING = "## Drawing"

#: Excalidraw ``fontFamily`` ids: 1 hand-drawn, 2 normal, 3 code.
FONT_FAMILY_NORMAL = 2
DEFAULT_LINE_HEIGHT = 1.25

ARROW_STROKE = "#1e293b"
LABEL_STROKE = "#475569"
LABEL_FONT_SIZE = 15

#: Advance width per character, as a multiple of ``fontSize``.
NARROW_RATIO = 0.6
WIDE_RATIO = 1.0
TAB_RATIO = NARROW_RATIO * 4

#: Overlapping filled rectangles are a layout heuristic, not a schema error. A
#: caller that stacks fills on purpose can drop defects carrying this prefix, and
#: must say so in its report.
OVERLAP_DEFECT_PREFIX = "overlap:"

#: Excalidraw stores a millisecond timestamp in ``updated``. A clock read here
#: would make two identical runs differ, so every generated element carries this
#: fixed value instead; the plugin overwrites it on the first real edit.
ELEMENT_UPDATED = 1

#: Anchor sides usable for arrow endpoints.
SIDES = ("top", "right", "bottom", "left")

_ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_ID_LENGTH = 10
_INT32_MAX = 2**31 - 1

_ZERO_WIDTH_CATEGORIES = frozenset({"Mn", "Me", "Cf"})
_WIDE_EAST_ASIAN_WIDTHS = frozenset({"W", "F"})

#: Conjoining Hangul jamo vowels and trailing consonants (grapheme-cluster classes
#: V and T, including the Extended-B block). They are ``Lo``, not marks, and are
#: not east-asian wide, so without this table a decomposed syllable would measure
#: wider than the precomposed one it renders as.
_ZERO_WIDTH_RANGES = ((0x1160, 0x11FF), (0xD7B0, 0xD7C6), (0xD7CB, 0xD7FB))

_ELEMENT_REQUIRED_KEYS = ("id", "type", "x", "y", "width", "height")


class SceneDefect(ValueError):
    """Raised instead of writing a scene that fails :func:`validate_scene`."""

    def __init__(self, defects):
        self.defects = tuple(defects)
        joined = "\n  ".join(self.defects)
        super().__init__(f"{len(self.defects)} scene defect(s):\n  {joined}")


class SceneWriteError(RuntimeError):
    """Raised when a write is unsafe, or when readback does not match intent."""


# --------------------------------------------------------------------------- #
# Numeric guards
# --------------------------------------------------------------------------- #


def _number(value, label):
    """Return ``value`` as a finite float, or raise with ``label`` in the message."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite, got {value!r}")
    return number


def _extent(value, label):
    number = _number(value, label)
    if number < 0:
        raise ValueError(f"{label} must be >= 0, got {number}")
    return number


def _positive(value, label):
    number = _number(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be > 0, got {number}")
    return number


def _color(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty color string, got {value!r}")
    return value


# --------------------------------------------------------------------------- #
# Deterministic identity
# --------------------------------------------------------------------------- #


def _digest(*parts):
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).digest()


def _encode_id(digest):
    value = int.from_bytes(digest, "big")
    base = len(_ID_ALPHABET)
    chars = []
    for _ in range(_ID_LENGTH):
        value, remainder = divmod(value, base)
        chars.append(_ID_ALPHABET[remainder])
    return "".join(reversed(chars))


def stable_int(*parts):
    """Deterministic ``1..2**31-1`` integer for Excalidraw ``seed``/``versionNonce``."""
    return 1 + int.from_bytes(_digest(*parts), "big") % _INT32_MAX


class _IdFactory:
    """Issues collision-free ids that depend only on namespace, kind and order."""

    def __init__(self, namespace):
        self._namespace = namespace
        self._counts: dict[str, int] = {}
        self._issued: set[str] = set()

    def issue(self, kind, key=None):
        ordinal = self._counts.get(kind, 0)
        self._counts[kind] = ordinal + 1
        if key is not None and not isinstance(key, str):
            raise TypeError(f"key must be a string or None, got {type(key).__name__}")
        seed = (self._namespace, kind, "k" if key else "n", key if key else ordinal)
        for attempt in range(64):
            candidate = _encode_id(_digest(*seed, attempt))
            if candidate not in self._issued:
                self._issued.add(candidate)
                return candidate
        raise RuntimeError(f"could not issue a unique id for {kind} after 64 attempts")


# --------------------------------------------------------------------------- #
# Unicode-aware text measurement
# --------------------------------------------------------------------------- #


def _zero_width(char):
    """True when ``char`` composes onto the character before it and adds no width."""
    if unicodedata.category(char) in _ZERO_WIDTH_CATEGORIES:
        return True
    code = ord(char)
    return any(low <= code <= high for low, high in _ZERO_WIDTH_RANGES)


def char_ratio(char):
    """Advance width of one character as a multiple of ``fontSize``.

    Combining marks, variation selectors, joiners, other format characters and
    conjoining Hangul jamo take no horizontal room, so a decomposed (NFD) string
    measures the same as its precomposed (NFC) form. East-asian *wide* and
    *fullwidth* characters — Hangul syllables, CJK ideographs, kana, fullwidth
    forms, most emoji — take a full ``fontSize``; everything else takes
    ``NARROW_RATIO``. This is a layout estimate, not font metrics: an emoji ZWJ
    sequence is over-measured because each pictograph counts, which widens the box
    instead of clipping it. When a real font clips, widen ``max_width`` rather than
    adding a metrics dependency.
    """
    if char == "\t":
        return TAB_RATIO
    if _zero_width(char):
        return 0.0
    if unicodedata.east_asian_width(char) in _WIDE_EAST_ASIAN_WIDTHS:
        return WIDE_RATIO
    return NARROW_RATIO


def text_width(line, font_size):
    """Estimated rendered width of a single line (no newline handling)."""
    size = _positive(font_size, "font_size")
    return sum(char_ratio(char) for char in str(line)) * size


def dims(text, font_size, line_height=DEFAULT_LINE_HEIGHT):
    """Return ``(width, height)`` for already-wrapped text."""
    size = _positive(font_size, "font_size")
    ratio = _positive(line_height, "line_height")
    lines = str(text).split("\n")
    width = max((text_width(line, size) for line in lines), default=0.0)
    return width, len(lines) * size * ratio


def _clusters(text):
    """Split into base-character clusters so marks never separate from their base."""
    clusters: list[str] = []
    for char in text:
        if clusters and char != "\t" and _zero_width(char):
            clusters[-1] += char
        else:
            clusters.append(char)
    return clusters


def _split_to_fit(word, font_size, max_width):
    """Break one unspaced run into pieces that each fit ``max_width``."""
    if text_width(word, font_size) <= max_width:
        return [word]
    pieces: list[str] = []
    current: list[str] = []
    current_width = 0.0
    for cluster in _clusters(word):
        cluster_width = text_width(cluster, font_size)
        if current and current_width + cluster_width > max_width:
            pieces.append("".join(current))
            current = []
            current_width = 0.0
        current.append(cluster)
        current_width += cluster_width
    if current:
        pieces.append("".join(current))
    return pieces or [""]


def wrap(text, font_size, max_width):
    """Wrap ``text`` to ``max_width``, breaking unspaced runs when needed.

    Explicit newlines survive as hard breaks. Runs of spaces inside a paragraph
    collapse to one. Every produced line fits ``max_width`` unless a single
    cluster is wider than ``max_width``, in which case it takes a line of its own.
    """
    size = _positive(font_size, "font_size")
    limit = _positive(max_width, "max_width")
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        words = [word for word in paragraph.split(" ") if word]
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            for index, piece in enumerate(_split_to_fit(word, size, limit)):
                if not current:
                    current = piece
                elif index == 0 and text_width(f"{current} {piece}", size) <= limit:
                    current = f"{current} {piece}"
                else:
                    lines.append(current)
                    current = piece
        lines.append(current)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Pure-JSON scene assembly and validation
# --------------------------------------------------------------------------- #


def build_scene(elements, view_background="#ffffff", grid_size=None):
    """Wrap a raw element list in the Excalidraw scene envelope."""
    return {
        "type": SCENE_TYPE,
        "version": SCENE_VERSION,
        "source": SCENE_SOURCE,
        "elements": list(elements),
        "appState": {"gridSize": grid_size, "viewBackgroundColor": view_background},
        "files": {},
    }


def _is_real_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _bbox(element):
    x = float(element["x"])
    y = float(element["y"])
    return x, y, x + float(element["width"]), y + float(element["height"])


def _overlaps(first, second):
    ax0, ay0, ax1, ay1 = _bbox(first)
    bx0, by0, bx1, by1 = _bbox(second)
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _validate_envelope(scene, defects):
    if scene.get("type") != SCENE_TYPE:
        defects.append(f"scene.type must be {SCENE_TYPE!r}, found {scene.get('type')!r}")
    version = scene.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        defects.append(f"scene.version must be an integer, found {version!r}")
    if not isinstance(scene.get("appState"), dict):
        defects.append("scene.appState must be an object")
    if not isinstance(scene.get("files"), dict):
        defects.append("scene.files must be an object")


def _validate_shape(element, position, defects):
    """Check one element's own fields. True when it is safe to cross-check."""
    if not isinstance(element, dict):
        defects.append(f"elements[{position}] must be an object, found {type(element).__name__}")
        return False
    missing = [key for key in _ELEMENT_REQUIRED_KEYS if key not in element]
    if missing:
        defects.append(f"elements[{position}] missing required key(s): {', '.join(missing)}")
        return False
    element_id = element["id"]
    if not isinstance(element_id, str) or not element_id:
        defects.append(f"elements[{position}].id must be a non-empty string, found {element_id!r}")
        return False
    if not isinstance(element.get("type"), str) or not element["type"]:
        defects.append(f"{element_id}.type must be a non-empty string")
    for key in ("x", "y", "width", "height"):
        if not _is_real_number(element[key]):
            defects.append(f"{element_id}.{key} must be a finite number, found {element[key]!r}")
        elif key in ("width", "height") and float(element[key]) < 0:
            defects.append(f"{element_id}.{key} must be >= 0, found {element[key]!r}")
    return True


def _validate_arrow_points(element, defects):
    element_id = element["id"]
    points = element.get("points")
    if not isinstance(points, list) or len(points) < 2:
        defects.append(f"arrow {element_id}.points must list at least two points")
        return
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            defects.append(f"arrow {element_id}.points[{index}] must be a two-number pair")
            continue
        if not all(_is_real_number(value) for value in point):
            defects.append(
                f"arrow {element_id}.points[{index}] must be finite, found {list(point)!r}"
            )
    first = points[0]
    if (
        isinstance(first, (list, tuple))
        and len(first) == 2
        and all(_is_real_number(value) for value in first)
        and (float(first[0]) != 0.0 or float(first[1]) != 0.0)
    ):
        defects.append(
            f"arrow {element_id}.points[0] must be [0, 0] because points are relative "
            f"to the arrow origin, found {list(first)!r}"
        )


def _mirrored(host, member_id, kind):
    bound = host.get("boundElements")
    if not isinstance(bound, list):
        return False
    return any(
        isinstance(entry, dict) and entry.get("id") == member_id and entry.get("type") == kind
        for entry in bound
    )


def _binding_targets(element):
    return {
        element[key]["elementId"]
        for key in ("startBinding", "endBinding")
        if isinstance(element.get(key), dict) and "elementId" in element[key]
    }


def _validate_arrow_bindings(element, by_id, defects):
    element_id = element["id"]
    for key in ("startBinding", "endBinding"):
        binding = element.get(key)
        if binding is None:
            continue
        if not isinstance(binding, dict) or "elementId" not in binding:
            defects.append(f"{element_id}.{key} must be an object carrying elementId")
            continue
        for numeric_key in ("focus", "gap"):
            if numeric_key in binding and not _is_real_number(binding[numeric_key]):
                defects.append(f"{element_id}.{key}.{numeric_key} must be a finite number")
        target_id = binding["elementId"]
        if target_id == element_id:
            defects.append(f"{element_id}.{key} binds the arrow to itself")
            continue
        target = by_id.get(target_id)
        if target is None:
            defects.append(f"{element_id}.{key} -> missing element {target_id!r}")
        elif not _mirrored(target, element_id, "arrow"):
            defects.append(f"{element_id} is not mirrored in {target_id}.boundElements as an arrow")


def _validate_membership(element, by_id, defects):
    element_id = element["id"]
    if element.get("type") == "text" and element.get("containerId") is not None:
        container_id = element["containerId"]
        container = by_id.get(container_id)
        if container is None:
            defects.append(f"text {element_id}.containerId -> missing element {container_id!r}")
        elif not _mirrored(container, element_id, "text"):
            defects.append(
                f"text {element_id} is not mirrored in container {container_id}.boundElements"
            )

    frame_id = element.get("frameId")
    if frame_id is not None:
        frame = by_id.get(frame_id)
        if frame is None:
            defects.append(f"{element_id}.frameId -> missing element {frame_id!r}")
        elif frame.get("type") != "frame":
            defects.append(
                f"{element_id}.frameId -> {frame_id} is a {frame.get('type')!r}, not a frame"
            )

    bound = element.get("boundElements")
    if bound is not None and not isinstance(bound, list):
        defects.append(f"{element_id}.boundElements must be a list")
        return
    for entry in bound or []:
        if not isinstance(entry, dict) or "id" not in entry or "type" not in entry:
            defects.append(
                f"{element_id}.boundElements entry must carry id and type, found {entry!r}"
            )
            continue
        member = by_id.get(entry["id"])
        if member is None:
            defects.append(f"{element_id}.boundElements -> missing element {entry['id']!r}")
            continue
        if entry["type"] == "text" and member.get("containerId") != element_id:
            defects.append(
                f"{element_id}.boundElements lists text {entry['id']} whose containerId "
                f"is {member.get('containerId')!r}"
            )
        if entry["type"] == "arrow" and element_id not in _binding_targets(member):
            defects.append(
                f"{element_id}.boundElements lists arrow {entry['id']} which has no "
                "binding back to it"
            )


def validate_scene(scene):
    """Validate a pure-JSON Excalidraw scene; an empty result means safe to write.

    Checks the envelope, then per element: required keys, non-empty string ids,
    unique ids, finite non-negative geometry, arrow ``points`` (two or more,
    finite, first exactly ``[0, 0]``), two-way arrow bindings, two-way bound-text
    ``containerId``, ``frameId`` resolving to a real frame, ``boundElements``
    entries resolving back to their host, and overlapping filled rectangles
    (prefixed with :data:`OVERLAP_DEFECT_PREFIX`).
    """
    if not isinstance(scene, dict):
        return [f"scene must be a JSON object, found {type(scene).__name__}"]

    defects: list[str] = []
    _validate_envelope(scene, defects)

    elements = scene.get("elements")
    if not isinstance(elements, list):
        defects.append(f"scene.elements must be a list, found {type(elements).__name__}")
        return defects

    by_id: dict[str, dict] = {}
    checkable: list[dict] = []
    for position, element in enumerate(elements):
        if not _validate_shape(element, position, defects):
            continue
        element_id = element["id"]
        if element_id in by_id:
            defects.append(f"duplicate element id {element_id!r}")
        by_id[element_id] = element
        checkable.append(element)

    for element in checkable:
        kind = element.get("type")
        if kind == "arrow":
            _validate_arrow_points(element, defects)
        if kind == "text":
            if not isinstance(element.get("text"), str):
                defects.append(f"text {element['id']}.text must be a string")
            if "fontSize" in element and not _is_real_number(element["fontSize"]):
                defects.append(f"text {element['id']}.fontSize must be a finite number")
        _validate_arrow_bindings(element, by_id, defects)
        _validate_membership(element, by_id, defects)

    cards = [
        element
        for element in checkable
        if element.get("type") == "rectangle"
        and not element.get("isDeleted")
        and element.get("backgroundColor", "transparent") != "transparent"
        and all(_is_real_number(element[key]) for key in ("x", "y", "width", "height"))
    ]
    for index, first in enumerate(cards):
        for second in cards[index + 1 :]:
            if _overlaps(first, second):
                defects.append(
                    f"{OVERLAP_DEFECT_PREFIX} filled rectangles {first['id']} and {second['id']}"
                )
    return defects


def validate_scene_json(text):
    """Validate a scene supplied as JSON text; a parse failure is the only defect."""
    try:
        scene = json.loads(text)
    except (TypeError, ValueError) as error:
        return [f"scene is not parseable JSON: {error}"]
    return validate_scene(scene)


def scene_summary(scene):
    """Counts and bounds for comparing a generated scene against what a viewer loads.

    This is arithmetic over the file, not a rendering check. Use it to confirm an
    opened view reports the element count this generator produced.
    """
    elements = [
        element
        for element in scene.get("elements", [])
        if isinstance(element, dict) and not element.get("isDeleted")
    ]
    counts: dict[str, int] = {}
    for element in elements:
        kind = str(element.get("type"))
        counts[kind] = counts.get(kind, 0) + 1
    boxes = [
        _bbox(element)
        for element in elements
        if all(_is_real_number(element.get(key)) for key in ("x", "y", "width", "height"))
    ]
    bounds = None
    if boxes:
        bounds = {
            "min_x": min(box[0] for box in boxes),
            "min_y": min(box[1] for box in boxes),
            "max_x": max(box[2] for box in boxes),
            "max_y": max(box[3] for box in boxes),
        }
    return {"total": len(elements), "by_type": dict(sorted(counts.items())), "bounds": bounds}


# --------------------------------------------------------------------------- #
# Element construction
# --------------------------------------------------------------------------- #

Element = dict[str, Any]

_TEXT_ALIGNMENTS = ("left", "center", "right")
_TEXT_VERTICAL_ALIGNMENTS = ("top", "middle", "bottom")

#: Keys a caller may not override through ``**style``: identity and determinism.
_RESERVED_KEYS = ("id", "type", "seed", "versionNonce")


def _side_point(element, side):
    """Absolute anchor point on one side of an element's bounding box."""
    if side not in SIDES:
        raise ValueError(f"side must be one of {', '.join(SIDES)}, got {side!r}")
    x = _number(element["x"], "element.x")
    y = _number(element["y"], "element.y")
    width = _extent(element["width"], "element.width")
    height = _extent(element["height"], "element.height")
    if side == "left":
        return x, y + height / 2
    if side == "right":
        return x + width, y + height / 2
    if side == "top":
        return x + width / 2, y
    return x + width / 2, y + height


def _bind(host, member_id, kind):
    """Add the mirrored ``boundElements`` entry the plugin needs on reload."""
    bound = host.setdefault("boundElements", [])
    if not isinstance(bound, list):
        raise TypeError(f"{host.get('id')!r}.boundElements is not a list")
    if not _mirrored(host, member_id, kind):
        bound.append({"type": kind, "id": member_id})


class Scene:
    """Builds the element list for exactly one drawing file.

    One ``Scene`` per output file. ``namespace`` is the only entropy source: it
    seeds every element id, ``seed`` and ``versionNonce``, so the same namespace
    plus the same calls in the same order produce byte-identical output. Use the
    vault-relative drawing path as the namespace unless two drawings must share
    ids on purpose.

    Every builder returns the created element dict. Mutate the returned dict to
    adjust style; pass it back to :meth:`arrow`, :meth:`group` or
    :meth:`add_to_frame` to relate elements. An element from another ``Scene`` is
    rejected rather than silently written as a dangling binding.
    """

    def __init__(self, namespace, view_background="#ffffff", grid_size=None):
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError(f"namespace must be a non-empty string, got {namespace!r}")
        self.namespace = namespace
        self.view_background = _color(view_background, "view_background")
        self.grid_size = None if grid_size is None else _positive(grid_size, "grid_size")
        self.elements: list[Element] = []
        self._ids = _IdFactory(namespace)
        self._by_id: dict[str, Element] = {}

    # -- membership ------------------------------------------------------- #

    def _member(self, element, label):
        """Return ``element`` after proving it is this scene's own object."""
        if not isinstance(element, dict) or "id" not in element:
            raise TypeError(f"{label} must be an element dict from this scene, got {element!r}")
        known = self._by_id.get(element["id"])
        if known is not element:
            raise ValueError(
                f"{label} element {element['id']!r} does not belong to this scene; "
                "binding across scenes would write a dangling reference"
            )
        return element

    # -- primitives ------------------------------------------------------- #

    def _base(self, kind, x, y, width, height, stroke, background="transparent", key=None, **style):
        reserved = [name for name in _RESERVED_KEYS if name in style]
        if reserved:
            raise ValueError(f"{', '.join(reserved)} is derived, not overridable")
        element_id = self._ids.issue(kind, key)
        element: Element = {
            "id": element_id,
            "type": kind,
            "x": _number(x, f"{kind}.x"),
            "y": _number(y, f"{kind}.y"),
            "width": _extent(width, f"{kind}.width"),
            "height": _extent(height, f"{kind}.height"),
            "angle": 0,
            "strokeColor": _color(stroke, f"{kind}.strokeColor"),
            "backgroundColor": _color(background, f"{kind}.backgroundColor"),
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": stable_int(self.namespace, kind, element_id, "seed"),
            "version": 1,
            "versionNonce": stable_int(self.namespace, kind, element_id, "versionNonce"),
            "isDeleted": False,
            "boundElements": [],
            "updated": ELEMENT_UPDATED,
            "link": None,
            "locked": False,
        }
        element.update(style)
        for axis in ("x", "y"):
            _number(element[axis], f"{kind}.{axis}")
        for extent in ("width", "height"):
            _extent(element[extent], f"{kind}.{extent}")
        self.elements.append(element)
        self._by_id[element_id] = element
        return element

    def rect(self, x, y, width, height, stroke, background="transparent", key=None, **style):
        """Rounded rectangle. Pass ``roundness=None`` for square corners."""
        style.setdefault("roundness", {"type": 3})
        return self._base("rectangle", x, y, width, height, stroke, background, key, **style)

    def text(
        self,
        x,
        y,
        body,
        font_size,
        color,
        max_width=None,
        container=None,
        align="left",
        valign="top",
        link=None,
        key=None,
        **style,
    ):
        """Text element measured with :func:`dims`; wrapped first when ``max_width`` is set.

        Passing ``container`` writes ``containerId`` *and* the mirrored entry in
        the container's ``boundElements``, because the plugin needs both halves.
        """
        if align not in _TEXT_ALIGNMENTS:
            raise ValueError(f"align must be one of {', '.join(_TEXT_ALIGNMENTS)}, got {align!r}")
        if valign not in _TEXT_VERTICAL_ALIGNMENTS:
            raise ValueError(
                f"valign must be one of {', '.join(_TEXT_VERTICAL_ALIGNMENTS)}, got {valign!r}"
            )
        size = _positive(font_size, "font_size")
        content = str(body)
        if max_width is not None:
            content = wrap(content, size, max_width)
        width, height = dims(content, size)
        container_id = None
        if container is not None:
            container_id = self._member(container, "container")["id"]
        element = self._base(
            "text",
            x,
            y,
            width,
            height,
            color,
            "transparent",
            key,
            text=content,
            rawText=content,
            originalText=content,
            fontSize=size,
            fontFamily=FONT_FAMILY_NORMAL,
            textAlign=align,
            verticalAlign=valign,
            containerId=container_id,
            autoResize=True,
            lineHeight=DEFAULT_LINE_HEIGHT,
            link=link,
            **style,
        )
        if container_id is not None:
            _bind(self._by_id[container_id], element["id"], "text")
        return element

    def box(
        self,
        x,
        y,
        width,
        body,
        font_size,
        stroke,
        background,
        link=None,
        pad_x=14,
        pad_y=10,
        text_color=None,
        dashed=False,
        min_height=0,
        key=None,
    ):
        """Card: one rectangle plus one bound label, height fitted to the wrapped text.

        Returns the *rectangle*, which is what :meth:`arrow` binds to. The label
        is wrapped to ``width - 2 * pad_x``, so a card never clips its own text
        unless a single unbreakable cluster is wider than that.
        """
        size = _positive(font_size, "font_size")
        outer = _positive(width, "width")
        inset_x = _extent(pad_x, "pad_x")
        inset_y = _extent(pad_y, "pad_y")
        inner = outer - 2 * inset_x
        if inner <= 0:
            raise ValueError(f"width {outer} leaves no room for pad_x {inset_x} on both sides")
        content = wrap(body, size, inner)
        _, text_height = dims(content, size)
        height = max(text_height + 2 * inset_y, _extent(min_height, "min_height"))
        rectangle = self.rect(
            x,
            y,
            outer,
            height,
            stroke,
            background,
            key,
            link=link,
            strokeStyle="dashed" if dashed else "solid",
        )
        self.text(
            x + inset_x,
            y + inset_y,
            content,
            size,
            text_color or stroke,
            container=rectangle,
            align="center",
            valign="middle",
            key=None if key is None else f"{key}/label",
        )
        return rectangle

    def arrow(
        self,
        start,
        end,
        label=None,
        start_side="right",
        end_side="left",
        dashed=False,
        elbow_y=None,
        gap=6,
        key=None,
    ):
        """Two-way bound arrow between two elements of this scene.

        ``points`` are relative to the arrow's own origin and always start at
        ``[0, 0]``. The route elbows through the midpoint when the two anchor
        sides do not line up, or through ``elbow_y`` when given. ``label`` becomes
        a bound text element centred on the route's midpoint.
        """
        head = self._member(start, "start")
        tail = self._member(end, "end")
        if head is tail:
            raise ValueError(f"an arrow cannot bind element {head['id']!r} to itself")
        start_x, start_y = _side_point(head, start_side)
        end_x, end_y = _side_point(tail, end_side)
        if elbow_y is not None:
            elbow = _number(elbow_y, "elbow_y")
            route = [(start_x, start_y), (start_x, elbow), (end_x, elbow), (end_x, end_y)]
        elif start_side in ("left", "right") and abs(start_y - end_y) > 2:
            middle = (start_x + end_x) / 2
            route = [(start_x, start_y), (middle, start_y), (middle, end_y), (end_x, end_y)]
        elif start_side in ("top", "bottom") and abs(start_x - end_x) > 2:
            middle = (start_y + end_y) / 2
            route = [(start_x, start_y), (start_x, middle), (end_x, middle), (end_x, end_y)]
        else:
            route = [(start_x, start_y), (end_x, end_y)]
        points = [[point_x - start_x, point_y - start_y] for point_x, point_y in route]
        span_x = [point[0] for point in points]
        span_y = [point[1] for point in points]
        binding_gap = _extent(gap, "gap")
        element = self._base(
            "arrow",
            start_x,
            start_y,
            max(span_x) - min(span_x),
            max(span_y) - min(span_y),
            ARROW_STROKE,
            "transparent",
            key,
            points=points,
            startArrowhead=None,
            endArrowhead="arrow",
            strokeStyle="dashed" if dashed else "solid",
            startBinding={"elementId": head["id"], "focus": 0, "gap": binding_gap},
            endBinding={"elementId": tail["id"], "focus": 0, "gap": binding_gap},
        )
        _bind(head, element["id"], "arrow")
        _bind(tail, element["id"], "arrow")
        if label is not None:
            width, height = dims(str(label), LABEL_FONT_SIZE)
            middle_x = (route[0][0] + route[-1][0]) / 2
            middle_y = (route[0][1] + route[-1][1]) / 2
            self.text(
                middle_x - width / 2,
                middle_y - height / 2,
                label,
                LABEL_FONT_SIZE,
                LABEL_STROKE,
                container=element,
                align="center",
                valign="middle",
                key=None if key is None else f"{key}/label",
            )
        return element

    def frame(self, x, y, width, height, name, key=None, **style):
        """Frame element. Create it before its members so it sits behind them."""
        if not isinstance(name, str) or not name:
            raise ValueError(f"frame name must be a non-empty string, got {name!r}")
        return self._base(
            "frame",
            x,
            y,
            width,
            height,
            LABEL_STROKE,
            "transparent",
            key,
            name=name,
            roundness=None,
            **style,
        )

    def add_to_frame(self, frame, *members):
        """Set ``frameId`` on each member; returns the frame."""
        host = self._member(frame, "frame")
        if host.get("type") != "frame":
            raise ValueError(f"{host['id']!r} is a {host.get('type')!r}, not a frame")
        for member in members:
            self._member(member, "frame member")["frameId"] = host["id"]
        return host

    def group(self, *members, key=None):
        """Give every member a shared deterministic ``groupIds`` entry; returns its id."""
        if len(members) < 2:
            raise ValueError("a group needs at least two members")
        group_id = self._ids.issue("group", key)
        for member in members:
            element = self._member(member, "group member")
            groups = element.setdefault("groupIds", [])
            if group_id not in groups:
                groups.append(group_id)
        return group_id

    # -- inspection ------------------------------------------------------- #

    def to_scene(self):
        """The pure-JSON scene object, envelope included."""
        return build_scene(self.elements, self.view_background, self.grid_size)

    def check(self, ignore_overlaps=False):
        """Run :func:`validate_scene`; empty means safe to write.

        ``ignore_overlaps=True`` drops :data:`OVERLAP_DEFECT_PREFIX` defects for a
        layout that stacks fills deliberately. Say so in the report when you use it.
        """
        defects = validate_scene(self.to_scene())
        if ignore_overlaps:
            return [defect for defect in defects if not defect.startswith(OVERLAP_DEFECT_PREFIX)]
        return defects

    def summary(self):
        """Element counts and bounds; see :func:`scene_summary`."""
        return scene_summary(self.to_scene())

    def render(self, frontmatter=None, description=""):
        """The full ``.excalidraw.md`` document as text, without touching the disk."""
        return render_drawing(self.to_scene(), frontmatter, description)

    def write(
        self,
        path,
        frontmatter=None,
        description="",
        overwrite=False,
        expected_sha256=None,
        allow_overlaps=False,
    ):
        """Validate, write atomically, read back, and return a :class:`WriteReport`.

        Raises :class:`SceneDefect` before touching the disk when
        :meth:`check` is non-empty, and :class:`SceneWriteError` when the write
        would clobber something, when ``expected_sha256`` does not match the bytes
        already on disk, or when readback does not reproduce what was intended.
        """
        blocking = self.check(ignore_overlaps=allow_overlaps)
        if blocking:
            raise SceneDefect(blocking)
        allowed = ()
        if allow_overlaps:
            allowed = tuple(
                defect for defect in self.check() if defect.startswith(OVERLAP_DEFECT_PREFIX)
            )
        scene = self.to_scene()
        document = render_drawing(scene, frontmatter, description)
        return _write_drawing(
            path,
            document,
            scene,
            overwrite=overwrite,
            expected_sha256=expected_sha256,
            allowed_overlaps=allowed,
        )


# --------------------------------------------------------------------------- #
# Markdown document assembly
# --------------------------------------------------------------------------- #

_FRONTMATTER_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")

#: The plugin can also store the scene as ``compressed-json``. That is codec
#: output, not something to author or hand-edit, and this module refuses to read
#: or produce it.
COMPRESSED_FENCE = "```compressed-json"


def _frontmatter_scalar(value, key):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"frontmatter {key!r} must be finite, got {value!r}")
        return str(value)
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValueError(f"frontmatter {key!r} must be a single line, got {text!r}")
    return text


def _frontmatter_block(frontmatter):
    """Render the YAML block, with the plugin marker first and always ``parsed``."""
    fields: dict[str, Any] = {PLUGIN_FRONTMATTER_KEY: PLUGIN_FRONTMATTER_VALUE}
    for key, value in dict(frontmatter or {}).items():
        if not isinstance(key, str) or not _FRONTMATTER_KEY.match(key):
            raise ValueError(f"frontmatter key {key!r} is not a plain YAML key")
        if key == PLUGIN_FRONTMATTER_KEY and value != PLUGIN_FRONTMATTER_VALUE:
            raise ValueError(
                f"this writer only emits plain JSON, so {PLUGIN_FRONTMATTER_KEY} must stay "
                f"{PLUGIN_FRONTMATTER_VALUE!r}, got {value!r}"
            )
        fields[key] = value
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            rendered = "[" + ", ".join(_frontmatter_scalar(item, key) for item in value) + "]"
        else:
            rendered = _frontmatter_scalar(value, key)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines)


def _text_index(scene):
    """The human-readable ``## Text Elements`` index, in element order."""
    entries = [
        f"{element['text']} ^{element['id']}"
        for element in scene.get("elements", [])
        if isinstance(element, dict)
        and element.get("type") == "text"
        and not element.get("isDeleted")
        and isinstance(element.get("text"), str)
        and isinstance(element.get("id"), str)
    ]
    return "\n\n".join(entries)


def render_drawing(scene, frontmatter=None, description=""):
    """Assemble the native ``.excalidraw.md`` document for a validated scene.

    Layout, top to bottom: YAML frontmatter carrying ``excalidraw-plugin: parsed``,
    the optional plaintext description, ``# Excalidraw Data``, the
    ``## Text Elements`` index, and the ``## Drawing`` JSON fence inside a ``%%``
    comment pair so reading the note shows the description rather than the scene.
    Unicode is written literally (``ensure_ascii=False``); non-finite numbers are
    refused rather than emitted as invalid JSON.
    """
    defects = validate_scene(scene)
    hard = [defect for defect in defects if not defect.startswith(OVERLAP_DEFECT_PREFIX)]
    if hard:
        raise SceneDefect(hard)
    note = str(description).rstrip()
    if DRAWING_HEADING in note or "```" in note:
        raise ValueError("description must not contain a drawing heading or a code fence")
    parts = [_frontmatter_block(frontmatter), ""]
    if note:
        parts += [note, ""]
    parts += [
        DRAWING_HEADING,
        "",
        TEXT_INDEX_HEADING,
        _text_index(scene),
        "",
        "%%",
        SCENE_HEADING,
        "```json",
        json.dumps(scene, ensure_ascii=False, indent=1, allow_nan=False),
        "```",
        "%%",
    ]
    return "\n".join(parts) + "\n"


def extract_scene(document):
    """Return the scene object embedded in an ``.excalidraw.md`` document.

    Reads the fence that follows the last ``## Drawing`` heading, so a JSON fence
    quoted in the description is not mistaken for the scene.
    """
    text = str(document)
    heading = text.rfind(SCENE_HEADING)
    if heading < 0:
        raise SceneWriteError(f"document carries no {SCENE_HEADING!r} section")
    tail = text[heading:]
    if COMPRESSED_FENCE in tail:
        raise SceneWriteError(
            "the drawing stores its scene as compressed-json; this module neither reads "
            "nor writes that codec. Switch the drawing to plain JSON in the plugin first."
        )
    opening = tail.find("```json\n")
    if opening < 0:
        raise SceneWriteError("document carries no ```json drawing fence")
    body = tail[opening + len("```json\n") :]
    closing = body.find("\n```")
    if closing < 0:
        raise SceneWriteError("the ```json drawing fence is unterminated")
    try:
        scene = json.loads(body[:closing])
    except ValueError as error:
        raise SceneWriteError(f"the drawing fence is not parseable JSON: {error}") from error
    if not isinstance(scene, dict):
        raise SceneWriteError(f"the drawing fence holds a {type(scene).__name__}, not an object")
    return scene


# --------------------------------------------------------------------------- #
# Non-destructive writing
# --------------------------------------------------------------------------- #


class WriteReport(NamedTuple):
    """What actually landed on disk. Quote these fields in the task report."""

    path: str
    sha256: str
    size: int
    replaced: bool
    summary: dict[str, Any]
    added_ids: tuple[str, ...]
    removed_ids: tuple[str, ...]
    binding_changes: tuple[str, ...]
    allowed_overlaps: tuple[str, ...]


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def read_drawing(path):
    """Return ``(document_text, sha256, scene)`` for an existing drawing.

    The digest is over the exact bytes read. Pass it back as ``expected_sha256``
    to replace that drawing; anything else means the caller never inspected the
    file it is about to overwrite.
    """
    with open(path, "rb") as stream:
        raw = stream.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SceneWriteError(f"{path} is not UTF-8 text: {error}") from error
    return text, _sha256(raw), extract_scene(text)


def _element_ids(scene):
    return {
        element["id"]
        for element in scene.get("elements", [])
        if isinstance(element, dict) and isinstance(element.get("id"), str)
    }


def _bindings(scene):
    """``(arrow id, which end, target id)`` triples, for before/after diffing."""
    pairs = set()
    for element in scene.get("elements", []):
        if not isinstance(element, dict) or element.get("type") != "arrow":
            continue
        for key in ("startBinding", "endBinding"):
            binding = element.get(key)
            if isinstance(binding, dict) and isinstance(binding.get("elementId"), str):
                pairs.add((str(element.get("id")), key, binding["elementId"]))
    return pairs


def _binding_changes(before, after):
    removed = sorted(f"- {arrow}.{end} -> {target}" for arrow, end, target in before - after)
    added = sorted(f"+ {arrow}.{end} -> {target}" for arrow, end, target in after - before)
    return tuple(removed + added)


def _create_exclusive(temp_path, path, payload):
    """Publish ``temp_path`` as ``path``, failing if ``path`` already exists.

    A hard link is atomic and exclusive in one step. Filesystems without link
    support (exFAT sticks, some network mounts) fall back to an ``O_EXCL`` create,
    which is still exclusive but publishes the bytes in place.
    """
    try:
        os.link(temp_path, path)
        return
    except FileExistsError as error:
        raise SceneWriteError(f"{path} appeared while this write was in flight") from error
    except OSError:
        pass
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise SceneWriteError(f"{path} appeared while this write was in flight") from error
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _write_atomic(path, payload, replace):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(prefix=".excalidraw-scene-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temp_path, path)
        else:
            _create_exclusive(temp_path, path, payload)
    finally:
        if os.path.lexists(temp_path):
            os.unlink(temp_path)


def _write_drawing(
    path, document, scene, overwrite=False, expected_sha256=None, allowed_overlaps=()
):
    """Write ``document`` to ``path`` without ever clobbering unexamined bytes."""
    if not isinstance(path, str) or not path.strip():
        raise SceneWriteError(f"path must be a non-empty string, got {path!r}")
    if not path.endswith(".md"):
        raise SceneWriteError(
            f"an Excalidraw drawing is Markdown and must end in .md (usually "
            f".excalidraw.md), got {path!r}"
        )
    if os.path.isdir(path):
        raise SceneWriteError(f"{path} is a directory")
    if os.path.islink(path):
        raise SceneWriteError(f"{path} is a symlink; writing through it would edit its target")

    exists = os.path.lexists(path)
    before_ids: set[str] = set()
    before_bindings: set[tuple[str, str, str]] = set()
    if exists:
        if not overwrite:
            raise SceneWriteError(
                f"refusing to overwrite the existing drawing {path}. A new visualization is a "
                "new file; to replace this exact drawing, read it with read_drawing(), keep a "
                "backup, and pass overwrite=True with expected_sha256=<that digest>."
            )
        if not isinstance(expected_sha256, str) or not expected_sha256.strip():
            raise SceneWriteError(
                f"replacing {path} requires expected_sha256, the digest of the exact bytes you "
                "inspected; without it the replacement is a blind overwrite."
            )
        _, current_digest, current_scene = read_drawing(path)
        if current_digest != expected_sha256.strip().lower():
            raise SceneWriteError(
                f"{path} changed since you inspected it: expected {expected_sha256}, found "
                f"{current_digest}. Re-read the drawing and re-check the diff before replacing it."
            )
        before_ids = _element_ids(current_scene)
        before_bindings = _bindings(current_scene)
    elif expected_sha256 is not None:
        raise SceneWriteError(
            f"expected_sha256 was supplied but {path} does not exist; the drawing you inspected "
            "is not the file you are about to write."
        )

    payload = document.encode("utf-8")
    intended_digest = _sha256(payload)
    _write_atomic(path, payload, replace=exists)

    stored_text, stored_digest, stored_scene = read_drawing(path)
    if stored_digest != intended_digest:
        raise SceneWriteError(
            f"readback of {path} does not match what was written: intended {intended_digest}, "
            f"found {stored_digest}"
        )
    readback_defects = [
        defect
        for defect in validate_scene(stored_scene)
        if not defect.startswith(OVERLAP_DEFECT_PREFIX)
    ]
    if readback_defects:
        raise SceneWriteError(f"the drawing on disk does not validate: {readback_defects}")
    after_ids = _element_ids(stored_scene)
    if after_ids != _element_ids(scene):
        raise SceneWriteError(f"readback of {path} lost or renamed element ids")
    for element in stored_scene.get("elements", []):
        if element.get("type") == "text" and f"^{element['id']}" not in stored_text:
            raise SceneWriteError(
                f"text element {element['id']} is missing from the {TEXT_INDEX_HEADING} index"
            )

    return WriteReport(
        path=path,
        sha256=stored_digest,
        size=len(payload),
        replaced=exists,
        summary=scene_summary(stored_scene),
        added_ids=tuple(sorted(after_ids - before_ids)) if exists else (),
        removed_ids=tuple(sorted(before_ids - after_ids)) if exists else (),
        binding_changes=_binding_changes(before_bindings, _bindings(stored_scene)) if exists else (),
        allowed_overlaps=tuple(allowed_overlaps),
    )


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #


def _demo():
    """Three cards and two labelled arrows, built the way a real generator would."""
    scene = Scene(namespace="obsidian-visualize/self-check")
    ingest = scene.box(0, 0, 260, "Ingest\ncollect raw events", 20, "#0369a1", "#ffffff")
    normalize = scene.box(420, 0, 260, "Normalize\nvalidate and shape", 20, "#0f766e", "#ffffff")
    store = scene.box(840, 0, 260, "Store\nappend to the log", 20, "#334155", "#ffffff")
    scene.arrow(ingest, normalize, "events")
    scene.arrow(normalize, store, "records")
    return scene


def _self_check():
    scene = _demo()
    defects = scene.check()
    assert not defects, defects
    assert text_width("e\u0301", 20) == text_width("e", 20), "a combining mark must add no width"

    first_dir = tempfile.mkdtemp(prefix="excalidraw-scene-a-")
    second_dir = tempfile.mkdtemp(prefix="excalidraw-scene-b-")
    note = "Self-check demo scene."
    first = scene.write(os.path.join(first_dir, "Demo.excalidraw.md"), description=note)
    second = _demo().write(os.path.join(second_dir, "Demo.excalidraw.md"), description=note)
    assert first.sha256 == second.sha256, "re-running the generator must be byte-identical"

    try:
        _demo().write(first.path, description=note)
    except SceneWriteError:
        pass
    else:
        raise AssertionError("writing over an existing drawing must be refused")

    _, digest, stored = read_drawing(first.path)
    assert digest == first.sha256
    assert not validate_scene(stored)
    replaced = _demo().write(
        first.path, description=note, overwrite=True, expected_sha256=digest
    )
    assert replaced.replaced and not replaced.added_ids and not replaced.removed_ids
    assert not replaced.binding_changes, replaced.binding_changes

    print(
        f"ok elements={first.summary['total']} "
        f"types={first.summary['by_type']} defects=0 "
        f"sha256={first.sha256[:12]} wrote={first.path}"
    )


if __name__ == "__main__":
    _self_check()
