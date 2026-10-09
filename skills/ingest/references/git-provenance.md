# Git provenance

One ingest, including every Raw, Wiki, Map and atom it touched and the removed Inbox original, is exactly one local commit. No `index.md` or `log.md`: sync carries content, git carries history. Track attachments without LFS; ignore only workspace, cache, trash and sync-lock artifacts according to live policy.

Order:

1. Before writing, check the index holds no staged entries. If it does, stop: they belong to someone else.
2. Write the files.
3. `git --literal-pathspecs add -- <exact paths this ingest touched>`. A path is an exact filename, never a glob.
4. Compare `git diff --cached --name-only` with that list. Anything extra or missing stops the commit.
5. `git commit -m "ingest: {title}"` with trailers `Ingest-Source: <source identity or canonical locator>` and `Ingest-Purpose: <purpose>`.

Unrelated dirty files stay unstaged and byte-unchanged. A page a human changed during the run is re-read and merged, never overwritten. Never hard reset, check out to settle content, amend an earlier ingest, or force push.

Publication is not part of ingest unless live vault policy says ingest pushes. When it does: `git push`; on a non-fast-forward, fetch once, stop and report the local SHA. Never create or delete a remote. A vault that is not a git repository skips this step and says so in the report.

Undoing an ingest is `git revert <sha>`, which also restores the Inbox original.
