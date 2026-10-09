---
name: capture
description: Captures explicitly selected tabs, URLs, files, conversations or agent sessions as Inbox candidates, bundling several sessions that worked on one topic into a single note. Use for save this conversation, capture these tabs, keep this excerpt, harvest these sessions, or bundle today's sessions on a topic. Not for automatic session backup, compiling knowledge, Inbox management, or Web Clipper template authoring.
license: MIT
metadata:
  version: "0.4.0"
---

# Capture

Built on 구요한's `/capture-tabs` (AI Research Capture). His step skeleton and names are kept; the owner's rules are stacked on top. Every decision against his version is recorded in [comparison](references/comparison.md).

Capture is the pre-ingest capture layer: it preserves evidence in the Inbox and stops at the candidate note. Compiling it is `ingest`; reviewing what waits is `inbox`.

## Purpose

Use this skill when the owner has a tab group, open tabs, a URL, a file, an AI-chat research session (ChatGPT, Gemini, Grok, Claude, Perplexity) or a set of agent sessions and wants it kept as Markdown in `00. Inbox/` before `ingest`.

The default output is one **research-bundle note** per topic, at `{topic-slug}` in the Inbox lane the destination already has for its kind (an AI-research lane for chat research, the matching `{NN Agent}` lane for agent sessions). Use the clippings lane only for short excerpts, social posts, or a manifest-only capture without substantial text. Never invent a lane. There is no `status` field: being in the Inbox is the state.

## Capture Principles

Invoke `principle-original-order`: the sequence the creator gave the material is evidence.

1. **Preserve evidence before synthesis.** Get the text first; read it afterwards. A note with thin original text and rich commentary has the priorities backwards.
2. **Keep raw copied transcript under `## Original Content`** — only text you acquired, in its original order, with speakers, timestamps, headings, code and media links intact.
3. **Put agent interpretation under `## Agent Capture Notes`, never inside `## Original Content`.** A summary, paraphrase or reconstruction is never Original Content. Existing `## Codex Capture Notes` sections are read as agent notes.
4. **Record source URLs, platform names, visible model names, capture method, and capture limitations.** Claim the browser or runtime was queried only when a tool actually queried it; a pasted export is a pasted export. Text you could not get (collapsed answers, paywalls, truncated spans) is named as an omission, never filled from memory, a model's summary or a neighbouring source.
5. **Do not create public share links, post messages, upload files, or change account settings.** An existing public link is provenance, not permission to create another. Expanding collapsed answers or scrolling to load history is reading; sending, regenerating or editing a message is not, and is never done.
6. **Only the selection.** Capture the tabs, sessions or ranges the owner named; never sweep a window, an unnamed tab group or every session of the day.

## Tool Choice

Prefer the least lossy available path, and record which one you used as `source_extraction`.

| Source | First choice | When it fails |
| --- | --- | --- |
| Existing tab group or open tabs | The aside browser: list tabs, read titles and URLs non-destructively, then read each selected tab's text | Ask the owner to paste or export the text |
| Normal URL that opens without the owner's session | `defuddle` | The aside browser, then a paste |
| Account-bound or script-rendered page, AI chat | The aside browser reading the page; a built-in copy/export control when it yields local text without a share link | The owner's export or paste |
| Video or podcast | `yt-dlp` for metadata and original-language subtitles | Manifest-only with the locator; say no transcript was available |
| Local file | Read it directly | Name the converter that is missing |
| Chat conversation | [conversations](references/conversations.md) | — |
| Agent sessions | [sessions](references/sessions.md) | — |

Vault reads and writes use `obsidian-cli` or plain files; `rg` finds earlier candidates.

## Process

### Step 0: Scope

Resolve from the request or the visible browser session:

- `topic` — the research topic or tab-group name;
- `platforms` — chat platforms, runtimes and source sites;
- `captureMode` — per member `fidelity`: `transcript`, `excerpt` (his `curated-excerpts`), `manifest-only`, or `mixed` on the bundle when members differ;
- `nextStep` — `inbox-only`, `run-inbox` or `ingest-now`;
- **purpose** — why this is kept and where it will be used (미래의 나에게 보내는 편지). Ask it **once for the whole bundle** unless the owner already said it. Save the answer verbatim as `purpose` with `purpose_origin: stated`; reuse a purpose given earlier in the task as `reused`; record `unknown` only if the owner declines. `ingest` reads this field and does not ask again. A purpose never triggers compilation.

If the topic or target tab group / session set is ambiguous, ask one concise question before touching the browser. Read the destination's capture template and property conventions now; field names follow `ingest`'s frontmatter (`source_locator`, `source_extraction`, `fidelity`, `purpose`, `purpose_origin`, `referenced`).

### Step 1: Read Tab Metadata

The capture unit is the **topic**, not the tab or session: several members that worked on one subject become one candidate. Build a manifest table, per member:

- platform or runtime;
- title;
- URL or `source_locator` (session id and range for agent sessions);
- visible model / account / workspace where it matters;
- role in research — "question answering", "counterpoint", "source evidence", "follow-up", or for an agent session the task it was given.

A single short excerpt or social post is a candidate on its own.

### Step 2: Extract Conversation Or Page Text

For each selected member, with the route from Tool Choice:

1. Prefer built-in copy/export controls when they produce local text without creating a public link.
2. Otherwise read the page text through the aside browser or `defuddle`.
3. If UI reading is the only path, read the visible conversation without sending new messages.
4. Record gaps, truncation, hidden collapsed answers, failed extraction, and paywalled or auth-only content as omissions, and set the member's `fidelity`.

Keep chronology within a conversation and the owner's order across members.

### Step 3: Create Inbox Note

Use the destination's capture template as the shape. Write a **new note**; never overwrite or reorder an existing candidate. A later capture on the same topic is a new note that links the earlier one in `referenced`.

Frontmatter carries `type: inbox`, `source_url` / `source_locator` per member, `platforms`, `source_extraction`, `fidelity`, `description` (one English sentence), `author`, dates, `purpose`, `purpose_origin`, and the vault's tags. Agent session notes use the agent lane's conventions instead: `type: idea`, `created_by: agent`, `authorship: agent`, `tags: [agent-session]` and the runtime's `session_id`. No `capture_status`: location is the state.

### Step 4: Add Capture Notes

Under `## Agent Capture Notes`, each item grounded in the members and marked as your reading:

- one-paragraph topic summary;
- key claims by platform or member;
- source URLs, papers and people the material itself cites;
- disagreements between platforms — or, for a session bundle, where members differ in task or result;
- missing evidence, omissions and follow-up questions;
- suggested Wiki pages to create or update during `ingest` — its analysis starts from this list.

**Originals traced by ingest.** When `ingest` composes this skill for an original that a secondary claim relies on, write a manifest-only candidate: the original's locator and identity in the manifest, `purpose` inherited with `purpose_origin: reused`, and under Agent Capture Notes the citing passage quoted from the Raw that pointed here, with that Raw's link. Do not fetch the full text unless asked; `ingest` acquires it when the candidate is processed, and its Raw keeps this candidate's note name so existing links resolve.

### Step 5: Route

- `inbox-only` (the default): stop after writing the note and report its path.
- `run-inbox`: compose `inbox` on the new note.
- `ingest-now`: compose `ingest` on the new note; the purpose is already recorded, so `ingest` reuses it.

## Verification

Read the written note back before reporting:

1. It exists in the intended Inbox lane, at a new path.
2. `## Original Content` is non-empty and matches what was obtained, or the note is explicitly `manifest-only`.
3. Every member has a locator and a fidelity, and every omission is named.
4. Agent synthesis is separated from raw content; nothing in Original Content came from your own summary.
5. `purpose` and `purpose_origin` are set.
6. If the next step was ingest, `ingest` preserved the Raw before the Inbox original left (its own review checks this).

Report the path, the members with their fidelity, the omissions, and the purpose.
