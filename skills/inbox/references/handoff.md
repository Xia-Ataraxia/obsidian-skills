# Selection and handoff

Use list or preview to obtain each candidate's path and SHA-256. The selection JSON supplies `selected_paths` and `selected_preimages` mapping each selected vault-relative path to `sha256:<digest>`. No selection is the empty batch, not the entire Inbox: the helper refuses it. Paths outside `--scope`, stale bytes and symlinks are refused.

Put the common `purpose` and `purpose_origin` in this request once. Missing purpose stays empty with unknown origin; an already stated purpose uses reused origin. Do not put purpose into each item. The `inbox/handoff@1` result identifies consumer ingest and status ready-for-ingest, not ingested.

`source_groups` joins only selected source records that share identity or locator. Each member retains its candidate path, zero-based `candidate_index` and complete structured source, including original text, per-source fidelity and omissions. Grouping is not permission to discard different excerpts or overwrite existing knowledge. `unclassified_paths` lists selected notes that do not use the capture schema; those require the actual ingest input reader rather than a fabricated source record.

The capture schema is `capture/candidate@1`. Its YAML-compatible JSON frontmatter contains `capture_sources`. This reader uses those structured original strings rather than splitting untrusted text at apparent Markdown headings. Generic Markdown notes can be previewed, but their provenance and fidelity stay unknown unless actually known.

Pass this selection and common purpose to the actual `ingest` skill once. Inspect its installed/current `SKILL.md` and scripts before choosing an executable interface. A tool gap or incompatible candidate reader is unavailable; do not use an always-success evaluator or substitute a mock to claim the end-to-end route.

The actual batch CLI is `ingest.py --vault <base> --handoff <actual-handoff.json> --request <aggregate-mapping.json> [--apply]`. Read ingest's current batch reference by skill identity before using it. Pass the unchanged emitted handoff, not a rebuilt list or a single-source request. Planning is read-only; application requires concrete output approval.

The current aggregate mapping has exactly `members` and `approval`. Each member is `{candidate_path, candidate_index, request}` and must cover one selected member exactly once. Its request supplies actual Raw/Wiki/analysis destinations and optional destination metadata. Source facts, purpose and approval are not repeated or overridden in member requests. The common purpose remains in the handoff once; aggregate approval names the final combined output effects, paths and preimages.

Map proven same-source excerpts to the same Raw/Wiki targets, retaining every member and its selected span. Do not discard a member because its identity or quotation matches another. The peer verifies the selected file digests and exact structured member records, merges planned output effects and returns `ingest/batch-result@1` with member results and actual readbacks. Group labels do not authorize merging explicitly conflicting source identities.

The helper still only prepares the handoff. Execute the peer batch once, never a per-member-purpose loop. Inspect refused or partial output honestly; a missing identity format or mapping capability is not made compatible by rewriting identities or falling back to single-source calls.

For retained candidate reprocessing, inspect ingest's real receipts and source index. Reuse existing output for proven same source; a title match alone is not proof. New excerpts from the same source can supply additional evidence and require an approved update, not a second independent source page. Inbox does not invent a parallel persistent result registry.

For deletion, construct a separate request after the owner's exact deletion decision. It has `approval_effect: ["delete"]`, approved or partially-approved state, a nonempty approval_basis, approval_scope equal to the selected paths and approval_preimage equal to selected_preimages. Approval for create/ingest/update never permits this command. Preflight reads every selected file before any deletion; competing edits are checked again before each unlink. A process interruption may leave a subset deleted; read back the actual scope before retrying and request approval against the remaining current bytes.
