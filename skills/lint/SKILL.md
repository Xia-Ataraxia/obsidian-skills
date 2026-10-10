---
name: lint
description: Checks an explicitly bounded vault scope for note structure, citations, missing frontmatter properties, broken or orphan links, Map coverage, Persona boundaries, and cross-vault targets. Use for vault lint, note health, link checks, or a Map coverage repair. Not for claim verification, sampled quality audit, template authoring, or unrestricted whole-vault correction; epistemic sampling belongs to `audit`, per-claim checks to `verify`.
license: MIT
metadata:
  version: "0.5.3"
---

# Lint

LLM Wiki lint / health check: orphans, broken links, contradictions, stale pages, Map sync and coverage, frontmatter coverage, context freshness and cross-vault link integrity. Lint reads structure, not meaning — whether a claim is true is `verify`, whether a cluster agrees with itself is `audit`.

Lint is report-first. It never auto-patches: every finding comes back as a report, and the owner picks which fixes to apply. Decisions against the reference workflow are recorded in [comparison](references/comparison.md).

Tools: `obsidian-cli` for unresolved links and backlinks when Obsidian is running, `rg` otherwise; `qmd query` for a renamed target; `git log` for modification age. One-liners are in [checks](references/checks.md).

## Scope and policy

Pin the scope: a folder, a Map cluster, named notes, or the whole vault only when asked. Read the destination's live policy for placement, required properties per role and Persona boundaries; do not carry a copy of it here. Field names follow `ingest`'s frontmatter.

Orphan and Map checks use the whole vault as the link source even when the scope is one folder: a note is not orphaned just because nothing inside the folder links to it. Say which link source was used.

Run every step unless the owner named a subset; a step that could not run is listed as a limit, not dropped.

## Process

### Step 1: Inventory

Count Raw notes, Wiki pages by role (Entity, Concept, Guide, Persona), Maps and Inbox candidates in scope. There is no `index.md` to compare against: the files are the catalog, and the Inbox location is the queue state.

### Step 2: Orphan Check

A Wiki page with no inbound link from any other note. Suggest the Map or related page that should hold it. A Raw note linked only from its own Wiki pages is fine; a Raw no Wiki page cites is reported separately as uncompiled evidence.

### Step 3: Broken Link Check

Wikilinks whose target does not exist. For each, name the likely fix: a renamed target (search for it), a page that should be created, or a link to remove. A link to an Inbox candidate is not broken while the candidate exists; `ingest` keeps its name for the Raw.

### Step 4: Contradiction Check

List every `> [!warning] Contradiction` callout with its page and age. Check whether a newer Raw on the same subject has appeared since; if so, mark it possibly resolved for `verify`. Lint never removes a callout.

### Step 5: Staleness Check

Pages with `confidence: low` or `explored: false` and no commit in 30 days or more (age from `git log`, not `date modified`). Staleness is a prompt to revisit, not an error.

### Step 6: Map Sync

Upstream this step synced `index.md`; this vault has none. The same question is asked of Maps: a page naming a Map in `related` that the Map does not link back, or the reverse; a Map linking a note that no longer exists. Report the gaps; fixing them is an owner-picked fix.

### Step 7: MOC Coverage

Every Wiki page should be reachable from at least one Map. List uncovered pages with the Map they most likely belong to, and Maps whose lists have grown past easy reading.

Invoke `principle-hierarchical-management` to decide which Map a page belongs under or whether a note sits in the wrong role folder: a page is read through its parent Map, Raw evidence and compiled knowledge are different roles, a chapter belongs under its Book Index. Suggest placement from live policy; never move a note as a lint fix.

Invoke `principle-collective-description` when judging a Map or hub: does it say what its collection covers and lacks, and does it link its members rather than repeat them. A bare-list Map, or a Paper hub that does not explain its captures, is a finding.

### Step 8: Frontmatter Coverage

미래의 나에게 보내는 편지 — the fields that tell a later reader why a note exists — plus the Exploration Gate, Bias Check and Persona health. Report each as n/total with failing paths:

- **Raw:** `purpose` (upstream `collectionPurpose`), `purpose_origin` with `inferred` and `unknown` counted separately as unconfirmed purposes, `source_locator` where the material has a location, `## Original Content` present and non-empty, and a limitation in `## Ingest Notes` when fidelity is partial. A secondary Raw carries `referenced` when its body reports another creator's work (invoke `principle-respect-des-fonds`).
- **Attachment location:** embeds pointing outside the vault's attachments location.
- **Exploration Gate:** `explored` on every Entity, Concept and Guide — missing is a gap, `false` is backlog, not an error.
- **Wiki:** `confidence` on every Concept, `high`, `medium` or `low` only; `source` and `related` present; H1, `## Sources` and `## Related` sections.
- **Bias Check:** every `confidence: high` or synthesis-heavy page carries one naming both a counter-argument and a data gap.
- **`verify` fields:** counted only when the vault uses them; a gap routes to `verify`.
- **Persona health:** `personaOf` resolves to an existing Entity; the body keeps its simulation-boundary callout; Persona content does not leak into shared Entity or Concept pages; the Entity's `source` holds no Raw the Persona has not absorbed (accumulation backlog). Spot-check one Quote Bank quote per Persona against the cited Raw's `## Original Content`; a mismatch is a fabrication-level finding.

### Step 9: Core Context Freshness

When `refresh-context` keeps a context snapshot, compare its date with the latest change to the mothership notes it draws on. If they moved after the snapshot, or the snapshot is over 30 days old, recommend `refresh-context`.

### Step 10: Cross-Vault Link Check (mothership only)

Skipped when no mothership is configured. Every `mothership` entry (upstream `mainVaultRelated`) is an `obsidian://open?vault=…&file=…` deeplink built as in `ingest` Step 0-a. Decode the `file` component and stat it under the mothership root, with and without `.md`. Ignore links inside code spans and fenced blocks — those are examples. Report source note → missing target.

For each broken one, `qmd query` the mothership read-only for a renamed equivalent and offer one to three candidates. **Do NOT auto-patch.** Lint never writes into the mothership.

## Output

Report in the conversation using [report](references/report.md):

1. **Stats**
2. **Orphans**
3. **Broken Links**
4. **Contradictions**
5. **Stale Pages**
6. **Map Sync**
7. **MOC Coverage**
8. **Frontmatter Coverage** — purpose, Exploration Gate, Bias Check, `verify` fields, Persona health
9. **Core Context**
10. **Cross-Vault Integrity** (mothership only)
11. **Not checked**
12. **Recommendations** — at most ten, the larger ones routed to `audit`, `verify` or `refresh-context` by name

Counts are observations; do not combine them into a score.

## Fixes, on request only

Apply only the fixes the owner picks — add a page to a Map, add a missing property whose value is known, repair a link to a confirmed renamed target — then read each changed note back. For a batch, show the diff for the first ten before continuing.

Never as a lint fix: delete or rename a note, remove a Contradiction callout, set `explored: true` or change `confidence` (those belong to `verify`), invent a `purpose` or other unknown value, or touch the mothership. Commit the applied fixes per the vault's git practice; no `log.md`.
