#!/usr/bin/env python3
"""Semantic tests for the formats these packages own.

Four distinct subjects, deliberately not mixed:

1. **Authored documentation.** Every JSON and YAML example shipped in a package
   is parsed with a real parser and checked against the rules that package
   documents. A broken example is a defect in the package.
2. **Shipped tools.** ``skills/obsidian-doctor/scripts/diagnose.py`` is executed
   as a subprocess over synthetic evidence bundles.
3. **Shipped helper scripts.** The two Python helpers are parsed with ``ast`` at
   the Python 3.9 grammar level and their import surface is read. That is
   syntax, not a run: no 3.9 interpreter is involved and neither script is
   executed by those tests.
4. **Recorded evidence.** The reports under ``tests/evidence`` and the rows
   ``docs/verification-matrix.md`` publishes from them are checked against each
   other, so a result cannot be published at a level the report never recorded.

The checkers below are test infrastructure, not a product. They are kept honest
by the malformed fixtures in ``fixtures/neutral-vault/fixture.json``: a checker
that accepted everything would fail those negative controls.

Evidence boundary: parsing a fixture proves a static property of the text. It is
not evidence that Obsidian rendered a canvas, that a Bases view materialised,
that the Web Clipper extension imported a template, or that a plugin ran.
Reading a recorded report proves what a past run wrote down, never that the run
happened again here. No test in this file touches a vault, a profile, or a
network.

Run:  python3 -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import ast
import datetime
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "neutral-vault" / "fixture.json"
DIAGNOSE = SKILLS_DIR / "obsidian-doctor" / "scripts" / "diagnose.py"

FIXTURE = json.loads(FIXTURE_PATH.read_text("utf-8"))

FENCE_RE = re.compile(r"^```(json|yaml)[ \t]*$\n(.*?)^```[ \t]*$", re.M | re.S)
UPSTREAM_IMPORT_MARKER = "Imported unmodified from"
ELISION = "\u2026"  # an authored ellipsis marks a deliberately abbreviated sample
WRONG_MARKER = "# WRONG"


# --------------------------------------------------------------------------- #
# fence extraction
# --------------------------------------------------------------------------- #
class Fence:
    __slots__ = ("path", "line", "lang", "text")

    def __init__(self, path: Path, line: int, lang: str, text: str):
        self.path = path
        self.line = line
        self.lang = lang
        self.text = text

    @property
    def label(self) -> str:
        return f"{self.path.relative_to(REPO)}:{self.line}"

    @property
    def is_marked_wrong(self) -> bool:
        head = self.text.lstrip().splitlines()
        return bool(head) and head[0].startswith(WRONG_MARKER)

    @property
    def is_elided(self) -> bool:
        return ELISION in self.text

    @property
    def is_expression_catalog(self) -> bool:
        """A catalog of quoted Bases expressions, not a document."""
        lines = code_lines(self.text)
        return bool(lines) and all(line[0] in "\"'" for line in lines)


def fences(package: str, lang: str, include_upstream: bool = False) -> list:
    found = []
    root = SKILLS_DIR / package
    if not root.is_dir():
        return found
    for path in sorted(root.rglob("*.md")):
        text = path.read_text("utf-8")
        if not include_upstream and UPSTREAM_IMPORT_MARKER in text[:1000]:
            continue
        for match in FENCE_RE.finditer(text):
            if match.group(1) != lang:
                continue
            found.append(Fence(path, text[: match.start()].count("\n") + 1, lang, match.group(2)))
    return found


# --------------------------------------------------------------------------- #
# annotated examples: one fence that pairs a "# WRONG" form with a "# CORRECT" one
# --------------------------------------------------------------------------- #
ANNOTATION_RE = re.compile(r"^#\s*(WRONG|CORRECT)\b")


def code_lines(text: str) -> list:
    """The lines a parser would see: comments and blank lines removed."""
    stripped = (line.strip() for line in text.splitlines())
    return [line for line in stripped if line and not line.startswith("#")]


def annotated_sections(text: str) -> list:
    """Split a fence at its ``# WRONG`` / ``# CORRECT`` comments.

    Returns ``(label, body)`` pairs where *label* is ``"wrong"``, ``"correct"``,
    or ``"unlabelled"`` for anything before the first annotation. A body keeps
    its own annotation line, so a section whose example is commented out has no
    code lines at all.
    """
    sections = []
    label = "unlabelled"
    body = []

    def flush():
        if any(line.strip() for line in body):
            sections.append((label, "\n".join(body) + "\n"))

    for line in text.splitlines():
        match = ANNOTATION_RE.match(line)
        if match:
            flush()
            label = match.group(1).lower()
            body = [line]
            continue
        body.append(line)
    flush()
    return sections


def wrong_example_kind(fence) -> str:
    """Which negative check a fence marked ``# WRONG`` supports.

    ``"document"``    the wrong form is document-shaped YAML, so the checker
                      that owns the package can reject it.
    ``"expression"``  the wrong form is a quoted Bases expression. Nothing in
                      this file evaluates expressions, so the limit is asserted
                      instead of a validation being claimed.
    ``"unsupported"`` any other shape. Callers fail on this rather than skip it,
                      so a new kind of negative example cannot enter the tree
                      unchecked.
    """
    bodies = [body for label, body in annotated_sections(fence.text) if label == "wrong"]
    if len(bodies) != 1:
        return "unsupported"
    lines = code_lines(bodies[0])
    if not lines:
        return "unsupported"
    if all(line[0] in "\"'" for line in lines):
        return "expression"
    return "document"


# --------------------------------------------------------------------------- #
# JSON Canvas 1.0, as documented by skills/obsidian-canvas
# --------------------------------------------------------------------------- #
CANVAS_NODE_TYPES = frozenset({"text", "file", "link", "group"})
CANVAS_TYPE_FIELD = {"text": "text", "file": "file", "link": "url"}
CANVAS_SIDES = frozenset({"top", "right", "bottom", "left"})
CANVAS_ENDS = frozenset({"none", "arrow"})
CANVAS_PRESET_COLORS = frozenset({"1", "2", "3", "4", "5", "6"})
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_canvas_color(value, where: str) -> list:
    if value is None:
        return []
    if isinstance(value, str) and (value in CANVAS_PRESET_COLORS or HEX_COLOR_RE.match(value)):
        return []
    return [f"color.invalid: {where} color {value!r}"]


def validate_canvas_node(node, where="node") -> list:
    if not isinstance(node, dict):
        return [f"node.not-object: {where}"]
    defects = []
    identifier = node.get("id")
    if not isinstance(identifier, str) or not identifier:
        defects.append(f"node.id-not-string: {where}")
    for field in ("id", "type", "x", "y", "width", "height"):
        if field not in node:
            defects.append(f"node.missing-field: {where} has no {field!r}")
    node_type = node.get("type")
    if isinstance(node_type, str) and node_type not in CANVAS_NODE_TYPES:
        defects.append(f"node.unknown-type: {where} type {node_type!r}")
    for field in ("x", "y", "width", "height"):
        if field in node and not is_integer(node[field]):
            defects.append(f"node.geometry-not-integer: {where} {field}={node[field]!r}")
    required = CANVAS_TYPE_FIELD.get(node_type)
    if required and not isinstance(node.get(required), str):
        defects.append(f"node.missing-type-field: {node_type} node needs {required!r}")
    defects.extend(check_canvas_color(node.get("color"), where))
    return defects


def validate_canvas_edge(edge, node_ids=None, where="edge") -> list:
    if not isinstance(edge, dict):
        return [f"edge.not-object: {where}"]
    defects = []
    for field in ("id", "fromNode", "toNode"):
        if not isinstance(edge.get(field), str) or not edge[field]:
            defects.append(f"edge.missing-field: {where} has no usable {field!r}")
    for field in ("fromSide", "toSide"):
        if field in edge and edge[field] not in CANVAS_SIDES:
            defects.append(f"edge.invalid-side: {where} {field}={edge[field]!r}")
    for field in ("fromEnd", "toEnd"):
        if field in edge and edge[field] not in CANVAS_ENDS:
            defects.append(f"edge.invalid-end: {where} {field}={edge[field]!r}")
    if node_ids is not None:
        for field in ("fromNode", "toNode"):
            target = edge.get(field)
            if isinstance(target, str) and target not in node_ids:
                defects.append(f"edge.dangling-reference: {where} {field}={target!r}")
    defects.extend(check_canvas_color(edge.get("color"), where))
    return defects


def validate_canvas_document(document) -> list:
    if not isinstance(document, dict):
        return ["document.not-object"]
    defects = []
    nodes = document.get("nodes", [])
    edges = document.get("edges", [])
    if not isinstance(nodes, list):
        return ["nodes.not-array"]
    if not isinstance(edges, list):
        return ["edges.not-array"]

    seen = set()
    node_ids = set()
    for index, node in enumerate(nodes):
        defects.extend(validate_canvas_node(node, f"nodes[{index}]"))
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            node_ids.add(node["id"])
    for index, edge in enumerate(edges):
        defects.extend(validate_canvas_edge(edge, node_ids, f"edges[{index}]"))
    for collection, label in ((nodes, "nodes"), (edges, "edges")):
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                continue
            identifier = item.get("id")
            if isinstance(identifier, str):
                if identifier in seen:
                    defects.append(f"document.duplicate-id: {identifier!r} in {label}[{index}]")
                seen.add(identifier)
    return defects


# --------------------------------------------------------------------------- #
# Bases documents, as documented by skills/obsidian-bases
# --------------------------------------------------------------------------- #
BASE_TOP_LEVEL_KEYS = frozenset({"filters", "formulas", "properties", "summaries", "views"})
BASE_VIEW_KEYS = frozenset(
    {"type", "name", "filters", "groupBy", "order", "sort", "limit", "summaries"}
)
BASE_FRAGMENT_KEYS = BASE_TOP_LEVEL_KEYS | BASE_VIEW_KEYS
BASE_FILTER_BRANCHES = frozenset({"and", "or", "not"})
BASE_GROUP_DIRECTIONS = frozenset({"ASC", "DESC"})


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses a duplicated mapping key instead of dropping one."""


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate mapping key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def load_yaml_strict(text: str):
    """Parse YAML, raising on a duplicated mapping key. Returns (value, defect)."""
    try:
        return yaml.load(text, Loader=DuplicateKeyLoader), None
    except yaml.constructor.ConstructorError as error:
        if "duplicate mapping key" in str(error):
            return None, f"yaml.duplicate-key: {error.problem}"
        return None, f"yaml.parse-error: {type(error).__name__}"
    except yaml.YAMLError as error:
        return None, f"yaml.parse-error: {type(error).__name__}"


def validate_base_filters(node, where="filters") -> list:
    if isinstance(node, str):
        return []
    if not isinstance(node, dict):
        return [f"filters.not-string-or-mapping: {where} is {type(node).__name__}"]
    keys = set(node)
    if len(keys) != 1 or not keys <= BASE_FILTER_BRANCHES:
        return [f"filters.not-exactly-one-key: {where} has {sorted(keys)}"]
    branch = next(iter(keys))
    members = node[branch]
    if not isinstance(members, list):
        return [f"filters.branch-not-list: {where}.{branch} is {type(members).__name__}"]
    defects = []
    for index, member in enumerate(members):
        defects.extend(validate_base_filters(member, f"{where}.{branch}[{index}]"))
    return defects


def enumeration_alternatives(value):
    """``"ASC | DESC"`` -> ``["ASC", "DESC"]`` for a documentation placeholder."""
    if isinstance(value, str) and "|" in value:
        return [part.strip() for part in value.split("|") if part.strip()]
    return None


def validate_base_view(view, where="views[?]", doc_mode: bool = False) -> list:
    if not isinstance(view, dict):
        return [f"view.not-mapping: {where}"]
    defects = []
    for field in ("type", "name"):
        if field not in view:
            defects.append(f"view.missing-field: {where} has no {field!r}")
        elif not isinstance(view[field], str) or not view[field].strip():
            defects.append(f"view.{field}-not-string: {where} {field}={view[field]!r}")
    for key in sorted(set(view) - BASE_VIEW_KEYS):
        defects.append(f"view.unknown-key: {where} declares {key!r}")
    if "filters" in view:
        defects.extend(validate_base_filters(view["filters"], f"{where}.filters"))
    if "order" in view and not isinstance(view["order"], list):
        defects.append(f"view.order-not-list: {where}.order is {type(view['order']).__name__}")
    if "limit" in view and not is_integer(view["limit"]):
        defects.append(f"view.limit-not-integer: {where}.limit={view['limit']!r}")
    if "groupBy" in view:
        defects.extend(validate_base_group_by(view["groupBy"], f"{where}.groupBy", doc_mode))
    return defects


def validate_base_group_by(group_by, where="groupBy", doc_mode: bool = False) -> list:
    if not isinstance(group_by, dict):
        return [f"groupBy.not-mapping: {where} is {type(group_by).__name__}"]
    defects = []
    if not isinstance(group_by.get("property"), str):
        defects.append(f"groupBy.missing-property: {where}")
    direction = group_by.get("direction")
    if direction is None:
        return defects
    alternatives = enumeration_alternatives(direction) if doc_mode else None
    if alternatives is not None:
        # A documented placeholder must enumerate only real values.
        for alternative in alternatives:
            if alternative not in BASE_GROUP_DIRECTIONS:
                defects.append(
                    f"groupBy.invalid-direction: {where} documents {alternative!r}"
                )
    elif direction not in BASE_GROUP_DIRECTIONS:
        defects.append(f"groupBy.invalid-direction: {where} direction={direction!r}")
    return defects


def validate_base_document(
    document, allow_view_fragment: bool = True, doc_mode: bool = False
) -> list:
    """Validate a ``.base`` document or a documented fragment of one.

    ``doc_mode`` accepts the ``a | b`` placeholder the package uses to enumerate
    legal values in prose examples, and checks the enumeration itself. A real
    ``.base`` file is validated without it.
    """
    if not isinstance(document, dict):
        return ["document.not-mapping"]
    allowed = BASE_FRAGMENT_KEYS if allow_view_fragment else BASE_TOP_LEVEL_KEYS
    defects = [f"document.unknown-key: {key!r}" for key in sorted(set(document) - allowed)]
    if "filters" in document:
        defects.extend(validate_base_filters(document["filters"]))
    if "groupBy" in document:
        defects.extend(validate_base_group_by(document["groupBy"], "groupBy", doc_mode))
    if "order" in document and not isinstance(document["order"], list):
        defects.append("view.order-not-list: order is " + type(document["order"]).__name__)
    if "limit" in document and not is_integer(document["limit"]):
        defects.append(f"view.limit-not-integer: limit={document['limit']!r}")
    views = document.get("views")
    if views is not None:
        if not isinstance(views, list):
            defects.append("views.not-list: views is " + type(views).__name__)
        else:
            for index, view in enumerate(views):
                defects.extend(validate_base_view(view, f"views[{index}]", doc_mode))
    return defects


TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:", re.M)


def split_alternatives(text: str) -> list:
    """Split a fence that documents several alternative forms of one key.

    The Bases package shows variants (``filters:`` as a string, then as ``and``,
    then as ``or``) in a single fence. That is a catalogue, not one document, so
    each variant is validated on its own.
    """
    starts = [match.start() for match in TOP_LEVEL_KEY_RE.finditer(text)]
    if len(starts) < 2:
        return [text]
    bounds = starts + [len(text)]
    return [text[bounds[i] : bounds[i + 1]] for i in range(len(starts))]


def strip_frontmatter_delimiters(text: str) -> str:
    """Return the YAML body of a ``---`` delimited frontmatter example."""
    stripped = text.strip("\n")
    lines = stripped.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(len(lines) - 1, 0, -1):
            if lines[index].strip() == "---":
                return "\n".join(lines[1:index]) + "\n"
    return text


# --------------------------------------------------------------------------- #
# Web Clipper templates, mirroring the upstream import validator
# --------------------------------------------------------------------------- #
CLIPPER_REQUIRED = ("name", "behavior", "properties", "noteContentFormat")
CLIPPER_DAILY_BEHAVIORS = frozenset({"append-daily", "prepend-daily"})
CLIPPER_PROPERTY_TYPES = frozenset(
    {"text", "multitext", "number", "checkbox", "date", "datetime"}
)


def validate_clipper_template(template) -> list:
    if not isinstance(template, dict):
        return ["document.not-object"]
    defects = []
    for field in CLIPPER_REQUIRED:
        if field not in template:
            defects.append(f"template.missing-field: no {field!r}")
    behavior = template.get("behavior")
    if behavior not in CLIPPER_DAILY_BEHAVIORS:
        for field in ("noteNameFormat", "path"):
            if field not in template:
                defects.append(
                    f"template.missing-destination: behavior {behavior!r} needs {field!r}"
                )
    if "context" in template and not isinstance(template["context"], str):
        defects.append("template.context-not-string")
    properties = template.get("properties")
    if properties is not None:
        if not isinstance(properties, list):
            defects.append("properties.not-array: " + type(properties).__name__)
        else:
            for index, entry in enumerate(properties):
                if not isinstance(entry, dict):
                    defects.append(f"property.not-object: properties[{index}]")
                    continue
                for field in ("name", "value"):
                    if field not in entry:
                        defects.append(
                            f"property.missing-field: properties[{index}] has no {field!r}"
                        )
                if "type" in entry and entry["type"] not in CLIPPER_PROPERTY_TYPES:
                    defects.append(
                        f"property.invalid-type: properties[{index}] type={entry['type']!r}"
                    )
    return defects


def codes(defects) -> set:
    return {defect.split(":", 1)[0] for defect in defects}


# --------------------------------------------------------------------------- #
# fixture-driven checker calibration
# --------------------------------------------------------------------------- #
class CheckerCalibrationTest(unittest.TestCase):
    """Negative controls: a checker that accepts everything must fail here."""

    def run_json_case(self, case, validator):
        try:
            document = json.loads(case["text"])
        except json.JSONDecodeError:
            return ["json.parse-error"]
        return validator(document)

    def test_valid_canvas_fixtures_produce_no_defect(self):
        for case in FIXTURE["canvas"]["valid"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.run_json_case(case, validate_canvas_document), [])

    def test_each_malformed_canvas_fixture_raises_its_own_defect(self):
        for case in FIXTURE["canvas"]["malformed"]:
            with self.subTest(case=case["id"]):
                found = self.run_json_case(case, validate_canvas_document)
                self.assertIn(case["expect_defect_code"], codes(found), found)

    def test_valid_bases_fixtures_produce_no_defect(self):
        for case in FIXTURE["bases"]["valid"]:
            with self.subTest(case=case["id"]):
                document, defect = load_yaml_strict(case["text"])
                self.assertIsNone(defect)
                self.assertEqual(validate_base_document(document), [])

    def test_each_malformed_bases_fixture_raises_its_own_defect(self):
        for case in FIXTURE["bases"]["malformed"]:
            with self.subTest(case=case["id"]):
                document, defect = load_yaml_strict(case["text"])
                found = [defect] if defect else validate_base_document(document)
                self.assertIn(case["expect_defect_code"], codes(found), found)

    def test_valid_clipper_fixtures_produce_no_defect(self):
        for case in FIXTURE["clipper"]["valid"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.run_json_case(case, validate_clipper_template), [])

    def test_lenient_clipper_fixtures_are_accepted_as_documented(self):
        """The upstream validator ignores schemaVersion and the behavior enum."""
        for case in FIXTURE["clipper"]["accepted_but_suspect"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.run_json_case(case, validate_clipper_template), [])

    def test_each_malformed_clipper_fixture_raises_its_own_defect(self):
        for case in FIXTURE["clipper"]["malformed"]:
            with self.subTest(case=case["id"]):
                found = self.run_json_case(case, validate_clipper_template)
                self.assertIn(case["expect_defect_code"], codes(found), found)

    def test_strict_loader_rejects_a_duplicate_key_a_lenient_loader_drops(self):
        text = "views:\n  - type: table\n    name: A\nviews:\n  - type: cards\n    name: B\n"
        lenient = yaml.safe_load(text)
        self.assertEqual(len(lenient["views"]), 1, "the lenient loader silently drops data")
        document, defect = load_yaml_strict(text)
        self.assertIsNone(document)
        self.assertTrue(defect.startswith("yaml.duplicate-key"))


class CanvasDocumentationTest(unittest.TestCase):
    """Every canvas example shipped in the package is a real canvas."""

    def setUp(self):
        self.fences = fences("obsidian-canvas", "json")

    def test_the_package_ships_canvas_examples(self):
        self.assertGreaterEqual(len(self.fences), 4)

    def test_every_json_example_parses(self):
        for fence in self.fences:
            if fence.is_elided:
                continue
            with self.subTest(fence=fence.label):
                json.loads(fence.text)

    def test_every_example_is_a_valid_document_node_or_edge(self):
        documents = 0
        for fence in self.fences:
            if fence.is_elided:
                continue
            document = json.loads(fence.text)
            with self.subTest(fence=fence.label):
                self.assertIsInstance(document, dict)
                if "nodes" in document or "edges" in document:
                    documents += 1
                    self.assertEqual(validate_canvas_document(document), [])
                elif "fromNode" in document or "toNode" in document:
                    self.assertEqual(validate_canvas_edge(document), [])
                else:
                    self.assertEqual(validate_canvas_node(document), [])
        self.assertGreaterEqual(documents, 1, "at least one whole-canvas example is needed")

    def test_documented_canvases_carry_no_dangling_edge(self):
        for fence in self.fences:
            if fence.is_elided:
                continue
            document = json.loads(fence.text)
            if not isinstance(document, dict) or "edges" not in document:
                continue
            node_ids = {
                node["id"]
                for node in document.get("nodes", [])
                if isinstance(node, dict) and isinstance(node.get("id"), str)
            }
            for index, edge in enumerate(document["edges"]):
                with self.subTest(fence=fence.label, edge=index):
                    found = validate_canvas_edge(edge, node_ids, f"edges[{index}]")
                    self.assertNotIn("edge.dangling-reference", codes(found))


class BasesDocumentationTest(unittest.TestCase):
    """Bases examples are classified, then validated in their own class.

    Upstream-imported references are exempt from parsing: they are reproduced
    verbatim under their original licence and their fences are expression
    catalogues, not documents.
    """

    def setUp(self):
        self.fences = fences("obsidian-bases", "yaml")
        self.documents = []
        self.wrong = []
        self.catalogs = []
        for fence in self.fences:
            if fence.is_marked_wrong:
                self.wrong.append(fence)
            elif fence.is_expression_catalog:
                self.catalogs.append(fence)
            else:
                self.documents.append(fence)

    def test_the_package_ships_base_documents(self):
        self.assertGreaterEqual(len(self.documents), 1)

    def blocks(self, fence):
        """Each independently valid unit inside one documentation fence."""
        _document, defect = load_yaml_strict(fence.text)
        if defect and defect.startswith("yaml.duplicate-key"):
            return split_alternatives(fence.text)
        return [fence.text]

    def test_every_document_example_parses_as_yaml(self):
        for fence in self.documents:
            for index, block in enumerate(self.blocks(fence)):
                with self.subTest(fence=fence.label, block=index):
                    document, defect = load_yaml_strict(block)
                    self.assertIsNone(defect, f"{fence.label}: {defect}")
                    self.assertIsInstance(document, dict)

    def test_every_document_example_satisfies_the_documented_schema(self):
        for fence in self.documents:
            for index, block in enumerate(self.blocks(fence)):
                document, defect = load_yaml_strict(block)
                with self.subTest(fence=fence.label, block=index):
                    self.assertIsNone(defect)
                    self.assertEqual(validate_base_document(document, doc_mode=True), [])

    def test_examples_marked_wrong_really_are_wrong(self):
        self.assertTrue(self.wrong, "the package documents no negative example")
        for fence in self.wrong:
            with self.subTest(fence=fence.label):
                document, defect = load_yaml_strict(fence.text)
                found = (
                    [defect] if defect else validate_base_document(document, doc_mode=True)
                )
                self.assertNotEqual(found, [], "a WRONG example that validates is misleading")

    def test_upstream_imports_are_reproduced_without_local_repair(self):
        imported = [
            path
            for path in sorted((SKILLS_DIR / "obsidian-bases").rglob("*.md"))
            if UPSTREAM_IMPORT_MARKER in path.read_text("utf-8")[:1000]
        ]
        self.assertTrue(imported, "the exemption must name at least one real import")
        for path in imported:
            with self.subTest(file=str(path.relative_to(REPO))):
                header = path.read_text("utf-8")[:1000]
                self.assertIn("MIT", header, "an import must record its licence")
                self.assertRegex(header, r"revision\n?[a-f0-9]{40}|[a-f0-9]{40}")


class UpstreamImportedFenceTest(unittest.TestCase):
    """The imported reference is read with ``include_upstream=True``, not repaired.

    That flag is the only way to reach a fence inside an upstream import. The
    imported fences are expression catalogues: every line parses on its own as
    one quoted Bases expression, and the fence as a whole is never a ``.base``
    document. Validating one as a whole document would invent a defect in text
    this repository may not edit, so the classification itself is checked here.
    """

    def setUp(self):
        self.local = fences("obsidian-bases", "yaml")
        self.combined = fences("obsidian-bases", "yaml", include_upstream=True)
        local_labels = {fence.label for fence in self.local}
        self.upstream = [fence for fence in self.combined if fence.label not in local_labels]
        self.imported = [
            path
            for path in sorted((SKILLS_DIR / "obsidian-bases").rglob("*.md"))
            if UPSTREAM_IMPORT_MARKER in path.read_text("utf-8")[:1000]
        ]

    def test_including_upstream_reaches_fences_the_default_scan_skips(self):
        self.assertTrue(self.imported, "the package imports nothing to exempt")
        self.assertGreater(len(self.combined), len(self.local))
        self.assertTrue(self.upstream, "include_upstream reached no additional fence")
        self.assertEqual(
            {fence.path for fence in self.local} & set(self.imported),
            set(),
            "the default scan must stay out of the imported files",
        )
        self.assertTrue({fence.path for fence in self.upstream} <= set(self.imported))

    def test_every_imported_fence_is_an_expression_catalog_not_a_base_document(self):
        for fence in self.upstream:
            with self.subTest(fence=fence.label):
                self.assertTrue(fence.is_expression_catalog)
                self.assertFalse(fence.is_marked_wrong)
                document, _defect = load_yaml_strict(fence.text)
                self.assertNotIsInstance(document, dict, "a catalogue is not one document")
                self.assertEqual(
                    validate_base_document(document, doc_mode=True),
                    ["document.not-mapping"],
                    "reading this catalogue as a whole base would report a false defect",
                )

    def test_every_imported_expression_parses_on_its_own(self):
        parsed = 0
        for fence in self.upstream:
            for index, line in enumerate(code_lines(fence.text)):
                with self.subTest(fence=fence.label, line=index):
                    value, defect = load_yaml_strict(line)
                    self.assertIsNone(defect, f"{fence.label}: {line}: {defect}")
                    self.assertIsInstance(value, str, "an entry is one expression")
                    self.assertTrue(value.strip())
                    parsed += 1
        self.assertGreaterEqual(parsed, 4, "the import documents no expression")

    def test_an_imported_wrong_expression_stays_commented_out(self):
        annotated = 0
        for fence in self.upstream:
            for label, body in annotated_sections(fence.text):
                if label != "wrong":
                    continue
                annotated += 1
                with self.subTest(fence=fence.label):
                    self.assertEqual(
                        code_lines(body),
                        [],
                        "an expression the import calls wrong must stay commented out "
                        "instead of becoming one of the catalogue's entries",
                    )
        self.assertGreaterEqual(annotated, 1, "the import annotates no wrong expression")


class ClipperDocumentationTest(unittest.TestCase):
    """Shipped template assets must be importable templates."""

    def setUp(self):
        self.package = SKILLS_DIR / "obsidian-clipper"
        self.assets = sorted(self.package.rglob("*.json"))

    def test_the_package_ships_template_assets(self):
        self.assertTrue(self.assets, "obsidian-clipper ships no JSON template")

    def test_every_shipped_asset_parses_and_validates(self):
        validated = 0
        for path in self.assets:
            with self.subTest(asset=str(path.relative_to(REPO))):
                document = json.loads(path.read_text("utf-8"))
                if isinstance(document, dict) and "behavior" in document:
                    validated += 1
                    self.assertEqual(validate_clipper_template(document), [])
        self.assertGreaterEqual(validated, 1, "no asset looked like a template")

    def test_every_documented_json_example_parses(self):
        for fence in fences("obsidian-clipper", "json"):
            if fence.is_elided:
                continue
            with self.subTest(fence=fence.label):
                json.loads(fence.text)

    def test_property_types_stay_inside_the_documented_enum(self):
        for path in self.assets:
            document = json.loads(path.read_text("utf-8"))
            if not isinstance(document, dict):
                continue
            for index, entry in enumerate(document.get("properties", []) or []):
                if isinstance(entry, dict) and "type" in entry:
                    with self.subTest(asset=path.name, property=index):
                        self.assertIn(entry["type"], CLIPPER_PROPERTY_TYPES)


class MarkdownPropertyExampleTest(unittest.TestCase):
    """Frontmatter examples in the markdown package must be real YAML."""

    def test_every_yaml_example_parses(self):
        found = fences("obsidian-markdown", "yaml")
        self.assertTrue(found, "the markdown package documents no property example")
        for fence in found:
            if fence.is_marked_wrong or fence.is_elided:
                continue
            with self.subTest(fence=fence.label):
                body = strip_frontmatter_delimiters(fence.text)
                document, defect = load_yaml_strict(body)
                self.assertIsNone(defect, f"{fence.label}: {defect}")
                self.assertIsInstance(document, dict, "frontmatter is a mapping")


class WrongExampleDisciplineTest(unittest.TestCase):
    """Every ``# WRONG`` example is judged, and an unjudgeable one fails here.

    A negative example is only useful if a checker really rejects it. Where the
    wrong form is document-shaped, the defect has to come from the wrong block
    itself rather than from the mixed content of the fence that contains it.
    Where the wrong form is a Bases expression, nothing in this file evaluates
    expressions, so the limit is asserted instead of a validation being claimed.
    An example matching neither shape fails instead of being skipped.
    """

    PACKAGES = ("obsidian-bases", "obsidian-markdown")

    def setUp(self):
        self.wrong = [
            fence
            for package in self.PACKAGES
            for fence in fences(package, "yaml")
            if fence.is_marked_wrong
        ]

    def is_frontmatter(self, fence) -> bool:
        return "obsidian-markdown" in fence.path.parts

    def defects(self, fence, body) -> list:
        """What the checker that owns this package reports about one block."""
        if self.is_frontmatter(fence):
            document, defect = load_yaml_strict(strip_frontmatter_delimiters(body))
            if defect:
                return [defect]
            return [] if isinstance(document, dict) else ["frontmatter.not-mapping"]
        document, defect = load_yaml_strict(body)
        if defect:
            return [defect]
        return validate_base_document(document, doc_mode=True)

    def test_the_packages_still_document_negative_examples(self):
        self.assertTrue(self.wrong, "no package marks an example WRONG any more")

    def test_every_wrong_example_has_a_supported_classification(self):
        for fence in self.wrong:
            with self.subTest(fence=fence.label):
                self.assertIn(
                    wrong_example_kind(fence),
                    ("document", "expression"),
                    f"{fence.label}: no negative check here can judge this WRONG example; "
                    "classify it in wrong_example_kind instead of letting it through",
                )

    def test_a_document_shaped_wrong_block_fails_where_its_correct_twin_does_not(self):
        pairs = 0
        for fence in self.wrong:
            if wrong_example_kind(fence) != "document":
                continue
            sections = annotated_sections(fence.text)
            wrong_body = next(body for label, body in sections if label == "wrong")
            wrong_codes = codes(self.defects(fence, wrong_body))
            with self.subTest(fence=fence.label):
                self.assertNotEqual(
                    wrong_codes, set(), "a WRONG block that validates is misleading"
                )
                for index, (label, body) in enumerate(sections):
                    if label != "correct":
                        continue
                    self.assertEqual(
                        wrong_codes & codes(self.defects(fence, body)),
                        set(),
                        f"block {index} carries the same defect, so the fence rather "
                        "than the WRONG form is what fails",
                    )
                    pairs += 1
        self.assertGreaterEqual(pairs, 1, "no WRONG/CORRECT pair was exercised")

    def test_an_expression_shaped_wrong_block_is_not_claimed_as_validated(self):
        checked = 0
        for fence in self.wrong:
            if wrong_example_kind(fence) != "expression":
                continue
            sections = annotated_sections(fence.text)
            sides = {
                wanted: [
                    line
                    for label, body in sections
                    if label == wanted
                    for line in code_lines(body)
                ]
                for wanted in ("wrong", "correct")
            }
            with self.subTest(fence=fence.label):
                self.assertTrue(
                    sides["correct"], "a WRONG expression needs its CORRECT form beside it"
                )
                reported = {}
                for label, lines in sides.items():
                    found = set()
                    for line in lines:
                        value, defect = load_yaml_strict(line)
                        self.assertIsNone(defect, f"{fence.label}: {line}: {defect}")
                        self.assertIsInstance(value, str, "an entry is one expression")
                        found |= codes(validate_base_document(value, doc_mode=True))
                    reported[label] = found
                self.assertEqual(reported["wrong"], {"document.not-mapping"})
                self.assertEqual(
                    reported["wrong"],
                    reported["correct"],
                    "these checkers do not evaluate Bases expressions; a result that "
                    "separated the two forms would claim semantics this file does not "
                    "implement",
                )
                checked += 1
        self.assertGreaterEqual(checked, 1, "no expression-shaped WRONG example was exercised")

    def test_a_catalog_of_two_correct_expressions_fails_to_parse_the_same_way(self):
        """Control: a catalogue fence's parse error is a shape artifact.

        Two expressions the package documents as CORRECT produce the same error,
        so that error is never evidence about a line marked WRONG.
        """
        catalogs = [
            fence
            for fence in fences("obsidian-bases", "yaml")
            if fence.is_expression_catalog and not fence.is_marked_wrong
        ]
        sample = next(
            (code_lines(fence.text) for fence in catalogs if len(code_lines(fence.text)) >= 2),
            None,
        )
        self.assertIsNotNone(sample, "the package documents no multi-expression catalogue")
        document, defect = load_yaml_strict("\n".join(sample[:2]) + "\n")
        self.assertIsNone(document)
        self.assertTrue(defect.startswith("yaml.parse-error"), defect)


# --------------------------------------------------------------------------- #
# shipped helper scripts: static syntax and import surface
# --------------------------------------------------------------------------- #
HELPER_SCRIPTS = (
    SKILLS_DIR / "obsidian-doctor" / "scripts" / "diagnose.py",
    SKILLS_DIR / "obsidian-visualize" / "scripts" / "excalidraw_scene.py",
)
DECLARED_FEATURE_VERSION = (3, 9)


def import_roots(tree) -> set:
    """Top-level module names an AST imports; a relative import keeps its dots."""
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                roots.add("." * node.level + (node.module or ""))
            elif node.module:
                roots.add(node.module.split(".")[0])
    return roots


class ShippedScriptSyntaxTest(unittest.TestCase):
    """Static checks on the two shipped Python helpers.

    Both packages declare "Python 3.9+, standard library only".
    ``ast.parse(..., feature_version=(3, 9))`` rejects grammar introduced after
    3.9, and the import scan names every module the file needs.

    This is syntax and import surface, not runtime validation: neither script is
    executed here, no 3.9 interpreter is involved, and a standard-library
    function added after 3.9 would still pass.
    """

    def setUp(self):
        self.sources = {}
        for path in HELPER_SCRIPTS:
            if not path.is_file():
                self.fail(f"{path.relative_to(REPO)} is missing")
            self.sources[path] = path.read_text("utf-8")

    def parse(self, path):
        level = ".".join(str(part) for part in DECLARED_FEATURE_VERSION)
        try:
            return ast.parse(
                self.sources[path],
                filename=str(path),
                feature_version=DECLARED_FEATURE_VERSION,
            )
        except SyntaxError as error:
            self.fail(
                f"{path.relative_to(REPO)}:{error.lineno}: not valid Python {level} "
                f"syntax: {error.msg}"
            )

    def test_both_declared_helper_scripts_are_present(self):
        self.assertEqual(len(self.sources), 2)

    def test_each_helper_parses_under_the_declared_grammar_level(self):
        for path in self.sources:
            with self.subTest(script=str(path.relative_to(REPO))):
                self.assertIsInstance(self.parse(path), ast.Module)

    def test_each_helper_imports_only_the_standard_library(self):
        stdlib = getattr(sys, "stdlib_module_names", None)
        if stdlib is None:
            self.skipTest("sys.stdlib_module_names needs Python 3.10+")
        for path in self.sources:
            with self.subTest(script=str(path.relative_to(REPO))):
                roots = import_roots(self.parse(path))
                self.assertTrue(roots, "the import scan found nothing to check")
                self.assertEqual(
                    sorted(root for root in roots if root not in stdlib),
                    [],
                    "the owning package documents standard library only",
                )

    def test_no_helper_reaches_into_a_relative_or_sibling_module(self):
        for path in self.sources:
            with self.subTest(script=str(path.relative_to(REPO))):
                roots = import_roots(self.parse(path))
                self.assertEqual(
                    sorted(root for root in roots if root.startswith(".")),
                    [],
                    "a shipped script must stand alone inside its package",
                )


# --------------------------------------------------------------------------- #
# the shipped diagnostic tool
# --------------------------------------------------------------------------- #
class DoctorClassifierTest(unittest.TestCase):
    """diagnose.py run as a subprocess over synthetic evidence bundles.

    A verdict about a fixture is a verdict about that text. It is never evidence
    about a live vault, a running app, or an installed plugin.
    """

    EXIT_DETERMINATE = 0
    EXIT_INDETERMINATE = 1
    EXIT_USAGE = 2
    EXIT_INPUT_ERROR = 3

    @classmethod
    def setUpClass(cls):
        if not DIAGNOSE.is_file():
            raise unittest.SkipTest(f"{DIAGNOSE} is not present in this checkout")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="obsidian-doctor-test-"))
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for path in sorted(self.tmp.rglob("*"), reverse=True):
            path.unlink()
        self.tmp.rmdir()

    def run_diagnose(self, *args):
        return subprocess.run(
            [sys.executable, str(DIAGNOSE), *args],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def write_bundle(self, name: str, payload) -> Path:
        path = self.tmp / f"{name}.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def statuses(self, document) -> dict:
        return {finding["id"]: finding["status"] for finding in document["findings"]}

    # -- catalog -------------------------------------------------------------
    def test_list_checks_publishes_the_status_and_exit_code_contract(self):
        result = self.run_diagnose("--list-checks")
        self.assertEqual(result.returncode, self.EXIT_DETERMINATE, result.stderr)
        catalog = json.loads(result.stdout)
        self.assertEqual(
            set(catalog["statuses"]),
            {"confirmed", "ruled_out", "unknown", "not_applicable"},
        )
        self.assertEqual(set(catalog["exit_codes"]), {"0", "1", "2", "3"})
        self.assertTrue(catalog["checks"])
        for check in catalog["checks"]:
            self.assertTrue(check["id"] and check["title"])

    def test_no_mode_selected_is_a_usage_error(self):
        result = self.run_diagnose()
        self.assertEqual(result.returncode, self.EXIT_USAGE, result.stdout)
        self.assertEqual(result.stdout, "", "a usage error must not emit a document")

    # -- bundles -------------------------------------------------------------
    def test_every_bundle_is_classified_as_the_fixture_expects(self):
        for case in FIXTURE["doctor"]["bundles"]:
            with self.subTest(case=case["id"]):
                path = self.write_bundle(case["id"], case["bundle"])
                result = self.run_diagnose("--fixture", str(path))
                document = json.loads(result.stdout)
                statuses = self.statuses(document)
                for check_id, expected in case["expect"].get("check_status", {}).items():
                    self.assertIn(check_id, statuses, "check disappeared from the catalog")
                    self.assertEqual(statuses[check_id], expected, check_id)

    def test_exit_code_reports_evidence_sufficiency_not_defect_count(self):
        """The documented invariant: exit 1 exactly when a check stayed unknown."""
        for case in FIXTURE["doctor"]["bundles"]:
            with self.subTest(case=case["id"]):
                path = self.write_bundle(case["id"], case["bundle"])
                result = self.run_diagnose("--fixture", str(path))
                document = json.loads(result.stdout)
                unknown = [
                    finding["id"]
                    for finding in document["findings"]
                    if finding["status"] == "unknown"
                ]
                expected_code = self.EXIT_INDETERMINATE if unknown else self.EXIT_DETERMINATE
                self.assertEqual(result.returncode, expected_code, unknown)
                self.assertEqual(document["status"], "indeterminate" if unknown else "ok")
                self.assertEqual(len(document["unknowns"]), len(unknown))
                if case["expect"].get("expect_indeterminate"):
                    self.assertTrue(unknown, "this bundle must stay indeterminate")

    def test_an_optional_channel_is_absent_unobserved_or_observed(self):
        """Absence is normal, an unobserved channel is unknown, never assumed."""
        triad = {
            "optional-channels-absent": "not_applicable",
            "plugin-channel-present-but-unobserved": "unknown",
            "plugin-channel-observed-available": "ruled_out",
        }
        by_id = {case["id"]: case for case in FIXTURE["doctor"]["bundles"]}
        for case_id, expected in triad.items():
            self.assertIn(case_id, by_id, "fixture lost a triad case")
            with self.subTest(case=case_id):
                path = self.write_bundle(case_id, by_id[case_id]["bundle"])
                result = self.run_diagnose("--fixture", str(path))
                statuses = self.statuses(json.loads(result.stdout))
                self.assertEqual(statuses["plugin-unavailable"], expected)

    def test_classification_never_reports_a_mutation(self):
        for case in FIXTURE["doctor"]["bundles"]:
            with self.subTest(case=case["id"]):
                path = self.write_bundle(case["id"], case["bundle"])
                document = json.loads(self.run_diagnose("--fixture", str(path)).stdout)
                self.assertEqual(document["mutations_performed"], [])

    def test_the_bundle_file_is_not_modified_by_a_run(self):
        case = FIXTURE["doctor"]["bundles"][0]
        path = self.write_bundle("readonly", case["bundle"])
        before = path.read_bytes()
        self.run_diagnose("--fixture", str(path))
        self.assertEqual(path.read_bytes(), before)

    def test_host_specific_values_are_reported_by_location_only(self):
        cases = [
            case
            for case in FIXTURE["doctor"]["bundles"]
            if case["expect"].get("must_not_echo")
        ]
        self.assertTrue(cases, "the fixture lost its sanitization case")
        for case in cases:
            with self.subTest(case=case["id"]):
                path = self.write_bundle(case["id"], case["bundle"])
                result = self.run_diagnose("--fixture", str(path))
                document = json.loads(result.stdout)
                self.assertEqual(
                    self.statuses(document)["fixture-not-sanitized"], "confirmed"
                )
                for secret in case["expect"]["must_not_echo"]:
                    self.assertNotIn(secret, result.stdout, "a flagged value was echoed")
                self.assertIsNot(document["subject"]["template_path"], None)
                self.assertNotIn(
                    "file://", str(document["subject"]["template_path"]).lower()
                )

    # -- unreadable input ----------------------------------------------------
    def test_every_unloadable_bundle_is_refused_with_an_input_error(self):
        for case in FIXTURE["doctor"]["unloadable"]:
            with self.subTest(case=case["id"]):
                path = self.write_bundle(case["id"], case["text"])
                result = self.run_diagnose("--fixture", str(path))
                self.assertEqual(result.returncode, self.EXIT_INPUT_ERROR, result.stdout)
                document = json.loads(result.stdout)
                self.assertEqual(document["status"], "input_error")
                self.assertEqual(document["findings"], [])
                self.assertTrue(document["reason"])

    def test_a_missing_fixture_path_is_an_input_error_not_a_crash(self):
        result = self.run_diagnose("--fixture", str(self.tmp / "absent.json"))
        self.assertEqual(result.returncode, self.EXIT_INPUT_ERROR, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "input_error")

    def test_a_directory_is_an_input_error_not_a_crash(self):
        result = self.run_diagnose("--fixture", str(self.tmp))
        self.assertEqual(result.returncode, self.EXIT_INPUT_ERROR, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "input_error")

    def test_the_documented_example_bundle_is_loadable_by_the_shipped_tool(self):
        examples = [
            fence
            for fence in fences("obsidian-doctor", "json")
            if not fence.is_elided and '"schema"' in fence.text
        ]
        self.assertTrue(examples, "the package documents no evidence bundle")
        for fence in examples:
            with self.subTest(fence=fence.label):
                payload = json.loads(fence.text)
                path = self.write_bundle("documented", payload)
                result = self.run_diagnose("--fixture", str(path))
                self.assertNotEqual(
                    result.returncode,
                    self.EXIT_INPUT_ERROR,
                    "the documented example is not accepted by the shipped tool",
                )
                self.assertEqual(json.loads(result.stdout)["evidence_schema"], payload["schema"])


# --------------------------------------------------------------------------- #
# recorded evidence and the matrix that publishes it
# --------------------------------------------------------------------------- #
EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
MATRIX_PATH = REPO / "docs" / "verification-matrix.md"
REPORT_KIND = "package-consumer-test-report"
REFERENCED_REPORTS = frozenset(
    {
        "native-app.json",
        "native-manifests.json",
        "clipper-selectors.json",
        "headless-local.json",
    }
)
NATIVE_RESULTS = frozenset({"passed", "limited"})
LIMIT_KEYS = ("limitations", "limitation", "unverified", "scope")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ABBREVIATED_DIGEST_RE = re.compile(r"`([0-9a-f]{4,})" + ELISION + r"([0-9a-f]{4,})`")
PASSED_ROWS_HEADING = re.compile(r"^##\s+Passed\b[^\n]*application and CLI[^\n]*$", re.M)


def matrix_table_ids(text: str, heading) -> list:
    """First-column ids of the first markdown table under *heading*."""
    match = heading.search(text)
    if match is None:
        return []
    found = []
    for line in text[match.end() :].splitlines():
        row = line.strip()
        if not row.startswith("|"):
            if found:
                break
            continue
        cell = row.split("|")[1].strip().strip("`")
        if not cell or cell == "id" or set(cell) <= set("- "):
            continue
        found.append(cell)
    return found


class EvidenceReportConsistencyTest(unittest.TestCase):
    """The recorded reports and the matrix rows that cite them must agree.

    These are file-consistency checks over text this repository already wrote:
    no application, CLI, browser, or network is touched, and nothing here
    re-observes anything a report claims. What they do catch is a result being
    published at a level its own report never recorded.
    """

    def setUp(self):
        self.reports = {
            path.name: json.loads(path.read_text("utf-8"))
            for path in sorted(EVIDENCE_DIR.glob("*.json"))
        }
        self.matrix = MATRIX_PATH.read_text("utf-8")

    def native_checks(self) -> list:
        return self.reports["native-app.json"]["checks"]

    def published_ids(self) -> list:
        return matrix_table_ids(self.matrix, PASSED_ROWS_HEADING)

    def test_every_report_the_matrix_cites_is_present_and_parses(self):
        self.assertTrue(REFERENCED_REPORTS <= set(self.reports), sorted(self.reports))
        for name, report in self.reports.items():
            with self.subTest(report=name):
                self.assertIsInstance(report, dict)

    def test_every_report_declares_the_shared_header(self):
        for name, report in self.reports.items():
            with self.subTest(report=name):
                version = report.get("schemaVersion")
                self.assertNotIsInstance(version, bool)
                self.assertEqual(version, 1)
                self.assertEqual(report.get("kind"), REPORT_KIND)

    def test_every_report_records_the_limit_of_what_it_shows(self):
        for name, report in self.reports.items():
            with self.subTest(report=name):
                stated = [key for key in LIMIT_KEYS if report.get(key)]
                self.assertTrue(stated, f"{name} records results without their limit")
                for key in stated:
                    value = report[key]
                    entries = value if isinstance(value, list) else [value]
                    for entry in entries:
                        self.assertIsInstance(entry, str)
                        self.assertTrue(entry.strip())

    def test_every_recorded_date_is_a_real_calendar_date(self):
        dated = 0
        for name, report in self.reports.items():
            if "date" not in report:
                continue
            with self.subTest(report=name):
                try:
                    datetime.date.fromisoformat(report["date"])
                except (TypeError, ValueError) as error:
                    self.fail(f"{name} records {report['date']!r}: {error}")
                dated += 1
        self.assertGreaterEqual(dated, 1, "no report records when it was produced")

    def test_native_check_results_stay_inside_the_recorded_vocabulary(self):
        checks = self.native_checks()
        self.assertTrue(checks, "the native report records no check")
        identifiers = [check["id"] for check in checks]
        self.assertEqual(len(identifiers), len(set(identifiers)), "duplicate check id")
        for check in checks:
            with self.subTest(check=check["id"]):
                self.assertIn(check["result"], NATIVE_RESULTS)
                for field in ("id", "method", "observed"):
                    self.assertIsInstance(check[field], str)
                    self.assertTrue(check[field].strip())

    def test_the_matrix_publishes_exactly_the_checks_recorded_as_passed(self):
        published = self.published_ids()
        self.assertTrue(published, "the passed-rows table was not found")
        self.assertEqual(len(published), len(set(published)), "a row is published twice")
        self.assertEqual(
            set(published),
            {check["id"] for check in self.native_checks() if check["result"] == "passed"},
            "the passed table and the report disagree about which checks passed",
        )

    def test_a_check_short_of_passed_is_still_published_but_never_as_passed(self):
        short = [check["id"] for check in self.native_checks() if check["result"] != "passed"]
        self.assertTrue(short, "the report keeps no limited result; a row was upgraded")
        published = set(self.published_ids())
        for check_id in short:
            with self.subTest(check=check_id):
                self.assertNotIn(check_id, published, "a limited result was published as passed")
                self.assertIn(check_id, self.matrix, "a limited result must stay published")

    def test_the_matrix_quotes_the_non_target_digest_that_was_recorded(self):
        non_target = self.reports["native-app.json"]["nonTarget"]
        digest = non_target["sha256"]
        self.assertRegex(digest, SHA256_RE)
        self.assertTrue(non_target["path"].strip())
        self.assertIn(non_target["path"], self.matrix, "the control file is not named")
        abbreviations = ABBREVIATED_DIGEST_RE.findall(self.matrix)
        self.assertTrue(abbreviations, "the matrix quotes no digest")
        for prefix, suffix in abbreviations:
            with self.subTest(digest=f"{prefix}{ELISION}{suffix}"):
                self.assertTrue(digest.startswith(prefix), digest)
                self.assertTrue(digest.endswith(suffix), digest)

    def test_the_headless_report_claims_a_pass_only_for_the_code_it_observed(self):
        report = self.reports["headless-local.json"]
        observed = report["observedExitCode"]
        self.assertNotIsInstance(observed, bool)
        self.assertIsInstance(observed, int)
        self.assertIs(report["accountOrNetworkOperation"], False)
        self.assertTrue(report["invocation"].strip())
        if report["result"] == "passed":
            self.assertEqual(observed, report["expectedExitCode"])

    def test_a_failed_browser_selector_is_never_recorded_as_a_capture(self):
        report = self.reports["clipper-selectors.json"]
        public = report["publicPage"]
        self.assertTrue(public["result"].strip())
        self.assertNotEqual(public["result"], "passed")
        self.assertTrue(public["limitation"].strip())
        self.assertTrue(report["unverified"], "a failed surface must name what stays unverified")
        self.assertTrue(report["mutations"].strip())
        synthetic = report["synthetic"]
        self.assertEqual(synthetic["result"], "passed")
        self.assertTrue(synthetic["selectors"], "a passed selector run returned no selector")
        for selector, value in synthetic["selectors"].items():
            with self.subTest(selector=selector):
                self.assertTrue(selector.strip())
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())

    def test_every_manifest_validation_records_its_command_and_exit_code(self):
        checks = self.reports["native-manifests.json"]["checks"]
        self.assertTrue(checks, "the manifest report records no run")
        for check in checks:
            command = check["command"]
            with self.subTest(command=" ".join(command)):
                self.assertIsInstance(command, list)
                self.assertTrue(command)
                for argument in command:
                    self.assertIsInstance(argument, str)
                    self.assertTrue(argument.strip())
                self.assertNotIsInstance(check["exitCode"], bool)
                self.assertIsInstance(check["exitCode"], int)
                self.assertTrue(check["observed"].strip())


if __name__ == "__main__":
    unittest.main()
