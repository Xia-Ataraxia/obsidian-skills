---
name: obsidian-cli
description: Drives a running Obsidian desktop app through its official `obsidian` command-line binary to read, create, search, move, append, and audit vault notes, properties, tasks, tags, and links, and to reload, evaluate, screenshot, and inspect plugins or themes. Use when the user asks to read or create a note from the terminal, move or rename a vault note, search vault content, set a property, check backlinks or unresolved links, or reload a plugin and check its errors. Also use for Korean requests such as "이 노트를 가리키는 백링크 확인해줘" or "어떤 노트가 여기로 링크하는지 찾아줘". Not for Obsidian Markdown syntax or where a note belongs — use a format or vault-policy skill; not for a third-party CLI with a similar name, a headless sync client, or raw filesystem edits inside a vault.
license: MIT
metadata:
  version: "0.5.1"
---

# Obsidian CLI

Use the official `obsidian` CLI to operate a running Obsidian instance: read, create, search, move, mutate, and audit vault content, and drive the plugin and theme development loop. Success means the intended vault was targeted explicitly, the effect was authorized, and the result was read back from the exact path — not inferred from an exit code.

## Binary identity

The executable is `obsidian`, installed by the Obsidian desktop app. It talks to an app instance, so Obsidian must be open for vault and developer commands to work.

Confirm the surface before relying on it:

```bash
obsidian version    # answers only when the app is running and reachable
obsidian help       # the authoritative command catalog for that build
```

`obsidian help` is always up to date for the installed build; this manual describes operations and their guarantees, not a frozen catalog. When the two disagree, `help` wins and the difference is version skew — see [version skew](references/operations.md#4-version-skew).

There is no fallback surface. A third-party tool distributed under the name `obsidian-cli` — this skill's name, not this skill's binary — a headless sync client, an editor plugin, and raw shell writes into the vault folder are all different systems with different guarantees. If `obsidian` is missing, the app is not running, or the requested command is not in `help`, report that capability gap instead of substituting one of them. Full docs: https://help.obsidian.md/cli

## Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian vault="Research" create path="Scratch/My Note.md" overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

Every command's exact parameter set comes from `obsidian help`. This manual shows the forms it documents; where a parameter name is not shown here, read it from `help` rather than guessing a plausible one.

## File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

Prefer `path=` for every mutation. Both the active file and wikilink resolution depend on live app state, so they can silently select a different note than the one under discussion.

## Vault routing

Commands target the most recently focused vault by default. That default is app state you did not set, so it is only acceptable for throwaway reads. Pass `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

Name `vault=` explicitly on every mutation, and on any read whose output you will act on. If the vault name is unknown, ambiguous, or the request never named one, stay read-only and see [vault resolution](references/operations.md#1-vault-resolution). Never hardcode a vault name, absolute path, or account identifier into reusable content.

## Operations

Reads:

```bash
obsidian read file="Meeting Notes"
obsidian read path="Projects/Roadmap.md"
obsidian daily:read
```

Create and additive writes:

```bash
obsidian create name="New Note" content="# Hello" template="Template"
obsidian create path="Projects/Roadmap.md" content="<full body>" overwrite
obsidian append file="Meeting Notes" content="New line"
obsidian prepend path="Projects/Roadmap.md" content="Status: draft"
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="Meeting Notes"
```

`create ... overwrite` replaces the whole note body; it is a destructive command wearing a create name. Use the narrowest command that produces the requested change — `append`, `prepend`, or the `property:` family — and reserve whole-body writes for notes the task is genuinely authorized to replace.

Move:

```bash
obsidian help move
obsidian vault="Research" move path="Scratch/Draft.md" to="Projects/Draft.md"
```

A move changes the note's identity in the vault. Whether inbound links are rewritten depends on the vault's link-update setting, so do not assume either way — audit links afterwards and verify all three of destination, old path, and backlinks. See [write and move failures](references/operations.md#3-write-and-move-failures).

Search and audit:

```bash
obsidian search query="search term" limit=10
obsidian backlinks file="Meeting Notes"
obsidian links               # scope parameters per `obsidian help`
obsidian unresolved          # scope parameters per `obsidian help`
obsidian tasks daily todo
obsidian tags sort=count counts
```

`obsidian help` also lists a `search:context` variant of `search`. Search has been observed returning empty output with exit code 0 for a term that is present in the vault. Empty is indeterminate, never proof of absence — retry, then report the result as unconfirmed. See [app or runtime unavailable](references/operations.md#2-app-or-runtime-unavailable).

Deletes:

```bash
obsidian delete path="Scratch/probe.md"
```

`delete` is destructive and needs explicit approved scope naming the exact paths. Clean up only probe files this task created.

Plugin and vault state:

```bash
obsidian plugins versions
obsidian plugins filter=community versions
obsidian plugins:enabled
obsidian plugin:enable       # target parameter per `obsidian help`
obsidian plugin:reload id=my-plugin
```

Read-only Sync state for a vault the desktop app already syncs is exposed by the `sync:` family listed in `obsidian help`; pairing, daemons, and headless clients are a different system and are out of scope here.

Use clipboard and count flags only when the installed command's help lists them. Obsidian 1.12.7 `help create` lists `open` and `newtab`, but not `silent`; omit `open` when no new view is wanted. `total` is supported by the list commands that advertise it.

## Mutation contract

Every vault mutation follows this sequence. Skipping a step is how unrelated content gets lost.

1. **Resolve.** Fix the exact vault, the vault-relative path, and the authorized effect before the first write. A working command is not authority to change a vault.
2. **Read first.** `obsidian read path="<target>"` and keep that output as the pre-change snapshot.
3. **Write narrowly.** Pick the smallest command that produces the requested change. Never rewrite a whole note to change one line.
4. **Read back.** Re-read the same exact path and confirm two things: the requested change is materialized, and every untouched region — frontmatter, other sections, block IDs, links, trailing structure — matches the pre-change snapshot.
5. **Interpret honestly.** Exit code 0 is not materialized content. Empty output is indeterminate, not success and not absence. A matching filename or title is not a verified body.

If readback is impossible because the app or bridge is unavailable, say the mutation is unverified rather than reporting it as done, and follow [failure safety](references/operations.md#5-failure-safety).

## Plugin development

### Develop/test cycle

After making code changes to a plugin or theme, follow this workflow:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat from step 1:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings or unexpected logs:
   ```bash
   obsidian dev:console level=error
   ```

### Additional developer commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` to see additional developer commands including CDP and debugger controls.

`eval` executes arbitrary JavaScript inside the app. Keep it to read-only expressions unless a mutation through `eval` is explicitly authorized, and prefer a dedicated command whenever one exists. Plugin-provided commands only exist while that plugin is installed and enabled; their absence is plugin state, not a broken CLI.

## Composition and boundaries

This package works standalone and owns the command surface, vault routing, the mutation contract, and readback evidence. It does not own Obsidian Markdown syntax, note meaning, filing, templates, or write authorization.

Load a note-format or vault-policy skill only when the request explicitly needs that decision. No such skill being installed is the normal case, not a degraded one; one being installed but not selected stays unused. A composed skill never re-specifies the commands documented here, and never converts a usable tool into permission to change a vault.

Out of scope: third-party CLIs, headless sync pairing and daemons, raw filesystem edits inside a vault, non-Obsidian Markdown, and web page extraction.

## Failure branches

Load [references/operations.md](references/operations.md) when an operation mutates, fails, or returns something ambiguous:

- [Vault resolution](references/operations.md#1-vault-resolution) — unknown, ambiguous, or silently wrong vault.
- [App or runtime unavailable](references/operations.md#2-app-or-runtime-unavailable) — missing binary, closed app, unresponsive bridge, empty output.
- [Write and move failures](references/operations.md#3-write-and-move-failures) — partial writes, half-completed moves, destination collisions, bulk stops.
- [Version skew](references/operations.md#4-version-skew) — a command or parameter this manual names is not in the installed build.
- [Failure safety](references/operations.md#5-failure-safety) — destructive set, retry hazards, and the failure report shape.

## Verification

- [ ] The binary was identified as `obsidian` and answered `obsidian version` before any claim about it.
- [ ] The target vault was named explicitly for every mutation and acted-on read.
- [ ] The narrowest command for the requested effect was used; whole-body writes and deletes had explicit approved scope.
- [ ] Every mutation was read back from the exact path, with untouched regions compared against the pre-change snapshot.
- [ ] Empty or exit-code-only results were reported as indeterminate or unverified, never as success.
- [ ] No third-party binary, raw file write, or invented command substituted for a missing capability.

## Attribution

Imported and modified from the MIT-licensed `obsidian-cli` skill in [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills), Copyright (c) 2026 Steph Ango (@kepano). The permission notice is retained in this repository's root `LICENSE`; the pinned source revision and the list of modifications are in Git history.
