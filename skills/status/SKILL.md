---
name: status
description: Reports read-only knowledge-vault counts, declared property presence, Inbox backlog, Paper Analysis hub/file counts, and derived-snapshot age from explicitly named responsibility roots. Use for a management snapshot or backlog check. Not for judging purpose fulfillment, knowledge quality, search freshness, process health, or making any vault change.
license: MIT
metadata:
  version: "0.2.0"
---

# Status

Observe the named responsibility roots without changing the vault.

Success is a machine-readable report whose counts can be traced to explicit
vault-relative roots and whose limitations prevent presence metrics from being
misreported as quality, feedback, verification, or runtime health.

## Inputs

Use `scripts/status.py` with an existing vault and a JSON scope:

```bash
python3 scripts/status.py --vault VAULT --scope scope.json
```

The scope is `status/scope@1`:

```json
{
  "schema": "status/scope@1",
  "roots": [
    {"name": "questions", "path": "20. Wiki/Questions"},
    {"name": "personas", "path": "20. Wiki/Personas"}
  ],
  "paper_analyses": "40. Paper Analyses",
  "inbox": "00. Inbox",
  "snapshots": [
    {"name": "agent-context", "path": "90. Settings/Derived/agent-context.md"}
  ],
  "properties": ["purpose", "source_locator"]
}
```

Resolve these paths from the destination's actual policy or reviewed candidate.
Do not substitute similarly named folders, invent a missing responsibility, or
use a writable folder as permission for anything.

Read [the shared contract](references/contract.md) before interpreting approval
or evidence fields from neighboring workflows.

## Report semantics

- `roots[].markdown_files` counts Markdown files recursively in that exact root.
- `properties` counts top-level frontmatter key presence only. Presence is not
  truth, completeness, purpose fulfillment, citation quality, or review.
- `paper_analyses.top_level_directories` counts first-level hub containers.
  `root_markdown_files` counts Markdown files directly in the Paper Analyses
  root, and `markdown_files` counts every Markdown file below it. Root-level
  `type: paper-hub` files are additionally counted by file and deduplicated by
  their materialized ingest `source_identity`; missing and duplicate identities
  remain explicit. These values remain separate.
- `inbox.markdown_files` is backlog volume, not urgency or ingest eligibility.
- Snapshot age comes from the materialized file timestamp. It does not prove
  that the snapshot is correct, approved, loaded, or being used by a runtime.

The helper reads only bounded flat frontmatter from counted notes; it does not
consume note bodies. It rejects traversal, hidden routes, symlinks, duplicated
root names, missing roots, and malformed frontmatter. It prints structured
semantics flags and `mutations_performed: []` in every successful report.

## Boundaries

Status is read-only. It never creates a report note, repairs metadata, refreshes
an index, rewrites a snapshot, starts a process, or treats an online process as
successful knowledge behavior. Compose `reindex` or `refresh-context` by
explicit identity only when that separate task is requested.

Python 3.8 or newer and the standard library are sufficient.
