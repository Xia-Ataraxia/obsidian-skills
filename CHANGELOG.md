# Changelog

## Unreleased

- Add four independent archival principle packages: `principle-respect-des-fonds`, `principle-original-order`, `principle-hierarchical-management`, and `principle-collective-description`.
- Register twenty-four owning packages in the inventory, installer, manifests, and documentation; test principle-only installation without sibling directories or shared contract copies.
- These are local candidate changes; historical published pins and runtime evidence are unchanged.

## 0.3.0 — 2026-10-07

- Breaking: the native plugin and marketplace identity is renamed from `obsidian-skills` to `secondbrain-skills` (`PKG_NAME`, every plugin and marketplace manifest, installer commands, asset ledger). Install with `secondbrain-skills@secondbrain-skills`; uninstall the retired `obsidian-skills@obsidian-skills` identity first. Package names and contents are unchanged.
- Bumped the collection release identity to `0.3.0` in every manifest, `install.sh` and each package `metadata.version`. The recommended `PKG_PIN` moves to the release merge in a follow-up pin commit.
- Historical install evidence for 0.1.0 keeps the identity that was actually observed.

## 0.2.2 — 2026-10-07

- `ingest` absorbs the bstack `book` unit into its Book branch: book-note triggers (Yes24/Aladin URL, ISBN or title), acquisition order, per-field provenance labels, work/edition identity, human-reading preservation and highlight-to-chapter mapping. `fetch_yes24.py` and `fetch_aladin_toc.py` are copied byte-identically from bstack; see PROVENANCE.md.
- Bumped the collection release identity to `0.2.2` in every manifest, `install.sh` and each package `metadata.version`. Plugin identity `obsidian-skills@obsidian-skills` is unchanged. The recommended `PKG_PIN` moves to the release merge in a follow-up pin commit.
- No host install or fresh-load of `0.2.2` is claimed here.

## 0.2.1 — 2026-10-07

- Fixed four packages that Hermes Agent v0.21.5 would not install. Installing `0.2.0` with `hermes skills tap add Xia-Ataraxia/secondbrain-skills` and `hermes skills install Xia-Ataraxia/secondbrain-skills/<name> --yes` installed 16 of 20 packages; Hermes `skills_guard` gave `obsidian-markdown`, `obsidian-bases`, `obsidian-clipper` and `reindex` a CAUTION verdict, which blocks a community-source install. Every finding was a false positive on harmless text, but each blocked distribution.
- `obsidian-markdown`, `obsidian-bases`, `obsidian-clipper`: an exclamation mark written as a one-backtick code span matched the guard's HIGH `inline_shell_exec` rule. The three lines now name the mark, show `![[Note Name]]`, or use a padded double-backtick span. Meanings, rendered text and routing descriptions are unchanged.
- `reindex`: copying the process environment to set `PYTHONIOENCODING` for qmd matched the guard's HIGH `python_os_environ` rule. qmd is a Node CLI, so the variable never affected it. The helper now sets no environment, decodes qmd stdout as strict UTF-8 whatever the caller's locale (a non-UTF-8 locale used to crash on non-ASCII member paths), refuses undecodable stdout as `qmd_output_undecodable`, and decodes stderr readbacks with replacement.
- Added a regression test that scans every shipped file under `skills/` with these two guard rules and reports `file:line`, with negative controls.
- Bumped the collection release identity to `0.2.1` in every manifest, `install.sh` and each package `metadata.version`. Plugin identity `obsidian-skills@obsidian-skills` is unchanged. The recommended `PKG_PIN` moves to the release merge commit in a docs-only follow-up.
- No host install or fresh-load of `0.2.1` is claimed here. The four guard verdicts were rerun locally with the Hermes v0.21.5 `scan_skill` against this tree.

## 0.2.0 — 2026-10-07

- Bumped the collection release identity from `0.1.0` to `0.2.0` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `install.sh` and every package `metadata.version` that carries the collection version. Since `0.1.0` the collection gained the eleven knowledge packages, the `reindex` qmd display-parser fix and the repository rename to `secondbrain-skills`, but every manifest still said `0.1.0`, so a host that installed `0.1.0` saw no upgrade. A minor bump makes native plugin upgrades see the change. Plugin identity `obsidian-skills@obsidian-skills` is unchanged.
- Manifest prose now describes what the plugin actually ships: twenty packages, nine native and eleven knowledge. Package lists and counts are unchanged.
- `install.sh` now keeps three revisions apart: `PKG_PIN` (the recommended current source, moved to the release merge commit by a docs-only follow-up because a commit cannot name its own hash), `PKG_HERMES_PIN` (the historical `c22ce26…` revision the operator's Hermes install was observed at) and `PKG_TAG_PIN`/`PKG_TAG_VERSION` (the immutable `v0.1.0` tag). The provenance test previously required the historical Hermes record to equal the moving install pin and failed once the pin advanced; it now binds each record to its own revision.
- Credited the design inspiration for the knowledge operation set: Yohan Koo's [cmds-llm-wiki](https://github.com/johnfkoo951/cmds-llm-wiki). No files or text were copied; see `PROVENANCE.md`.
- No runtime install, fresh-load, tag or marketplace publication is claimed for `0.2.0`. The historical Claude Code and Hermes results stay bound to their original revisions.

## 0.1.0 — Unreleased

- Split reusable Obsidian work into nine independently discoverable packages: Markdown, Bases, Canvas, Mermaid, visualization, official CLI, Web Clipper, plugin/Templater diagnosis, and Headless Sync.
- Modified pinned MIT upstream Markdown/Bases/Canvas/CLI material with preserved package-local notices. Authored the remaining workflows, diagnostic and drawing helpers, and safety boundaries independently from the public source responsibility inventory.
- Added native distribution metadata and an explicit, non-overwriting local installer with dry-run and collision reporting. Native route documentation is distinct from tested installation claims.
- Added equivalent English and Korean onboarding, original SVG brand/demo assets, neutral fixtures, source-unit/provenance audits, and adversarial package/helper/installer tests.
- Exercised selected format and official CLI operations in an isolated synthetic Obsidian 1.12.7 app profile. See the verification matrix for actual checks and unverified environments.

### Knowledge registration correction

- From existing local source revision `25f484a63e7278e1864f08b372eea3d96e809289`, populated the existing `knowledgePackages` arrays in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` with `capture`, `inbox`, `ingest`, `query`, `verify`, `audit`, `lint`, `status`, `reindex`, `refresh-context` and `onboard`.
- Preserved native registration and every other metadata field, including version `0.1.0`. This records existing packages, not new behavior, installation or fresh-load proof. No code or asset import, relicensing or new source grant is involved; existing notices and rights limits remain unchanged.

### Local release candidate documentation

- Documented the twenty-package `secondbrain-skills` collection in both READMEs, the install matrix and the verification matrix: nine native packages and eleven knowledge packages, each with its role.
- `install.sh --help` now names the twenty packages. Option grammar, routes, selection and copy behavior are unchanged.
- Manifest prose no longer says the knowledge packages are listed as each one lands; all eleven are listed. Package lists, counts and version `0.1.0` are unchanged.
- Evidence levels are kept apart: static manifest registration, temporary materialization by the directory copy, local script behavior, and the earlier native records for the nine published packages. No runtime load of a knowledge package, automatic discovery, app execution, Sync, deployment or deeplink opening is claimed.
- The two transferred `ingest` helpers and their tests keep their unresolved origin rights and public-redistribution hold. This candidate is not a rights grant or a publication approval.

This is a local candidate, not a published release. No deployed installation, private consumer change, old-owner retirement, or production recovery has occurred. Those effects require their own authorization and evidence. Unresolved lifecycle policy remains unresolved.
