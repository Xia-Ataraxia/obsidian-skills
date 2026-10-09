---
name: ingest
description: Preserve selected URL, file, text or Inbox evidence as Raw and compile source-grounded Entity, Concept, Paper, Book, Persona or Guide knowledge. Use for ingest, paper analysis, book notes (책 노트, 독서 노트, 목차 넣어줘), chapter promotion and attributed Persona updates. Not automatic collection, corpus indexing, personal profiles or undesignated research questions.
metadata:
  version: "0.3.0"
---

# Ingest

A lean router for selected evidence, not permission to write. Read the destination's live policy, placement and templates, the [shared contract](references/contract.md), and [frontmatter](references/frontmatter.md). Design decisions against the reference workflow are recorded in [comparison](references/comparison.md); the helper's simplification record is [script inventory](references/script-inventory.md). Resolve exact scope and effects before writing. Blank/all input delegates selection to `inbox`; direct ingest does not require `capture`.

## Step 0 — Purpose and scope

Reuse the owner's purpose; ask one consolidated question only when it is absent. A batch may share one purpose. Unknown purpose allows preservation, not automatic compilation. Select the per-type reference: [articles](references/articles.md), [videos](references/videos.md), [repositories](references/repositories.md), [mail](references/mail.md), [conversations](references/conversations.md), [papers](references/papers.md) or [books](references/books.md). Prefer live placement over category inference; do not persist `category`.

## Step 0-a — Read-only mothership connections

When configured and relevant, search the mothership read-only. Verify each target exists before recording `mothership` links. Build `obsidian://open?vault=…&file=…` with `urllib.parse.quote(value, safe='')` for both components; never invent a target or write a mothership People note. No counterpart vault is required.

## Step 0.5 — Acquisition and conversion

Obtain the selected range, retaining original attachments in the approved `_attachments` location. Use an actually available document converter or audio transcription tool; failure is a gap, not success. Record `source_extraction`, `source_attachment` and narrative conversion/coverage limits in `## Ingest Notes`, even for converted text input. See the per-type reference for acquisition tools.

## Step 1 — Analyze provenance before compiling

Invoke `principle-respect-des-fonds`. Distinguish primary originals from secondary interpretation. Inspect bounded existing Raw, Entity and Concept candidates before creating anything: stable identity, then canonical URL/locator, never title alone. Identify claims, counterevidence, reusable concepts and missing ranges without quotas or reading index.md.

## Step 2 — Preserve Raw in original order

Invoke `principle-original-order`. Use [raw](templates/raw.md). Preserve each original in its own Raw; secondary Raw links all originals through `referenced`. Existing capture bodies are append-only; better extraction creates a new Raw linking the earlier capture, never silently replaces it. Keep exact preflight body spans outside notes, verify unchanged body prefixes and read back newly written capture spans.

Ingest never deletes its input; it records the Raw Original Content extent and selected bytes in its session state. Inbox→Raw becomes a move only through `inbox delete` with a separate exact-path delete approval: immediately before unlinking, it must compare the current Inbox bytes with the approved preimage, the Raw Original Content extent with the selected capture bytes, and the whole Raw with its expected postimage. Pause/drain affected writers or verify their destination switch. Do not substitute whole-file Inbox/Raw hash equality; metadata differs. Do not delete other originals.

## Step 3 — Update before create

Invoke `principle-hierarchical-management`. Both the secondary author and each original author become source-grounded Entities, including people, not mothership People records. Use [entity](templates/entity.md), [concept](templates/concept.md) and [guide](templates/guide.md). Update proven existing pages before creating new ones, with exact reviewed diffs and preservation of unrelated human content: the helper's `update_path` member takes a reviewed postimage outside the vault, whole preimage/postimage digests and offset-located preserved spans. New Entities need a one-line `description` and may list `related` links. New Concept/atom analyses need an explicit one-line evidence-grounded `confidence` and may add a one-line `description` and `related` links; existing Concepts only gain an appended analysis, with frontmatter (including `explored`) unchanged.

Concepts use Overview/Details/Related/Sources/Open Questions, explicit Contradiction callouts, `confidence` and a Bias Check. New Entities, Concepts and Guides start `explored: false`. Restructuring an existing terminology Concept requires the owner's reviewed diff. No fixed page count or fabricated bridge notes.

## Step 3.5 — Persona mode

Only append to an existing designated Persona after resolving its corresponding Entity. Use [persona](templates/persona.md): verify each quotation in Raw Original Content, retain attribution, date and anchor, and append stance/Timeline/Log without replacing earlier contradictions. Keep `personaMaturity` unchanged; never create a Persona as an ingest side effect. GitHub evidence uses raw-at-commit-SHA URLs.

## Step 4 — Connect collectively

Invoke `principle-collective-description`. Check exact wikilink targets and source/related relationships; leave no newly created orphan. Do not automatically update Maps/MOCs in standard mode. Book B-4 alone permits the approved Book Index→existing Map link. No automatic query, report or reindex effects.

## Step 5 — Stage provenance, not index.md

Follow [git provenance](references/git-provenance.md). One ingest transaction is one commit, including all its Raw and Wiki effects. No index.md is created or synchronized.

## Step 6 — Record history, not log.md

No log.md. Commit trailers identify sources and exact owned paths; [re-ingest](references/reingest.md) uses git history as truth, with state outside the vault. Publication needs its own authorization.

## Step 7 — Review and read back

Verify actual writes, preserved originals, source anchors, incomplete coverage, links, non-target bytes and partial failures. Finish the approved Inbox move only after Step 2's immediate checks, compare staged blobs to intended postimages, then commit and publish through the approved git procedure. Reindex remains separately requested. Report exact Raw paths, source identity, purpose, obtained ranges, limitations, reused/updated knowledge and evidence level. Exit 0 alone is not proof.

## Paper mode

Use [papers](references/papers.md) and [paper hub](templates/paper-hub.md): ar5iv/PMC HTML → PDF → Markdown → OCR last, with actual full-text coverage checks. Prefer Zotero metadata; unregistered keys use `provisional:`. Hub placement follows live Role Placement, not the schema. No mandatory 12-stage pipeline, atomic-note quota, RQ creation or p7 verifier.

## Book mode

Follow [Book B-1–B-5 and Promotion](references/books.md), preserving the upstream progressive-read procedure with only Apatheia paths, compact schema/status override and git history replacing index/log. A chapter scaffold requires the obtained `book_title`; `reading_paths` (verbatim) and per-chapter `toc_description`/`locator` are supplied only as obtained evidence, never invented. Promotion is one guarded transaction over the chapter and its Index: acquired text from outside the vault replaces the exact placeholder, navigation resolves, and the read chapter's checkbox is ticked. Partial coverage becomes `reading`, full becomes `completed`; `reading`→`completed` is unsupported. Web books keep B-1 URL acquisition; a commercial book first needs lawful text and an approved file/page locator adaptation. Do not compile unread chapter content.

## Local helper

Read [interface](references/interface.md) and [batch mappings](references/batches.md) before invoking `python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --state "$SESSION"` (acquire and preflight; `SESSION` outside the vault), then `python3 scripts/ingest.py --vault "$VAULT" --apply-state "$SESSION"` only for the reviewed, approved effects. Helpers preserve bytes; agents perform semantic synthesis. For converted text, the retained attachment is the real original passed as `attachment_source` with its digest. Every coverage level can carry `notes`. The helper resolves every wikilink it records — new Raw `author`/`referenced`, new Entity and Concept/atom `related`, and update postimage `author`/`referenced`/`source`/`related` — to exactly one existing or same-session path and refuses otherwise; it proves existence, not relevance, so review each link before approval. A refusal is a reportable defect, not something to route around. Compose `obsidian-cli` explicitly for approved app operations. Python 3.8+ standard library is sufficient for the core helper; optional per-type acquisition dependencies and unavailable runtime checks stay explicit.
