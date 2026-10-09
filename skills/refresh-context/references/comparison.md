# Three-column comparison

Upstream: 구요한 `/refresh-context`, commit `863ca43`. One row per upstream step or section; this is the decision record, not a second procedure.

| 구요한 (863ca43) | secondbrain refresh-context before this revision | Decision + reason |
| --- | --- | --- |
| Intro: Core Context is a 시점 snapshot | dated snapshot of the owner | Adopt his term and §1–§5 section map; owner adds "sources stay the truth" and the derived-file location from AGENTS. |
| When to Run: lint/status 30 days or drift; mothership major version; new essay → §4; 7 axes change; §1 continuity | when to run list | Adopt all five triggers; owner adds staleness against a listed source change and "old but unchanged → date check only". |
| Step 1 Load Current Core Context | load snapshot | Adopt; also read `version` and `source`. |
| Step 2 (옵션) Re-Read Mothership System Files: version, date modified, changelog, §5 impact | mothership re-read + git log | Adopt his four captures; owner adds `git -C … log --since`, read-only, missing mothership reported and run continues. |
| Step 3 (옵션) Re-Read Personal Essays; new essays last 60 days via `find … -mtime -60 \| head -10` | re-read sources + new essays as candidates | Adopt; drop `head -10` cap; owner adds candidates-not-sources and no guessing from folder names. |
| Step 4 Diff & Propose: side by side, new essays one line, "전체 / 부분 / 거부" | section diff with source line | Adopt the three-way ask; stack traceability, keep owner wording, axes owner-defined with downstream-shift warning. |
| Step 5 Apply: update sections, `snapshot_date`, `date modified`, version minor/major, `source` | apply on OK, byte-for-byte rest | Adopt; `date modified` → `date_modified`; owner adds untouched sections byte-for-byte and read-back. |
| Step 6 Log: append to `log.md` | git commit message | Adapt: no `log.md` (repo decision); his log fields become the commit message; commit only on the owner's ask. |
| Output: age, changes, essays, version | report 1–5 | Adopt + mothership drift line. |
| allowed-tools incl. qmd | rg, qmd, git | Adapt: tools in one line. |
| (absent) | boundaries | Owner addition: never edit Me, AGENTS, policy, mothership, qmd config or runtime profiles; never publish. |
