---
name: onboard
description: Initializes an independent personal or knowledge vault through a short owner interview that fills template placeholders and writes the core context note, proposes settings changes for an existing vault, and resumes an interrupted setup by detecting what is already done. Use for fresh vault setup, additive onboarding, or a zero-diff rerun. Not for moving existing notes, installing skills, Sync pairing, source ingestion, or editing vault policy.
metadata:
  version: "0.5.4"
---

# Onboard

Turn a starting vault into the owner's vault in about ten minutes by interviewing them and filling everything in, without requiring or creating a counterpart vault. The skeleton is 구요한's `/onboard`; decisions against it are in [comparison](references/comparison.md).

## Philosophy

1. **Context-first** — fill *who you are* (Core Context) before ingesting; without it every `ingest` purpose question and every `query` answer is generic.
2. **Answer-1-of-many** — ask a handful per turn; the owner answers only what is relevant. Context accumulates across turns.
3. **Agent-does-the-typing** — the owner speaks in plain words; you write frontmatter, placeholders and Core Context.
4. **Resume-safe** — rerunning detects what is done and continues from the first unfinished step; a finished vault changes nothing.

## Pre-flight

```bash
pwd
rg -l '\{(your-name|Your Name|PATH_TO_[A-Z_]+|your-mothership-vault-name|YYYY-MM-DD)\}' -g '*.{md,json,yml,yaml,sh}' . | wc -l
rg -m1 '^status:' "Core Context.md"
```

- 0 placeholder files and `status: active` → already onboarded. Say so and ask whether to revisit anything (identity or axis changes belong to `refresh-context`).
- Target missing or empty → lay down the starting vault first: ask the role (`personal` or `knowledge`) and the template folder, copy it into the empty target (`cp -R "$TEMPLATE/." "$VAULT"`), and recommend `git init` — Git is the vault's log. Never copy over an existing vault; confirm the owner may use the template's files and plugins.
- A vault that already has notes but was never onboarded → no copy; touch only what the owner approves (settings below).
- Otherwise → Interview.

## Interview — 필수 5 + 옵션 2 (answer-1-of-many)

In voice mode one question at a time, in text a batch. After each answer, confirm it back in one or two sentences.

**Q1 — Location & name.** The vault's absolute path comes from `pwd`. Ask the name to use inside the vault (real name, handle, any script — it goes into wikilinks) → `{your-name}` / `{Your Name}`.

**Q2 — Operating mode.**
- **Mode A (standalone)**: this vault only; mothership placeholders are ignored.
- **Mode B (mothership)**: an existing main vault is the mothership and this one a satellite. The mothership is read-only from here, always.

**Q3 — (Mode B only) Mothership path & name.** Its absolute path, checked to exist, and its registered Obsidian vault name — the folder name used in `obsidian://open?vault=`, not the path. Confirm the registration with `obsidian-cli`.

**Q4 — Core Context §1 identity (core).** Name, role, field, main activities, and the **continuity statement**: in one to three sentences, which earlier question today's work grew out of.

**Q5 — Core Context §2 reuse axes, 5–9 (core).** Where a source might end up: research, writing, teaching, consulting, product, essays, community… Seven is a good number; too few and everything piles on one, too many and they stop discriminating. These axes are what the owner answers when `ingest` asks a source's purpose.

**Optional — §3 personal frameworks / §4 philosophy, 3–5.** Fill when given; otherwise skip (`refresh-context` can add them later).

**When stuck (failure mode): passive mode.** If answers do not come, ask for paths to existing writing (blog, essays, the mothership's Me note), read them, and propose §1 and §2 for the owner to correct. Nothing in Core Context is invented.

## Fill

**F1 — Placeholder replacement.** Show the values (name, vault path, today's date in the owner's timezone, and in Mode B mothership path and name). After OK, replace only the literal tokens across `.md`, `.json`, `.yml`/`.yaml` and `.sh` files, `.git` excluded (`sed -i ''` on macOS): `{your-name}`, `{Your Name}`, `{PATH_TO_YOUR_LLM_WIKI}`, `{YYYY-MM-DD}`; in Mode B also `{PATH_TO_YOUR_MOTHERSHIP_VAULT}`, `{PATH_TO_YOUR_MOTHERSHIP}`, `{your-mothership-vault-name}`.

**F2 — Write Core Context.md.** Draft §1 identity and §2 reuse axes (plus optional §3/§4) from the interview, and §5 listing the mothership's system files in Mode B; in Mode A delete §5. Show the draft and confirm. Then set `status: template` → `active`, `snapshot_date` to today, keep `version: "1.0"`.

**F3 — Verify replacement.** Run the pre-flight `rg` again. No output passes; in Mode A the unused mothership placeholders may remain harmlessly.

**Settings for an existing vault.** Only `.obsidian/app.json`, `.obsidian/daily-notes.json`, and the `data.json` of the `homepage`, `templater-obsidian` and `obsidian-excalidraw-plugin` plugins are in scope. Show the exact top-level keys to change with old and new values; apply only approved keys, leave every other key and the formatting untouched, with Obsidian closed or idle.

## Resume logic

Every run starts at the pre-flight and continues at the first unfinished step: placeholders remain → F1; Core Context still `status: template` → F2; both done → already onboarded.

## Wrap-up

Read back the files written and list them. Then suggest:

1. `status` — the vault at a glance.
2. A first `ingest <URL>` — when the purpose question comes, answer with one of the §2 reuse axes ("미래의 나에게 보내는 편지", a letter to your future self).
3. A first `query <question>`.
4. As it grows: recurring open questions become Research Question cards in `20. Wiki/25. Questions/`; a defended claim becomes a Synthesis card.
5. Later: `capture` and `inbox` for collecting before ingesting, `qmd` for search (`reindex`).

Do not install skills, sync, migrate notes or ingest as a side effect.

Tools: `rg`, `sed`, `git`, `obsidian-cli`.
