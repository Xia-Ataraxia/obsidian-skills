# Draw inside Obsidian

The target is an Obsidian Excalidraw drawing, not a second editor. Keep the exact
vault and destination selected by the owner. There is no `.diagrams` default,
browser app, server lifecycle, automatic installation or plugin-settings change.
`obsidian-cli` owns targeting, opening and eval transport; `obsidian-doctor`
owns plugin diagnosis. This package owns scene preparation, bounded workbench
edits, preservation receipts and plugin-render inspection.

## Admission and evidence

Read the installed target's manifest, then probe the enabled plugin and methods
in that same app. User-reported usage, a remote inventory, official source and an
installed manifest are four different observations. Record their dates and
versions separately. Unknown installed versions stay unknown.

The implementation facts below were inspected in official source revision
`f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79`, whose manifest declares 2.28.1.
This is a source pin, not a minimum compatible version or installed-version
claim. Method admission is still required:

- `getAPI(view)` creates a separate EA workbench; `clear()` begins a transaction.
- `copyViewElementsToEAforEditing(elements, true)` clones selected elements and
  copies their image metadata; edit copies with `getElement(originalId)`.
- `addElementsToView(false, false, true)` submits selected copies without prematurely saving the preceding rendered revision. `viewUpdateScene({appState: {}})` uses the pinned view's synchronous flush without changing scene content, then `view.forceSave(true, true)` requests native persistence and waits for pending native save work. These methods are admitted before mutation. Neither a truthy submission nor a completed save replaces independent disk readback.
- `getSceneFromFile(file)` uses the plugin loader, including its codec. It returns
  elements/appState, **not** the full image-file store.
- `getEmbeddedFilesLoader()` creates a separate native loader.
  `createSVG(path, false, undefined, loader)` reloads the saved template through
  it. The helper decorates that owned loader's public `loadSceneFiles` boundary
  to capture the exact file's native `scene.files` before and after loading.
  It requests validated cache reads and force-reloads its image ids. Loading
  must reach the native `completed` state; a missing callback or failed loader
  is not asset evidence. No scene codec is decoded by this helper. The temporary
  SVG is not inspected render evidence; the owned loader/workbench are disposed.
- `addMermaid(source, true)` returns element ids or an error value; its
  implementation also carries returned image data into the EA image workbench.
- `createPNG(path, 1, undefined, undefined, "light", 24)` uses the drawing as a
  template through the native loader, rather than exporting stale EA elements.

The older utility overview documents only two `addElementsToView` parameters and
a different default for save. The pinned declaration and implementation expose
four/five parameters. These recipes explicitly pass the first three; do not
infer a new installed surface from an older prose example.

## Create and open

For a new drawing, keep the deterministic Python path in `SKILL.md`. It emits
`.excalidraw.md`, the plugin marker, text index and full JSON. Run the generator
and `Scene.check()`, retain its write receipt, then open the exact output through
the selected `obsidian-cli` surface. Compare the loaded element ids/count with
the authored scene; focus the exact Excalidraw view, not a same-named note.

For an already normalized upstream/exported `.excalidraw` scene, use
[`../scripts/import_scene.py`](../scripts/import_scene.py):

```sh
python3 scripts/import_scene.py \
  --source Synthetic/Flow.excalidraw \
  --target Synthetic/Flow.excalidraw.md \
  --expected-source-sha256 <digest-of-the-exact-inspected-source>
```

Run paths relative to the resolved workspace/vault, not necessarily the package.
Both paths are mandatory. The adapter is stdlib-only and new-file-only: it
preserves the entire scene envelope, element ids, custom fields and embedded
`files`, builds the native text index from raw/original text, checks references
and assets, creates exclusively and reads back. It refuses skeleton elements,
pending Mermaid, missing image data, symlinks and collisions. It never replaces
an existing plugin drawing. Existing frontmatter, prose, text records and
plugin-managed assets are therefore not rebuilt from a standalone source.
The Python format/readback check proves A/B only; open and inspect in the plugin
to establish C/D, including real image loading.

Do not silently use EA `create({templatePath})` as this adapter. In the inspected
implementation, the generated Markdown text index is based on the EA workbench,
while template elements are concatenated separately. That path needs its own
template-text/asset checks before it can replace this complete-wrapper adapter.

## Inspect, lint and edit

[`../scripts/inspect.mjs`](../scripts/inspect.mjs) is the upstream inspection and
layout-lint code adapted to read `.excalidraw.md`. It has no writer:

```sh
node scripts/inspect.mjs inspect Synthetic/Flow.excalidraw.md
node scripts/inspect.mjs lint Synthetic/Flow.excalidraw.md
```

It reports ids, labels, frames, connections, dimensions, dangling/one-way
bindings and heuristic overlaps/tight labels. Warnings are not font measurement
or render proof. Full structural validation remains the Python validator.
For compressed drawings, the reader refuses; use native scene readback and
inspect a task-owned JSON export instead. Never patch codec bytes.

[`../scripts/plugin-workbench.js`](../scripts/plugin-workbench.js) is a
dependency-free executable helper for the selected Obsidian eval/Script Engine
context. Evaluate the exact file bytes; its IIFE returns a helper object. Pass
`{app, automation: ExcalidrawAutomate}` explicitly. Loading it performs no
operation, installs nothing and selects no vault.

Call `probe(context)` before an operation. Open the exact target through
`obsidian-cli`, then call `snapshot(context, exactDrawingPath)`. Keep its exact
document, SHA-256, independently loaded elements, native saved assets
(`savedAssets.serialized` and `savedAssets.loaded`), live elements and live files
outside the workbench. Native saved asset data must agree with the live data
URLs when captured. Take a fresh snapshot with this helper revision; older
snapshots without native saved assets refuse before commit. Review those
preimages and the proposed selected-id diff.

Call `update(context, {baseline, expectedSha256, patches})`, where `patches` maps
only approved ids to changed fields. For example, an approved rectangle movement
is `{cardId: {x: 320}}`. Include every dependent label/arrow whose geometry or
binding is expected to change in the reviewed scope. Unknown fields are retained
by cloning the existing element, not creating a substitute. Identity/bookkeeping
replacement is refused. Deletion is not implied by movement or relabelling.

The helper checks both live and disk preimages before preparation and again
after any asynchronous preparation, then performs one native persistent commit.
It reloads independently and checks targeted values, non-target elements,
unknown/custom fields, existing live assets and independently loaded saved
assets, non-target text-index records, and Markdown outside the selected
index/scene. Both live and persisted element ids must be unique and equal their
baseline sets plus exactly the returned, approved Mermaid addition ids.
Unexpected or duplicate ids cannot hide behind a baseline-member comparison.
Saved assets are checked in both native pre-loading and resolved stores; an
intact live cache is not proof of disk integrity. The saved document is checked
again after native reload to detect drift during asynchronous asset loading.

Preservation is a content contract, not identical plugin serialization. Four top-level bookkeeping fields (`version`, `versionNonce`, `updated`, `index`) may change; nested custom fields, identities, text, geometry and styles remain strict except for the approved patch. The native 2.28.1 normalization observed in isolated QA permits only absent-to-null top-level `labelPosition` and `baseFontSize` on text elements, and image status transitions among absent, `pending` and `saved` after that same file id's independently loaded image bytes are verified unchanged. Non-null label values, other status values and nested fields do not inherit these exceptions.

A fresh snapshot also binds each plain Embedded Files wiki link with Obsidian's `metadataCache.getFirstLinkpathDest`, the vault's actual file list and `readBinary`. Its exact vault-relative target and attachment SHA-256 must remain unchanged. A shortened link such as `[[Attachments/Pixel.png]]` to `[[Pixel.png]]` is accepted only when both native resolutions select that exact file and the short spelling matches only one actual vault file. Repointing, ambiguity, identical bytes at another path, lengthening, unresolved links and unsupported wiki-link forms refuse; a live image cache alone cannot establish this binding. Other embedded records keep their exact spelling. Plugin-managed index separator whitespace may normalize, but frontmatter, user prose and unrelated text-index content must remain unchanged. A geometry-only text patch does not authorize rewriting its text-index record.

The native save request is not a synchronous disk acknowledgment. Before its single commit the helper subscribes to the exact drawing's `vault.modify` event, flushes the native scene, forces its native save, then awaits that signal with a 30-second bound before independent readback. It disposes the subscription/deadline on every exit. A missing event, failed reload or old partial-effect receipt must not be rewritten as success; do not replay its mutation. Use a fresh snapshot and a new owner-approved transaction for another operation.

These are optimistic checks, **not** an exclusive editor lock or OS compare-and-
swap. Do not edit concurrently during the native commit. A post-commit drift,
failed save or failed reload is a **partial effect**, not a success and not an
automatic rollback. Retain both preimage and actual result and report the drift.
Errors after a commit attempt have `partialEffect: true`, including when the
native surface cannot establish saved-asset integrity. This marks a possible
partial native effect, not a claim that the commit completed. Do not replay a
mutation to make its receipt look clean.

## Mermaid into the plugin drawing

For a new Mermaid drawing, first create/open an empty deterministic plugin
drawing at the exact approved destination. Take a fresh snapshot, then call
`update(context, {baseline, expectedSha256, mermaid: source})`. Conversion occurs
through the installed plugin's `addMermaid`, not a separately bundled renderer.
No hard-coded diagram-size threshold selects this path.

This helper adds a diagram; it does not replace unrelated existing elements.
An error/null/empty conversion, id collision or conflicting image id stops
before native commit. Re-import is another additive transaction, not an implicit
replacement of earlier Mermaid ids. Plan replacement/deletion separately.
Native flowchart conversion is the intended first runtime fixture. Other diagram
types may produce image fallbacks; their assets and Embedded Files serialization
require separate runtime checks. If that changes protected Markdown, the helper
reports a partial preservation failure rather than claiming success.

For the upstream skeleton shorthand and palette/layout recipes, read
[`skeleton.md`](skeleton.md) and [`style.md`](style.md). Do not pass an unnormalized
standalone skeleton directly to `elementsDict` or to the Markdown adapter.

## Reload, export, inspect

Use `renderPNG(context, {path, expectedSha256})` against the exact newly read
digest. It reloads the saved drawing through the plugin's template/asset loader
and returns a Blob; it does not choose or write an image destination. The caller
must have separate authority for the task-owned image destination, save its
bytes and **look at the image**, including embedded images and CJK text.

Use the caller-owned asynchronous handshake in
[`workbench.md`](workbench.md) for the official CLI's synchronous eval transport:
one fresh caller token per mutation or export. The helper's returned Promise is
not a synchronous CLI result. Subscribe to completion/state before triggering
an operation; avoid arbitrary sleep-based tests.

Report C only for actual load/readback in the selected Obsidian plugin, and D
only after its export/view screenshot was inspected. Unit tests of these helper
boundaries are neither C nor D. A standalone Excalidraw image proves neither.

## Exact isolated QA scope

When an approved isolated app surface is available, record app/plugin versions,
artifact hashes and profile/vault identity in private evidence. Use a new
task-owned synthetic vault/profile, copied approved plugin artifacts only, and
no user settings/data/profile. Keep all drawings, assets and exports there.
Exercise: create/open, full-scene import with labels and an inline image,
selected edit with a user custom field and an unrelated control drawing,
flowchart Mermaid insertion, stale disk/live refusal, compressed-file native
readback, independent reload and plugin export. Inspect desktop and narrow view
captures where meaningful. Compare control and attachment hashes, then close
only the owned app/profile and retain a cleanup receipt.

If copied artifact provenance, profile launch authority or exact QA root is
missing, finish A/B and source/API checks, then request those concrete effects.
Do not use a production vault, enable a plugin, or infer prior canary permission
from a historical verification row. No live C/D result is recorded by this recipe.
