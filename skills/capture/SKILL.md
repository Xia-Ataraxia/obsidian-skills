---
name: capture
description: Captures explicitly selected tabs, URLs, files, conversations or agent sessions as Inbox candidates, bundling several sessions that worked on one topic into a single note. Use for save this conversation, capture these tabs, keep this excerpt, harvest these sessions, or bundle today's sessions on a topic. Not for automatic session backup, compiling knowledge, Inbox management, or Web Clipper template authoring.
license: MIT
metadata:
  version: "0.3.0"
---

# Capture

Keep the material the owner selected, with its actual acquisition limits.

## Output contract

One new Inbox candidate per topic separates Original Content from Agent Capture Notes and records the shared [field contract](references/contract.md). Transcript, excerpt, manifest-only and mixed captures retain per-source fidelity. A source list is never displayed as obtained full text. Inaccessible or missing text stays absent, with an omission; it is not reconstructed from a summary.

Agent session notes land in the destination's `00. Inbox/{NN Agent}` lane (for example `01 Chat`, `04 GJC`; resolve the actual lane from the live vault, never invent one) with frontmatter `type: idea`, `created_by: agent`, `authorship: agent`, `tags: [agent-session]` and the runtime's `session_id`. There is no queue `status`: the Inbox location is the processing state, and `inbox` hands the note to `ingest` from there.

The default end is candidate capture, not ingest. No upload, share-link creation, send, automatic session report or full-session backup is performed.

## Workflow

1. Read the destination vault's applicable policy, property conventions and actual capture template. Confirm the exact candidate destination and create approval. Never treat a template's path as approval.
2. Resolve only the selected sources and ranges. Several sessions on one topic become one [topic bundle](references/sessions.md), not one note each. Input designation, semantic kind and extraction method are separate fields. Do not discover or capture unrelated tabs, conversations or sessions.
3. For conversations read [conversations](references/conversations.md); for existing runtime session spans read [sessions](references/sessions.md). Use `obsidian-clipper` by identity only when authoring or repairing an extension template is needed. Do not claim the browser or runtime was queried when only an export was supplied.
4. Retain acquired source bytes, speaker/time/anchor information and known omissions. Agent interpretation belongs in Agent Capture Notes.
5. Ask once why this is being kept and where it will be used, unless the owner already said. Ingest reuses the answer, so a bundle is never asked twice. Record unknown only if the owner declines. Purpose does not trigger compilation.
6. Materialize and read back the exact candidate; report its fidelity and digest. Compose `inbox` or `ingest` by identity only if the owner requested that follow-up.

## Local helper

`python3 scripts/capture.py --vault <declared-base> --request <request.json>`

Read [the request format](references/requests.md) before using the helper. It handles supplied browser/reader/runtime extraction text or explicit UTF-8 files and inclusive line spans. It does not fetch URLs, enumerate browser tabs, query private runtimes, run template hooks, or infer destinations. Missing tools are unavailable, not a successful full capture.

The helper writes only a new `.md` file named in exact create approval with an `absent` preimage. Existing files, symlink routes and traversal are refused. Exit 0 reports a materialized capture with a readback digest; exit 1 reports refusal or an I/O error. Usage errors exit 2.
