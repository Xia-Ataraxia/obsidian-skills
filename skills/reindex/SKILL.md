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
scripts/qmd-reindex.sh    # qmd update && qmd embed, in the background
qmd status                # confirm document and vector counts afterwards
```

- The script works the same from every runtime (Claude Code, GJC, Codex,
  Hermes). It returns at once; the run starts after 8 seconds with no further
  call, and one run handles a burst. Its log is
  `$TMPDIR/secondbrain-qmd-reindex.log`.
- `qmd update` and `qmd embed` act on the whole index, so every collection in
  it is refreshed. Both are incremental and never touch the notes themselves.
- To reindex in the foreground, run `qmd update && qmd embed` directly. Use
  `qmd embed -f` only after the embedding model changed.
- When `qmd` is not installed the script exits quietly; report that.

A runtime with edit hooks can call the same script after each note edit, passing
the edited path as the argument or the hook's JSON on stdin; it then reindexes
only when that path is a note inside a qmd collection. The Claude Code plugin
wires this in `hooks/hooks.json`. Other runtimes need their own hook entry.

Report the counts `qmd update` printed and the final `qmd status` totals.
Document count and vector count are separate numbers and need not match.
