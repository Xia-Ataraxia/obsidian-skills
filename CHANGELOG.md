# Changelog

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
