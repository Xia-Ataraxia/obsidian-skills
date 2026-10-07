---
name: inbox
description: Lists, previews, counts and reports recursive Inbox candidates, then hands an explicitly selected scope and one common purpose to ingest. Use for review my Inbox, preview these candidates, process this selection, or inspect duplicate sources. Not for capture, automatic RSS compilation, knowledge synthesis, or unattended candidate deletion.
license: MIT
metadata:
  version: "0.2.1"
---

# Inbox

Make candidates and their limits visible before any knowledge compilation.

## Output contract

Read-only recursive listing, preview, count and status, or one ingest handoff containing only the selected candidates and one common purpose. Same-source groups use proven source identity or matching locator and preserve every selected span. Retained candidates are not deleted after handoff.

Read the shared [field contract](references/contract.md). Unknown purpose or source identity stays unknown. A manifest is not full text. No unselected candidate, RSS arrival or arbitrary quantity target authorizes compilation.

## Workflow

1. Resolve the destination's actual Inbox scope and read its policy and metadata conventions. A recursive folder selector is a read scope, not a write allowlist.
2. List candidates recursively. Preview selected items with fidelity and omissions, separating original content from capture notes. Malformed or inaccessible candidates are errors, not complete entries.
3. Confirm the explicit selection and reuse the purpose already stated for this batch. Do not ask once per item or attach a made-up purpose to RSS candidates.
4. Group by source identity or locator, never title or author. Retain distinct excerpts within a group. Before reprocessing retained candidates, have `ingest` inspect its actual source/result receipts and reuse matching results rather than create duplicate Wiki pages.
5. Compose `ingest` by identity once with the unchanged handoff and an explicit aggregate member/output mapping and approval, using its actual `--handoff` batch interface. Read [handoff details](references/handoff.md). The local helper prepares the batch, not the knowledge output. A prepared batch is not an executed ingest.
6. Read back ingest's actual outputs and record its failures and reuse decisions. Candidate deletion is a separate owner decision; it is never the successful-ingest default.

## Local helper

`python3 scripts/inbox.py <list|count|status|preview|handoff|delete> --vault <base> --scope <relative-inbox>`

Preview also needs `--candidate <relative-path>`. Handoff and delete need `--request <selection.json>`.

List/count/status/preview/handoff are read-only and emit JSON on stdout. All selected paths must be within the declared Inbox and have matching preview digests. Traversal and symlink routes are refused. Deletion requires a distinct request with only the `delete` effect, exact selected scope, owner basis and matching preimages. Exit 0 describes the observed result, exit 1 reports a refusal/I/O error and usage exits 2. A listing with errors reports partial status and its errors; it never reports a complete candidate count.
