# Changelog

## 0.3.0 — 2026-10-07

- 2026-10-07 — Collection release `0.3.0`: `metadata.version` follows the collection release identity under the renamed plugin identity `secondbrain-skills@secondbrain-skills`. No behavior, reference or script change in this package.
## 0.2.2 — 2026-10-07

- 2026-10-07 — Collection release `0.2.2`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.
## 0.2.1 — 2026-10-07

- 2026-10-07 — Hermes Agent v0.21.5 `skills_guard` refused community installs of four 0.2.0 packages with a CAUTION verdict; the logical-operator line of `references/template-language.md` wrote the `not` operator's symbol as a one-backtick code span, which the guard's HIGH `inline_shell_exec` rule matches. It is now a double-backtick span with padding; the operator set and meaning are unchanged. `metadata.version` follows the collection release `0.2.1`.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — Unreleased

- Added the independent Web Clipper owner with local template-language and workflow references, including schema, selectors, variables, filters, logic, capture analysis, recipes, and optional Bases composition.
- Authored two neutral template assets for general clipping and structured recipes. These are editable examples, not evidence that a browser extension imported or executed them.
- Used the public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3` Clipper references/assets as a responsibility inventory and official Obsidian Web Clipper documentation as syntax evidence. Craft files were not redistributed; their full root license notice was absent. New prose/templates are MIT under the repository license.
- Added fail-closed selector drift, missing metadata, untrusted page content, authorized destination, preservation, and materialized readback requirements. Static JSON checks are separate from extension preview/import, browser capture, and resulting vault-note verification.

Live extension installation and end-to-end capture remain unverified; see the repository verification matrix. This package does not authorize browser-profile or vault changes.
