# Repository contract

This repository owns twenty independent Agent Skills, the `secondbrain-skills` collection: nine native Obsidian skills and eleven knowledge skills.

- Native: Markdown, Bases, Canvas, Mermaid, visualization, official CLI operations, Web Clipper, plugin/Templater diagnosis, and Headless Sync. Each `skills/obsidian-*/SKILL.md` owns exactly its named feature.
- Knowledge: `capture`, `inbox`, `ingest`, `query`, `verify`, `audit`, `lint`, `status`, `reindex`, `refresh-context`, and `onboard`. Each `skills/<name>/SKILL.md` owns exactly its named task and carries no `obsidian-` prefix.

There is no callable root skill, mandatory shared runtime, compatibility alias, or hidden dispatcher. `docs/naming.md` fixes package and file names. `source-inventory.json` maps every capability unit to exactly one owning package, and `scripts/audit_inventory.py` enforces it.

## Authoring

- Keep required references, assets, and scripts inside the owning package. Compose neighboring packages by explicit identity only when the task needs them.
- The shared approval, purpose, source, and fidelity field contract is authored once in `docs/contracts.md`. `scripts/sync_contracts.py <name>...` generates the byte-identical `skills/<name>/references/contract.md`; never edit a copy. Name only the packages you own, and run the all-package form only when no other writer is active.
- Preserve MIT notices for upstream-derived files. Record exact source revision, modifications, and asset rights in `PROVENANCE.md` and the package changelog.
- Use only synthetic public examples. Never include credentials, private account identifiers, workstation paths, personal notes, internal plans, or raw private logs.
- Respect the destination vault's live policy and exact task authorization. A format skill never grants write permission. Optional policy tools are unused unless explicitly selected; their absence is normal.
- Never turn missing app/plugin/network evidence into success. Separate static validation, runtime discovery, materialized readback, and rendered verification.
- Test malformed inputs, non-target preservation, partial failure, and package isolation. Test behavior, not exact instructional wording.

## Effect boundaries

Local candidate tests do not authorize remote publication, deployed installation, consumer changes, or retirement of another source owner. Keep the existing owner intact until an explicitly approved canary and fresh-load verification succeed. Recovery restores exact approved source/configuration versions, never resets, mirrors, deletes, or overwrites user notes or metadata.

Do not modify other worktrees or installed caches. No commit, push, remote creation, host installation, or protected policy change without separate concrete-effect authorization. Unresolved lifecycle decisions remain unresolved.
