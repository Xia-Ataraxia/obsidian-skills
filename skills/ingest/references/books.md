# Books

Resolve the actual bibliography and TOC source, then separate the book index from selected chapter evidence and analysis.
Record read/obtained/compiled states independently.
The CLI records no compiled field: chapter `status` reflects only acquisition coverage, and a selected analysis does not establish complete chapter compilation.
Unread or unobtained chapters remain not-obtained/not-compiled and get no fabricated Raw body. Book stubs explicitly label their non-empty placeholder as not obtained.

## Book Ingest Mode — B-1–B-5 and Promotion

Adopted from 구요한 `/ingest` at `863ca43`: preserve the progressive procedure below. Only adaptations are Apatheia paths, the compact frontmatter/status override and git history replacing index/log.

### B-1 — Fetch TOC and URL pattern

Detect a multi-page book/docs site with at least five chapters. Fetch the complete TOC and preface. Preserve every chapter title, Part and one-line description in the original language. Test the URL pattern by directly fetching two chapter URLs before naming/scaffolding. If either fails, stop for another source rather than invent URLs.

This URL acquisition remains the contract for web books. A commercial or offline book has no chapter URLs to test: scaffolding it needs lawfully obtained text and an explicitly approved file/page locator adaptation recorded per chapter. Until both exist, its chapters stay unlocated and unpromotable; nothing here substitutes a guessed URL or page.

### Book cited by a source

A located book that a source merely cites gets one Book Index and nothing else until it is read. Build it from the bibliography and TOC as actually obtained (see Bibliographic acquisition), every field labelled by origin, the inherited `purpose` recorded `reused`, and the citing Raw named in its Ingest Notes. Link it from the citing Raw through `referenced`. Create no chapter stubs: the Index lists the TOC as plain lines, not links to stubs that do not exist. A commercial or offline book takes the same path. When the owner starts reading, create the chapter stubs, then Promotion works as written. Reading state lives in `status` and the Index, never in the folder a note sits in; nothing is moved when a book is read.

### B-2 — Create Book Index (one Raw)

Use `templates/book-index.md` under `10. Raw Sources/03 Books`, named `YYYY-MM-DD-{authorSlug}-{bookSlug}-book-index.md`. The Index `# ` heading is the exact obtained one-line title, never derived from the path. The preface is preserved verbatim in Original Content. TOC has every chapter as `- [ ] [[stub]] — {obtained title}`, followed by ` — {toc_description}` only when the TOC source supplied that one-liner, grouped under `### {Part}` headings when parts are given (unparted chapters may only precede the first Part). Reading Paths holds the source's reading paths verbatim; an absent value and an explicit `null` (reported unavailable) each render a distinct `Not recorded:` line, never inferred paths. Progress Tracking is `| Ch | Title | Status | Read on |` with one `| N | [[stub]] | stub | — |` row per chapter. Ingest Notes record how many chapter locators and TOC descriptions were supplied and the Reading Paths state; these counts state what was obtained, not that it was checked. The Index has no chapterNumber and no status.

### B-3 — Create N chapter stubs

Use `templates/book-chapter.md` in the same Books location, named `YYYY-MM-DD-{authorSlug}-{bookSlug}-ch{NN}-{slug}.md`. Record a chapter `source_locator` only as obtained evidence (a direct chapter URL also fills `source_url`); never invent one. A stub without a recorded locator cannot be promoted later. Supply `toc_description` only when the source gives a one-liner: it becomes `description` and TOC Preview; otherwise `description` is `""` and TOC Preview states that none was supplied, and the title is never relabelled as a one-liner. The stub keeps inherited book purpose, `status: stub`, integer chapterNumber, original-language chapterPart, bookIndex and chapterPrev/chapterNext links (null at endpoints) to its adjacent TOC chapters. Its body renders the title, the Source section (direct URL or an explicit `Not recorded:` line, Book link, previous/next), TOC Preview, Original Content's explicit non-empty pending-fill placeholder, an empty human Reading Notes section and Ingest Notes. Acquisition time means scaffold time, not chapter-read time. No chapter-specific Wiki pages yet. Validation allows explicitly marked stubs without treating placeholders as source evidence.

### B-4 — Book-level Wiki only

Compile only what TOC/preface supports: book Entity, author Entity, optional companion-site Entity, 1–3 anchor Concepts named in the preface, and optional 0–1 Guide if the preface provides reusable methodology. Link the Book Index from the relevant Map, creating the Map when none exists (Step 4). Do not precompile unread chapter concepts.

### B-5 — Record scaffold

One git commit records the whole scaffold and its actually compiled book-level knowledge. No index.md/log.md effects; follow git-provenance.md.

### Promotion — when a chapter is selected for reading

Promotion fills one chapter stub the owner has read. It reuses the book's purpose.

1. Acquire the chapter verbatim from the stub's recorded locator (`source_locator`, else `source_url`). The stub's Original Content must still be exactly the template's pending-fill placeholder.
2. Replace only that placeholder with the acquired text, and rewrite `status` and `date_modified`. All other bytes stay, including Source, TOC Preview, human Reading Notes, Ingest Notes and the five navigation fields.
3. Coverage decides status: `full` → `completed`; `partial` or `excerpt` → `reading`. Only `status: stub` is promotable. A later `reading`→`completed` change needs the missing text as a new full Raw; an existing Original Content is never rewritten.
4. Before writing, `bookIndex` must resolve to the promotion Index and `chapterPrev`/`chapterNext` to the adjacent TOC chapters (null at the endpoints).
5. In the Index change only this chapter's TOC checkbox `[ ]`→`[x]` (ticked for both `reading` and `completed`, because the chapter was actually read) and its Progress row to `| N | [[chapter]] | reading-or-completed | date |`. The row keeps partial coverage explicit. Nothing else in the Index changes.
6. Compile the chapter's Wiki pages by Step 3, quoting the acquired text: update existing Concepts and Entities first.
7. The chapter, Index and Wiki pages are one `ingest:` commit. Read back every result, then reindex.

## Bibliographic acquisition

Prefer the URL the user supplied.
Read a Yes24 product page with `defuddle` or the aside browser for title, authors, publication date, ISBN-13, TOC and publisher text.
When the TOC is missing, open `https://www.aladin.co.kr/shop/wproduct.aspx?ISBN=<ISBN13>`; its TOC images are `…/letslook/…_toc<N>.jpg` (`_toc1` is the cover) and count as TOC text only after OCR is actually performed.
For a title or ISBN alone, search Yes24 first and then Aladin.
For classic or historical texts, distinguish the recognized local title, the original-language title, the translator and the edition.

Label every recorded field by origin: observed storefront metadata, OCR or inferred summary, or user-supplied reading context.
A storefront blurb is not a finished summary, and a three-line summary is not catalog fact.
A storefront blurb or empty TOC is unfinished bibliographic work, not a finished book note.

## Work and edition identity

Search for the existing work and edition with verified bibliographic data (ISBN, author, translator, publisher, edition) before creating a note.
A translated or alternate title alone does not establish a different work, and differing editions are never merged silently.
Discovering another title is not a reason to rename an existing note; a requested move needs a supported, link-preserving surface.
The destination vault's template decides note identity, field mapping, naming and placement; a missing book template or registration blocks creation and is reported as such, not worked around with an invented schema.

## Selected chapters

Obtain only the selected chapters or supplied excerpts.
Retain original page/chapter locations, quotation boundaries, missing pages and conversion provenance.
Write purpose-grounded chapter analysis with links back to the obtained evidence, and reusable Concepts only where their independent information value warrants them.
A complete TOC is not a complete book, and a selected chapter is not whole-book coverage.

## Human reading

The personal book/review template remains owned by the destination vault.
Preserve the destination's human reading sections: thinking, reactions, dated personal bullets, anecdotes and next steps.
Quotes stay quotes and first-person notes stay first-person.
When updating, map existing highlights onto the TOC chapters instead of appending them as a dump, and keep the richer copy of a duplicated highlight.
When the exact review append is authorized, put agent suggestions and useful verified links only in its actual permitted Suggested/Linking sections through the destination's adapter; the CLI does not rewrite review sections.
