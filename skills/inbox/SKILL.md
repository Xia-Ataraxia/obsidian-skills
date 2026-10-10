---
name: inbox
description: Lists, previews, counts and reports recursive Inbox candidates, then hands an explicitly selected scope and one common purpose to ingest. Use for review my Inbox, preview these candidates, process this selection, or inspect duplicate sources. Not for capture, automatic RSS compilation, knowledge synthesis, or candidate deletion.
license: MIT
metadata:
  version: "0.5.4"
---

# Inbox

Built on 구요한's `/inbox` (LLM Wiki Inbox Scanner). His step skeleton and names are kept; the owner's rules are stacked on top. Every decision against his version is recorded in [comparison](references/comparison.md).

Scan `00. Inbox/` for unprocessed candidates and offer to ingest them, delegating per-file work to `ingest`. This skill reads and reports only: it never edits, moves or deletes a candidate. Removing an ingested candidate is the second half of `ingest`'s move into Raw.

Tools: `obsidian-cli` or plain file reads over the vault; `rg` over frontmatter for counts and locators; `qmd` when a locator is missing and you need a likely existing Raw.

## Input

- Blank or `all`: scan every lane.
- A lane or folder name (e.g. `articles`, `papers`): scan only that lane.
- `count` or `status`: show counts without detail, then stop.
- Named notes: preview those.

## Inbox Structure

Read the destination's actual `00. Inbox/` and the lanes it has; never assume a layout. A typical vault has lanes such as Articles, Papers, Transcripts, Clippings, AI Research and `{NN Agent}` session lanes (e.g. `01 Chat`, `04 GJC`), plus the root.

A note in a lane already has its kind assigned by where it sits. A note at the Inbox root is uncategorized: say so rather than guessing a lane; `ingest` settles its placement. Location is the state: a note in the Inbox is unprocessed, and there is no `status` field to read or set.

## Process

### Step 1: Scan

Walk the Inbox recursively; skip non-notes such as `.gitkeep`. If empty everywhere, report "Inbox is empty. Nothing to ingest." and stop. A note that cannot be read, or whose frontmatter does not parse, is reported as a problem, not counted as a candidate.

### Step 2: Preview

For each candidate, read the frontmatter and the start of the body (about the first 100 lines of a long note) and settle:

- **source** — `source_url` or `source_locator`, platform or runtime, author when stated, date clipped;
- **kind** — from the lane; for a root note, suggest one and mark it as a suggestion;
- **fidelity** — `transcript`, `excerpt`, `manifest-only` or `mixed`, plus the omissions the note names. A manifest-only note is a list, not text; never present it as full content;
- **purpose** — the recorded `purpose` and `purpose_origin`, or that none is recorded;
- **size** — rough length of Original Content, language, and for a bundle the number of members;
- **topics** — two or three, read from Original Content, not the capture notes alone. A claim found only in Agent Capture Notes is the capturer's reading.

**Duplicates.** Match by stable identity: `source_identity`, then canonical `source_url` or `source_locator`, or a session id; titles and authors never prove sameness. Check within the Inbox (candidates sharing a locator form one group; keep every distinct excerpt, since two clips of one page may hold different passages) and against existing Raw (flag the candidate with the Raw's path so `ingest` reuses or extends it; a fuller extraction becomes a new Raw linking the earlier one, and that call belongs to `ingest`).

### Step 3: Present

Lead with counts per lane and a total pending. Then one detail table:

| # | Lane | Note | Source | Fidelity | Purpose | Size | Topics | Duplicate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

List problems (unreadable notes, missing locators, root-level notes) below it. For `count` or `status`, stop here.

### Step 4: Ask

Ask two questions in one turn:

1. **Scope** — 전부 / 카테고리만 / 선택만: all, one lane, or named notes. No answer means nothing is selected; the whole Inbox is never assumed.
2. **Purpose mode** — 미래의 나에게 보내는 편지: why were these kept, and where will they be used?
   - **Single-axis bulk** (the default) — one purpose for the whole selection, asked once and applied to every note;
   - **Reuse** — keep the `purpose` a candidate already carries, where it does;
   - **Per-file** — the owner says the reasons differ; `ingest` asks per note;
   - **Auto-infer** — "알아서 판단": `ingest` infers from the source and the vault, states its reason, and records `purpose_origin: inferred`.

Never attach a purpose the owner did not give or approve, and never invent one for RSS or other automatic arrivals.

### Step 5: Ingest

Compose `ingest` with the selected note paths, the purpose per note, and the duplicate flags from Step 2. `ingest` owns everything after: placement in Raw by kind, preserving the candidate's source metadata, the 10–15 Wiki pages, Maps, the move out of the Inbox, and the commit. For a batch, notes run sequentially with progress per note: `[3/7] Ingesting: {note}`. A prepared selection is not an executed ingest.

### Step 6: Cleanup

Do not delete anything: `ingest` removes each candidate itself once its Raw passes the preservation check. Here, check what it reported against disk:

- each selected candidate has a Raw under the candidate's note name;
- each ingested candidate has left the Inbox; one still present is reported as a failed or partial ingest, not cleaned up here;
- unselected candidates are untouched.

Report what was ingested, what remains, and anything that failed.

## Notes

- Lane and frontmatter are both category signals; when they disagree, report the disagreement and let `ingest` decide placement from the destination's live policy. No `category` field is written.
- Web Clipper and RSS arrivals carry source metadata but no owner purpose; Step 4 is where one is given.
- For batches of five or more, keep the progress lines; never parallelize writes to the same Raw or Map.
