---
name: inbox
description: Lists, previews, counts and reports recursive Inbox candidates, then hands an explicitly selected scope and one common purpose to ingest. Use for review my Inbox, preview these candidates, process this selection, or inspect duplicate sources. Not for capture, automatic RSS compilation, knowledge synthesis, or candidate deletion.
license: MIT
metadata:
  version: "0.3.0"
---

# Inbox

Make candidates and their limits visible before any knowledge compilation.

## Output contract

Read-only recursive listing and preview of the declared Inbox (`00. Inbox/**`, lanes `{NN Agent}`), or one `inbox/handoff@1` record containing only the selected candidates and one common purpose. Location is the processing state: no queue `status` is read or written. Same-source groups use proven source identity or matching locator and preserve every selected span. Candidates are retained after handoff; `ingest` removes each one it has preserved in Raw.

Read the shared [field contract](references/contract.md). Unknown purpose or source identity stays unknown. A manifest is not full text. No unselected candidate, RSS arrival or arbitrary quantity target authorizes compilation.

## Workflow

1. Resolve the destination's actual Inbox scope and lanes and read its policy. The vault root and scope are arguments, never assumed. A recursive folder selector is a read scope, not a write allowlist.
2. List candidates recursively. Preview selected items with fidelity and omissions, separating original content from capture notes. Malformed or inaccessible candidates are errors, not complete entries.
3. Confirm the explicit selection and reuse the purpose already stated for this batch. Do not ask once per item or attach a made-up purpose to RSS candidates.
4. Group by source identity or locator, never title or author. Retain distinct excerpts within a group. Before reprocessing, have `ingest` reuse matching existing Raw output rather than create duplicates.
5. Compose `ingest` by identity once with the handoff's members and common purpose. Read [handoff details](references/handoff.md). A prepared batch is not an executed ingest.
6. Read back ingest's actual outputs: the Raw, the pages it touched, and that each ingested candidate has left the Inbox. This package never deletes a candidate.

## Local helper

`python3 scripts/inbox.py <list|preview|handoff> --vault <base> --scope <relative-inbox>`

Preview needs `--candidate <relative-path>`. Handoff needs `--request <selection.json>`, which lives outside the vault.

No command writes; each emits JSON on stdout. Selected paths must be inside the scope with matching preview digests; traversal and symlinks are refused. A listing with errors reports `complete: false` and its errors. Exit 0 is an observed result, exit 1 a refusal (`{"refused": ...}`), usage exits 2.
