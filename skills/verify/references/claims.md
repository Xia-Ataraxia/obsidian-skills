# Claims — Claim Type Taxonomy, Evidence Scope Levels, primary or secondary

Read this during Phase 1 and Phase 3. It is the vocabulary the Verification Report uses. `claimType` and `evidenceScope` are report labels; they are not written to frontmatter (see [comparison](comparison.md)).

## What counts as a claim

A claim is a sentence a reader could be wrong to rely on: it asserts what something is, what happened, what was measured, what works, or what it means. Headings, questions, link lists and plans are not claims. When a paragraph strings several assertions together, split it; one verdict per assertion.

Extract up to **10 major claims** per page. When the page holds more, prefer, in order: claims the owner named; claims the page's description or Overview depends on; concrete claims (numbers, dates, names, quotations, attributions); claims other pages link to for support; the rest. Say in the report how many claims the page holds and which ones were left out.

## Claim Type Taxonomy (6 types)

Name one type per claim. The type decides what evidence would settle it.

| Type | Definition | What settles it |
| --- | --- | --- |
| `definition` | What X *is* | The source that coined or standardised the term, and agreement with how other pages use the same word. |
| `empirical` | Measurable fact | Only the figure, with its unit and conditions, found in the cited source. A rounded or re-derived figure is a finding, not a pass. |
| `theoretical` | Framework, pattern, hypothesis | Locating who proposed it, and checking the page states it as theirs, not as established fact. |
| `historical` | Event, timeline, attribution | A dated, attributable source; a later retelling is weaker than a contemporaneous record. |
| `prescriptive` | How-to, recommendation, norm | Whose advice it is and under what conditions it was given; advice stripped of its conditions is a finding. |
| `interpretive` | Synthesis, opinion, judgment | No source can confirm it; it can only be fairly attributed and bounded. Ask whether it is labelled as interpretation and whether a Bias Check names its strongest counter. |

Use `mixed` when ≥3 types are present; that is a description, not a defect.

## Primary or secondary (external criticism)

Invoke `principle-respect-des-fonds` for each claim before judging its strength.

- **Primary**: the creator of the cited Raw produced the claim — their own measurement, argument or account.
- **Secondary**: the cited Raw reports another creator's work — a newsletter citing a study, a talk quoting a paper, a post summarising a benchmark.
- **User-original**: the claim rests on the owner's own mothership notes; it is confirmable only as "the owner holds this".

For a secondary claim, follow the Raw's `referenced` list to the original:

- original already in Raw → check the claim against the original, not the retelling, and note where the retelling drifted;
- original linked only as an Inbox candidate, or as a Book Index whose chapter is still unread (no chapter text in Raw) → the claim is unconfirmed at the original; report the candidate and recommend ingesting it; the citing Raw is not proof;
- no `referenced` entry and no locatable original → provenance unknown; the claim can at most be attributed to the secondary author, never confirmed as the original creator's finding.

A quotation inside a secondary source is not the original. Attribution that silently moves a secondary author's interpretation onto the original creator is a 정합성 (Consistency) failure, even when both texts exist.

## Evidence Scope Levels (5, plus one)

Describe how far the page's support reaches, once for the page and per claim where it differs.

| Scope | Meaning |
| --- | --- |
| `single-source` | One Raw backs the page. |
| `multi-source-primary` | 2+ Raw, all primary, from different creators. |
| `multi-source-mixed` | Primary + secondary (commentary, interpretation). |
| `synthesis-only` | Derived from other Wiki pages, no direct Raw. |
| `user-original` | Sourced from the owner's mothership notes. |
| `secondary-only` | Owner addition: only secondary Raw, with originals unacquired (Inbox candidate, unread Book Index) or unknown. |

Count lines of evidence, not links: two Raw from the same creator, or a secondary that only repeats one primary, are one line.

## Confidence calibration

Compute the recommendation **independently** — without looking at the declared `confidence` — then compare.

| Conditions | Recommended `confidence` |
| --- | --- |
| 3+ independent primary sources that check out, no counter-evidence, no unresolved Phase 2 conflict, older than 30 days or survived an earlier review | `high` |
| 1–2 primary sources that check out, no counter-evidence | `medium` |
| `single-source`, `secondary-only`, `synthesis-only`, or written within the last 7 days and never reviewed | `low` |
| Credible counter-evidence present and unresolved | `low`, and the page is reported **disputed** |

Declared > recommended → **OVERCLAIM**: propose lowering it or name the source that would justify it. Declared < recommended → **UNDERCLAIM**: propose raising it. Either way the change is a proposal until the owner approves it.

## Bias Check

When the page is, or would be, `high`, or rests mostly on synthesis, it needs a `> [!note] Bias Check` (ingest's Concept template places it under Details). If it is missing or generic, draft one for this page's central claim: the strongest counter-argument a careful critic would make, and the specific data gap — the missing original, the absent replication, the unexamined counter-case. A placeholder sentence does not count.
