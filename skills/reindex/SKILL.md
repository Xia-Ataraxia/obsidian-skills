---
name: reindex
description: Refreshes the qmd search index (BM25 and embeddings) after notes change. Use when the owner requests a search-index refresh, at the end of an ingest, or after bulk edits made outside the agent. Not for creating collections, editing qmd configuration, choosing models, querying notes, or changing source files.
license: MIT
metadata:
  version: "0.4.0"
---

# Reindex

Refresh the configured qmd index so new and changed notes are searchable. The
index and its collections are whatever qmd is already configured with; this
skill does not create, rename, or edit them.

```bash
qmd update    # BM25: re-reads changed files only
qmd embed     # vectors: embeds new or changed chunks only
qmd status    # confirm document and vector counts
```

- `qmd update` and `qmd embed` act on the whole index, so every collection in
  it is refreshed. Both are incremental and never touch the notes themselves.
- `qmd embed` can take minutes when many documents are pending; run it in the
  background and report when it finishes.
- Use `qmd embed -f` only after the embedding model changed.
- When `qmd` is not installed, report that and stop; nothing else is affected.

Report the counts `qmd update` printed and the final `qmd status` totals.
Document count and vector count are separate numbers and need not match.
