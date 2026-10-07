# Changelog

## 0.2.2 — 2026-10-07

- 2026-10-07 — Collection release `0.2.2`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.
## 0.2.1 — 2026-10-07

- 2026-10-07 — Collection release `0.2.1`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — Unreleased

- Mermaid guidance written for generic renderers keeps producing blocks that pass in a live editor and then fail, or quietly look wrong, inside a vault whose app carries a pinned Mermaid build → this package makes the bundled renderer the acceptance surface: an evidence ladder that separates authoring checks, parse validation, materialized readback, and render QA in the target app; a family-selection table; the syntax and escaping rules that actually break blocks; exact fence and nesting rules; a safe exact-edit and readback procedure for notes; and a fallback policy that forbids shipping a smaller diagram that says less.
- Version-gated diagram families were the main failure mode and had no local answer → [`references/compatibility.md`](references/compatibility.md) adds a decision gate, a keyword table with the reason for each spelling, a runnable capability probe, a failure-reading table that separates an unsupported family from an unsupported feature from a readability problem, a render-QA definition distinct from parsing, and a result-recording format that leaves the bundled Mermaid version `unknown` rather than guessed.
- Reconstructing unfamiliar grammars from memory produced invalid blocks → [`references/diagram-catalog.md`](references/diagram-catalog.md) ships fifteen copy-ready families split into a conservative core and a version-gated set, each gated entry naming a fallback plus what that fallback drops, with one worked fallback conversion.

### Grounded facts and sources

Authoring evidence, read 2026-09-29:

- `architecture-beta` is documented as v11.1.0+ — <https://mermaid.js.org/syntax/architecture.html>
- `treemap-beta` is the documented keyword and upstream flags its syntax as still evolving — <https://mermaid.js.org/syntax/treemap.html>
- Sankey and XY chart detectors match `/^\s*sankey(-beta)?/` and `/^\s*xychart(-beta)?/` on `mermaid-js/mermaid@develop`, which is why this package writes the `-beta` spelling: it is the one that also parses on older bundles — `packages/mermaid/src/diagrams/sankey/sankeyDetector.ts`, `packages/mermaid/src/diagrams/xychart/xychartDetector.ts`
- Flowchart rules taken from upstream syntax documentation: quoting for troublesome characters, entity-code escapes (`#quot;`, `#35;`, decimal codes), Markdown-string labels with real line breaks, `graph` as an accepted alias, lowercase `end` breaking the parser, and a node id beginning with `o`/`x` after an edge turning it into a circle/cross edge — <https://mermaid.js.org/syntax/flowchart.html>
- Flowchart defaults (theme, look, layout engine) changed at v12.0.0, so identical source renders differently across major versions — upstream flowchart documentation
- Obsidian renders Mermaid from a `mermaid` code block, links nodes to notes through the `internal-link` class, requires quoting note names with special characters, and excludes those links from Graph view — <https://help.obsidian.md/advanced-syntax>
- Kanban column/task structure and the `assigned`/`ticket`/`priority` metadata keys with their four allowed priority values — <https://mermaid.js.org/syntax/kanban.html>
- User journey task syntax `Task name: <score>: <actors>` with the score bounded to 1–5 inclusive — <https://mermaid.js.org/syntax/userJourney.html>

No version probe was run in this authoring environment: no Obsidian installation, no Mermaid CLI, and no vault were available. The package deliberately hardcodes no bundled Mermaid version and ships the probe procedure instead. `verified_against:` is therefore empty for this entry.

### Provenance

- Source-informed by `skills/obsidian/references/mermaid.md` and `skills/obsidian/references/mermaid-diagram-catalog.md` in the craft-skills tree at revision `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, opened read-only as requirement evidence for which problems this package must solve.
- No prose, table, checklist, or example block was copied from those files. Every rule here was re-derived from the upstream Mermaid and Obsidian documentation cited above, and every example was newly authored around one synthetic public-library scenario.
- The upstream catalog credited its examples to a third-party collection it did not name with a resolvable link or license notice, so none of that example text was carried forward and no rights claim about it is made here.
- All files in this package are original work covered by the repository's MIT `LICENSE`. No upstream MIT notice applies, because no upstream-derived file is included.

### Limitations

- Evidence level A only. No block in this package has been parse-validated by a Mermaid build or rendered in an Obsidian installation; catalog entries are authored against current grammar documentation and state that status in the file.
- Detector evidence comes from the `develop` branch, which can lead the released version. It supports the claim that the `-beta` spellings remain accepted, not any claim about a specific shipped release.
- The one second-hand baseline encountered in the source material — one installation reported as Obsidian 1.13.1 with Mermaid 11.13.0 rendering the catalogued families — was not reproduced and is recorded here as a data point only. It is not a support statement, and it must not be reused in place of probing the target installation.
- Upstream version badges exist for some families and not others; `kanban`, `treemap-beta`, and the in-fence config header are treated as version-gated by policy rather than by a documented introduction version.
- Obsidian publishes no user-facing bundled-Mermaid version, so the probe reports capabilities rather than a version number.
