# Selection, handoff and deletion

## Location is the state

Candidates live under the destination's Inbox scope, passed as `--scope` (for example `00. Inbox`). Agent lanes are the first-level `{NN Agent}` folders such as `01 Chat` or `04 GJC`; `list` reports each candidate's `lane` (`null` outside a lane). There is no queue `status` field in candidates, handoffs or results: a note in the Inbox is unprocessed, and leaves the Inbox only through an approved `delete` after ingest preserved it in Raw. A capture-side `status` property is ignored.

## Selection

Use `list` or `preview` to obtain each candidate's path and `sha256:` digest. The selection JSON supplies `selected_paths` and `selected_preimages` (path → `sha256:<digest>`). No selection is the empty batch, not the entire Inbox: the helper refuses it. Paths outside `--scope`, stale bytes, traversal and symlinks are refused. Malformed notes (unterminated frontmatter, duplicate keys, non-UTF-8, contradictory fidelity) are listing errors with `complete: false`, never counted candidates. Request and state files must live outside the vault.

## `inbox/handoff@1`

Put the common `purpose` and `purpose_origin` in the selection request once. Missing purpose stays empty with unknown origin; an already stated purpose uses reused origin. The record carries `schema`, `consumer: ingest`, `scope`, `selected_paths`, `selected_preimages`, `lanes`, `purpose`, `purpose_origin`, `source_groups`, `unclassified_paths` and `mutations_performed: []`. Emitting it is not an ingest.

`source_groups` joins only selected source records that share identity or locator, never titles. Each member retains its candidate path, zero-based `candidate_index` and complete structured source, including original text, per-source fidelity and omissions. Grouping is not permission to discard different excerpts. `unclassified_paths` lists selected notes without the `capture/candidate@1` schema; ingest reads those as `file` inputs rather than a fabricated source record.

Feed ingest once: build its request with `members` (one per handoff member: `source_input: candidate` or `file`, `locator` = candidate path, `candidate_index`, destinations) and the common `purpose`, then run `ingest.py --vault <base> --request <request.json> --state <state.json>` to plan and `--apply-state <state.json>` (optionally `--git`) after output approval. Keep the state file: it records each Raw's Original Content extent and selected bytes. Ingest never deletes its input.

## Deletion (5-C)

`inbox.py delete --vault <base> --scope <inbox> --request <delete.json> --ingest-state <state.json>` is the only route that unlinks an Inbox original. The request is a separate owner decision: `approval_effect: ["delete"]` only, approved or partially-approved state, nonempty `approval_basis`, `approval_scope` = exact paths, `approval_preimage` = `sha256:` of the input bytes that ingest recorded. Create/ingest approval never permits it.

For every path, preflight and again immediately before each unlink:

1. the original's current bytes equal the approved Inbox input bytes recorded by ingest;
2. each Raw's `## Original Content` extent, read now, equals the selected captured bytes recorded at ingest preflight;
3. each Raw's current bytes equal the expected postimage recorded in the session (which itself must hold the selected span).

Whole-file Inbox/Raw hash equality and mothership-backup predicates do not apply. Any mismatch refuses and reports; nothing is deleted. An interruption may leave a reported subset deleted; read back the scope before retrying. In a git-tracked vault, record the unlinks afterwards with ingest (inbox stays independent and never runs git): save the `delete` JSON outside the vault and run `ingest.py --vault <base> --apply-state <state.json> --record-deletions <delete-result.json>`. It requires the ingest commit to be published, refuses ahead/unrelated-staged/locked repos, then checks origin/main still holds the approved input bytes and each path is absent locally, stages exactly those deletions, commits `inbox: delete {n} ingested originals` with `Ingest-Source: <ingest commit SHA>`, pushes and reads back origin/main. It records only originals that origin/main holds with the approved input bytes. An original that was never tracked (for example a git-ignored or not-yet-committed capture) leaves no tracked change after its unlink: `--record-deletions` refuses it as `remote preimage drift since write: <path>` and commits nothing. That refusal is not a 5-C failure; the unlink stays valid. Read back that the path is absent on disk and has no `git status` entry, and do not commit, stage or retry anything for it. Pause/drain affected Inbox writers (session hooks) or prove their destination switch before deleting.
