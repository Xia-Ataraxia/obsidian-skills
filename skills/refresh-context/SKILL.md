---
name: refresh-context
description: Re-reads the owner's named Me, policy, and user-instruction sources, diffs them against the derived agent-context snapshot, proposes the changes, and applies them after the owner says yes. Use when derived agent context must be refreshed after source changes, or when status or lint reports the snapshot as stale. Not for editing Me or policy, inventing personal context, automatic reloads, public context publication, or requiring a counterpart vault.
license: MIT
metadata:
  version: "0.5.1"
---

# Refresh Context

[[Core Context]] is the owner's **시점 snapshot** — who they are at a point in time: §1 identity and continuity statement, §2 reuse axes, §3 frameworks, §4 philosophy, §5 mothership references. When the owner's thinking develops, or the (optional) mothership changes, the snapshot must follow. Every `ingest` purpose question and every `query` answer is tailored to it, so a stale snapshot quietly bends all later work. The sources stay the truth; this skill brings the snapshot back in line with them and nothing more. The skeleton is 구요한's `/refresh-context`; decisions against it are in [comparison](references/comparison.md).

The note is usually `Core Context.md`, sometimes a derived file such as `90. Settings/Derived/agent-context.md`; use the one the vault's AGENTS file names.

## When to Run

- `lint` or `status` flags "Core Context > 30 days old", or a later change to a source it lists, or mothership drift.
- (with a mothership) a mothership system file changed version, precedence, folders or roles.
- The owner published a new essay or manifesto — §4 philosophy may need updating.
- A reuse axis (§2) was added, dropped or renamed, or the owner's role changed.
- The continuity statement (§1) needs updating, or the owner asks.

A snapshot that is old but whose sources have not changed needs only its date checked, not a rewrite; say so.

## Step 1: Load Current Core Context

Read the note in full: `snapshot_date`, `version`, the `source` list, and §1–§5. This is the "before" side of the diff.

## Step 2: (optional) Re-Read Mothership System Files

Read, read-only, each mothership file §5 registers (its AGENTS, CLAUDE or policy notes). For each, capture:

- `version` — bumped?
- date modified — newer than the snapshot? With Git: `git -C "$MOTHERSHIP" log --since="$SNAPSHOT_DATE" --oneline -- <files>`.
- the first changelog entry — what changed?
- whether the change touches the §5 table: precedence, audience, focus, memory type.

No mothership registered: skip and say so. A registered mothership missing on disk is reported and the run carries on with this vault.

## Step 3: (optional) Re-Read Personal Essays

Re-read every note in the frontmatter `source` list in full. Then scan for **new** essays from the last 60 days in the essay location §5 names (`find "$ESSAYS" -name '*.md' -mtime -60`, or `qmd` for recent writing). New essays are candidates, not sources: summarize each in one line and let the owner decide. Do not add sources by guessing from folder names; if none can be identified, ask.

## Step 4: Diff & Propose

Show side by side, section by section:

- **Current Core Context** (§1–§4 core sections, §5 when touched);
- **Proposed updates**, each with the source line behind it;
- **New essays** discovered, one-line summary each, asking whether to promote them into §4 philosophy and `source`.

Owner judgment on top:

- Every proposed claim traces to a source just read; anything untraceable stays out. Never fill a section from names, paths or an older snapshot.
- Keep the owner's own wording where it still holds. Refreshing is not rephrasing.
- Reuse axes are the owner's to define; propose a change only when a source states it, and flag that later `ingest` purposes and `query` answers will shift.

Ask: **"Apply this diff? (all / some sections / none)"** — in the owner's language.

## Step 5: Apply

If approved, edit only the approved sections and leave the rest of the file byte-for-byte. Set `snapshot_date` and `date_modified` to today, add approved essays to `source`, bump `version` (minor for §2/§4/§5 changes, major for a restructure). A later proposal needs its own OK. Read the note back.

## Step 6: Log

There is no `log.md`; Git history is the log. The commit message carries what his log entry did: `Core Context refreshed (v<old> → v<new>)`, the mothership drift found, essays incorporated, sections updated, and a one-line why. Commit only when the owner asks; otherwise give the message ready to use.

## Output

1. **Snapshot age**: was N days, now 0 (or unchanged, and why).
2. **Changes applied**: one line per section changed; sections left as they were.
3. **Mothership drift**: files changed since the last snapshot, or not configured.
4. **New essays added to source**: count and titles.
5. **Version bump**: old → new.

Never edit Me, AGENTS, policy notes, user instructions, the mothership or another vault, qmd configuration or runtime profiles from here; if a source looks wrong, tell the owner. Do not publish the snapshot.

Tools: `rg`, `qmd`, `git`.
