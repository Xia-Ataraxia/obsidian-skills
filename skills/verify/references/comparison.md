# Three-column comparison

Upstream: 구요한 `/verify`, commit `863ca43`. One row per upstream section or step; this is the decision record, not a second runtime procedure.

| 구요한 (863ca43) | secondbrain verify before this revision | Decision + reason |
| --- | --- | --- |
| Description: verify one page against 3 criteria, write `verificationStatus` back, flag conflicts as disputed | one page, three gates, report then approved write-back | Adopt the single-page scope and the three criteria; adapt write-back to an approved `## Verification` entry instead of status keys. |
| allowed-tools incl. `mcp__qmd__query` | tools named in one line | Adapt: name `qmd`, `rg`, `obsidian-cli`, `defuddle`, `yt-dlp`, the aside browser, `git`; no scripts. |
| Prerequisite: read Core Context (7 reuse axes) | absent | Adapt: the owner's stated `purpose` on Raw and mothership links stand in for the 7 axes (see 2.4). |
| Input: page name via Glob, path, `--latest`, `--no-write-back`, `--resolve` | name/path, claims, report only, resolve | Adopt all, plus owner-named claims; `latest` via git or mtime. |
| Conceptual Framework — 3 Quality Gates: 지식요건해당성 / 정합성 / 확증가능성 | gates renamed in plain English questions | Adopt his Korean and English names verbatim; the earlier paraphrase hid the source. |
| Gate 1 SPO: Subject · Predicates · Objects · Source · Evidence Scope · Claim Type | subject/structure/frontmatter/claims | Adopt the SPO vocabulary; Source may be Raw or the owner's mothership notes (`mainVaultRelated` → mothership links). |
| Gate 2 four frames: vs source, vs other Wiki, vs CLAUDE.md, vs Core Context | source, original, other pages, vault rules | Adopt the four frames; add "the original behind it" via `referenced` (owner, principle-respect-des-fonds); Core Context → purpose alignment. |
| "Conflicts are flagged `disputed`, not deleted"; deletion last resort | shown not deleted | Adopt; the mark is the `> [!warning] Contradiction` callout shared with `ingest`, not a `disputed` key. |
| Gate 3: independent confidence, overclaim/underclaim, Bias Check; output steers /query | same, with evidence reach | Adopt verbatim incl. "how strongly /query may speak". |
| Claim Type Taxonomy (6) + `mixed` | renamed kinds (Definition, Measurement, Event, Model, Advice, Reading) | Adopt his six names (`definition`, `empirical`, `theoretical`, `historical`, `prescriptive`, `interpretive`) and `mixed`; keep the owner's "what settles it" column. |
| Evidence Scope Levels (5) | renamed reach levels incl. "retellings only" | Adopt his five names; adapt by adding `secondary-only` (owner's retellings-only level, needed by the `referenced` rule). |
| Phase 1.1 frontmatter: required 7, layer keys, v5 `claimType`/`evidenceScope` | ingest frontmatter fields | Adapt to `ingest`'s names (`source`, `related`, `explored`, `confidence`, `referenced`); reject writing `claimType`/`evidenceScope`/`layer`/`mainVaultCmds` — they are report labels, recorded in the `## Verification` entry. |
| Phase 1.2 SPO structure: H1, ≥2 H2, Sources, Related | structure per ingest template | Adopt, against `ingest`'s Concept/Entity/Guide templates; two-subject drift is a split recommendation. |
| Phase 1.3 per-claim metadata, up to 10 claims | at most ten, priority order | Adopt; keep owner's selection priority and left-out reporting. |
| Phase 1 verdict eligible / partial / ineligible | pass / partial / fail | Adopt his labels; ineligible pages still continue (owner). |
| Phase 2.1 source fidelity, top 5, HALLUCINATION SUSPECTED, actions a/b/c | unsupported at source | Adopt his label and actions; search the Raw's `## Original Content`. |
| (none) | secondary claims checked against `referenced` original | Owner addition (2.1b): primary/secondary via `referenced`; candidate-only original = unconfirmed; none = provenance unknown. |
| Phase 2.2 cross-page: related, qmd, Grep; four conflict shapes; Disputed Claim callout + `disputed: true` on both | same search and shapes; Contradiction callout | Adopt search order and four shapes; adapt callout name to `Contradiction`; reject `disputed` key; counterpart callout needs approval. |
| Phase 2.3 policy consistency (CLAUDE.md rules list) | report deviations, lint fixes | Adapt to the destination's live policy; fixing stays with `lint`. |
| Phase 2.4 Core Context alignment, soft flag "orphaned from user purpose" | absent | Adapt: check against `purpose` / mothership links; keep his soft-flag label. |
| Phase 3.1 source count and type (primary/secondary/user-original) | lines of evidence | Adopt, plus owner's collapse of same-creator and retelling sources. |
| Phase 3.2 counter-evidence search | same | Adopt. |
| Phase 3.3 calibration table high/medium/low/disputed; OVERCLAIM/UNDERCLAIM | table without `disputed` value | Adopt table and labels; adapt `disputed` to "low + reported disputed" since `confidence` stays high/medium/low per `ingest`. |
| Phase 3.4 Bias Check generation | same | Adopt; no generic stubs. |
| Phase 3.5 `explored` gate, `exploredBy`, `exploredDate` | ask owner | Adopt the never-auto-flip rule; reject `exploredBy`/`exploredDate` — the `## Verification` entry and git record who and when. |
| Phase 4 write-back of v5 keys (`verificationStatus`, `verifiedAt`, `verifiedBy`, `disputed`) | `## Verification` entry on approval | Reject status keys and schema envelope; adapt to a dated `## Verification` entry, owner approval first, unverified default for unchecked claims. |
| Phase 4 append `log.md` | git history | Reject; history is git. |
| Output: Verification Report block | report sections | Adopt his report shape and labels, adding originals, left-out claims and proposed write-back. |
| Failure Modes 1–6 | same six in prose plus two | Adopt all six under his names; add Secondary as primary and Note text as instruction (owner). |
| Resolution mode: new evidence; keep both / remove one / downgrade | same, with what counts as new evidence | Adopt; owner rule defines new evidence and excludes preference or prior summaries. |
| Integration: v5 keys in CLAUDE.md; /audit, /query, /lint consume keys | absent | Adapt: `query` reads the `## Verification` entry and `confidence`; `audit` reuses the gates; `lint` coverage of v5 keys rejected with the keys. |
