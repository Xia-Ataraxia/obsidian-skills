# Selected Inbox batches

```bash
python3 scripts/ingest.py --vault "$VAULT" --handoff "$HANDOFF" --request "$MAPPING"
python3 scripts/ingest.py --vault "$VAULT" --handoff "$HANDOFF" --request "$MAPPING" --apply
```

This consumes the actual `inbox/handoff@1` produced by Inbox.
It is a package-local input boundary, not a dispatcher or shared runtime.
The single-source `--request` interface remains available without `--handoff`.

## Inputs

The handoff supplies its existing schema, ready-for-ingest status, consumer ingest, Inbox scope, selected_paths, selected_preimages, one purpose/purpose_origin, source_groups, unclassified_paths and empty mutations_performed.
Each captured member identifies candidate_path, zero-based candidate_index and the complete source record.
The helper verifies the selected files' current SHA256, scope, member indices and exact structured source values.
It refuses missing, duplicate, altered, unselected or outside-scope members.
Group labels are not identity or permission: explicit differing source identities are kept distinct even if Inbox grouped their common locator.

The mapping JSON has exactly two keys:

- `members`: a list of `{candidate_path, candidate_index, request}`.
- `approval`: one concrete owner approval record for the final batch effects.

Every selected member needs exactly one mapping.
The captured member's `request` supplies the existing single-source output fields: raw_path, optional wiki_path, analyses, attachment_path, chapters, methodology, citation, optional_links, targets, Persona citation fields, bounded catalog and destination note_fields.
Do not repeat or override purpose, approval, source_input, locator, candidate_index, source_kind, identity, obtained_at, text or selection there.
Those source facts are read from the actual digest-bound capture member.

For a selected unclassified file, use candidate_index null.
Its request must explicitly provide the real source_kind and obtained_at required by the direct file reader, plus any actually known identity, fidelity, omissions or selected range and its output fields.
The input is that selected UTF-8 file, with locator resolved against --vault.
No source record or provenance is invented for it.

The common handoff purpose is used once at invocation and recorded as reused in every produced note when known.
Unknown stays unknown and permits preservation only.
If supplied, destination user_intent_interview must equal the common purpose.
Nothing prompts for a second purpose.

## Shared sources and output approval

Resolve targets explicitly before applying.
Map proven same-source excerpts to the same Raw/Wiki identity, or name the existing identity in the bounded catalog.
Earlier Raw outputs from this exact batch extend that catalog; no whole-vault scan is added.
Distinct excerpts and selected spans are appended as separate evidence even when their quoted text happens to match.
An incompatible second Wiki target or conflicting output identity is refused, not renamed or silently duplicated.
Conflicting known identities require separate outputs.

Planning uses an in-memory output view so later members can reuse earlier planned notes without writing temporary destination fixtures.
The resulting `changes` list contains the final effect for each target, not conflicting intermediate create/update requests.
New outputs require create approval and absent preimages.
Existing notes require update approval, their actual preimage and approval_diff[path] equal to the final planned approval_diff_sha256, including all selected contributions.
For ordinary appends this is append_sha256; first compilation of a Raw-only source also binds its known compiled_target field and uses update_sha256 plus the explicit proposed_diff.
Review the returned proposed_diff/proposed_append before approving either mutation.
Source and candidate eligibility is never output approval.

All members, required metadata, citations, destinations and aggregate permissions are preflighted before the first write.
Selected input digests and all output preimages are checked again immediately before application.
Selected candidates are retained unchanged, even when an output mapping accidentally names one.
No unselected source is consumed or compiled.

## Result and recovery

Exit 0 returns `ingest/batch-result@1`, planned or applied, the common purpose, selected paths/preimages, one result per member and the merged changes.
Applied results include the same exact file readback digests as single-source ingestion.
Exit 1 returns `ingest/error@1`; usage exits 2.
A refused preflight writes nothing.

This is not a crash-atomic transaction.
An I/O failure or interruption after application starts can leave completed files; the existing apply error records completed writes when available.
Inspect the actual target, preserve completed evidence and resume only with current preimages and exact approval.
Quiesce competing source and output writers while applying.
Do not convert a plan, grouping result, partial apply or exit code into a full knowledge or installed-runtime claim.
