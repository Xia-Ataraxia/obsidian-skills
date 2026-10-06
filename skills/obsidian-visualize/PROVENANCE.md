# Plugin-first source integration

Implementation revision: **0.2.0**. The collection's release identity remains
0.1.0: existing tests bind package metadata.version to the collection manifests.

## Imported source and rights

- Source: https://github.com/Jonghakseo/pi-extension
- Exact revision: `a4a8107885d2e944d03d8ebc7d9b1cdcf8b7521f` (resolved and read 2026-10-04).
- Package: `packages/skill-excalidraw`, published metadata version 0.1.3.
- Root LICENSE is a complete MIT grant, copyright 2026 Jonghak Seo; its exact
  notice is retained in [NOTICE](NOTICE). License SHA-256:
  `98e16fcc766bfadb58da83c0ca4b127f199300f407d97758cf0b31aa8ae0f829`.
- [source-map.json](source-map.json) enumerates all 19 pinned package/root-notice
  files, original SHA-256/byte counts, adopted targets and exclusions. The three
  adopted capabilities belong solely to F05, not a new package or router.

[`scripts/inspect.mjs`](scripts/inspect.mjs) retains upstream inspect/lint
algorithms but removes every write, standalone lifecycle, app/browser launch and
build dependency. It reads plain plugin Markdown fences, fails closed on
compressed data/malformed structures and adds finite-geometry/mirrored-reference
checks. [`references/style.md`](references/style.md) adapts palette, spacing and
layout recipes to deterministic layouts and plugin exports.
[`references/skeleton.md`](references/skeleton.md) adapts the shorthand idea
to the existing generator/native workbench; automatic standalone normalization,
random identity replacement and live whole-scene merge are not adopted.

## Original adaptations

- [scripts/import_scene.py](scripts/import_scene.py): stdlib-only full-scene
  adapter, mandatory source SHA-256, exclusive new target, preserved envelope,
  unknown/custom fields, ids and inline image data; native raw/original text
  index and readback. No overwrite or skeleton/codec support.
- [scripts/plugin-workbench.js](scripts/plugin-workbench.js): original
  dependency-free native EA operations; exact target, disk/live/asset preimages,
  selected copy/edit/save, additive native Mermaid conversion, independent
  reload and native-template PNG export. Optimistic concurrency, not an editor
  lock. Post-commit drift is a partial effect and never auto-rolled back.
- [scripts/excalidraw_scene.py](scripts/excalidraw_scene.py): original generator
  remains deterministic/stdlib-only. Replacement preimages are rechecked after
  temporary payload flush and before atomic replacement; deleted text tombstones
  no longer require live text-index entries.
- [references/plugin-workflow.md](references/plugin-workflow.md) and
  [references/workbench.md](references/workbench.md): native admission, explicit
  CLI ownership, persistence/readback/render boundaries and exact isolated QA.

## Official implementation facts, not copied code

Official plugin source pin:
`f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79`; manifest declares **2.28.1**,
not an installed version. Read 2026-10-04:

- https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/manifest.json
- https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/docs/API/ExcalidrawAutomate.d.ts
- https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/src/shared/ExcalidrawAutomate.ts
- https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/src/utils/excalidrawAutomateUtils.ts
- https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/src/shared/EmbeddedFileLoader.ts

The older utility overview and current declaration/implementation differ in
parameter counts/defaults for addElementsToView. Use admitted methods with
explicit arguments, not an inferred installed version. The template loader
handles native codec/image loading, but EA.create builds its Markdown index
from EA elements separately from template elements. That is why full-scene
Markdown import uses the tested explicit wrapper adapter rather than silently
assuming template creation preserves a complete native index.

### Independent source-gate repairs

The source gate reproduced two false-success cases: saved assets disappeared
while the live cache remained intact, and unexpected/duplicate element ids
were not excluded by baseline-only checks. The repair compares independently
loaded native saved assets as well as live files, and requires exact unique
live/persisted id sets including only approved native Mermaid additions.

The native saved-asset reader uses the public EA loader factory and `createSVG`
loader argument. It decorates only its fresh loader's public `loadSceneFiles`
method, captures the matching `ExcalidrawData.file`/`scene.files` around native
loading, requests validated/forced image reloads and requires `terminalState`
to be `completed`. The native template parser handles compressed data. No
private plugin import, manual codec, user configuration or cached live-view
read substitutes for this native saved-file boundary. Owned PDF resources and
the temporary workbench are disposed; no image destination is written.

The additional official loader source above was read at the same pin on
2026-10-04, SHA-256
`e58d4ff412786126ca20644cde0eb55684dabc78a49497848aaf616903c2e74c`.
Its public loading options, completion states, and the public data `file`/`scene`
fields were checked alongside `ExcalidrawData.ts` and the existing EA/template
sources. This is source correspondence, not installed-version or C/D proof.
If an admitted native surface cannot provide the callback/data/completion
state, snapshot refuses or a post-commit error reports `partialEffect: true`.
No automatic rollback or replay is introduced. Fresh native-asset snapshots
are required; older snapshots are refused before mutation.

No plugin code or binary is copied. Current installed-version/enablement facts
are not established by this source change; prior inventories have their own
freshness and do not pin a current runtime. Historical native verification is
not repeated or upgraded.

## Assets, dependencies and evidence limits

### Native observations on 2026-10-06

An isolated runtime identified Obsidian 1.12.7, Electron 39.8.3 and Excalidraw 2.28.1. Official release assets matched their pinned hashes: https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.28.1. They were used privately for native QA and are not shipped in this package. The tagged LICENSE contains AGPL-v3 text despite the tagged package metadata's MIT declaration; no redistribution right over those binaries is asserted.

Native load, selected-color persistence, independently loaded image bytes and inspected plugin PNG/app views were observed. Saving adds native metadata and can shorten an embedded-file link. The selected content-preservation contract admits those equivalent changes only while preserving element content/custom fields and the exact resolved attachment target and bytes. A redirected link is not equivalent even when its file contents happen to match.

The native operation also returned before its queued file write. The original helper now subscribes to the selected file's modification event before commit, flushes the native scene with `viewUpdateScene({appState: {}})`, requests `forceSave(true, true)`, then independently reloads the saved result. All 14 owning-module checks and 41 affected helper regressions pass. A fresh native transaction returned a clean persisted-readback receipt, preserving every non-target element, image bytes and the exact attachment target; its final native PNG and app screenshot were inspected. Failed transactions are retained as failures, not upgraded or replayed. These observations do not certify other plugin versions, production enablement, Mermaid conversion or image-fallback coverage.

No standalone dist, server, browser app, dependency tree, fonts, image library or
Obsidian plugin artifact is shipped. The upstream tree contains source and a
synthetic JSON example, not a built app; the example/wrapper/app are excluded.
Third-party app/font bundle redistribution rights are not needed or claimed.
The briefly prepared standalone source and owner-local development dependency
tree were removed when the requested scope became plugin-first.

Python 3.9+ remains standard library only. Optional inspection uses Node.js
(author checks: 24.21.0). Native helper operations use the target app's already
enabled EA/Web Crypto surfaces, discovered before effects; no npm dependency,
build, installation, configuration change or default destination is required.

Author tests exercise file format/readback, conflicts/preservation and stateful API boundaries; those tests alone prove no runtime or render behavior. The isolated observations above supply native load/render evidence for their specific fixture only. Runtime Mermaid/image fallbacks remain unverified. No standalone image substitutes for plugin proof.
Existing release attestations do not cover this new source; later exact-tree
release and privacy revalidation is required before any publication/deployment.
