# Three-column comparison

Upstream: 구요한 `/ingest`, commit `863ca43`. The row labels identify every Step and mode; this is the decision record, not a second runtime procedure.

| 구요한 (863ca43) | Current secondbrain ingest 0.3.0 | Decision + reason |
| --- | --- | --- |
| Input: arguments by material; blank→inbox | request URL/file/text/candidate | Adapt: skill routes modes; CLI carries source input; blank delegates inbox selection. |
| Category Detection: Inbox→Clipper category→inference→Articles | per-type references | Adapt: live placement first; folder/source_kind replaces category field. |
| Step 0: mandatory single purpose question, once per batch | purpose/purpose_origin, shared batch purpose | Adopt purpose once, reuse stated purpose; reject collectionPurpose/user_intent_interview duplicates. |
| Step 0-a: mothership search/stat/deeplinks; mainVaultRelated/mainVaultCmds | absent | Adapt: read-only verified obsidian://open links in mothership; reject commands and mothership writes. |
| Step 0.5: binary conversion, attachment and five conversion fields | HTML stdlib; converted text loses history | Adopt actual conversion and retained attachment; source_extraction plus narrative Ingest Notes replace redundant conversion fields. |
| Step 1: concepts/entities/guides/claims/connections, read index.md | bounded catalog and selected evidence compilation | Retain analysis without quotas or index.md; invoke principle-respect-des-fonds for primary/secondary distinction. |
| Step 2: MOVE verbatim, preflight, verify before rm | Plan/effect approval/digests; no deletion | Adopt preservation and separately approved Inbox deletion with immediate source/span/postimage checks. Append-only existing captures; better extraction creates new Raw. Multiple originals each get Raw and referenced links; principle-original-order. |
| Step 3: compile 10–15 pages | no quota | Reject quota: source and purpose determine output. |
| Step 3 Concept: Overview/Details/Related/Sources/Open Questions, Contradiction, confidence, Bias Check, explored:false | exact append preserving human sections | Adopt structured Concept updates, reviewed diff before restructuring terminology/human notes. |
| Step 3 Entity: 22. Entities | restricted Entity, no People creation | Adapt to 20. Wiki/02 Entities; secondary and original authors both become Entities; no mothership People. Invoke principle-hierarchical-management. |
| Step 3 Guide: 23. Guides | absent | Adopt 20. Wiki/03 Guides; type guide and non-Raw Properties status. |
| Step 3.5 Persona: existing card quote/Timeline/Log, maturity unchanged, GitHub raw@sha | existing Persona append only | Adopt Entity prerequisite, verify quotes in Original Content, raw-at-SHA, no new Persona or maturity changes. |
| Step 4: wikilinks/MOC updates/no orphans | designated relationships, no bridge notes | Adopt links/no orphans and principle-collective-description; reject automatic standard-mode MOC updates. Book B-4 explicitly links Index to existing Map only. |
| Step 5: full index.md synchronization | absent | Reject; history is one git commit per ingest. |
| Step 6: append log.md | absent | Reject; git history and trailers identify transactions. |
| Step 7: verbatim/cleanup/links/qmd reindex | JSON status/readback; separate reindex | Adopt readback, separate Inbox-delete approval/checks, staged blob comparison and commit; reindex remains separate. |
| Paper Mode P-0–P-7, Zotero Tier-0: 12-stage analysis, RQ gate, hub/atoms/p7_verify | partial-range visibility, hub/citekey | Adapt: full Markdown Raw + Zotero; ar5iv/PMC HTML→PDF→Markdown→OCR last, verified coverage, provisional citekey. Reject mandatory 12 stages, atoms, RQ and p7. Hub placement belongs to live Role Placement, not schema. |
| Book Mode B-1–B-5 and Promotion: TOC, preface Index, chapter stubs, book Wiki, progressive reading | Yes24/Aladin TOC | Adopt progressive procedure: fetch two chapter URLs, verbatim preface/Reading Paths, TOC/Progress, book+author Entities, 1–3 preface anchor Concepts, optional Guide, existing Map link; preserve all five chapter fields on promotion. Only adaptations: Apatheia Books paths, compact frontmatter/status override, git instead of index/log. |
| Guide mode: reusable methodology | no dedicated template | Adopt source-grounded Guide, explored:false and required Properties status, without manufactured methodology. |
