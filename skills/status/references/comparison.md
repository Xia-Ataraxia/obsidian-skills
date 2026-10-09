# Three-column comparison

Upstream: 구요한 `/status`, commit `863ca43`. One row per upstream step or section; this is the decision record, not a second procedure.

| 구요한 (863ca43) | secondbrain status before this revision | Decision + reason |
| --- | --- | --- |
| allowed-tools Read/Glob/Grep/Bash | read-only, `rg`/`find`/`git` | Adapt: tools in one line; read-only stated as the rule. |
| 1. Read `index.md` Stats table and catalog | no index | Reject: no `index.md` (repo decision); actual counts are the stats. Step kept by number so the skeleton lines up. |
| 2. Read `log.md` last 5 operations | `git log` recent | Adapt: Git history is the log; `git log -5`. |
| 3. Count actual files per folder incl. Paper hubs, Inbox all subfolders | per-area counts, hubs vs files, Inbox >30 days | Adopt his folder list; stack owner judgment: hubs and files separately, Inbox age, location is the state, missing folder ≠ zero, roots reported. |
| 4. Index vs actual discrepancies | absent | Adapt: no index drift; report declared-but-missing folders and Markdown outside declared roots. |
| 5. Coverage check `collectionPurpose` (미래의 나에게 보내는 편지) | `purpose` coverage + inferred/unknown | Adapt: `collectionPurpose` → `purpose`; his phrase kept; `purpose_origin` inferred/unknown counted. |
| 6. Cross-vault check `mainVaultRelated` | `mothership` coverage | Adapt: `mainVaultRelated` → `mothership`; "not applicable" without a mothership. |
| 7. Exploration Gate check `explored` | `explored` present + false backlog | Adopt name; owner adds false-count as backlog and role-scoped denominator, plus Bias Check count. |
| 8. Core Context age `snapshot_date` | snapshot age, git fallback | Adopt; owner adds git fallback, staleness against source changes, template = unfinished onboarding. |
| Output block (📊 … Recent Activity … Issues) | plain block | Adapt: same layout and labels minus emoji, with Papers, Bias Check and roots lines; recent activity from commits. |
| Issues: index out of sync, orphan pages, inbox waiting, collectionPurpose missing → /lint, Exploration Gate → /lint, Core Context > 30 days → /refresh-context | routing to skills | Adapt: index-sync row dropped; orphan detection left to `lint`; every issue routed to its owning skill; no score or ranking. |
