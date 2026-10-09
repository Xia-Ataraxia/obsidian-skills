# Selection and handoff

## Location is the state

Candidates live under the destination's Inbox scope, passed as `--scope` (for example `00. Inbox`). Agent lanes are the first-level `{NN Agent}` folders such as `01 Chat` or `04 GJC`; `list` reports each candidate's `lane` (`null` outside a lane). There is no queue `status` field in candidates, handoffs or results: a note in the Inbox is unprocessed, and leaves the Inbox when ingest has preserved it in Raw. A capture-side `status` property is ignored.

## Selection

Use `list` or `preview` to obtain each candidate's path and `sha256:` digest. The selection JSON supplies `selected_paths` and `selected_preimages` (path → `sha256:<digest>`). No selection is the empty batch, not the entire Inbox: the helper refuses it. Paths outside `--scope`, stale bytes, traversal and symlinks are refused. Malformed notes (unterminated frontmatter, duplicate keys, non-UTF-8, contradictory fidelity) are listing errors with `complete: false`, never counted candidates. The request file must live outside the vault.

## `inbox/handoff@1`

Put the common `purpose` and `purpose_origin` in the selection request once. Missing purpose stays empty with unknown origin; an already stated purpose uses reused origin. The record carries `schema`, `consumer: ingest`, `scope`, `selected_paths`, `selected_preimages`, `lanes`, `purpose`, `purpose_origin`, `source_groups`, `unclassified_paths` and `mutations_performed: []`. Emitting it is not an ingest.

`source_groups` joins only selected source records that share identity or locator, never titles. Each member retains its candidate path, zero-based `candidate_index` and complete structured source, including original text, per-source fidelity and omissions. Grouping is not permission to discard different excerpts. `unclassified_paths` lists selected notes without the `capture/candidate@1` schema; ingest reads those as `file` inputs rather than a fabricated source record.

Feed ingest once with the handoff's members and common purpose. Each member is one source: `candidate` members are read from their structured source record, `unclassified_paths` as plain files. Ingest writes the Raw, checks its verbatim original content, then removes the candidate as the second half of the move.
