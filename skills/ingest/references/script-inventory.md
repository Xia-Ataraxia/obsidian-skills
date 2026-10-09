# Ingest script inventory and Phase 2 decisions

Measurements count UTF-8 source bytes and physical `splitlines()` lines, not generated files or tests. Baseline was recorded by Python AST enumeration before deletion. Core runtime module scope is the import graph of `ingest.py`; independent acquisition helpers are shown separately. Inbox runtime is Phase 6 and is unchanged.

## Baseline → final

| Scope/file | Baseline bytes | Baseline lines | Baseline modules | Final bytes | Final lines | Final modules | Decision/reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ingest.py | 14245 | 264 | 1 | 58580 | 944 | 1 | Keep/rewrite; compact request/session effects, Book spans, safe writes, opt-in `--git` wiring, reviewed `update_path` members, template-rendered Entities and Concept/atom notes, exact link resolution, stat-verified mothership deeplinks, template-rendered Book Index/chapter scaffolds and guarded chapter+Index promotion. |
| request.py | 8804 | 215 | 1 | 0 | 0 | 0 | Merge validation into source; remove CLI approval protocol and dataclass layers. |
| source.py | 6457 | 152 | 1 | 20024 | 409 | 1 | Keep/merge input and YAML helpers; fix declared extraction/conversion; update-member and promotion parsing, Book scaffold keys and outside-vault digest-bound files. |
| storage.py | 10431 | 234 | 1 | 0 | 0 | 0 | Delete Plan/Change objects; merge safety into plain session records/functions. |
| batch.py | 8458 | 152 | 1 | 0 | 0 | 0 | Delete handoff mapping protocol; members preflight in main. |
| vaultgit.py (Phase 3-b) | 0 | 0 | 0 | 8030 | 174 | 1 | New; one-ingest-one-commit git transaction, loaded only with `--git`; literal pathspecs and restart refusal of staged owned entries that differ from the postimage. |
| **Core runtime** | **48395** | **1017** | **5** | **86634** | **1527** | **3** | Phase 2 ended at 35848 B / 658 lines / 2 modules; Phase 3-b adds the opt-in git module; the update-member, Entity-template, notes, real-attachment, identity-drop, link-resolution and mothership repairs, then the Book scaffold/promotion rework and the Concept/atom template renderer, push the core above its baseline. |
| fetch_yes24.py | 4285 | 122 | 1 | 4285 | 122 | 1 | Keep unchanged; Book B-1 metadata/TOC acquisition. |
| fetch_aladin_toc.py | 1141 | 41 | 1 | 1141 | 41 | 1 | Keep unchanged; Book B-1 chapter URL acquisition. |
| web-source-validate.py | 7627 | 232 | 1 | 7627 | 232 | 1 | Keep unchanged; article/video extraction verification still called by skill. |
| youtube-transcript-extract.py | 14741 | 399 | 1 | 14741 | 399 | 1 | Keep unchanged; transcript acquisition still called by skill. |
| **All ingest scripts** | **76189** | **1811** | **9** | **114428** | **2321** | **7** | Independent tools are not core import modules. Final columns re-measured 2026-10-08 after the Concept/atom template renderer fix. |

The approximate 20KB/450-line target is exceeded deliberately: explicit span-based Book promotion, body-prefix/metadata safety, recorded capture extents for inbox 5-C, retained candidate input translation, a strict stdlib frontmatter reader/emitter, persistent temporary session serialization and aggregate readback cannot be deleted merely to meet a size metric. The git transaction lives only in the opt-in `vaultgit.py`; no long-lived registry, compatibility dispatcher or shared runtime was added. The runtime is standard-library only; PyYAML is used by tests only to cross-check emitted frontmatter.

## Complete baseline symbol decisions

Every top-level function/class and class-owned method is included below; grouped items share the stated decision/reason. External library calls are not runtime ownership edges.

| File | Items | Decision and reason |
| --- | --- | --- |
| request.py | Refused | Merge into source; one local refusal type. |
| request.py | string, strings, mapping, records | Merge into parse's explicit validation; remove repetitive wrappers. |
| request.py | public_locator, source_identity | Keep/merge into source public_locator/identity; credentials, escaping locators and malformed digest identities still refuse. |
| request.py | Analysis, Chapter, Request | Delete dataclasses; ordinary validated request records suffice. |
| request.py | line_range, parse | Merge into source.parse; preserve inclusive range/date/purpose/unknown-key validation, add extraction/conversion and author/referenced. |
| source.py | HTMLText, __init__, handle_starttag, handle_endtag, handle_data | Keep; readable HTML, hidden script/style suppression and attachment retention. |
| source.py | Source | Delete dataclass; acquisition returns a small record. |
| source.py | candidate | Keep/rewrite; actual structured candidate member, explicit mixed index, real provenance, body-notes translation of legacy capture evidence. |
| source.py | read_source | Keep/fix; file/text consume declared extraction and conversion, default only when unspecified. Preserve selected UTF-8 bytes. |
| source.py | read_file, fetch | Keep; exact file path, HTTP content-type/redirect locator checks. |
| storage.py | digest, target, metadata, note | Merge into source; stdlib top-level reader (plain/quoted scalars, inline/block lists, duplicate-key refusal, refuse-on-need for unparseable values) replaces the flat JSON-only reader; emitter writes JSON-quoted scalars and block lists for new notes only. |
| storage.py | link | Merge into ingest; reject unrepresentable wikilinks. |
| storage.py | Change, Change.receipt | Delete class; receipt reads plain temporary records. |
| storage.py | Plan, Plan.__init__, Plan.read, Plan.new_note, Plan.add | Delete object; stage/build implement staged view, exclusive create and prefix-preserving append with whole-byte preimages. |
| storage.py | Plan.receipt protocol, Plan.authorize, Plan.bind_compilation | Delete approval/binding protocol; no generated compiled association or approval fields in notes. |
| storage.py | Plan.apply | Merge into apply; preserve input/output drift checks, exclusive create, atomic update replacement, readback and partial-write reporting. |
| ingest.py | same_source | Keep/rewrite; identity → URL → locator, never title. Explicit new capture path is not redirected into prior evidence. |
| ingest.py | checked_quote | Keep; obtained-content grounding and location required, manifest cannot support claims. |
| ingest.py | build | Keep/rewrite; Raw/core fields, notes provenance, selected spans, Concept/Entity/Persona outputs, Paper hub captures and Book scaffold/promotion. |
| ingest.py | main | Keep/rewrite; request/member sessions and exact apply-state seam; no git. |
| ingest.py (post-baseline) | identity_applies, link_list, exact_entry, exact_file, resolve_links, mothership_root, verify_mothership | Add 2026-10-08 repair; empty legacy identity drop on non-identity-bearing notes only, exact-case nonsymlink link resolution against existing or same-session paths with ambiguity refusal, and allow-listed `obsidian://open` deeplinks stat-verified under an explicit read-only root. |
| ingest.py (post-baseline) | stub_placeholder, book_chapters, fill, template_parts, reading_paths_state, render_book_index, render_chapter, resolve_note, names, section, index_progress | Add 2026-10-08 Book rework; template-rendered Index/chapter scaffolds from obtained `book_title`, verbatim `reading_paths`, optional `toc_description` and explicit locators only, and guarded promotion that checks the placeholder span, resolves navigation and edits exactly one Index checkbox and Progress row. |
| source.py (post-baseline) | book_keys, parse_promotion | Add 2026-10-08 Book rework; scaffold-only key validation and the exact promotion key set. |
| batch.py | selected_members | Delete protocol; explicit member JSON selects inputs. Phase 6 must migrate Inbox's existing handoff shape; do not pretend it is consumed. |
| batch.py | build_batch | Merge into main member loop; common purpose once, independent acquisition, staged aggregate target view and whole-batch preflight. |
| fetch_yes24.py | fetch, _html_to_md, _meta, _textarea, _authors, _pub_date, _isbn, _categories | Keep unchanged; concrete Book metadata/TOC extraction, synthetic port tests retained. |
| fetch_aladin_toc.py | fetch_toc_urls | Keep unchanged; concrete Book chapter URLs. |
| web-source-validate.py | strip_frontmatter, extract_content_section, count_words, find_markers, _youtube_video_id, source_identity, validate, main | Keep unchanged; bounded extraction and source validation. |
| youtube-transcript-extract.py | ExtractionResult, fail, parse_video_id, word_count, extract_transcript, transcript_status, transcript_is_usable, transcript_diagnostic, parse_frontmatter, run_defuddle, fetch_gateway, fetch_gateway.fetch (nested HTTP worker), fetch_oembed, fetch_ytdlp, choose_metadata, main | Keep unchanged; transcript recovery/metadata/failure diagnostics. |

## Call graph before and after

Baseline core: `main → parse → Request/Analysis/Chapter`; `main → build_batch → selected_members → build`; `build → Plan.read/new_note/add/bind_compilation, candidate/read_source, same_source, checked_quote, metadata/digest/link/target`; `candidate → read_file/metadata/public_locator/source_identity`; `read_source → read_file/fetch/HTMLText`; `main → Plan.apply → authorize → Change.receipt/digest/metadata`, then target/exclusive-create/update/readback. Source imported request+storage, storage imported request, batch imported all three core layers.

Final core: `main → plan → parse/parse_update`; `parse → public_locator/identity`; `plan → build → candidate/read_source → read_file/fetch/HTMLText`; `plan → update → outside_file/metadata/original_spans/compile_analyses/stage`; `build/update → compile_analyses → checked_quote/render_entity/wikilink_target/verify_mothership/stage`; `update → identity_applies/link_list/verify_mothership`; `build → link_list/verify_mothership` for final Raw fields; `plan → mothership_root` (with `--mothership-root`) and `plan → resolve_links → exact_file → exact_entry`; `verify_mothership → exact_file` (lstat/listdir only); `build → outside_file` for text-input attachments; `build → core/note/metadata/same_source/checked_quote/link/stage/patch_fields`; `build → book_chapters → public_locator` and `build → render_book_index/render_chapter → template_parts/fill/note/reading_paths_state`, with `render_chapter → stub_placeholder`; `update → promote → metadata/wikilink_target/stub_placeholder/original_spans/outside_file/patch_fields/index_progress/compile_analyses/stage`; `index_progress → target/outside_file/metadata/body_offset/names/section/resolve_note/stage`; `parse → book_keys` and `parse_update → parse_promotion → public_locator`; `main → state_encode/state_decode/receipt/apply`; `apply → target/digest/receipt`, then exclusive-create/update/readback and capture extent/postimage checks; ingest never unlinks (Inbox deletion is `inbox delete`). Only ingest imports source. Temporary state holds preimages/postimages and writer-known extents outside notes.

Independent helper edges: Yes24 `fetch → _authors/_categories/_html_to_md/_isbn/_meta/_pub_date/_textarea`; Aladin `fetch_toc_urls → HTTP/regex`; validator `main → validate → extract_content_section/count_words/find_markers/source_identity → _youtube_video_id`; YouTube `main → parse_video_id/run_defuddle/fetch_gateway/choose_metadata/transcript_diagnostic`, `choose_metadata → parse_frontmatter/fetch_oembed/fetch_ytdlp`, diagnostic/status/word-count → extract_transcript. Their imports and implementations are unchanged.

## Test ports before deletion

`tests/test_ingest.py` was replaced with behavior-focused tests before deleting request/storage/batch. Its ports protect direct source bytes, HTML attachment rules, declared conversion, unknown purpose, selected line omission reporting, structured candidate input/digest identity, explicit distinct-source refusal, source-grounded analysis, Persona append/maturity, unknown YAML bytes, target symlink/collision safety, whole-session drift refusal, original body prefix (CRLF/no final newline/heading decoys), exclusive create, partial-result readback, and capture extent rechecks without input deletion. Tests no longer assert removed approval hashes, digest frontmatter, compiled bindings, paper-hub type, six-methodology metadata or fake chapter-state metadata. Those old representation assertions are intentionally obsolete; methodology/completeness judgements belong to skill analysis, not generated CLI fields.

Repeated capture preserves original body bytes by append-prefix rules; no old Original Content extent is guessed from headings or a digest field. New capture offsets come from the writer's prefix bytes. The previous implicit catalog redirect/compiled-target binding was removed: better extraction must create a new explicit Raw, and caller-resolved destinations are reviewed directly.

The final integration test in `tests/test_inbox.py` was ported, with leader approval, from `--handoff`+mapping+approval to members JSON. It still runs real capture→Inbox selection→ingest, verifies selected excerpts and resulting compact Raw, retained candidate bytes and untouched unselected RSS. All other Inbox tests and Inbox runtime are unchanged. **Phase 6 dependency:** Inbox still emits `inbox/handoff@1`; it must emit member JSON or drop that handoff file. The CLI does not read it.

## Synthetic canary evidence

All evidence is from owned temporary vaults; no live vault was written.

- A: two Raw captures plus grounded Concept and Entity, one common purpose, declared defuddle/markitdown provenance in Ingest Notes, exact selected extents and all readbacks.
- B: excerpt/OCR followed by a new full/marker Raw sharing identity; old Raw bytes unchanged; new Raw references earlier capture; Paper hub lists both and preserves unknown YAML spelling. No role-placement path is invented by runtime.
- Book: preface index with TOC/Progress, two stubs, then exact-offset promotion of one chapter; only placeholder/status/date_modified and designated progress checkbox span change; five navigation fields and unread sibling retained.
- Adversarial: input/output drift, duplicate YAML keys, credential/escaping locators, mixed candidate selection, CRLF/no-final-newline, heading decoys, symlinks, unsupported metadata, partial I/O and post-write corruption before original deletion.

Focused verification (Phase 2 historical receipt; later runtime changes are verified per CHANGELOG entry):

```text
python3 -m pytest tests/test_ingest.py tests/test_ingest_metadata_contract_ports.py tests/test_ingest_web_source_validate_ports.py tests/test_ingest_youtube_transcript_extract_ports.py -q
50 passed, 8 subtests passed
python3 -m pytest tests/test_ingest_git.py -q
22 passed
python3 -m pytest tests/test_inbox.py -q
24 passed
```

The `22 passed` git receipt predates later additions. `tests/test_ingest_git.py` now defines 28 test methods and `tests/test_ingest.py` 31, a static count of `def test_` lines from 2026-10-08, not a pass receipt. No current per-file pass count is recorded here.

## Live-vault preflight canaries (2026-10-08)

Preflight only against the destination vault: no `--apply`, `--apply-state` or `--git`; requests, session states and outputs stay outside the vault, and vault `git status`/HEAD and the guarded hashes were identical before and after. A planned result proves byte checks, not approval.

- A (secondary Raw with two originals): two new original Raws, a reviewed secondary Raw postimage preserving its Original Content span by offsets and digest, three new Entities grounded in that preserved span, and a reviewed Concept postimage. The first combined preflight was **refused** (`update changes source identity field: source_identity`): the Concept preimage carried a legacy empty `source_identity`. After the identity repair, the unchanged request (same postimages and digests) re-ran preflight-only and **plans** five creates and two updates, with every Raw `author`/`referenced` and postimage `author`/`referenced`/`source`/`related` target resolved to an existing or same-session path; vault HEAD, `git status`, both guarded preimages, the proposal files and the read-only mothership People note hashed identically before and after. Planned is byte evidence only: the Concept restructure still needs the owner's reviewed diff and nothing was applied or accepted.
- B (full-text paper capture): `coverage: full` with no omissions, caller notes, the real PDF stored through `attachment_source`/`attachment_sha256`, and two co-author Entities with descriptions and mutual `related` links. It plans four creates; the earlier excerpt Raw and the paper-analysis folder stay untouched. Linking the existing hub (B-5) awaits its own exact update approval.

Link-planning defects found earlier are repaired: Raw `author`/`referenced` (including `note_fields` overrides) and update postimage `author`/`referenced`/`source`/`related` now resolve with the same exact rules as Entity and new Concept/atom `related`, and unresolved or ambiguous targets refuse. The Entity template carries an optional `mothership` key, filled only with stat-verified deeplinks and omitted otherwise. New Concept/atom notes now render from the package Concept template (template keys in order, required one-line `confidence`, optional `description`/`related`, `explored: false`); that template has no `mothership` key, so Concept analyses still refuse `mothership`.

Removed-field search (`approval_|fidelity|source_content_|compiled_target|selected_range`) over scripts finds **only** the read-only legacy `capture/candidate@1` input keys in `source.candidate`; no emitted Raw fields or executable approval/digest/binding protocol remains. This narrow exception is required by the approved inventory: capture's input schema is not Raw's output schema. Literal keys are kept visible rather than obfuscated to manufacture a zero-match search. A stricter search excluding `fidelity` reports no matches.
