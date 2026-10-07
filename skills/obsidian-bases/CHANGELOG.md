# Changelog

## 0.2.1 — 2026-10-07

- 2026-10-07 — Hermes Agent v0.21.5 `skills_guard` refused community installs of four 0.2.0 packages with a CAUTION verdict; this package's YAML troubleshooting list wrote the exclamation mark as a one-backtick code span, which the guard's HIGH `inline_shell_exec` rule matches. It is now a double-backtick span with padding; the rendered list and its meaning are unchanged. `metadata.version` follows the collection release `0.2.1`.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — Unreleased

Not published, not installed anywhere, and not exercised against a running Obsidian app by this entry's author. What follows records the imported material, the modifications made to it, the evidence behind every addition, and what remains unverified.

### Upstream source and attribution

- Origin: the `skills/obsidian-bases/` package of [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills), pinned at commit `3ccff5338ea700537839b21900aa5358a0402c98`.
- License: MIT License, Copyright (c) 2026 Steph Ango (@kepano). The pinned source carries a root `LICENSE`. That copyright notice and the MIT permission notice cover this material and must accompany any copy or substantial portion of it, including this package; the package-local `LICENSE` file carries both, as does the repository-root `LICENSE`.
- Relationship: imported, then modified. This package now owns the Bases recipe locally. It is not a mirror, an alias, or a fallback of the upstream package, and it reaches no router, core, or dispatcher.
- Files taken from it: `SKILL.md` (source digest SHA-256 `c0037f20926c7d8591cdd040365e4c0e4c0c4146386a506f28f241faee9a27d9`) and `references/FUNCTIONS_REFERENCE.md` (source digest SHA-256 `208fd63aead9bca1975626fea52605e6ab9434dc0529d923feb36b18b8877d3b`).

### `references/FUNCTIONS_REFERENCE.md` — imported unmodified, retained in full

- The upstream text is present byte for byte: global, any-type, date, duration, date-arithmetic, string, number, list, file, link, object, and regular-expression sections, with every signature and description. Verified by SHA-256 of the file body against the pinned source: both `208fd63aead9bca1975626fea52605e6ab9434dc0529d923feb36b18b8877d3b`.
- The only local addition is the leading HTML comment carrying the import notice, the MIT attribution, and the statement that this catalog is complete on its own. Whole-file digest with that header: `b8917cb1aa82d87fde093b5b80db500a32d19a59fb973a5a9292897e436314f2`.
- This entry did not change the file. It is the package's complete function catalog, which is what makes the skill resource-closed: no remote page and no other package has to be fetched to write a filter or a formula.

### `SKILL.md` — imported and modified

Preserved from upstream, unmodified in substance: the create/scope/formulas/views/validate workflow steps, the schema block, filter structure and the filter-operator table, the three property kinds and the file-property table, the `this` keyword rules, the formula examples, the key-function table, the Duration type rules and date arithmetic, the table/cards/list/map view blocks, the default summary-formula table, all three complete examples (task tracker, reading list, daily notes index), the embed syntax, the YAML quoting rules, the troubleshooting sections, and the four `help.obsidian.md` reference links.

Modifications and additions:

- Frontmatter: `name` unchanged; `description` extended with preservation and readback triggers, the embedded `base` block and `groupBy`/`sort`/`limit` trigger words, and an explicit not-for list (Markdown note syntax, `.canvas` structure, Dataview, vault CLI) so routing stays unambiguous.
- Added an ownership paragraph stating that the package is standalone and resource-closed, and a scope note that format capability is not vault write authority.
- Added a `Scope` section: what is owned, what belongs to the target vault's own written policy (purpose, placement, template, provenance), and the rule that `obsidian-markdown`, `obsidian-canvas`, and `obsidian-cli` are named by identity only when a task actually reaches those artifacts. Added the standalone/optional-composition statement: no plugin, server, or configuration is required, an explicitly selected surface composes optionally, absence is normal, and presence without selection means unused.
- Workflow: prepended target resolution and read-first, and split the final step into readback and render as separate claims.
- Schema block: added `sort` and `kanban`, clarified that `limit` caps displayed rows and `order` lists columns, and added a note that views may carry view-state keys this schema does not list, which must survive an edit.
- Filters: added that global and view filters combine with `AND`, and the rule that a filter object holds exactly one of `and`/`or`/`not` over a heterogeneous list.
- Added an arithmetic-operator table alongside the upstream comparison/logical table.
- File properties: added the `file.file` row, the performance caveat on `file.backlinks`, and the refresh caveat on `file.backlinks`/`file.properties`; expanded the `this` entries with the documented examples.
- Formulas: added formula-to-formula references with the no-cycle constraint and the note that a formula's YAML string still yields a typed value.
- Added a `Rows: Filter, Group, Sort, Limit` section: a key-by-key table separating candidate selection, grouping, row order, row cap, and column order; the `ASC`/`DESC` meaning per property type; tie-breaking by later `sort` entries; the single-`groupBy` constraint; empty group values; and the rule that which rows a `limit` keeps is a rendered outcome to read, not to assert.
- Views: added the Kanban block and a layout-availability table with app versions and extra requirements, plus the statement that layout availability is a runtime fact of the installed build and not assertable from YAML.
- Summaries: added the distinction between the top-level custom-summary section (where `values` is the property's values across the result set) and the per-view `summaries` map, with an example.
- Added a worked example with a neutral three-note fixture, a base using `filters`, `groupBy`, `sort`, `order`, and `limit`, and an explicit expected-row table naming group, row order, and column order, plus why each row is present or absent.
- Embeds: added that a selector-less embed renders the first view so reordering views changes it, that `#View Name` is matched by name and renaming breaks embeds silently, and that a fenced `base` block uses the identical schema with the note owned by `obsidian-markdown`.
- Troubleshooting: added circular formulas, and a section stating that an empty or unexpected view is a data/index/capability result rather than a syntax error to be fixed by loosening the schema.
- Added a static `Validation Checklist` and the explicit statement that passing it proves nothing about materialization or rendering, an `Operations` pointer, the `references/operations.md` reference link, and an `Attribution` section.

### `references/operations.md` — authored for this repository

New file, original wording. It covers the authorization boundary and the target vault's policy ownership; optional composition with `obsidian-cli` and `obsidian-markdown` by explicit selection only; safe edits that keep unrelated views, view order and names, unrelated formulas and properties, and unknown view-state keys; validate-before-write with no partial writes; an error table mapping each condition to the exact key path to report; a triage order for empty or unexpected results (wrong file, filters, property mismatch, scope, index, capability); static validation, exact readback, and rendered verification as three separate claims with the specific rendering evidence to collect and the app version to scope it to; embedded blocks and `#View Name` embed hazards including `this` changing meaning inside an embed; reporting and privacy rules; and a verification checklist.

### Evidence

Requirements evidence, read read-only:

- `skills/obsidian/references/bases.md` (SHA-256 `d4387d4535976a12c483f8315e76e0d53cdeee47f449757a161a19fb78cdce82`) and `skills/obsidian/references/markdown.md` of a local Craft skills checkout pinned at commit `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, used only to establish which problems this package must solve: target-vault authorization before mutation, the separation of a valid document from a loaded file from a rendered view, empty results as an app/index/filter question, embed composition with note handling, and runtime plugin requirements as facts rather than inferences. That checkout carries no root license or notice file, so no prose, table, checklist, or example was copied or redistributed from it; every requirement was reauthored independently here.

Format evidence, read 2026-09-29 from official Obsidian sources:

- Bases syntax reference — <https://help.obsidian.md/bases/syntax>: global and view filters concatenated with `AND`; a filter object holding one of `and`/`or`/`not` over strings or nested objects; a base with no filters matching every file; formula-to-formula references without cycles and formulas stored as YAML strings with data-determined output types; the `properties` display-name shape; `values` in a custom summary and its difference from the per-view `summaries` map; the default summary-formula table; the `file.file` property, the `file.backlinks` performance note, and the non-refreshing note on `file.backlinks`/`file.properties`; the `this` behaviour in main content, embed, and sidebar; the arithmetic operators and duration units; and the documented statement that a view may store additional keys for its own state, which is the basis for the preserve-unknown-keys rule.
- Bases views documentation — <https://help.obsidian.md/bases/views>: the layout table with app versions (table 1.9, cards 1.9, list 1.10, kanban 1.14, map 1.10 requiring the Maps plugin) and that community plugins can add layouts; kanban columns coming from a grouped property, which is why the kanban block here carries a `groupBy`; multiple sorts ordered by priority with per-type ascending/descending meanings; grouping limited to one property; the results count being the number of results in view; and the `![[File.base]]` / `![[File.base#View]]` embed behaviour where the first view is used by default.
- `obsidian.d.ts` from the official `obsidianmd/obsidian-api` repository, since 1.10.0: `BasesConfigFile` and `BasesConfigFileView` confirm the serialized `.base` shape used here — `filters`, `properties`, `formulas`, `summaries`, `views[]`, and per view `type`, `name`, `filters`, `groupBy`, `order`, `summaries`; `BasesEntryGroup` documents that entries without a value for the grouping key are grouped under a null key, which is the basis for the empty-group rule.

Runtime evidence for the worked example:

- The `sort` and `limit` view keys and the expected-row table come from a base rendered in the native app during this release effort, in an isolated, disposable profile with the Bases core plugin enabled over a synthetic three-note vault. The app was **Obsidian 1.12.7**, and the official CLI in that same profile answered `obsidian version` with `1.12.7 (installer 1.12.7)`. The run is recorded in `tests/evidence/native-app.json` (`environment.app`: `Obsidian 1.12.7`, `environment.cli`: `official obsidian 1.12.7`) as check `F02-filter-group-sort-limit`, observed as "2 results, active group, Study-B before Study-A; archived Study-C absent; source notes unchanged". The fixture in `SKILL.md` reproduces that base and those notes, and its expected-row table matches that observation: two rows under a single `status active` group, `Study-B` (priority 1) above `Study-A` (priority 2), with the `file.name` column left of `priority`.
- This entry's author did not run the app. The observation above was produced by the lane that recorded `tests/evidence/native-app.json`, and it is cited here as the source of the example's expected result, not as a verification performed in this lane. Every behavioural claim in this package is scoped to Obsidian 1.12.7; another build is a different observation. `sort` is not named in the published syntax reference or in `BasesConfigFileView`; it is documented here as a view key on the strength of that observed render plus the documented statement that views carry their own state keys.
- Correction: an earlier draft of this entry stated Obsidian 1.13.7. That number was read off the `obsidian-1.13.7.asar` filename sitting in the isolated profile directory -- a downloaded application archive, not a running-app or CLI version report -- and no run at that version exists. The only version actually observed for this package's evidence is 1.12.7, from the CLI `version` output and `tests/evidence/native-app.json`.

### Privacy and scope

- Only public, neutral, synthetic examples are used. No credentials, account identifiers, workstation paths, personal notes, internal plans, or raw private logs are present, and the fixture vault content is invented for this package.
- Sources were read from local pinned checkouts and official public documentation. Nothing outside this package was created or modified.
- No gates, linters, or formatters were run in this lane, and no installation or release was performed. The runtime evidence cited above was produced by the lane that recorded `tests/evidence/native-app.json` and is attributed to it; this entry claims no destination-vault verification of its own.
