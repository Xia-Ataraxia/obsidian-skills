# Changelog

## 0.2.1 — 2026-10-07

- 2026-10-07 — Hermes Agent v0.21.5 `skills_guard` refused community installs of four 0.2.0 packages with a CAUTION verdict; the first line of `references/EMBEDS.md` showed the embed prefix as a one-backtick code span, which the guard's HIGH `inline_shell_exec` rule matches. It now names the exclamation mark and shows `![[Note Name]]`; the definition is unchanged. This package carries no `metadata.version`.

## 0.1.0 — Unreleased

Not published, not installed anywhere, and not yet exercised against a running Obsidian app. This entry records the imported material and the modifications made to it, nothing more.

### Upstream source and attribution

- Origin: the `skills/obsidian-markdown/` package of `kepano/obsidian-skills`, pinned at commit `3ccff5338ea700537839b21900aa5358a0402c98`.
- Files taken from it: `SKILL.md`, `references/CALLOUTS.md`, `references/EMBEDS.md`, `references/PROPERTIES.md`.
- License: MIT License, Copyright (c) 2026 Steph Ango (@kepano). That copyright notice and the MIT permission notice cover this material and must accompany any copy or substantial portion of it, including this package; the repository-root `LICENSE` carries both.
- Relationship: imported, then modified. This package now owns the Obsidian Flavored Markdown recipe locally; it is not a mirror or a fallback of the upstream package.

Behavioral requirements about target authorization, non-Markdown destination identity, source-context destination readback, and separating rendering from resolution came from an internal requirements source that carries no license notice at its root. Those requirements were re-expressed here in this package's own wording; no text from that source was reused.

### Imported unchanged

- `SKILL.md`: the introduction paragraph, the wikilink-versus-Markdown-link note, and every syntax section with its examples -- internal links and block IDs, embeds, callouts, properties, tags, comments, highlight, math, Mermaid, footnotes, the complete note example, and the five `help.obsidian.md` reference links.
- `references/CALLOUTS.md`: basic callout, foldable callouts, nested callouts, the supported-type table with aliases and colors, and the custom-CSS callout snippet.
- `references/EMBEDS.md`: note embeds, image embeds and sizing, external images, audio embeds, PDF embeds, base embeds, list embeds with block IDs, and the search-result `query` block.
- `references/PROPERTIES.md`: the frontmatter example, the property-type table, the default-property list, and the tag character rules.

### Added to `SKILL.md`

- A `Scope` section that states what this package owns, hands note meaning, filing, template choice, provenance, and house style to the target vault's own written policy, and names `obsidian-canvas`, `obsidian-bases`, and `obsidian-cli` by identity only for artifacts this package does not own.
- A standalone-operation statement: no vault plugin, mutation server, environment variable, or personal configuration is required, and an explicitly selected vault surface composes optionally.
- `Resolve the target before writing`: vault root, vault-relative target note, named effect, and authority, with read-only behavior until all four are known and reuse of authority the task already granted.
- `Authorized change and preservation`: read before writing, change only what was requested, an explicit preservation list, a no-normalization rule, a no-rename-to-fix-a-link rule, and a destructive-effect list needing explicit scope.
- `Link targets that are not Markdown notes`: extension retention for `.canvas`, `.base`, `.png`, and `.pdf` targets, why a bare stem is a different link, and folder-path disambiguation.
- `Destination readback`: text readback, source-context destination resolution through `app.metadataCache.getFirstLinkpathDest(linkpath, sourcePath)` with exact argument shapes, null and wrong-path interpretation, a rule against gating on a note's whole unresolved-link set, an unverified report when the app or index is absent, and a separate render check including the documented shapes-only canvas embed.
- `Anti-patterns` and a `Verification` checklist covering target resolution, preservation, extension retention, link readback, render checking, and destructive scope.
- Extended frontmatter `description` with preservation and readback triggers plus the out-of-scope artifacts; `name` is unchanged.
- Workflow: a target-resolution and read-first step ahead of the upstream steps, and readback folded into the final verification step.
- Reference list: the three package-local reference files added beneath the upstream links.

### Added to the references

- `references/CALLOUTS.md`: structure rules (`[!type]` placement, case-insensitive identifier, fold-marker position, `>` on every line), Markdown content inside callouts, alias-versus-type clarification, an intent-to-type selection table, unrecognized-type behavior, notes on the CSS variable formats, a failure table, and a verification checklist.
- `references/EMBEDS.md`: link-versus-embed guidance, heading and block subpath exactness, a self-embed and cycle warning, pipe semantics for size versus display text, a video-embed section the upstream `SKILL.md` referenced without an upstream section, an `Embed Canvas` section with the documented shapes-only behavior, external media and iframe caveats, path-ambiguity rules, a failure table, and a verification checklist.
- `references/PROPERTIES.md`: frontmatter placement rules, per-type value shape notes, list-form guidance, quoting and readback for links in properties, frontmatter tag rules (no spaces, not digits-only, `/` nesting), a safe-edit procedure that preserves unrelated keys and order, a failure table, and a verification checklist.

### Deliberately absent

- No dispatcher that sends the reader to another package for Obsidian Markdown syntax; this package answers directly.
- No root router, no shared runtime core, no aliases, and no shadow copies of the upstream files.
- No dependency on a personal vault, note, path, account, environment variable, or server; neutral examples only.
- No local `.canvas`, `.base`, or CLI schema; those are reported as gaps when the matching skill is unavailable.

### Native discovery restoration — Unreleased

- Restored independently worded Korean note-cleanup intent in the `SKILL.md` description. Existing English discovery, exclusions and every body byte are unchanged; this is not a scope expansion or version bump.
- Requirement lineage: public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, Korean note-cleanup routing intent, re-expressed without copied source prose or corpus examples. Existing MIT notices remain intact; no new source grant is claimed.
- Direct static comparison confirmed description-only insertion and body preservation; existing frontmatter checks passed independently. Live skill discovery and routing were not exercised. Version remains `0.1.0`; these prose records add no test or runtime claim.
