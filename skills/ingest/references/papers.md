# Papers — mandatory twelve-axis pipeline

Every paper runs P-0 to P-7 in order, inside the same single ingest run. The goal: someone who reads only the notes understands the paper better than from one pass over the original, and never has to reopen it to check a claim.

## P-0 — Purpose, scope and research question

One question, asked once: why this paper, and which existing research question or manuscript it serves, if any. Reuse a purpose the owner already gave. Link only an RQ or manuscript the owner designates; never derive one from the title. If the paper is outside the vault's stated domain, say so and stop until the owner confirms.

## P-1 — Type and strategy

Classify the paper as `quantitative`, `qualitative`, `theory-concept`, `mixed-methods`, `scale-development` or `meta-analysis`, and state the choice with its reason. Ask only when two types fit equally.

| Strategy | When | What is written now |
| --- | --- | --- |
| full | default | atoms on all twelve axes |
| progressive | the owner asks for a first pass, or the paper is long (about 15,000 words or more) | atoms on the core axes; every other axis gets a named stub in the hub, listed as unfinished |

Core axes: quantitative S02·S03·S08·S09·S12; qualitative S02·S04·S08·S09·S12; theory-concept S04·S06·S08·S09·S12; mixed-methods S06·S08·S09·S12; scale-development S06·S07·S08·S09·S12; meta-analysis S04·S08·S09·S10·S12. A progressive run is reported as progressive, never as complete.

## P-2 — Raw

Resolve the DOI or full citekey against the actual paper. Surname plus year is a search hint, never identity. Acquire in order: ar5iv or PMC HTML, then PDF, then Markdown conversion, with OCR last. Check body, figures, tables, references and appendices against the original and record missing ranges in `## Ingest Notes`. Retain the PDF as `source_attachment`. Use resolved Zotero metadata and a registered citekey when available; otherwise `citekey: provisional:<candidate>`, reported as pending. Save the Raw as in Step 2.

## P-3 — Hub and atoms

The twelve axes are coordinates, not a file count.

| Axis | Coordinate | What it answers |
| --- | --- | --- |
| S01 | Citation | Full bibliographic record. Held by the hub only; no atom. |
| S02 | Purpose and general rationale | What the work is for and why that matters broadly. |
| S03 | Fit and specific rationale | Where it sits in prior literature and what gap justifies it. |
| S04 | Participants | Who or what was studied. |
| S05 | Context | Where and under what conditions; how far it applies. |
| S06 | Steps in sequence | Procedure, design or argument, in order. |
| S07 | Data | What counted as data and how it was gathered. |
| S08 | Analysis | How the data or material was worked on, and to answer what. |
| S09 | Results | Primary findings or outputs. |
| S10 | Conclusions | How the authors say the results answer S02. |
| S11 | Cautions | Limits the authors state, plus the analyst's reservations. |
| S12 | Discussion and writing value | What the owner can carry into their own work, read against the purpose. |

S04–S09 and S11 bend to the paper type:

| Type | S04 | S05 | S06 | S07 | S08 | S09 | S11 emphasis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| quantitative | sample, selection | setting | procedure | measures, collection | statistical methods | estimates with uncertainty | threats to inference; association vs. cause |
| qualitative | researcher position, then participants | field site | procedure with duration | notes, transcripts, artefacts | coding and interpretation | what was happening there, with participant quotations | trustworthiness |
| theory-concept | core constructs and their definitions | scope conditions | argument in order | sources the argument builds on | conceptual work done: redefine, merge, split, typify, propose | framework, model, typology, propositions | untested or over-broad claims |
| mixed-methods | per-strand samples | setting | design and strand sequence | per-strand data | per-strand analysis and integration points | strand results and joint inference | whether the strands are really integrated |
| scale-development | samples per phase | construct domain | development phases | items and item generation | factor and measurement models | reliability, validity, final scale | exploratory vs. confirmatory evidence; scoring limits |
| meta-analysis | included studies | search and eligibility | review protocol | coded variables and effects | model, heterogeneity, moderators | pooled effects | bias and certainty |

An axis the paper truly does not address is recorded in the hub as an explicit gap. It is never filled with boilerplate.

**P-3a — Blueprint.** Before writing atoms, draft the hub from [paper hub](../templates/paper-hub.md) with:

- Coverage Map: every section of the original mapped to the atoms that will carry it, so nothing is silently dropped;
- Step Map: S01–S12, each with its atoms or its gap;
- Atom Catalog: every planned atom with the single question it answers.

A knowledge atom is one concept, claim, distinction, mechanism or case. Test: does this note answer exactly one question? If a sub-idea needs more than a paragraph, split it. A dense section normally yields several atoms and a full-length paper thirty or more; the count follows the content, not a cap. Do not pre-select only what seems relevant to the purpose: the purpose is a layer on top of full coverage, not a filter.

**P-3b — Compile.** Write each atom from [paper atom](../templates/paper-atom.md). Each atom has exactly one `analysisStep`; an atom spanning two axes is two atoms. The body, in order:

1. Analysis context — paper, purpose, axis, the one question;
2. Plain introduction — for a reader who has never met the idea;
3. Precise explanation — terms unpacked, mechanisms and differences made explicit; rearranging the paper's own sentences is not explanation;
4. Example;
5. Evidence — two to six verbatim quotations with their location in the original. Statistics, definitions and participant words are always quoted, never paraphrased;
6. Relations — sibling atoms and existing Wiki pages.

Analyst additions are labelled as such and never presented as the authors' words. Finish the hub: fill the catalog with links, mark each axis done, stub or gap.

## P-4 — Wiki promotion

Promote reusable knowledge out of the paper into Concept, Entity and Guide pages by the Step 3 rules: update the matching page first, create otherwise. At least 10–15 Wiki pages touched. A promoted Concept drops paper-specific framing and keeps the paper as `source`. Authors and instruments become Entities; a reusable method or scale becomes a Guide.

## P-5 — Research-question sync

For each owner-designated RQ or manuscript, add the hub link and one sentence on what the paper supports or contradicts there. Personal drafts are otherwise untouched.

## P-6 — Maps and commit

Link the hub from the relevant Map; atoms are reached through the hub. Then Step 5.

## P-7 — Verification gate

The run is not complete until every item passes. Fix and recheck on failure.

- every quotation in every atom is found verbatim in the Raw (`grep -F` each one);
- every atom has exactly one `analysisStep` between 2 and 12 and links its hub;
- every axis S02–S12 has at least one atom, a named stub (progressive) or an explicit gap;
- every atom is in the hub's Atom Catalog and every catalog entry exists;
- every Coverage Map section points at an atom or a stated omission;
- every wikilink resolves;
- the promotion floor in P-4 is met, or the shortfall is explained.

Report the type, strategy, atom count per axis, promoted pages and any unfinished axis. Then Step 7.

## Persona

An existing Wiki Persona can receive a dated citation or stance append, with contrary stances preserved. Never create a Persona or profile during paper ingest.
