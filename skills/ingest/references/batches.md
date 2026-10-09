# Selected batches

Use the same direct CLI with one JSON request:

```json
{
  "purpose": "Understand public evidence preservation",
  "members": [
    {
      "source_input": "candidate",
      "source_kind": "article",
      "locator": "Inbox/public-candidate.md",
      "obtained_at": "2026-10-08",
      "candidate_index": 0,
      "raw_path": "Raw/public-article.md"
    }
  ]
}
```

```bash
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --state "$SESSION"
python3 scripts/ingest.py --vault "$VAULT" --apply-state "$SESSION"
```

One common nonempty purpose is applied once, with `purpose_origin: reused` for each member. Members otherwise use the [direct interface](interface.md). All members preflight before the first mutation. Exact input bytes and all aggregate target preimages are held in session state outside notes. Later members read staged Raw/Wiki output, so selected excerpts can share an explicit destination without losing earlier evidence. Different source identities cannot share a Raw. New full-text captures must name a new Raw path rather than reuse the old excerpt destination.

The final `ingest/result@2` contains one merged change per path and one result per member. Readback checks verify final postimages. A refused preflight writes nothing; a partial I/O failure reports already written outputs. Quiesce competing writers, inspect partial output and preflight a new reviewed session against current bytes; do not blindly replay a stale session or replace human changes. The Phase 3 caller wraps the aggregate writes in one git transaction, not one commit per member.

## Inbox boundary

The old `--handoff` mapping and CLI approval protocol are removed. `inbox.py` emits `inbox/handoff@1`, a prepared selection, **not** a request understood by the ingest CLI; this boundary is kept as is (see the independently selected inbox skill, references/handoff.md). The caller maps exactly the selected candidates/member indices into the members JSON above, one member per handoff member, preserving the handoff's purpose and checking its selected input preimages before preflight. Do not silently consume unselected RSS or infer destinations from a group title.

The regression replay uses the real capture→inbox selection, maps selected members explicitly, and verifies retained candidate/unselected bytes.

## Category batches

Re-ingest of existing Raw is proven per category by one representative pilot, nine in all (the categories listed in [re-ingest](reingest.md)), each preflighted, approved and published as its own single `--git` commit with disk/HEAD/origin readback. A published pilot proves the procedure for its category; it authorizes no further notes. A category batch holds at most ten members of one Raw category and needs its own exact-path approval of its reviewed postimages; approval of one batch never carries to the next batch or to another category. Batches use the same restartable [re-ingest](reingest.md) manifest.

Ingest never deletes its input. Deleting an Inbox original is a separate owner decision executed only by `inbox delete`, which applies 5-C against this run's session state. This does not authorize unrelated original cleanup or mothership operations.
