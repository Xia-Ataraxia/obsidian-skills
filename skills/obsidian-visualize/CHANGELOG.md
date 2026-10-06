# Changelog

## 0.2.0 — Unreleased source implementation

- 2026-10-06 — Observed the native workflow in an isolated Obsidian 1.12.7, Electron 39.8.3 and Excalidraw 2.28.1 installation. Native drawing load, selected-color persistence, independently loaded image bytes and inspected plugin PNG/app views were observed. Strict serialization preservation first failed because native saving adds metadata and shortens attachment links.

  The selected content-preservation contract now admits only equivalent native normalization, retaining element identities, custom fields, image bytes and the exact resolved attachment target. Content changes and redirected links still fail. The helper subscribes to the exact file modification before committing, flushes the native scene update, and requests a native forced save before independently reloading it.

  The owning module passes all 14 checks using a physical temporary directory, and all 41 affected helper regressions pass. A fresh native transaction returned a clean persisted-readback receipt with only its selected color changed; the final PNG and app screenshot were inspected. Earlier failed transactions and the symlink-ancestry test failure remain recorded, not replayed or weakened. This observation does not certify Mermaid/image fallback coverage or a production installation. Official API/source references remain pinned below.
- 2026-10-04 — Repaired the independently reproduced G1/G2 source-gate failures.
  Saved assets are now captured through a fresh native template/embedded-files
  loader, independently of the live asset cache, before and after commit.
  Missing/changed saved data or unavailable/failed native readback cannot yield
  a preservation receipt. Live and persisted element ids must be unique and
  match the baseline plus exactly approved Mermaid additions. Post-attempt
  failures expose `partialEffect: true`; no rollback or replay is attempted.
  Added saved-asset corruption and separate live/persisted unexpected/duplicate
  id regressions, plus a native-loader completion signal without sleeps.
  Source correspondence includes public `EmbeddedFileLoader.ts` at the same
  official pin below. Native C/D remains unverified.
- 2026-10-04 — Absorbed useful source from
  `Jonghakseo/pi-extension@a4a8107885d2e944d03d8ebc7d9b1cdcf8b7521f`
  (`skill-excalidraw` 0.1.3) into this existing owner: read-only inspection/layout
  lint and adapted skeleton/palette/spacing recipes. Retained its complete
  `Copyright (c) 2026 Jonghak Seo` MIT grant in package `NOTICE`; full source-tree
  digests, exclusions and target mappings are in `source-map.json`. No standalone
  app/server/browser/build lifecycle, binary, font or new skill is shipped.
- Added original `import_scene.py`: explicit inspected-source SHA-256 and new
  `.excalidraw.md` destination, full scene/ids/custom-field/inline-asset
  preservation, raw/original text index, exclusive creation and readback.
  Existing drawings, skeletons and pending Mermaid are refused; native
  plugin-managed compressed drawings are never patched as codec bytes.
- Added original `plugin-workbench.js` for an already-enabled plugin: exact-target
  live/disk/asset snapshots, selected-id copied edits, additive native
  `addMermaid`, one persistent EA commit, independent reload/preservation checks,
  and PNG export through the plugin's saved-template/asset loader. Preparation
  rechecks stale preimages; post-commit failure is reported as a partial effect
  without replay or automatic rollback. This is optimistic concurrency, not a
  lock against a user editing during the commit.
- Preserved the deterministic stdlib generator and all existing routing cases.
  Added a final replacement-preimage check after temporary payload flush and
  fixed deleted-text tombstone readback, matching its existing live text index.
  Plugin-first guidance distinguishes file-only A/B from actual Obsidian C/D,
  retains exact destination policy and CLI/doctor ownership, and specifies the
  isolated synthetic native QA surface.
- Official facts were read from
  `zsviczian/obsidian-excalidraw-plugin@f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79`
  (source manifest 2.28.1): `docs/API/ExcalidrawAutomate.d.ts`,
  `src/shared/ExcalidrawAutomate.ts`, and
  `src/utils/excalidrawAutomateUtils.ts`. `getSceneFromFile` omits the binary
  store; image preservation needs independent native saved-asset loading as
  well as live/Markdown checks. The older
  utility prose has fewer `addElementsToView` parameters/different save defaults,
  so calls use explicit admitted methods. Native template creation's text-index
  construction is not assumed to cover concatenated template elements; the
  full-scene wrapper adapter tests that behavior instead. Exact official URLs
  and sources are retained in package `PROVENANCE.md`.
- Installed runtime version was not established. Historical isolated verification
  and earlier inventories are not current plugin proof. Author checks cover
  new-file import, ids/custom fields/assets/text-index preservation, deleted text,
  late preimage conflict, malformed inputs, non-target controls, read-only
  inspection and stateful native API-boundary success/refusal/partial-failure
  cases. Those boundaries are tested without executing Obsidian; no current
  C/D render or runtime Mermaid/image fallback is claimed.
- `metadata.implementation_version` is now 0.2.0. `metadata.version` stays at the
  collection's 0.1.0 release identity required by existing manifest tests;
  manifests, authenticated native inventory, registration and existing release
  artifacts are unchanged. New lineage uses the additive owner-local source map.
  Later exact-tree release/privacy revalidation is required.

## 0.1.0 — Unreleased

- 2026-09-29 — Established `obsidian-visualize` as the independent owner of visual-form selection and Excalidraw file generation in this repository. The package operates on its own: no callable root skill, no dispatcher, no shared runtime, and no compatibility alias. Neighboring packages (`obsidian-canvas`, `obsidian-mermaid`, `obsidian-markdown`, `obsidian-cli`) are named by identity only and are never loaded automatically; no document in this package links to a file outside it.
- 2026-09-29 — Diagram requests were being answered by whichever form was convenient, and "the drawing renders" was being claimed from the fact that a file had been written → `SKILL.md` makes both explicit: a four-row selection table keyed on what the nodes actually are (Canvas for note references, Excalidraw for free shapes, a Mermaid fence for in-note structure, a table for values), and a four-level evidence ladder that separates static validation (A), materialized readback (B), runtime load in the target app (C), and inspected render QA (D). Levels A and B are reachable with Python and a filesystem alone; C needs an installation and D additionally needs the plugin already installed and enabled. The package states that it cannot install or enable a plugin and cannot render anything, and that an SVG or PNG assembled from the same numbers would restate the JSON rather than prove the plugin parses it.
- 2026-09-29 — Completed `scripts/excalidraw_scene.py` into a full working generator (Python 3.9+, standard library only, no pip or network dependency). The existing measurement, validation, and identity sections were preserved as-is; this entry adds the element builders (`rect`, `text`, `box`, `arrow`, `frame`, `add_to_frame`, `group`), the native Markdown document assembly (`render_drawing`, `extract_scene`, `read_drawing`), the non-destructive writer with its `WriteReport` receipt, and the module self-check. `python3 excalidraw_scene.py` builds a demo pipeline, validates it, writes it into two temporary directories, asserts the two files are byte-identical, asserts that a second write to the same path is refused, and replaces the drawing through the digest-guarded path.
- 2026-09-29 — Determinism is a property of the module, not a convention: element ids, `seed`, `versionNonce`, and `updated` derive from `(namespace, element kind, creation order, optional caller key)` through BLAKE2b, so there is no clock, no PRNG, and no process entropy anywhere in the file, and two runs of the same generator produce identical bytes. Ids deliberately ignore element text so relabelling a card keeps its id and its diff small; an explicit `key=` pins an id to a caller-chosen name so a change in construction order does not renumber a scene.
- 2026-09-29 — Correctness work on the generator in this entry: geometry is checked for real, finite values at construction time (booleans are rejected as coordinates, extents must be non-negative, font sizes positive); an arrow bound to itself, to an element belonging to a different `Scene`, or to an unknown anchor side is refused before it can become a dangling reference; derived identity fields cannot be overridden through `**style`; frontmatter keys and values are validated so a multi-line value cannot break the YAML block, and a description cannot smuggle in a second drawing fence; JSON is emitted with `allow_nan=False` so a non-finite number can never be written as invalid JSON.
- 2026-09-29 — Unicode measurement fix: conjoining Hangul jamo (grapheme-cluster classes V and T, `U+1160–U+11FF`, `U+D7B0–U+D7C6`, `U+D7CB–U+D7FB`) are `Lo` rather than combining marks and are not east-asian *wide*, so a decomposed (NFD) syllable measured wider than the precomposed syllable it renders as and cards sized from it were too wide. Those ranges now measure as zero-width in both `char_ratio` and the cluster splitter that keeps wrapping from separating a mark from its base, so NFD and NFC text measure identically. Advance width remains an estimate, not font metrics; an emoji ZWJ sequence is over-measured, which widens a card instead of clipping it.
- 2026-09-29 — Non-destructive writing is enforced by the module, not by guidance: a new drawing is published exclusively (a hard link from a temporary file in the destination directory, falling back to an `O_EXCL` create on filesystems without links), a replacement is an atomic `os.replace`, and no path is ever truncated in place. Replacing an existing drawing requires `overwrite=True` *and* `expected_sha256` — the digest of the exact bytes the caller inspected — after which the writer re-verifies the digest, diffs element ids and arrow bindings, replaces atomically, reads the file back, revalidates it, and returns `added_ids`, `removed_ids`, and `binding_changes`. A directory, a symlink, a path not ending in `.md`, and any existing file with no `## Drawing` section are all refused, so a plain note cannot be turned into a drawing by accident even with a correct digest.
- 2026-09-29 — Overlapping filled rectangles are reported as a layout heuristic (`overlap:` prefix) rather than a schema error. A caller that stacks fills on purpose passes `allow_overlaps=True` and receives those defects back in `report.allowed_overlaps` to quote in its report, instead of silently dropping them.
- 2026-09-29 — Added `references/workbench.md` for the two cases that genuinely need the plugin's automation API — an interactive edit inside a drawing the user has open right now, and embedding a file that must go through the plugin's file store. It opens with an admission probe whose results are read as a hard gate (a disabled plugin, an absent automation object, a missing method, or a drawing that is not open each stop the path), then covers the pre-mutation snapshot, the build-and-persist calls, a caller-owned two-token handshake for completing an async call through the CLI's synchronous `eval`, and the reload-then-render order that separates a live scene that looks right from a file that actually holds the edit. Element count is explicitly not a reason to use this path, and nothing in it installs, enables, or updates a plugin.
- 2026-09-29 — Added `tests/test_visualize.py` (repository test root, not inside the package): Unicode and wrapping edge cases, invalid builder input, validation of hand-built foreign scenes, document round-tripping, write refusals and non-target preservation, re-run determinism and diff reporting, and package integrity including link resolution inside the package and the standard-library-only import set. The suite tests behavior, not instructional wording, and makes no runtime, plugin, or rendering claim.
- 2026-09-29 — Only synthetic public English examples are used. No credentials, account identifiers, workstation paths, vault names, private note content, or raw logs appear in any file in this package.

### Grounded facts and sources

Authoring evidence, read 2026-09-29:

- An `.excalidraw.md` drawing is Markdown carrying `excalidraw-plugin: parsed` in frontmatter, a human-readable `## Text Elements` index whose entries end with `^<elementId>`, and the real scene in a fenced `json` block under `## Drawing`, wrapped in a `%%` pair. The plugin can alternatively store that scene as `compressed-json`, which is codec output — this package neither writes nor diffs it. Source: the [Excalidraw plugin repository](https://github.com/zsviczian/obsidian-excalidraw-plugin).
- Scene envelope fields (`type: "excalidraw"`, integer `version`, `source`, `elements`, `appState`, `files`) and element requirements: a bound label needs `containerId` on the text *and* a mirrored `{"type":"text","id":…}` entry in its container's `boundElements`; an arrow's `startBinding`/`endBinding` are `{elementId, focus, gap}` mirrored as `{"type":"arrow","id":…}` on both endpoints; `points` are relative to the arrow's own origin with the first point exactly `[0, 0]`; `frameId` and `groupIds` carry frame and group membership; `fontFamily` ids are 1 hand-drawn, 2 normal, 3 code. Same source, plus the published [ExcalidrawAutomate type surface](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/master/docs/API/ExcalidrawAutomate.d.ts) for the API names quoted in `references/workbench.md`.
- The Canvas branch defers node/edge schema, colors, and ID conventions to the JSON Canvas format owner; this package adds only the selection rule and the vault-resolution check. Source: [JSON Canvas 1.0 spec](https://jsoncanvas.org/spec/1.0/).
- Text advance width is derived from the East Asian Width property (`W` and `F` cost a full `fontSize`) plus a zero-width class for combining marks, enclosing marks, and format characters, and now also for conjoining Hangul jamo. Sources: [UAX #11 East Asian Width](https://www.unicode.org/reports/tr11/) and the Hangul syllable-composition classes L, V, and T in [UAX #29](https://www.unicode.org/reports/tr29/).
- The official Obsidian CLI's `eval` returns synchronous values only, which is why the exception path needs a caller-owned launch/poll handshake rather than an `await` inside one evaluation. Recorded as a constraint on the exception path; the command surface itself belongs to `obsidian-cli`.

No Obsidian installation, no Excalidraw plugin, and no destination vault were available in this authoring environment. Evidence levels C and D were therefore not reached for anything in this package, and no element count, view load, or rendered image is claimed anywhere in it.

### Provenance

- Requirements evidence was taken by reading three files of a local craft-skills checkout pinned at revision `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, opened read-only: `skills/obsidian/references/visualize.md` (format choice, file anatomy, procedure, safety rules, result reporting), `skills/obsidian/references/ea-workbench.md` (plugin admission, workbench acquisition, persistence, async completion guard, reload and render QA), and `skills/obsidian/scripts/excalidraw_scene.py` (which problems a generator helper must solve).
- That checkout carries no root license or notice file, so no prose, table, checklist, code block, or example from it was copied or redistributed. Every requirement was reimplemented in original wording and original code: the generator shares no function body, naming scheme, or data layout with the file that was read as evidence, and the handshake in `references/workbench.md` is a different design (one caller-held token guarding a single run record) rather than a transcription of the one described there. Public vendor documentation is cited directly for every factual claim above.
- The upstream helper read as evidence used `random` for ids and seeds, a fixed-range width table, and a `FileExistsError` guard on write. None of that was carried over: this generator derives identity from a namespace digest, measures with `unicodedata`, and requires an inspected-bytes digest before it will replace a drawing.
- All files in this package are original work under the MIT `LICENSE` shipped in this package. No upstream MIT notice applies, because no upstream-derived file is included. The third-party Excalidraw plugin is cited as a primary source and is neither vendored nor redistributed here.

### Limitations

- Evidence level B is the ceiling reached in this entry. Static validation and materialized readback are proven by the module itself; no drawing in this package has been opened in Obsidian, loaded by the Excalidraw plugin, or rendered and inspected.
- Every JavaScript block in `references/workbench.md` was authored against published API documentation and was never executed: no plugin was present to execute it against. The admission probe exists precisely so a caller discovers that state itself instead of assuming the surface is available.
- Text measurement is an estimate, not font metrics. Emoji ZWJ sequences and regional-indicator pairs are over-measured (each pictograph counts), which widens a card rather than clipping it; when a real font still clips, the documented fix is to widen `max_width`, not to add a metrics dependency.
- The overlap check is axis-aligned bounding-box only. It does not model rotation, stroke width, rounded corners, or text that a real font renders wider than estimated.
- `compressed-json` scenes are out of scope in both directions: the writer never produces one, and a drawing stored that way cannot be diffed or replaced through this module — it is reported as a refusal.
- The exclusive-create fallback used on filesystems without hard-link support publishes bytes in place rather than by rename. It remains exclusive (an existing path is never clobbered) but is not atomic under a concurrent reader on those filesystems.
- Scope note: this entry records authored content. The module self-check (`python3 scripts/excalidraw_scene.py`) was executed in this authoring environment and passed, writing only into temporary directories; no gate, formatter, linter, or candidate-test run is recorded here, no installation or release was performed, and no destination vault was read or written.
