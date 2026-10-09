# Three-column comparison

Upstream: 구요한 `/audit`, commit `863ca43`. The row labels identify every upstream section and Phase; this is the decision record, not a second runtime procedure. The procedure is written in this package's own words; no upstream file is copied.

| 구요한 (863ca43) | secondbrain audit before this revision | Decision + reason |
| --- | --- | --- |
| Prerequisite: read Core Context for the 7 reuse axes | live policy only | Reject the Core Context read as a prerequisite; scope and live policy suffice, and purpose alignment is judged per page from `purpose`. |
| Relation to /verify: planner vs worker | planner vs worker | Adopt verbatim framing. |
| Input: `--full`, `--moc`, `--recent`, `--confidence high`, `--no-save`, `--compare` | Step 0 scope in prose | Adopt the same scopes and compare; `--recent` reads `git log --since` instead of `date modified`; `--no-save` becomes the default, since saving needs approval. Owner rule: never widen scope unasked. |
| Conceptual Framework: 지식요건해당성 / 정합성 / 확증가능성, Claim Type taxonomy, Evidence Scope levels | criteria paraphrased as eligibility gaps, disagreement, confidence | Adopt his three names, Korean included; the taxonomy and levels stay owned by `verify`, named not restated. |
| Scaling Strategy table | absent | Adopt; the Confirmability row adds disputed pages, matching his Phase C. |
| Phase 0 — Inventory: find Wiki/MOC, cluster map, audit-orphan pages | Step 1 Inventory | Adopt; MOC becomes Map, folders from live policy; invoke principle-hierarchical-management. |
| Phase A.1 — Frontmatter coverage: claimType, evidenceScope, confidence, explored, mainVaultRelated, verificationStatus | Step 2 sweep | Adapt to our names: mainVaultRelated → `mothership` (its resolution is `lint`), verification fields only when the vault uses them; add Raw `purpose`/`purpose_origin`/`source_locator` (collectionPurpose → `purpose`) with inferred/unknown counted apart. |
| Phase A.2 — SPO structure: H1, Sources, Related | Step 2 | Adopt; Bias Check on high-confidence pages added here. |
| Phase A.3 — Source citation density, synthesis-only must declare `evidenceScope` | synthesis pages noted | Adapt: synthesis-only reported, not a failure; declaration wording left to `verify`. |
| Phase A.4 — Policy violations from CLAUDE.md (YAML/body indent, quoted wikilinks, Mermaid labels, layer mismatch) | absent | Adapt: count whatever the live policy defines; repair routed to `lint`; no copied rule list. |
| Phase A output: Eligibility score | n/total plus 20 paths | Reject the score (owner rule: counts are observations); keep coverage table and 20-path cap. |
| Phase B — Consistency Clusters steps 1–4 and the four drift kinds | Step 3 | Adopt his four steps and kinds; hallucination suspects joined to the list. Invoke principle-respect-des-fonds for creator-based disagreement. |
| Phase B conflict default: `disputed: true` + `> [!warning] Disputed Claim` via `/verify --resolve` | Contradiction callout via verify | Adapt: the ingest Contradiction callout is the vault's marker; no `disputed` property. Audit queues, never writes. |
| Phase B concurrency: one sub-task per MOC | parallel subagents | Adopt, with ingest's delegation rule: paths in, one line per finding out, lighter model. |
| Phase B audit-orphan handling: per-tag pseudo-cluster or uncluster-able | same | Adopt; invoke principle-collective-description. |
| Phase B output incl. Consistency score formula | per-cluster findings | Adopt the lists; reject the `100 − 5×…` score. |
| Phase C — Confirmability Sampling: all high, stale explored:false (>30d by date modified), disputed, random 10% stratified | Step 4 same four groups | Adopt in his order; age from git log; disputed = Contradiction callout or prior unresolved flag. |
| Phase C abbreviated /verify Phase 3: source counts, counter-evidence (Grep + qmd), recommended confidence, over/underclaim, Bias Check | Step 4 | Adopt; add external criticism (primary/secondary/owner-original per `ingest`) and partial-fidelity Raw. Audit proposes confidence, never writes. |
| Phase C concurrency: batches of ~20 in parallel | absent | Adopt. |
| Phase C output: calibration table, over/underclaim, Bias Check %, Confirmability score | report table | Adopt the tables and n/total; reject the score. |
| Phase D — Synthesis: three 0–100 scores + composite Vault Health | Step 5 ranking, no score | Reject all scores and the composite (owner rule); keep per-criterion counts. |
| Phase D Top 10 actions and priority signals | Step 5 | Adopt his four signals plus hallucination suspects and STALE FLAG first; each `verify [[Page]] — reason`. |
| Phase E — Save report to `30. Queries/…-Q-vault-audit.md` with query-result frontmatter (`reusableFor`, author Claude) unless `--no-save` | save on approval | Adapt: save only on approval at the live policy's query location with the vault's own template; no fixed frontmatter block. |
| Phase E body sections incl. `## Vault Health` and `## Drift Since Last Audit` | report.md | Adapt: report.md keeps his phase sections and Drift; Vault Health section removed. |
| Phase E append to `log.md` | no log | Reject; git history is the log. |
| Output: terminal summary with Vault Health and three scored criteria | report in conversation | Adapt: same three criteria under his names as counts, Top 10, drift; no emoji block, no scores. |
| Failure Mode 1 — MOC out of sync | same | Adopt; route to `lint` Map sync. |
| Failure Mode 2 — Oversized cluster (50+) | 40+ split | Adopt with ~40 threshold and a ~5 lower bound (owner: merge tiny clusters). |
| Failure Mode 3 — Sample bias | same | Adopt. |
| Failure Mode 4 — Audit storm, `STALE FLAG` | repeat flag | Adopt his name and escalation. |
| Failure Mode 5 — Concurrency safety | writing during audit | Adopt; the only write is the approved report. |
| Failure Mode 6 — Confirmability vs source ground truth | same | Adopt. |
| Failure Mode 7 — Action list explosion | cap at ten | Adopt. |
| (none) | silent coverage loss | Keep owner rule as Failure Mode 8: sample never exhaustive, unread = not examined. |
| Integration: consumes v5 keys; lint vs audit; Top 10 feeds /verify; `--moc` after ingest | Neighbours | Adopt the division and incremental audit; v5 keys only when the vault uses them. |
| Scheduling Suggestion: lint weekly, audit monthly | absent | Reject a fixed cadence; the owner schedules. |
