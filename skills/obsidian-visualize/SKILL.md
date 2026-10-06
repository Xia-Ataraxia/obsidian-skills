---
name: obsidian-visualize
description: Chooses the visual form for a piece of knowledge and builds the file that carries it — a JSON Canvas graph of existing notes, or a deterministic .excalidraw.md drawing generated with this package's stdlib script. Use when a request asks for an architecture, data-flow, pipeline, sequence, dependency, or status diagram in a vault, when an Excalidraw drawing must be generated, regenerated, or safely replaced, or when it is unclear whether a Canvas, an Excalidraw drawing, a Mermaid block, or a plain table is the right answer. Also for seeing, inspecting, importing, editing or rendering Excalidraw inside Obsidian, including plugin Mermaid import and 플로우차트·아키텍처도·개념도. Not for Mermaid source inside a note, JSON Canvas schema details, note prose and properties, or installing the Excalidraw plugin — use the obsidian-mermaid, obsidian-canvas, obsidian-markdown, or obsidian-cli package.
license: MIT
metadata:
  version: "0.1.0"
  implementation_version: "0.2.0"
---

# Obsidian Visualize

Pick the visual form the evidence supports, then produce the file that carries it — a diagram is a file with a documented shape, not a runtime object that needs a plugin to exist.

Done means: the form fits what is being shown, every claim in the drawing traces to inspected evidence, the drawing is a new file unless replacing a named one was asked for, static validation is clean, readback proves the intended bytes landed, and the report says exactly which evidence level was reached instead of implying a picture was seen.

## Choose the form first

| What the nodes are | Form | Why |
| --- | --- | --- |
| Existing vault notes to navigate — a map of content, a reading path, a note dependency map | **JSON Canvas** (`.canvas`) | Nodes are file references; clicking one opens the note |
| Free shapes with no backing note — architecture, data flow, deployment, status cards, labelled routes | **Excalidraw** (`.excalidraw.md`) | Arbitrary geometry, styling, bound labels, frames |
| A small structural diagram that belongs *inside* a note's prose | **Mermaid fence** | Travels with the note; no attachment to manage |
| Values, comparisons, ordered attributes | **Markdown table** | A table that answers the question beats a diagram that decorates it |

This is a decision, not a fallback ladder. Do not deliver a Canvas because Excalidraw geometry looked tedious, and do not deliver an Excalidraw drawing of note titles when the user wants to click through to the notes. If the request names a form, that form is the answer unless it cannot carry the content — then say so before switching.

`obsidian-canvas` owns the `.canvas` node/edge schema, colors, and ID rules; `obsidian-mermaid` owns fenced Mermaid source; `obsidian-markdown` owns note prose, links, and properties. This package owns the choice above, Excalidraw file generation, and the vault-specific checks in the workflow below. Compose those packages by name when the task genuinely reaches into them; nothing here dispatches to them automatically.

## Evidence ladder

Four separate claims. Never report a higher one on the strength of a lower one.

| Level | What it proves | How it is produced |
| --- | --- | --- |
| A — Static validation | The scene is structurally sound: unique ids, resolvable two-way bindings, finite geometry | `Scene.check()` / `validate_scene()` before writing |
| B — Materialized readback | The intended bytes are at the intended path and still parse | The writer's own readback; `read_drawing()` afterwards |
| C — Runtime load | The target app opened the file as a drawing and reports the expected element count | Opening the file in the target Obsidian (`obsidian-cli` owns the command surface) and comparing against `Scene.summary()` |
| D — Render QA | The drawing is actually legible: no overlaps, no clipping, correct hierarchy | Exporting an image through the installed plugin and looking at it |

A and B on the generator/import path need nothing but Python and the filesystem. C needs a target installation; D additionally needs the Excalidraw plugin present and a human or vision-capable reviewer looking at the export. This package cannot install or enable a plugin and carries no rasteriser: its native helper asks an already-enabled plugin to export the reloaded drawing. An SVG or PNG assembled from the same numbers, or rendered in a standalone Excalidraw app, does not prove the Obsidian plugin parses it.

When C or D cannot be reached, name the level reached and list the rest as unverified. "Validated and written" is a complete, honest result at level B. "Rendered correctly" is a lie at level B.

## Workflow

1. **Ground the content.** Collect the evidence for every claim the diagram will make: files at a pinned revision, note contents, measured values. Label declared configuration as declared and inspected behavior as inspected; do not merge a name-similar concept into a box because the words matched. A reference image supplies visual language only — never services, protocols, or numbers.
2. **Choose the form** with the table above, and choose the view the evidence supports (pipeline, sequence, data contract, deployment, observability). An architectural request answered with a three-box linear overview is the wrong view even when it validates.
3. **Write a small deterministic generator** that computes layout from measured text. For Excalidraw, import [`scripts/excalidraw_scene.py`](scripts/excalidraw_scene.py) and build with `Scene`. For Canvas, a short dict-and-`json.dump` script is enough; the schema belongs to `obsidian-canvas`. Never hand-place coordinates by eye and never hand-edit the generated file — fix the generator and regenerate.
4. **Validate before writing** (level A). Excalidraw: `Scene.check()` must be empty. Canvas: unique ids, every `fromNode`/`toNode` resolves, no two nodes overlap, and — this package's own check — every `file` node path and every wikilink target actually resolves in the destination vault. A plausible note name is not a resolved one.
5. **Write a new file** (level B). `Scene.write()` refuses to touch an existing path unless the replacement rules below are satisfied, and reads the result back before returning.
6. **Load it in the target app** (level C) and compare the element count against `Scene.summary()["total"]`.
7. **Render QA** (level D) only when the plugin is present: export an image through it, look at the result for overlapping cards, clipped labels, unreadable text, and wrong hierarchy, then fix the generator and regenerate. [`references/workbench.md`](references/workbench.md) has the admission probe, the async handshake the CLI needs, and the reload-then-render order.
8. **Report** the path, the form and why, the evidence trail, and the highest level actually reached.

## Excalidraw file anatomy

An `.excalidraw.md` drawing is Markdown, top to bottom:

````text
---
excalidraw-plugin: parsed
---
Optional plaintext description shown in Reading view.

# Excalidraw Data

## Text Elements
Ingest ^Kh3nD0pQ2f

Store ^b7TqL1wRxa

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"…","elements":[…],"appState":{…},"files":{}}
```
%%
````

- `excalidraw-plugin: parsed` is the marker that makes the note a drawing.
- `## Text Elements` is a human-readable index: the element's text, a space, then `^<elementId>`, one blank line between entries. The plugin reads the real scene from the fenced JSON.
- The `%%` pair hides the scene from Reading view.
- The plugin can also store the scene as `compressed-json`. That is codec output. Never author or hand-edit it; this package refuses both to write it and to diff against it.

Element essentials the generator already handles: a **bound label** needs `containerId` on the text *and* a mirrored `{"type":"text","id":…}` entry in the container's `boundElements`; an **arrow** needs `startBinding`/`endBinding` of `{elementId, focus, gap}` mirrored as `{"type":"arrow","id":…}` on both endpoints, with `points` relative to the arrow's own origin and the first point exactly `[0, 0]`; **frames** and **groups** relate elements through `frameId` and `groupIds`. Missing either half of a two-way reference renders wrong or breaks on reload, which is what level A checks.

## Plugin-first import and editing

When the request is to see or change Excalidraw **inside Obsidian**, use
[`references/plugin-workflow.md`](references/plugin-workflow.md). It covers
new `.excalidraw.md` creation and exact opening, an inspected full-scene import,
selected-id native edits, Mermaid addition, independent plugin readback and
native export QA. Existing plugin drawings, their text indexes, frontmatter,
prose and assets are not replaced with a fresh standalone scene.

The package-local tools are [`scripts/import_scene.py`](scripts/import_scene.py)
(new-file-only full-scene adapter),
[`scripts/inspect.mjs`](scripts/inspect.mjs) (read-only inspection/layout lint),
and [`scripts/plugin-workbench.js`](scripts/plugin-workbench.js) (native
ExcalidrawAutomate snapshot, selected update, Mermaid addition and PNG export).
Read [`references/skeleton.md`](references/skeleton.md) for upstream shorthand
adaptation boundaries and [`references/style.md`](references/style.md) for
palette/spacing/layout recipes. Their lineage and capability mapping are in
[`PROVENANCE.md`](PROVENANCE.md) and [`source-map.json`](source-map.json).

Resolve exact artifact and authorized effect; inspect current bytes and live
preimages; preserve everything outside the selected ids/fields; use the selected
supported native surface; reload the exact persisted result; report actual
evidence and prerequisites; leave unresolved version/runtime facts unknown.
No default destination, standalone app lifecycle or plugin installation is added.

## The generator API

`scripts/excalidraw_scene.py` is Python 3.9+ standard library only — no pip install, no plugin, no network. Import it directly:

```python
import sys
sys.path.insert(0, "skills/obsidian-visualize/scripts")
from excalidraw_scene import Scene, read_drawing

scene = Scene(namespace="Systems/Ingest Overview")
frame = scene.frame(-60, -60, 1220, 220, "Ingest path")
ingest = scene.box(0, 0, 260, "Ingest\ncollect raw events", 20, "#0369a1", "#ffffff")
store = scene.box(420, 0, 260, "Store\nappend to the log", 20, "#334155", "#ffffff")
scene.add_to_frame(frame, ingest, store)
scene.arrow(ingest, store, "events")

defects = scene.check()
assert not defects, defects
report = scene.write("Systems/Ingest Overview.excalidraw.md", frontmatter={"tags": ["diagram"]})
print(report.path, report.sha256, report.summary)
```

**Determinism.** `namespace` is the only entropy source. Element ids, `seed`, `versionNonce` and `updated` derive from `(namespace, element kind, creation order, optional key)` — no clock, no PRNG. The same generator run twice produces byte-identical output, and because ids ignore element text, relabelling a card keeps its id and its diff small. Pass `key="ingest"` to pin an id to a name instead of to creation order when the build order may change.

**Builders** — each returns the element dict, which you may mutate for style:

| Call | Result |
| --- | --- |
| `Scene(namespace, view_background="#ffffff", grid_size=None)` | One scene per output file |
| `.rect(x, y, width, height, stroke, background="transparent", key=None, **style)` | Rounded rectangle |
| `.text(x, y, body, font_size, color, max_width=None, container=None, align="left", valign="top", link=None, key=None, **style)` | Text, measured and optionally wrapped; `container=` writes both halves of the bound-label pair |
| `.box(x, y, width, body, font_size, stroke, background, link=None, pad_x=14, pad_y=10, text_color=None, dashed=False, min_height=0, key=None)` | Card: rectangle plus bound label, height fitted to the wrapped text. Returns the rectangle |
| `.arrow(start, end, label=None, start_side="right", end_side="left", dashed=False, elbow_y=None, gap=6, key=None)` | Two-way bound arrow; elbows through the midpoint when the anchors do not line up, or through `elbow_y` |
| `.frame(x, y, width, height, name, key=None, **style)` | Frame. Create it before its members so it sits behind them |
| `.add_to_frame(frame, *members)` / `.group(*members, key=None)` | Set `frameId`; share a deterministic `groupIds` entry |

**Measurement** — `wrap(text, font_size, max_width)`, `dims(text, font_size)`, `text_width(line, font_size)`, `char_ratio(char)`. Advance width is east-asian aware: wide and fullwidth characters cost a full `fontSize`, everything else `0.6×`, and combining marks, joiners, variation selectors and conjoining Hangul jamo cost nothing, so decomposed text measures like its precomposed form. It is an estimate, not font metrics — an emoji ZWJ sequence is over-measured, which widens a card rather than clipping it. If a real font still clips, widen `max_width`; do not add a metrics dependency.

**Inspection and output** — `.check(ignore_overlaps=False)`, `.summary()`, `.to_scene()`, `.render(frontmatter=None, description="")`, `.write(...)`. Standalone: `validate_scene(scene)`, `validate_scene_json(text)`, `scene_summary(scene)`, `render_drawing(scene, …)`, `extract_scene(document)`, `read_drawing(path) -> (document, sha256, scene)`, `build_scene(elements, …)`.

**Refusals.** Non-finite or negative geometry, a blank color, a non-positive font size, an unknown anchor side, an arrow bound to itself or to an element from another `Scene`, padding wider than its card, and any attempt to override a derived `id`/`type`/`seed`/`versionNonce` all raise at construction time. `SceneDefect` (carrying `.defects`) is raised instead of writing a scene that fails validation; `SceneWriteError` is raised for every unsafe write and for a readback that does not match intent.

**Overlaps** are a layout heuristic, not a schema error: two filled rectangles that intersect produce a defect prefixed `overlap:`. Passing `allow_overlaps=True` writes anyway and returns those defects in `report.allowed_overlaps` — quote them in the report rather than silently dropping them.

## Replacing an existing drawing

A new visualization request is a new file. `write()` refuses an existing path outright, and refuses `overwrite=True` without `expected_sha256`, because a replacement whose baseline was never read is a blind overwrite.

```python
document, digest, previous = read_drawing("Systems/Ingest Overview.excalidraw.md")
# keep `document` as the backup, and diff `previous` against what you are about to write
report = scene.write(path, overwrite=True, expected_sha256=digest)
assert not report.removed_ids, report.removed_ids   # nothing dropped silently
```

The writer then verifies the digest still matches, writes atomically (temp file in the destination directory, then an exclusive link or an atomic replace — never a truncate-then-write), reads the result back, revalidates it, and reports the diff. It also refuses a path that is a directory or a symlink, a path not ending in `.md`, and any existing file that has no `## Drawing` section — so a plain note can never be turned into a drawing by accident, even with a correct digest.

`report` is the receipt to quote: `path`, `sha256`, `size`, `replaced`, `summary`, `added_ids`, `removed_ids`, `binding_changes`, `allowed_overlaps`.

## Safety rules

- Producing a valid drawing is not authorization to write into a vault. Resolve the exact target path and the authorized effect first; stay read-only when either is missing.
- Back up and diff before replacing. `removed_ids` or unexplained `binding_changes` mean stop and report, not continue.
- Never hand-patch generated output, never author `compressed-json`, and never write a drawing through a shell redirect or stream editor.
- Never put a host path, vault name, account identifier, private note content, or secret into a shipped example, a frontmatter field, or an element link.
- Never click through a trust, permission, or plugin-installation dialog in the target app to make a drawing render. Report the missing layer and hand that decision to the operator.
- A failed check, an unresolved link, or an uninspected render is a partial result. Report it as a blocker, not a success.

## Live plugin edits (exception path)

Use the plugin's automation API for an authorized selected edit of a plugin-managed drawing, Mermaid insertion into that drawing, or embedding through the plugin's own file store. Fresh geometry still uses deterministic file generation; element count is not a reason to switch surfaces. Native workbench updates preserve the existing document instead of regenerating it.

[`references/workbench.md`](references/workbench.md) covers plugin and API admission, the build-and-persist calls, the caller-owned token handshake the CLI's synchronous `eval` requires, and the reload-then-render order that separates "the live scene looks right" from "the file on disk holds it".

## Requirements

- Python 3.9+ for the generator. Standard library only, by design.
- Node.js for optional read-only `inspect.mjs` (author checks used 24.21.0). No npm dependency or build is required. `plugin-workbench.js` runs in the admitted Obsidian JavaScript context using its native EA API and Web Crypto; it has no server or browser dependency.
- Level C needs a target Obsidian installation; `obsidian-cli` owns the command surface for opening a file and reading back what loaded.
- Level D additionally needs the Excalidraw plugin already installed and enabled in that vault. Its absence is a normal outcome to report, not a failure to work around.
- Primary sources: the [Excalidraw plugin repository](https://github.com/zsviczian/obsidian-excalidraw-plugin) and its published [ExcalidrawAutomate API surface](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/master/docs/API/ExcalidrawAutomate.d.ts) for the drawing format and API, and the [JSON Canvas 1.0 spec](https://jsoncanvas.org/spec/1.0/) for the Canvas branch.

## Verification

- [ ] The chosen form matches the selection table, and the reason is stated.
- [ ] Every box, label, and arrow traces to inspected evidence; declared configuration is labelled as declared.
- [ ] Layout came from a deterministic generator, not from hand-placed coordinates.
- [ ] `Scene.check()` is empty, or every remaining defect is an `overlap:` one that was deliberately allowed and reported.
- [ ] The drawing is a new file, or a replacement backed by `read_drawing()`, a digest, and a reviewed id/binding diff.
- [ ] Wikilink and Canvas `file` targets resolve in the destination vault.
- [ ] The report names the highest evidence level reached (A, B, C, or D) and lists the rest as unverified.
- [ ] No host path, vault name, account identifier, or secret appears in the output.

## Attribution

The deterministic generator, full-scene adapter, native workbench helper and plugin workflow are original work under [LICENSE](LICENSE). Inspection/layout lint and the skeleton/style resources are adapted from Jonghak Seo's MIT-licensed pi-extension at the pin in [PROVENANCE.md](PROVENANCE.md), with its full grant retained in [NOTICE](NOTICE). No standalone app, font, binary or Obsidian plugin is redistributed. See [CHANGELOG.md](CHANGELOG.md) for source facts, versions, modifications and unrun runtime checks.
