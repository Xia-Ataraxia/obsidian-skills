---
name: ingest
description: Turn one selected URL, file, text or Inbox candidate into a preserved Raw source plus 10–15 created or updated Wiki pages, updated Maps and a refreshed index, in a single run. Use for ingest, paper analysis (12-axis), book notes (책 노트, 독서 노트, 목차 넣어줘), chapter promotion and attributed Persona updates. Not automatic collection, personal profiles or undesignated research questions.
metadata:
  version: "0.5.0"
---

# Ingest

One request runs to the end. The owner naming a source and asking for ingest approves every standard effect below for that source: create the Raw, create and update Wiki pages and Maps, move the Inbox original into Raw, compose `capture` for the originals Step 1 traces, commit, and reindex. Do not stop for a plan review or a second approval between steps. Stop only when a preservation check fails, the source cannot be obtained, or a paper falls outside the vault's scope.

The destination's live policy, placement and templates, and [frontmatter](references/frontmatter.md) govern every step. Decisions against the reference workflow are recorded in [comparison](references/comparison.md). Blank or `all` input delegates selection to `inbox`; direct ingest does not require `capture`.

## Delegation

Run Steps 0-a–1 in one subagent and Steps 3–4 in parallel subagents of at most five pages each, Maps last, on a lighter model when you can choose. Pass paths, not content; each returns one line per item, never quoted text or page bodies. The main thread keeps everything else.

## Step 0 — Purpose (mandatory)

Ask one consolidated question before anything else: why was this collected and where will it be used. Save the answer verbatim as `purpose`.

- Skip the question only when the owner already stated the purpose in this task, or the source is a capture candidate that carries one. Record `reused`.
- If the owner says to decide ("알아서", "자동으로"), infer the most likely use from the source and the vault's context, state the inference and its reason, and record it.
- A batch asks once: one purpose for all, or one per source.

Select the per-type reference: [articles](references/articles.md), [videos](references/videos.md), [repositories](references/repositories.md), [mail](references/mail.md), [conversations](references/conversations.md), [papers](references/papers.md) or [books](references/books.md). A paper always uses Paper mode; a multi-chapter book or docs site uses Book mode. Prefer live placement over category inference; do not persist `category`.

## Step 0-a — Mothership connections

When a mothership is configured, search it read-only with the source's key concepts and the purpose. Keep the 2–5 most relevant notes. Verify each target exists before recording `mothership` links, and build `obsidian://open?vault=…&file=…` with `urllib.parse.quote(value, safe='')` for both components. Never invent a target or write into the mothership.

## Step 0.5 — Acquisition and conversion

Obtain the full selected source. Convert binaries with an available document converter and audio with a transcription tool; retain the original in the `_attachments` location, except where the per-type reference says none is kept. A failed conversion halts the run with the missing tool named. Record `source_extraction`, `source_attachment` and conversion limits in `## Ingest Notes`.

## Step 1 — Analyze

Invoke `principle-respect-des-fonds`. Read the whole source and extract:

- 3–8 key concepts worth a Concept page;
- 1–5 entities: people, organizations, products, models, tools;
- 0–3 pieces of practical guidance worth a Guide;
- key claims to track, with counterevidence;
- connections to pages that already exist.

Apply external criticism per key claim. A claim produced by this source's creator is primary. A claim reporting another creator's work is secondary: when the original is located and already in Raw, link it through `referenced`; when it is a book identified by title and author with a catalogue or publisher record, and no Index for it exists, build its Book Index per [books](references/books.md) and link that through `referenced`; when otherwise located but not yet acquired, compose `capture` for a manifest-only Inbox candidate with the inherited `purpose` (`reused`) and the citing passage in its capture notes, and link that candidate through `referenced`; when unlocated, record provenance unknown in `## Ingest Notes` and attribute the claim to this creator, never as primary.

Search existing Raw, Entity, Concept, Guide and Map pages before creating anything. Match by stable identity or canonical locator first, then by meaning: a page about the same idea under another title is the same page.

## Step 2 — Preserve Raw (move, not copy)

Invoke `principle-original-order`. Use [raw](templates/raw.md). Write the original verbatim under `## Original Content` — no summary, no trimming, images and media links included. Each original gets its own Raw. A Raw made from an Inbox candidate keeps the candidate's note name, so wikilinks to the candidate resolve to the Raw without a relink. An existing Raw body is never rewritten; a better extraction becomes a new Raw linking the earlier one.

Check before moving on: `## Original Content` is present, its length matches the obtained source, and embedded media, quotations and code blocks survived.

When the source came from the Inbox, delete the Inbox original once that check passes. This is the second half of the move; leaving it causes a duplicate ingest on the next scan. A URL, an external file or raw text leaves nothing to delete. Never delete before the check passes.

## Step 3 — Compile Wiki pages

Invoke `principle-hierarchical-management`. For each concept, entity and guide from Step 1, update the existing page or create a new one. Use [concept](templates/concept.md), [entity](templates/entity.md) and [guide](templates/guide.md). **Target: 10–15 Wiki pages touched per source.** A thin source may fall short; say so in the report rather than padding with empty pages.

Updating an existing page is the default when one matches:

- add the new information under the relevant section, merging with what is there rather than appending a duplicate block;
- add the Raw to `source` and new cross-references to `related`;
- when the new information contradicts the page, keep both and add a `> [!warning] Contradiction` callout; it needs two located claims that cannot both be true, so a detail of a retelling that the checked material is merely silent about goes to Open Questions or Ingest Notes as unverified, and before asserting that a secondary account conflicts with its original, check the original or its creator's own account;
- preserve human-written passages and unknown frontmatter keys.

New pages: Concepts use Overview/Details/Related/Sources/Open Questions with a `confidence` per [frontmatter](references/frontmatter.md); Entities cover both the secondary author and each original author; Guides hold step-by-step practice. Every new page starts `explored: false`. A `confidence: high` or synthesis-heavy page carries a Bias Check callout with a counter-argument and a data gap.

## Step 3.5 — Persona

When the author or main speaker matches an existing designated Persona, append to it using [persona](templates/persona.md): 1–3 quotations verified against Raw Original Content, a dated position row, and a log line. Keep contradictory positions visible and `personaMaturity` unchanged. Never create a Persona during ingest. GitHub evidence uses raw-at-commit-SHA URLs.

## Step 4 — Connect and update Maps

Invoke `principle-collective-description`. Add wikilinks between all related pages. Create or update the relevant Map/MOC so every page touched in this run is reachable from one. Leave no new orphan.

## Step 5 — Commit

Follow [git provenance](references/git-provenance.md). One ingest is one local commit containing all its Raw, Wiki and Map effects, with trailers naming the source. No `index.md` or `log.md`; history is the log. Publication needs its own request.

## Step 6 — Review

Check every item and fix failures before reporting:

- Raw has verbatim `## Original Content` of the expected length;
- the Inbox original is gone when the source came from the Inbox;
- every new wikilink resolves and no duplicate page was created;
- every secondary claim's original is linked, captured as an Inbox candidate or Book Index, or recorded as provenance unknown;
- every new page has `explored: false`, and high-confidence pages have a Bias Check;
- every mothership link resolves on disk;
- every touched page is linked from a Map.

## Step 7 — Reindex and report

Invoke `reindex` so the new pages are searchable. Report the Raw path, purpose, originals linked, captured or unlocated, pages created, pages updated, Maps touched, the page count against the 10–15 target, coverage gaps and open questions.

## Paper mode

Mandatory for every paper. Follow [papers](references/papers.md): purpose and scope gate, paper type, Raw, a hub plus knowledge atoms across all twelve analysis axes, Wiki promotion of at least 10–15 pages, and the verification gate. Use [paper hub](templates/paper-hub.md) and [paper atom](templates/paper-atom.md). The run is complete only when the gate passes.

## Book mode

Follow [Book B-1–B-5 and Promotion](references/books.md): fetch the table of contents, write the Book Index and chapter stubs, compile a small set of book-level Wiki pages, and promote a chapter when the owner reads it. A book that a source only cites gets the Index alone, per that reference. Never compile unread chapter content.

## Tools

Pages: `defuddle`; transcripts: `defuddle`, `yt-dlp`; pages behind login or JavaScript: the aside browser; search: `qmd`; app operations: `obsidian-cli`.
