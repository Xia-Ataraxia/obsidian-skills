# Changelog

## 0.1.0 — 2026-09-29

- Imported and modified the full official CLI skill from `kepano/obsidian-skills@3ccff5338ea700537839b21900aa5358a0402c98`, `skills/obsidian-cli/SKILL.md`. Retained its syntax, targeting conventions, command examples, and plugin/theme workflow.
- Added explicit vault authorization, official binary identity, narrow mutations, exact materialized readback, non-target preservation, partial-failure handling, and optional-only policy/format composition.
- Authored the operations reference from behavioral requirements in public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, `skills/obsidian/references/cli.md`. No craft prose was copied; that source has MIT metadata but no full root license notice.
- Checked official Obsidian CLI 1.12.7 in an isolated synthetic vault: create, search, move, readback, unresolved-link audit, and missing-source failure. Replaced the move placeholder with documented `path=`/`to=` arguments. Removed `silent`, absent from that build's `help create`; opening is opt-in with `open`/`newtab`.
- Preserved Copyright (c) 2026 Steph Ango (@kepano) and the complete MIT permission notice in this package's `LICENSE`. New authored material is MIT under the repository license.

These checks do not establish agent-native installation, other CLI versions, remote Sync, or permission to alter a user's vault.
