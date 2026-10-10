---
name: principle-skill-creating
description: Apply when creating, editing, reviewing or trimming an Agent Skill package - deciding what belongs in SKILL.md versus templates, scripts, agents or references, whether a helper script or test should exist, and what to delete. Use for 스킬 만들기, 스킬 고쳐줘, 스크립트로 강제하지 마, 템플릿으로 빼자, skill authoring and skill review.
license: MIT
metadata:
  version: "0.5.3"
---

# Skill creating

## Apply when

Apply before adding or changing anything in a skill package, and when a skill feels heavy, brittle or over-guarded. This principle is independently usable without sibling packages.

## Principle

Ask first where the computation happens. There are exactly two answers, and confusing them is how skills fail.

- **Latent space** is the model steered by Markdown: taste, judgment, reading intent from a vague request, special cases, what to select, classify, order and write, and when to stop.
- **Deterministic space** is code: arithmetic, identity and hash computation, exact-match lookup such as dedup, queries, bookkeeping past what a model can hold in its head, and real external actions through their own tool or API.

The direction is always Markdown calling code. Judgment written as code is brittle and fails on the cases nobody enumerated. Bookkeeping left to the model fails at scale.

## The package

A package is `skills/<name>/SKILL.md` plus only the resources it actually uses. `SKILL.md` is the only file at the package root; everything else lives in a subfolder.

| Part | Holds | Rule |
| --- | --- | --- |
| `SKILL.md` | The recipe: steps, judgment, stop conditions | Write what you would tell the next person doing this job. One request runs to the end; a step that must happen is stated as mandatory and checked in a closing review step, not by a gate. |
| `templates/` | Output shapes | A shape described in prose is a template that has not been written yet. Keep in the body only what the template cannot show. |
| `scripts/` | Thin tools | One question answered or one action performed. Never orchestrates steps, carries judgment as flags, or blocks the run. Prefer a tool that already exists over a new script. |
| `agents/` | Briefs for subagents | Use when independent workers do similar but different work in parallel. |
| `references/` | Depth read on demand | Per-type detail the body links to. Not a second copy of the recipe. |
| `assets/` | Files the output uses | Only what a step consumes. |

## One owner per rule

Before writing, search the sibling packages for the same trigger, step or rule.

- A rule lives in one package. When another package needs it, name that package instead of restating it.
- When two packages say different things about the same case, that is a defect: decide which one owns it and delete the other statement in the same change.
- Two descriptions must not claim the same request. Say what the neighbour owns in the description's last sentence when they are close.

## Keep it light

- History is the Git log. A package carries no `CHANGELOG.md`. Do not edit `metadata.version` per change; the release sets it.
- Checks enforce package format only: valid frontmatter, a name that matches the directory, links that resolve. Do not write tests for a package's scripts or for its wording; routing evals for a description are format checks and stay.
- Delete before adding. No speculative helper, compatibility alias, fallback path or retired stub; a retired thing is removed and stays in history. Build the missing piece when it is actually needed.
- When a task can only proceed through a script's pipeline, the script is a gate. Delete it and state the steps in the body.
- When a body step is counting, matching or tracking many items, give it a thin script.
- Write each rule as one imperative line that names the tool or the action. Do not record the incident that prompted it, its reasons, or flag-level detail the tool's own help gives; that belongs in the commit message.
- Keep a prohibition only when breaking it loses something that cannot be restored. Defensive prose that restates the obvious is weight.

Example: a mail archive skill had a script that listed, fetched, deduplicated, rendered and wrote every note. Selection and rendering were judgment, so the script went away and the body now gives the steps; the note shape moved to a template; a twenty-line script that answers "which message ids are already archived" stayed.

This contextual principle never authorizes a write, move, or deletion.
