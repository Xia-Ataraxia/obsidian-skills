# Papers

## Identity and artifacts

Resolve DOI or full citekey and bibliography against the actual selected paper.
Surname plus year is a search hint, never identity: different DOI values remain different papers.
Use optional Zotero/Better BibTeX links and original PDF locations only when actually resolved and authorized; neither integration is required.
Retain the original PDF/export or actual conversion attachment, with tools, date and missing page/figure/appendix ranges.

Acquire in order: ar5iv/PMC HTML, then PDF, then Markdown conversion, with OCR last. An HTML fetch alone does not establish full coverage of scanned PMC/BMJ papers. Verify body, figures, tables, references and appendices against the selected original; record missing ranges and conversion quality in `## Ingest Notes`. Retain the PDF in `source_attachment` when obtained.

Prefer resolved Zotero metadata and a registered citekey; otherwise use `citekey: provisional:<candidate>` and report registration as pending, without a second boolean field.

Separate the source Raw from its Paper hub and reusable Concept notes. There is no mandatory 12-stage pipeline, atomic-note quota, RQ gate or p7 verifier.
The hub uses `templates/paper-hub.md`, `type: paper`, `reference/paper`, Properties-required status and a `source` wikilink list covering current full and earlier excerpt captures. Its `## Captures` explains those roles. Better extraction creates a new full Raw with `referenced` pointing to the earlier excerpt, preserving earlier body bytes. Hub placement follows live Role Placement with per-paper analyses, not a new Wiki folder; existing analysis folders remain untouched.
Each atom makes one independently useful contribution with an actual quotation/location; reviewer/analyst supplements are labelled interpretation, not the author's words.
Concept promotion removes paper-specific assumptions only through source-grounded semantic judgment and reuses an existing Concept when it matches.
Do not reduce analysis coordinates to a fixed set of summary files or cap a meaningful catalog.

## Methodology branches

| Type | Read and analyze against obtained evidence |
| --- | --- |
| quantitative | Design, variables/operationalization, sample and selection, identification assumptions, estimates/uncertainty, robustness and threats to inference. Separate association from causal claims |
| qualitative | Research setting, participant selection, researcher position, collection/coding method, theme evidence and negative cases, reflexivity and transferability. Preserve participant quotations and their context |
| theory-concept | Problem, definitions, constructs, assumptions, argument steps, propositions, boundary conditions, competing accounts and implications. Distinguish deduction from empirical support |
| mixed-methods | Rationale and sequence, each component's design/evidence, integration points, joint displays, convergent/divergent findings and limits. Do not call two disconnected methods integrated |
| scale-development | Construct domain, item generation, content validity, sample, factor/measurement model, reliability, validity evidence, invariance and scoring limits. Distinguish exploratory and confirmatory evidence |
| meta-analysis | Protocol/search/eligibility, included studies, coding and effect calculation, model, heterogeneity, moderator/sensitivity analyses, bias and certainty. A reference list is not the included-study dataset |

Use these axes where the selected evidence supports them; absent methods or results are explicit gaps rather than invented boilerplate.
Track obtained/analyzed/unreviewed ranges in the Coverage Map.
For progressive work report the current selected range and unfinished axes; full completion requires actual source-wide review, not a hub/atom count.

## Connections

Link only the owner-designated existing RQ or manuscript, with the supported relationship explained.
Keep personal drafts untouched and do not create a research question from the paper's title.
An existing Wiki Persona can receive an approved dated citation/stance append, preserving contrary stances and cumulative sources.
Do not create a Persona or profile during paper ingest.
