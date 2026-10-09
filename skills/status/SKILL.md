---
name: status
description: Reports read-only knowledge-vault counts, declared property presence, Inbox backlog, Paper Analysis hub/file counts, and derived-snapshot age. Use for a management snapshot or backlog check. Not for judging purpose fulfillment, knowledge quality, search freshness, process health, or making any vault change.
license: MIT
metadata:
  version: "0.5.1"
---

# Status

Show the current state of the wiki at a glance. The skeleton is 구요한's `/status`; decisions against it are in [comparison](references/comparison.md).

Status is read-only: it writes, repairs and reindexes nothing, and points at the skill that would. Counts are presence, never quality — a Raw with `purpose:` filled is not thereby well purposed. Run from the vault root, use the folder names the vault's AGENTS file declares (the ones below are the usual defaults), and report the roots you actually counted; a missing folder is reported missing, not zero.

## Process

1. **Stats and catalog.** There is no `index.md` Stats table to read; the counts in step 3 are the stats.
2. **Last five operations** come from Git history, not `log.md`: `git log -5 --oneline`, and `git log --since=7.days --oneline | wc -l` for the week's volume.
3. **Count actual files:**
   - `10. Raw Sources/**/*.md` → raw sources
   - `20. Wiki/21. Concepts/*.md` → concepts
   - `20. Wiki/22. Entities/*.md` → entities
   - `20. Wiki/23. Guides/*.md` → guides
   - `20. Wiki/24. Maps/*.md` → Maps (MOCs)
   - `20. Wiki/25. Questions/*.md` → research questions
   - `30. Queries/*.md` → queries
   - `40. Paper Analyses/*/` → paper hubs (one citekey folder each), and `40. Paper Analyses/**/*.md` → paper files; report both, they answer different questions
   - `00. Inbox/**/*.md` → pending inbox items, all subfolders, plus how many are older than 30 days. Inbox location is the state; there is no queue field. Volume is not urgency.
4. **Discrepancies.** With no index there is no index drift; instead report folders the AGENTS file declares but that are missing, and Markdown found outside every declared root.
5. **Coverage check**: `rg -l '^purpose:'` across `10. Raw Sources` → coverage % (미래의 나에게 보내는 편지 — the letter each Raw carries to its future reader). Also count `purpose_origin: inferred|unknown`; those Raw are worth naming.
6. **Cross-vault check**: `rg -l '^mothership:'` across `20. Wiki` → coverage %. Only meaningful when a mothership is configured in Core Context; otherwise report "not applicable", not 0%.
7. **Exploration Gate check**: `rg -l '^explored:'` across `20. Wiki` → coverage %, and the `explored: false` count as the exploration backlog (not a defect). Scope the denominator to Entities, Concepts and Guides; a Map without `explored` is missing nothing. Count pages with a Bias Check too.
8. **Core Context age**: `snapshot_date` from `Core Context.md` frontmatter → days since (fall back to `git log -1 --format=%cs -- "Core Context.md"`). Over 30 days, or older than a later change to a source it lists, is stale. A missing note or `status: template` means onboarding never finished.

Use `rg -L` to list files missing a field when the owner wants names. Tools: `rg`, `find`, `git`.

## Output

```
LLM Wiki Status — <vault>  (<date>)
──────────────────────────
Raw Sources:  <n>   (purpose coverage: <n/N> = <p>%; inferred/unknown <n>)
Wiki Pages:   <n>   (Concepts <n>, Entities <n>, Guides <n>, Questions <n>)
MOCs:         <n>
Queries:      <n>   (filed-back ratio: <queries>/<wiki> = <p>%)
Papers:       <hubs> hubs · <files> files
Inbox:        <n> pending  (>30 days: <n>)

mothership:   <n/N> wiki pages = <p>%  | not applicable
explored:     <n/N> wiki pages = <p>%  · <n> still false
Bias Check:   <n> pages

Core Context: snapshot <date> (<d> days ago)
──────────────────────────
Recent Activity (last 5 commits)
- <date> <subject>
──────────────────────────
Issues (if any)
- <finding> → <skill that handles it>
Roots counted: <list>; missing: <list>
```

Route each issue: large or old Inbox → `inbox`; purpose, mothership, explored or Bias Check gaps → `lint` for the per-file list; Core Context > 30 days → `refresh-context`; unfinished onboarding → `onboard`; search missing known pages → `reindex`. Do not rank the vault or turn the percentages into a score.
