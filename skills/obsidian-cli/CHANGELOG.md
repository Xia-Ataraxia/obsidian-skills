# Changelog

## 0.2.2 — 2026-10-07

- 2026-10-07 — Collection release `0.2.2`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.
## 0.2.1 — 2026-10-07

- 2026-10-07 — Collection release `0.2.1`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — 2026-09-29

- Imported and modified the full official CLI skill from `kepano/obsidian-skills@3ccff5338ea700537839b21900aa5358a0402c98`, `skills/obsidian-cli/SKILL.md`. Retained its syntax, targeting conventions, command examples, and plugin/theme workflow.
- Added explicit vault authorization, official binary identity, narrow mutations, exact materialized readback, non-target preservation, partial-failure handling, and optional-only policy/format composition.
- Authored the operations reference from behavioral requirements in public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, `skills/obsidian/references/cli.md`. No craft prose was copied; that source has MIT metadata but no full root license notice.
- Checked official Obsidian CLI 1.12.7 in an isolated synthetic vault: create, search, move, readback, unresolved-link audit, and missing-source failure. Replaced the move placeholder with documented `path=`/`to=` arguments. Removed `silent`, absent from that build's `help create`; opening is opt-in with `open`/`newtab`.
- Preserved Copyright (c) 2026 Steph Ango (@kepano) and the complete MIT permission notice in this package's `LICENSE`. New authored material is MIT under the repository license.

These checks do not establish agent-native installation, other CLI versions, remote Sync, or permission to alter a user's vault.

## 0.1.0 — Unreleased native restoration

- Restored independently worded Korean backlinks discovery in the `SKILL.md` description, preserving its existing English scope, binary distinctions, exclusions and body.
- Added supported read-only `vaults verbose` registry discovery and `vault info=path` cross-checking in `references/operations.md`. The task-selected name must map to one registered root; missing, stale or ambiguous registration stops before effects. No default is changed, remembered default probed, raw-state fallback added or write authority inferred.
- Requirement lineage: public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, Korean backlinks discovery and explicit registry-to-target resolution, re-expressed without copied prose or corpus examples. Existing MIT notices remain unchanged; no new source grant is claimed.
- Official source: <https://help.obsidian.md/cli>; precise consulted publisher document: <https://raw.githubusercontent.com/obsidianmd/obsidian-help/master/en/Extending%20Obsidian/Obsidian%20CLI.md>, 32,586 bytes, SHA-256 `884d3f36a30ad2dc08bcdc84c1243e17e255677a2bd4a7a1aa0d8f77939fc012`. Lines 137-148 require explicit vault name/id first; lines 1208-1225 document `vault info=path` and `vaults verbose`.
- Static source comparison and independent documentation retrieval confirmed the recipe and description preservation; existing frontmatter checks passed independently. Bundle metadata `1.12.7` does not establish a live CLI version or help catalog. Current help/version probes timed out; no current registry command, live routing or runtime verification was performed. The earlier `1.12.7` tests above remain historical, not current proof. Version stays `0.1.0`; no new tests or unchanged-suite rerun accompanies these prose records.
