# Direct ingest interface

Run from the package or supply its script path explicitly:

```bash
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST"
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --apply
```

Plan is read-only but obtains the selected source.
Exit 0 returns status planned or applied, the exact paths, source reuse, fidelity, omissions, range and changes.
Apply includes per-file readback digests and evidence_level materialized.
Exit 1 is refusal/acquisition/I/O failure, including completed writes when a partial apply fails; usage exits 2.
No hidden registry, dispatcher, environment path or runtime effect exists.
The caller must quiesce other writers during an approved update; a preimage check detects observed drift, not an unobserved race after that check.

The CLI imports package-local modules, with paths relative to the package root: `scripts/request.py` parses and validates requests; `scripts/source.py` reads selected sources and retains conversion, range and candidate provenance; `scripts/storage.py` plans exact-path changes, checks approval and preimages, and applies writes with readback; `scripts/batch.py` binds handoff members to current selected files and builds one batch plan through the ingest builder.
These are internal imports of `scripts/ingest.py`, not separate user tasks, aliases or a shared runtime.

## Request

Use a JSON object with these fields:

| Field | Contract |
| --- | --- |
| `source_input` | url, file, text or candidate |
| `source_kind` | article, video, repository, mail, conversation, book, paper, other |
| `locator` | Public canonical URL without credentials/query, a file/candidate path relative to the declared vault, or a caller-supplied stable text identifier |
| `identity` | Known DOI, full citekey, commit/message identifier or content digest; empty when unknown. Exactly sha256: plus 64 lowercase hex digits is accepted only as identity, never as an acquisition locator. DOI URLs normalize to lowercase doi identifiers |
| `text` | Obtained direct text when source_input is text |
| `obtained_at` | Actual ISO date/date-time supplied by the caller |
| `purpose`, `purpose_origin` | Owner purpose with stated/reused origin; empty/unknown when absent |
| `fidelity`, `omissions` | Actual full/partial/excerpt/manifest-only/mixed and known missing ranges. Default partial is not a completeness claim |
| `selection` | Optional inclusive obtained-text line range `[first,last]`; outside lines become omissions |
| `raw_path` | Exact new Raw artifact or known same-source path |
| `attachment_path` | Exact original attachment destination; required for HTML conversion |
| `catalog` | Bounded exact existing Raw paths for source identity checks; incomplete scope is not global absence proof |
| `wiki_path` | Optional policy-resolved compiled page or Paper hub |
| `analyses` | Supplied agent synthesis entries `{path,body,quote,anchor,role}`; role atom or concept. Quote must occur in obtained evidence; anchor is caller-checked original location |
| `chapters` | Book TOC entries `{title,lines}`; lines null for unread/unobtained chapters, otherwise inclusive range in the obtained text |
| `methodology`, `citation` | Paper methodology type and full supplied bibliography |
| `optional_links` | Actually resolved public DOI/Zotero/BBT identifiers; no account identifiers or guessed PDF paths |
| `targets` | Only designated existing RQ/manuscript/Entity/Guide/Map/MOC paths; links only, never edits or creates |
| `persona_path`, `stance`, `stance_quote`, `stance_anchor` | Exact existing type persona note and attributed citation to append |
| `candidate_index` | Explicit zero-based capture source member for a mixed candidate; single member needs no index |
| `note_fields` | Per-new-note exact path mapping of destination-required type/tags/date_created/date_modified/user_intent_interview/title. Supply actual policy values; shared source/approval/provenance fields cannot be overridden |
| `approval` | Concrete owner statement encoded as the contract's approval fields |

Unknown keys are refused.
The CLI's source contract is not a replacement for destination core metadata: supply the actual note_fields for a policy that requires them.
The script emits flat frontmatter with JSON values (valid YAML), preserving newlines and Unicode in source text.
It reads that encoding and simple native scalar fields only; richer existing YAML needs the destination's real adapter, not a guessed parser.
Unknown existing keys and original/human body bytes are preserved; there is no generic generated-note replacement or metadata normalization.
When a previously Raw-only source is first compiled, the known generated compiled_target field is bound under exact update approval.
Further attempts to compile that source into another Wiki target are refused; the first binding is not silently replaced.

## Approval

The caller records approved or partially-approved approval_state, nonempty approval_basis, exact approval_scope, approval_effect create/update, and per-output approval_preimage absent or sha256 digest.
For every existing update, approval_diff[path] must equal the plan's approval_diff_sha256.
For additive appends this equals append_sha256. The narrow Raw compiled_target binding returns update_sha256 (the exact full postimage hash), plus proposed_diff showing that scalar transition and proposed_append for any additional selected evidence.
Approve that binding as an update with its actual preimage, never as a create-only side effect.
The plan returns these concrete changes for review.
No create approval authorizes update, delete, sending, or a newly appeared target.
Preflight resolves every proposed effect before the first write.
A partial I/O result preserves finished output for inspection; resume with current preimages and approval, never reset or replace notes.

## Peer handoff

The actual capture helper writes capture/candidate@1 with capture_sources containing original_content and each source's contract fields.
Candidate ingest reads the selected structured member, not visible headings that source text can forge.
It inherits that member's locator, identity, input, extraction, date, fidelity, conversions and omissions.
An inbox/handoff@1 is a prepared selection, not an ingest request: resolve each selected member into this request with the batch purpose and its exact destination approval.
Use `--handoff H.json --request M.json` to execute that selection once through the actual batch boundary; read [batch mappings](batches.md).
Multiple excerpts of the same source share a Raw/hub identity; approved evidence appends retain each selected range.
Retained candidates remain untouched.
Do not pass the entire handoff as a single-source `--request`, omit the output mapping/approval, or claim a prepared handoff was executed.
