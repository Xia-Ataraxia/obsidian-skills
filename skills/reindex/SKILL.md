---
name: reindex
description: Refreshes BM25 and embedding derivations only for one audited qmd collection in an isolated named index, requiring Paper Analyses and refusing Inbox, personal, public, company, or memory roots. Use when the owner requests a search-index refresh or scoped index-status check. Not for creating collections, editing qmd configuration, choosing models, querying notes, or changing source files.
license: MIT
metadata:
  version: "0.3.0"
---

# Reindex

Refresh one already configured qmd collection without changing source notes or
touching any other qmd collection.

Current qmd CLI `update` and `embed` operate on an index, not one collection.
This package therefore requires a named index whose preflight status exposes
exactly one collection: the selected collection. A shared or multi-collection
index is refused rather than partially updated or silently mixed.

## Inputs

Use `scripts/reindex.py` with an existing vault and a reviewed scope:

```bash
python3 scripts/reindex.py --vault VAULT --scope scope.json
```

The `reindex/scope@1` document names the isolated qmd index, its sole
collection, and the allowed responsibility roots:

```json
{
  "schema": "reindex/scope@1",
  "index": "knowledge-vault",
  "collection": "knowledge",
  "include_roots": [
    "10. Raw Sources",
    "20. Wiki",
    "30. Queries",
    "40. Paper Analyses",
    "50. References"
  ],
  "paper_analyses": "40. Paper Analyses"
}
```

The helper verifies that every included root exists, Paper Analyses is present,
and no included route names Inbox, personal, public, company, or memories. It
parses the collection's exact canonical `Path` and requires its glob union to
equal the approved `<root>/**/*.md` masks. Prefix matches, brace expansion, and
extra wildcards are refused. It then audits actual indexed membership with
`qmd ls` against the visible Markdown files below those roots:

```text
qmd --index <index> update
qmd --index <index> ls qmd://<collection>/
qmd --index <index> embed
qmd --index <index> status
```

No model flag or model environment override is added. Model selection remains
with the selected qmd index configuration.

Read [the shared contract](references/contract.md) for evidence semantics.

## Outcomes

- Result status `reindexed`: every preflight, update, membership, embed, and
  final status command completed successfully.
- Result status `unavailable`: no qmd executable was found before invocation.
- Error status `refused`: invalid input, unsafe paths, failed preflight,
  membership mismatch, nonzero qmd exit, bounded command timeout, or qmd stdout
  that is not valid UTF-8 (`qmd_output_undecodable`; member paths are never
  guessed from undecodable bytes).
- Error status `unavailable`: the selected executable could not be launched.

The report includes exact argument arrays and bounded stdout/stderr readbacks.
Document count and vector count remain separate; equality is never required.
On an error, `mutations_performed` lists only confirmed effects. If `update` or
`embed` was attempted before the failure, `mutation_state` is
`possible_unconfirmed` and `effects_possible` names the derivation scope. An
empty confirmed-mutation list in that state does not mean zero effects.
Preflight refusal keeps `mutation_state: none` and an empty possible-effects
list.

## Boundaries

The helper does not create, rename, include, exclude, or edit a collection; does
not write qmd configuration; does not run a global unnamed index; and does not
touch the vault. Configure the single-collection named index separately through
qmd's supported interface and obtain any trust approval there.

Python 3.8 or newer and the standard library are sufficient. qmd is an optional
external dependency: absence is reported as `unavailable`.
