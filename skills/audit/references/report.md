# Audit report shape

Use these sections in this order. Every count is written as n of total, the denominator being what was examined. No Vault Health score, sub-score or composite.

## Scope and coverage

- Requested scope and how it was resolved (Map, folder, date window, confidence filter).
- Phase 0 inventory: pages in scope, Maps, pages in at least one Map, audit-orphan pages.
- Phase C sample: size of each group, total sampled, total in scope, and the stratification used for the random remainder.
- Not examined: clusters, groups or pages skipped, with the reason.

## 1. Eligibility (지식요건해당성)

A table of field and section presence (confidence, explored, source, related, H1, Sources, Related, Bias Check on high-confidence pages; purpose, purpose_origin with inferred and unknown counted separately, source_locator on Raw). Synthesis-only pages and policy violations as counts. Up to twenty failing paths per row; the rest are counted.

## 2. Consistency (정합성)

Grouped by Map. For each conflict: the pages involved, the quoted claim lines, the kind (different definition, contradicting empirical claims, contradicting prescriptions, divergent interpretations of one Raw, hallucination suspect), and the proposed action. Then cross-cluster conflicts, then audit-orphan pages with a suggested Map, then how oversized clusters were split.

## 3. Confirmability (확증가능성)

A table of page, declared confidence, proposed confidence, reason. Separate overclaim and underclaim lists. Bias Check presence on sampled high-confidence pages as n of total.

## Top 10 actions

At most ten `verify [[Page]] — reason` lines in priority order; `STALE FLAG` repeats first. A count of further candidates if any.

## Drift since last audit

Only when a prior report was supplied: per-criterion count change and pages flagged both times. No overall verdict.

## Limits

What the sample cannot show, Raw notes that were not opened, and any tool that was unavailable.
