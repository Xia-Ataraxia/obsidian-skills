# Three-column comparison

Upstream: 구요한 `/lint`, commit `863ca43`. The row labels identify every upstream Step and section; this is the decision record, not a second runtime procedure. The procedure is written in this package's own words; no upstream file is copied.

| 구요한 (863ca43) | secondbrain lint before this revision | Decision + reason |
| --- | --- | --- |
| Prerequisite: read Core Context once per session | live policy read | Adapt: read live policy and, for Step 9 only, the context snapshot `refresh-context` keeps. |
| Step 1: Inventory — read index.md, glob Wiki and Raw, compare | Inventory | Adopt the counts; reject index.md — files are the catalog, the Inbox location is the queue state. |
| Step 2: Orphan Check | Orphans | Adopt; owner additions: whole vault as link source, uncompiled Raw reported apart. |
| Step 3: Broken Link Check — create or remove | Broken links | Adopt; add the rename option and the Inbox-candidate exception from `ingest`. |
| Step 4: Contradiction Check | Contradictions | Adopt; never remove a callout, possible resolution routed to `verify`. |
| Step 5: Staleness Check — 30+ days, confidence low, by date modified | Staleness | Adapt: age from git log; `explored: false` also counts. |
| Step 6: Index Sync — add/remove index entries, update stats | Map coverage sync gaps | Adapt to Map Sync: no index.md (git history); the same sync question asked of Maps, reported not auto-fixed. |
| Step 7: MOC Coverage | Map coverage | Adopt his name; invoke principle-hierarchical-management and principle-collective-description. |
| Step 8: v2/v4/v5 Frontmatter Coverage — 미래의 나에게 보내는 편지 | Frontmatter and section coverage | Adopt the heading and his terms; map collectionPurpose → `purpose`, mainVaultRelated → `mothership`; reject mainVaultCmds (no mothership category links). Add `purpose_origin` inferred/unknown, `source_locator`, `## Original Content`, partial-fidelity note, `referenced` (principle-respect-des-fonds). |
| Step 8 Attachment location | embeds outside attachments | Adopt. |
| Step 8 Exploration Gate (v4): explored; exploredBy/exploredDate completeness | explored coverage | Adopt explored presence and backlog; reject exploredBy/exploredDate — git history records who and when. |
| Step 8 Bias check (v4): Counter-argument and Data gap | Bias Check | Adopt. |
| Step 8 v5 verification fields: claimType, evidenceScope, verificationStatus, disputed queue | absent | Adapt: counted only when the vault uses them; gaps and disputes route to `verify`. |
| Step 8 Persona health (v6.3): personaOf, personaMaturity, Simulation Boundary, Accumulation Log, stale persona, Quote Bank spot check | Persona health | Adopt personaOf, boundary, accumulation backlog and the Quote Bank spot check; maturity values left to live policy; owner addition: no Persona leak into shared pages. |
| Step 9: Core Context Freshness — snapshot_date vs mothership, 30 days | Context freshness | Adopt; snapshot owned by `refresh-context`. |
| Step 10: Cross-Vault Link Check (mothership only) | Mothership links | Adopt, mothership only. |
| Step 10.1: Broken mainVaultRelated URLs — inline python, decode, stat with/without .md, strip code | deeplink stat | Adopt the method on the `mothership` field; reject the inline script — `rg` plus decode, named in checks. |
| Step 10.2: Broken mainVaultCmds categories, pipe-alias strip | absent | Reject: this vault records no mothership category links. |
| Step 10.3: Auto-fix suggestion, READ-ONLY by default, qmd 1–3 candidates, do NOT auto-patch | candidates, no writes | Adopt. |
| Step 10.3 `--fix-crossvault` auto-apply | absent | Reject: lint never writes into the mothership. |
| Output 1–5: Stats, Orphans, Broken Links, Contradictions, Stale Pages | report items | Adopt names and order. |
| Output 6: Index Issues — found and fixed | absent | Adapt to Map Sync, reported not fixed. |
| Output 7–9: v2 / v4 / v5 coverage % | one coverage section | Adapt: one Frontmatter Coverage section as n/total, plus MOC Coverage listed separately. |
| Output 10: Core Context | Context freshness | Adopt. |
| Output 11: Cross-Vault Integrity | Mothership links | Adopt without mainVaultCmds. |
| Output 12: Recommendations (top 10) | at most ten | Adopt; add Not checked before it (owner rule: a skipped step is a limit). |
| (implicit) Index Sync edits pages during lint | report-first, fixes on request | Keep owner rule: never auto-patch; counts not a score; owner-picked fixes with read-back and a ten-diff preview. |
