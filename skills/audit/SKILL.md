---
name: audit
description: Samples an explicitly bounded knowledge scope for quality risks, states coverage and limits, compares a prior report when supplied, and saves a report only on owner approval. Use for vault health sampling, periodic knowledge review, or verify follow-up prioritization. Not for exhaustive claim verification, bulk Wiki repair, or quality scoring; mechanical link and frontmatter health belongs to `lint`, single-page claim checks to `verify`.
license: MIT
metadata:
  version: "0.5.3"
---

# Audit

Whole-vault knowledge integrity audit. Audit applies the same three criteria as `verify` — 지식요건해당성 (Eligibility), 정합성 (Consistency), 확증가능성 (Confirmability) — but at scale, through Map clusters and prioritized sampling. It does not verify every page; it surfaces drift patterns and ranks the next `verify` calls. Audit is the planner; `verify` is the worker.

Audit is read-only on the vault. The only write is the report, and only after the owner approves it in conversation. Decisions against the reference workflow are recorded in [comparison](references/comparison.md).

Two owner rules hold throughout:

- **A sample is never exhaustive.** Every finding is stated against what was actually read. Unread pages are "not examined", never "clean".
- **Counts are observations, not a score.** Report numbers per criterion; never fold them into a Vault Health percentage, grade or composite. A falling count can mean pages were fixed or pages were not sampled.

Tools: `rg` for the deterministic sweep, `qmd query` for semantic counter-evidence, `obsidian-cli` for backlinks when Obsidian runs, `git log` for modification age and prior reports.

## Input

The owner names the scope: the whole Wiki (`--full`), one Map cluster (`--moc`), pages changed in the last N days (`--recent`, read from `git log --since`), only `confidence: high` pages, or a named set. Never widen a cluster or folder into the whole vault unasked. A prior report supplied for comparison (`--compare`) is read now; its open findings feed Phase D and Failure Mode 4. Read the destination's live placement policy for where Raw, Wiki and Map notes live; do not assume folder names. The criteria, Claim Type Taxonomy and Evidence Scope Levels are owned by `verify`; field names follow `ingest`'s frontmatter.

## Scaling Strategy

| Criterion | At single page (`verify`) | At vault scale (audit) |
| --- | --- | --- |
| **Eligibility** | full per-claim check | deterministic sweep — counts and gaps |
| **Consistency** | full cross-page search | Map-cluster batched — each Map is one semantic cluster |
| **Confirmability** | full calibration | prioritized sampling — every `high`, every stale `explored: false`, every disputed page, a stratified tenth of the rest |

## Process

### Phase 0 — Inventory

List the Wiki pages and Maps in scope, then build cluster membership from Map bodies: each Map's outgoing wikilinks to Wiki pages is one cluster. Invoke `principle-hierarchical-management` — a Map is the parent context of its pages, so a page is understood through the Map that holds it.

Record: pages in scope, Maps, pages in at least one Map, pages in none, the largest and smallest clusters. **Audit-orphan pages** (in zero Maps) are included in Phase A and cannot be cluster-reviewed in Phase B. Print the inventory before Phase A.

### Phase A — Eligibility Sweep (deterministic)

Pure search, no judgment; it should take seconds. Report each check as n/total plus at most twenty failing paths.

- **A.1 Frontmatter coverage.** Wiki: `confidence`, `explored`, `source`, `related`, and the `verify` fields when the vault uses them. Raw: `purpose`, `purpose_origin`, `source_locator`; count `purpose_origin: inferred` and `unknown` separately, since an inferred purpose was never confirmed. `explored: false` is review backlog, not a failure.
- **A.2 SPO structure.** H1, `## Sources`, `## Related` present; every `confidence: high` page carries a Bias Check.
- **A.3 Source citation density.** Pages whose body cites no Raw note are synthesis-only. Not a failure — a synthesis page may draw only on other Wiki pages — but it must say so, and its claims cannot be traced to an original.
- **A.4 Policy violations.** Whatever the live policy states as mechanical rules (YAML form, quoted wikilinks, a page in the wrong role folder). Count them; their repair is `lint`.

Presence is all Phase A checks; whether a value is right is Phase C.

### Phase B — Consistency Clusters

Each Map cluster is reviewed on its own. Clusters are independent, so they go to parallel subagents on a lighter model when you can choose: pass paths, receive one line per finding, never page bodies.

For each cluster:

1. **Load cluster** — read the Map and every page it links.
2. **Extract claims** — from each page its three to five central claims (Subject · Predicate · Object).
3. **Cross-compare** within the cluster:
   - same concept, **different definition** — the commonest drift;
   - **contradicting empirical claims** — different numbers, dates or attributions for the same fact;
   - **contradicting prescriptions** — "always X" on one page, "avoid X" on another;
   - **same Raw Source, divergent interpretations**;
   - **hallucination suspects** — a number, date or quotation the cited Raw does not appear to contain; sampled here, confirmed only by `verify`.
4. **Report conflicts** — every page involved, the quoted claim lines, the kind, and the proposed action: usually `verify` both pages with a `> [!warning] Contradiction` callout on each, never deleting either side. Audit queues the action; it does not write it.

Invoke `principle-respect-des-fonds` when two pages disagree because they rest on different creators: a secondary page restating a primary study is not independent corroboration, and a page attributing a secondary author's interpretation to the original creator is itself a finding.

**Cluster size.** Under about five pages, merge the cluster with its nearest neighbour by shared tags or links. Over about forty, split it by tag intersection or sub-Map, review each part, then compare only central claims across parts; say how each split was made.

**Audit-orphan handling.** Group the Map-less pages into a per-tag pseudo-cluster by their top tags, or list them as unclusterable with a suggested Map. Either way they are a structural finding; invoke `principle-collective-description` — a page no aggregate describes has no context for the next reader.

**Cross-cluster** disagreement is rarer; run one `qmd query` per central claim of the high-confidence pages.

### Phase C — Confirmability Sampling (prioritized)

The target population is the union of four groups, in this priority order:

1. **All `confidence: high` pages** — the strongest claims, read in full, not sampled.
2. **Stale unexplored backlog** — `explored: false` with no commit for 30 days or more.
3. **Disputed pages** — a Contradiction callout, or flagged in the prior report and not since touched.
4. **Random 10% stratified sample of the remainder** — stratified by role (Concept, Entity, Guide, Map); never plain random.

State each group's size and the total sampled against the total in scope.

For each target, an abbreviated `verify` Confirmability read:

- count primary, secondary and owner-original sources (external criticism as in `ingest` Step 1);
- whether a cited Raw notes partial fidelity in `## Ingest Notes` while the page treats it as complete;
- a `qmd query` and `rg` search for counter-evidence elsewhere in the vault;
- **overclaim** — `high` on one source or on secondary sources only; **underclaim** — `low` despite several independent primary sources;
- on high-confidence pages, a Bias Check naming both a counter-argument and a data gap.

Audit proposes a `confidence` with its reason; it never writes one. Batches of about twenty pages may run in parallel subagents.

### Phase D — Synthesis

No scores. Report the per-criterion counts from Phases A–C, then the **Top 10 actions**, each one line `verify [[Page]] — reason`, ranked by:

- pages in more than one conflict (Phase B);
- overclaimed `confidence: high` pages (Phase C);
- hallucination suspects;
- pages with a `source` wikilink that does not resolve (Phase A);
- high-traffic pages (many inbound `related`) with weak confirmability;
- `STALE FLAG` repeats from the prior report (Failure Mode 4), placed first.

When a prior report was supplied, compare per criterion: which counts grew, which shrank, which pages were flagged both times. Do not translate the comparison into "better" or "worse".

### Phase E — Save report (on approval)

Report in the conversation first, using [report](references/report.md). Saving is a separate decision: ask, and save one report note only when the owner says yes, at the location live policy gives for query results. Commit it per the vault's git practice. No `log.md` entry; git history is the log.

## Output

The conversation summary follows [report](references/report.md): scope and coverage, then 1. Eligibility (지식요건해당성), 2. Consistency (정합성), 3. Confirmability (확증가능성) as counts, then the Top 10 actions, then the comparison and limits.

## Failure Modes

1. **MOC out of sync** — a page names a Map in `related` but the Map does not link it, or the reverse. Leave it out of the cluster; report it as a Map sync gap for `lint`.
2. **Oversized cluster** — a forty-plus cluster reviewed whole gets skimmed. Split it as in Phase B.
3. **Sample bias** — an unstratified draw lands mostly on Entities. Stratify by role every time.
4. **Audit storm** — the same pages flagged every time. A page flagged in two consecutive audits with no `verify` since becomes a `STALE FLAG` at the top of the action list.
5. **Concurrency safety** — any page edit mid-audit makes later clusters read a moving vault. Audit is read-only on pages; the report is the only write, in Phase E; page changes wait for the `verify` the owner starts.
6. **Confirmability vs source ground truth** — Phase C reads cited Raw only partly. A flagged page is a candidate; the definitive source check is `verify` on that page.
7. **Action list explosion** — cap the list at ten and say how many more are in the report.
8. **Silent coverage loss** — a cluster or group skipped for time is reported as not examined, with the reason.

## Integration

`lint` owns mechanical health: broken links, orphans, frontmatter presence, mothership link resolution. `verify` owns the per-claim taxonomy and any change to `confidence` or `explored`. Run `lint` before an audit so mechanical noise does not crowd the epistemic findings; after a large `ingest`, audit only the touched Map clusters.
