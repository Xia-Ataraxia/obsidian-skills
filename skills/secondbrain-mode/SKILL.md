---
name: secondbrain-mode
description: Sets the working stance for a knowledge-vault task that spans several packages - delegate to background subagents, own their work, and finish with an independent review. Use for secondbrain-mode, 세컨드브레인 모드, or a multi-step vault task that spans capture, ingest and query. A single named task such as ingest or query runs directly without this package, and skill authoring alone belongs to principle-skill-creating.
license: MIT
metadata:
  version: "0.3.0"
---

# Secondbrain mode

A stance, not a dispatcher: every package runs directly from its own description. Load this when a task spans several of them.

## Stance

- Read the destination vault's live policy before any write. A package never grants write permission by itself.
- One request runs to the end. Ask once, up front, for what only the owner can answer; do not stop for a second approval between steps the request already covers.
- Read a `principle-*` package in full before applying it.
- Report what was written, what was skipped and what stayed unknown. Missing evidence is never success.

## Subagents

Delegate by default. The main thread keeps the request, the decisions and the summary; reading, per-source work and edits go to background subagents.

- Brief each one like a peer: the goal, what is already ruled out, file pointers instead of pasted content, and the package and principle it must read in full first.
- One subagent per independent unit: one source, one topic bundle, one package.
- A fix round goes to a fresh subagent with the original brief and the prior report.
- You own its work. Read the diff or the written notes yourself and write your own summary.

## Review

Anything that writes to the vault or changes a skill gets an independent review subagent.

- Give the reviewer the artifact and the governing package or principle, not your conclusion.
- Ask for findings with path and line, ordered by severity, and what it could not check.
- Fix each finding or dismiss it with a concrete reason, and report which was which.

## Changing a skill

1. Read `principle-skill-creating` in full.
2. Delegate the edit to a subagent briefed with that principle and the package path.
3. Run the repository's format checks; here, `python3 scripts/audit_inventory.py` and `claude plugin validate . --strict`.
4. Send the diff to a separate review subagent, asking where the change breaks the principle and where it duplicates or contradicts a sibling package.
