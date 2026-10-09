# Changelog

## Unreleased — Inbox lanes and 5-C deletion

- Enumerate `00. Inbox/**` with `{NN Agent}` lanes from a CLI-supplied vault and scope; drop queue status (candidate `status`, `count`/`status` commands, handoff `status`). Location is the processing state.
- `inbox/handoff@1` adds `lanes` and documents the actual ingest `members` + `purpose` request and session state.
- `delete` is now the only Inbox-original unlink route: separate exact-path delete approval plus predicate 5-C against ingest's session state (fresh original bytes, Raw Original Content span, expected Raw postimage), preflighted and rechecked before each unlink. No whole-file hash equality, no mothership-backup predicate. Ingest's own `delete_input` path was removed. In git vaults the deletion is committed by `ingest.py --record-deletions` (packages stay independent; inbox never runs git).

## 0.3.0 — 2026-10-07

- 2026-10-07 — Collection release `0.3.0`: `metadata.version` follows the collection release identity under the renamed plugin identity `secondbrain-skills@secondbrain-skills`. No behavior, reference or script change in this package.
## 0.2.2 — 2026-10-07

- 2026-10-07 — Collection release `0.2.2`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.
## 0.2.1 — 2026-10-07

- 2026-10-07 — Collection release `0.2.1`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 - 2026-10-03

- Added recursive candidate observation and digest-bound explicit selection.
- Added one common-purpose ingest handoff, same-source groups retaining selected spans, and separately approved deletion.
- Documented the actual peer batch CLI and aggregate mapping without per-member purpose dispatch.
