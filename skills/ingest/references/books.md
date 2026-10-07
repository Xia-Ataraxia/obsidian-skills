# Books

Resolve the actual bibliography and TOC source, then separate the book index from selected chapter evidence and analysis.
Record read/obtained/compiled states independently.
The CLI conservatively records compiled false at chapter level: the presence of a selected analysis does not establish complete chapter compilation.
Unread or unobtained chapters remain not-obtained/not-compiled and get no fabricated Raw body.

## Bibliographic acquisition

Prefer the URL the user supplied.
For a Yes24 product page run `uv run scripts/fetch_yes24.py <URL>` from this package directory; it prints title, subtitle, authors, cover, publication date, ISBN-13, categories, TOC and publisher text as JSON.
When that TOC is empty, run `uv run scripts/fetch_aladin_toc.py <ISBN13>`; it returns the Aladin TOC image URLs (cover excluded), which still need an actually performed OCR before they count as TOC text.
For a title or ISBN alone, search Yes24 first and then Aladin; the Yes24 fetcher does not accept Aladin URLs.
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
