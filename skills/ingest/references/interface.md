# Direct ingest interface

The package-local CLI uses Python 3.8+ standard library only; runtime skills ship no Python dependency. It emits JSON-quoted YAML scalars and block lists, and reads existing frontmatter with a strict top-level reader (plain/quoted scalars, inline and block lists), refusing duplicate keys or any needed value it cannot parse. Without `--git` it performs no git operation; it never scans a whole vault or authorizes unrelated effects.

```bash
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --state "$SESSION"
python3 scripts/ingest.py --vault "$VAULT" --apply-state "$SESSION"
# For an already reviewed request, preflight and apply in one invocation:
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --apply
# Only when the request carries mothership deeplinks:
python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST" --mothership-root "$MOTHERSHIP" --state "$SESSION"
```

`SESSION` must be outside the vault; exclusive creation prevents replacing another session. It contains exact input and output preimages, proposed postimages, and explicit selected-content byte extents. Protect it as source-bearing temporary state. Review it before application; remove it after the caller completes verification. Do not edit a session to bypass preconditions. `--apply-state` applies those exact bytes without refetching. A plain request invocation only acquires and preflights. `--state` and `--apply` may be combined. `--apply-state` cannot be combined with request/state/apply/mothership-root.

Exit 0 returns `ingest/result@2`, `planned` or `applied`, member results, one final change per path and `mothership_verified` (a list of `{link,file,check}`; empty when no new deeplink was checked). Applied results include readback digests. Exit 1 returns `ingest/error@2`; a partial apply error includes completed writes, including a written path whose readback failed. Usage errors exit 2. A successful CLI result proves materialized byte checks, not semantic completeness or git publication.

## JSON request

Required: `source_input` (`text`, `file`, `url`, `candidate`), `source_kind` (`article`, `video`, `repository`, `mail`, `conversation`, `book`, `paper`, `other`), `locator`, `obtained_at` (actual ISO date/time), and `raw_path`.

| Field | Meaning |
| --- | --- |
| `identity` | Known DOI, citekey or stable identity; empty if unknown. DOI URLs normalize; lowercase 64-hex SHA256 is identity only, not a URL. |
| `text` | Obtained UTF-8 content for text input. File/candidate paths are vault-relative; URL locators are canonical HTTP(S) without credentials or queries. |
| `purpose`, `purpose_origin` | Nonempty owner purpose with `stated`/`reused`, or empty purpose with `unknown` (preservation only). |
| `extraction`, `conversion` | Actual extraction, default `direct-read` only when unspecified; ordered conversion records `{tool,from,to}`. Recorded in Ingest Notes; extraction also maps to `source_extraction`. |
| `coverage`, `omissions` | `full`, `partial` (default), `excerpt`, `manifest-only`; missing ranges/quality limits. Full conflicts with omissions and is refused. Narrative evidence in Ingest Notes, never CLI-only Raw properties. |
| `notes` | Nonempty text list of acquisition/conversion narrative, rendered as a `Notes:` list in `## Ingest Notes` for every coverage level (including `full`). Notes are not omissions and never relax the full/omissions refusal. |
| `selection` | Inclusive obtained-text line range `[first,last]`; preserves CRLF/final-newline bytes and records outside lines as omissions. |
| `author`, `referenced` | Plain `[[vault/relative/path]]` wikilink lists (no alias, heading or `.md`). New full-text Raw should reference the earlier excerpt Raw. Each target must resolve as described under [Link resolution](#link-resolution); `note_fields` overrides are checked the same way. |
| `attachment_path` | Exact original attachment output, required for HTML conversion. For `file`/`url` input it stores the obtained bytes and HTML extraction appends the actual HTMLParser conversion step. |
| `attachment_source`, `attachment_sha256` | Required together with `attachment_path` for `text`/`candidate` input, and refused otherwise: a canonical absolute path to the real original (for example the PDF) outside the vault, with no symlink or `..` component, and its `sha256:<64 hex>` digest. Those exact bytes become the attachment; converted text is never written as the original. |
| `note_fields` | Per-Raw-path §7 metadata map, allowing destination-specific common/provenance fields only. No status or CLI bookkeeping. A `mothership` list here is verified like an Entity's. |
| `analyses` | Grounded `{path,body,quote,anchor,role}`; quote must occur in obtained content. Role `concept`/`atom` creates a new Concept note with exactly the package [concept template](../templates/concept.md) frontmatter keys in template order: it requires an explicit one-line, evidence-grounded `confidence`, accepts an optional one-line `description` (empty when absent) and `related` (plain `[[path]]` list resolved as below), records `source` as the Raw link and starts `explored: false`; the body is the source-grounded analysis block only, and the template's synthesis sections are agent work the helper never fabricates. Role `entity` creates from the package [entity template](../templates/entity.md) and then requires a one-line `description` and accepts `related` (plain `[[path]]` list; each target must exist or be written by the same session) and `mothership` (verified deeplink list, see [Mothership deeplinks](#mothership-deeplinks)), with `explored: false`. Template frontmatter keys and slots must match the renderer exactly; the optional `mothership` key is omitted from the note when the list is empty. Existing targets only gain an appended analysis block and refuse `description`/`related`/`mothership`/`confidence`; their frontmatter, including `explored`, is left byte-identical (no automatic explored or confidence change), so edit them with an update member. Concept/atom analyses do not accept `mothership`, and Entity analyses do not accept `confidence`. |
| `wiki_path` | Optional exact compiled destination; paper hubs use `type: paper`, a source list and Captures narrative. Live Role Placement determines the path. |
| `targets` | Exact existing designated connection paths; existence is checked, no implicit creation. |
| `persona_path`, `stance`, `stance_quote`, `stance_anchor` | Append an attributed obtained quotation to an existing Persona; preserve maturity and earlier content. |
| `candidate_index` | Zero-based structured capture member; mandatory for mixed candidates. Candidate prose/headings are never parsed as source evidence. |
| `chapters` | Book scaffold entries `{path,title,part?,locator?,toc_description?}` (single-line title). Creates explicit `status: stub` notes with the five chapter navigation fields and the [chapter template](../templates/book-chapter.md)'s exact pending-fill placeholder as the whole Original Content section; `locator` records the direct chapter `source_locator` (and `source_url` for HTTP(S)) that a later promotion must match. `toc_description` is the nonempty one-line description the author/TOC source actually supplies; omit it otherwise (empty or `null` refuses). It becomes the chapter `description` and TOC Preview; without it `description` is `""` and TOC Preview states that no one-liner was supplied — the title is never relabelled as one. The index gains `- [ ] [[chapter]] — title` TOC lines (with ` — toc_description` appended when supplied) and `\| N \| [[chapter]] \| stub \| — \|` Progress Tracking rows, the [index template](../templates/book-index.md) shapes. Chapters are promoted only through an update member's `promotion` ([Book promotion](#book-promotion)); an ordinary request naming an existing stub is refused. |
| `book_title` | Required with `chapters`: the exact obtained one-line book title, rendered as the Index `# ` heading. Never derived from `raw_path`. |
| `reading_paths` | Optional with `chapters`: the author-provided Reading Paths as nonempty verbatim text (multiline kept byte-for-byte; a level-1/2 heading line refuses because it would split Index sections), or `null` when the caller reports them unavailable. Absent and `null` each render a distinct `Not recorded:` line; nothing is inferred. |

`book_title` and `reading_paths` are refused on any request that is not a `book` with a nonempty `chapters` list, and on a wrong type. A scaffold member result adds `book`: `{title, reading_paths: supplied/unavailable/not-supplied, chapters, chapter_locators, toc_descriptions_absent: [chapter paths]}`; the Index Ingest Notes record the same locator, TOC-description and Reading Paths counts. These prove what the request supplied, not that the title, TOC or paths were faithfully obtained from the book.

## Update member

A member (or single request) carrying `update_path` replaces one existing note with a reviewed postimage. Nothing is appended automatically; the postimage file is the only content source. Exact keys:

```json
{
  "update_path": "Raw/secondary.md",
  "preimage_sha256": "sha256:<64 hex of the whole current file>",
  "postimage_file": "/absolute/path/outside/vault/secondary-postimage.md",
  "postimage_sha256": "sha256:<64 hex of the postimage file>",
  "preserve": [{"block": "original_content", "start": 635, "end": 18413, "sha256": "sha256:<64 hex of preimage[start:end]>"}],
  "analyses": [],
  "obtained_at": "2026-10-08T13:40:00+09:00",
  "purpose": "…", "purpose_origin": "stated"
}
```

`analyses`, `obtained_at` (required with analyses) and `purpose`/`purpose_origin` (injected in a batch) are optional; other keys are refused. Checks, all before any write:

- `update_path` is a canonical vault-relative existing regular file without symlinks; its current bytes (or bytes staged earlier in the same session) must hash to `preimage_sha256`.
- `postimage_file` is a canonical absolute path outside the vault with no symlink or `..` component, a regular file hashing to `postimage_sha256`. Both images need bounded, strictly readable frontmatter. Any nonempty `source_identity`, `source_locator` or `source_url` in the preimage must keep its value. An empty (`""`/null) legacy value may only be removed — never changed — and only when neither image is identity-bearing: identity-bearing means `type` is `raw`/`article`/`video`/`paper`/`book`/`repo`/`mail`/`chat`, a `reference/*` tag, or a body `## Original Content` heading. Raw, Paper hub and book identity fields therefore stay strictly protected even when empty.
- Postimage `author`, `referenced`, `source` and `related` must be lists of plain wikilinks, and every target must resolve ([Link resolution](#link-resolution)). Postimage `mothership` entries absent from the preimage list must verify ([Mothership deeplinks](#mothership-deeplinks)); entries kept from the preimage are carried, not re-verified, and are not reported as verified.
- Each `preserve` entry names a nonempty byte span `[start,end)` of the preimage body. The digest alone never locates bytes: the offsets locate them, the digest proves them, and spans may not overlap. `block: "body"` keeps those bytes; they must occur exactly once in the postimage body.
- `block: "original_content"` additionally requires exactly one `## Original Content` heading line (plus one optional blank line) outside the span, ending exactly at `start`; headings quoted inside the checked span are ignored. Heading plus span must occur exactly once in the postimage body, which may not gain another such heading. At most one such entry is allowed.
- A preimage whose body has an `## Original Content` heading must preserve it with an `original_content` entry.
- Every Raw update keeps the complete current body bytes, including whitespace, CRLF and a body BOM, as an unchanged prefix of the postimage body, and may not add an `## Original Content` heading. Frontmatter may be replaced (for example a canonical type/tag migration) and notes appended, but a correctly hashed `body` or `original_content` span that ends early never licenses truncating, editing or reordering the rest of the existing body. A note is Raw for this rule when its body has an `## Original Content` heading, when `update_path` lies under `10. Raw Sources/` (typed or untyped legacy, with or without the heading), or when its preimage `type` is `raw`/`article`/`video`/`repo`/`mail`/`chat`.
- Outside `10. Raw Sources/`, a `paper` or `book` note without the heading is not treated as Raw, because Paper hubs share those types. Paper hubs, `40. Paper Analyses` notes and Wiki Concepts are checked only by their reviewed `body` spans, so a reviewed restructure stays valid. A legacy Raw paper or book outside the Raw leaf without the heading therefore gets no whole-body guarantee from this helper. An update without an `original_content` entry needs a stated or reused purpose.
- A legacy Raw without `## Original Content` cannot ground quotations: it has no `original_content` span, so update analyses on it refuse. Only metadata migration and appended notes are possible.
- Update analyses need an `original_content` entry: quotes are checked against those preserved Raw bytes, never against new postimage bytes, and the source link is `update_path`. They may not target `update_path` itself.

Exactly one of `preserve` and `promotion` is required; `promotion` replaces the `preserve` checks with the [Book promotion](#book-promotion) checks.

The member result reports `preimage`, `postimage` digests and each preserved span's `before`/`after` offsets. The change enters the session (and `--git` owned paths) with exact before/after bytes, so apply and git drift checks cover it like any other update.

## Book promotion

An approved chapter promotion is an update member whose `preserve` is replaced by `promotion`. It is the only surface that changes an existing Raw body inside Original Content; ordinary Raw updates keep the complete-body-prefix rule above.

```json
"promotion": {
  "placeholder": {"start": 612, "end": 815, "sha256": "sha256:<64 hex of preimage[start:end]>"},
  "text_file": "/absolute/path/outside/vault/ch01.txt",
  "text_sha256": "sha256:<64 hex of the acquired chapter bytes>",
  "locator": "<the stub's recorded source_locator, else source_url>",
  "coverage": "partial",
  "date": "2026-10-09",
  "index": {"path": "Raw/Books/…-book-index.md", "preimage_sha256": "sha256:…", "postimage_file": "/absolute/…/index-post.md", "postimage_sha256": "sha256:…"}
}
```

Exactly these keys; anything else (for example a toggle) is refused. All checks run before any write:

- The preimage is a Book chapter stub: `type: book`, `status: stub`, integer `chapterNumber` ≥ 1, string `chapterPart`, plain-wikilink `bookIndex`, and `chapterPrev`/`chapterNext` present as plain wikilinks or null. The purpose must be stated or reused.
- `locator` equals the stub's recorded `source_locator` (or `source_url` when no locator is recorded); identity fields stay unchanged as for every update.
- `[start,end)` holds exactly the chapter template's pending-fill placeholder bytes and its digest, and is the whole Original Content section: the only `## Original Content` heading outside the span (plus one blank line) ends exactly at `start`, and only newlines then the next `## ` heading or end of file follow `end`. A copy quoted elsewhere, such as in Reading Notes, never qualifies.
- `text_file` follows the outside-file rule (canonical absolute path outside the vault, no symlink or `..`, regular file, digest bound). It is the acquired chapter: nonempty UTF-8 that does not still contain the placeholder.
- The chapter postimage must equal the preimage with only `[start,end)` replaced by the acquired bytes and with `status` and `date_modified` rewritten as JSON scalars: `status` is `completed` for `full` coverage, otherwise `reading` (`partial`/`excerpt`), and `date_modified` is `date`. Every other frontmatter and body byte, including the five navigation fields, Source, TOC Preview, human Reading Notes and Ingest Notes, stays identical.
- `index.path` is another existing Book Index (`type: book`, no `status` or `chapterNumber`) named by the chapter's `bookIndex`, hashed by `index.preimage_sha256`. Links name a note by vault-relative stem, or by basename when it sits in the Index's folder. The Index needs exactly one unchecked `- [ ] [[chapter]]` line under `## TOC` and exactly one `| N | [[chapter]] | stub | — |` row under `## Progress Tracking`, with N equal to `chapterNumber`. The Index postimage must change only that row, to `| N | [[chapter]] | reading-or-completed | date |`, plus that chapter's TOC box to `[x]` for both `reading` and `completed`, because the chapter was actually read. The row status (with the chapter `status`/coverage) keeps the partial-versus-full distinction: a `partial`/`excerpt` promotion records `reading`, a `full` one records `completed`. Its frontmatter and every other byte stay identical. A differently formatted Index refuses; no wider edit is licensed.
- `analyses` (with `obtained_at`) quote the acquired chapter text, never the placeholder, link to `update_path`, and may target neither the chapter nor its Index.

The member result reports `status`, `coverage`, preimage `placeholder` offsets, the postimage `text` extent, `text_sha256` and the Index `path`/`preimage`/`postimage`. Both notes enter the session and the `--git` owned paths, so one apply or one `ingest:` commit carries the chapter, the Index progress and any analyses. Only `stub` is promoted; a later `reading`→`completed` change is not supported by this surface.

## Link resolution

After all members preflight, each collected wikilink (new Raw `author`/`referenced`, new Entity and Concept/atom `related`, update postimage `author`/`referenced`/`source`/`related`) maps to `<path>.md` and must name exactly one target: a path written by the same session, or an existing regular vault file whose every component matches exactly (case-sensitive listing, no symlink). A missing target, a directory, or a link whose bare `<path>` also exists or is planned (ambiguity) refuses the whole request. No basename search and no cross-package helper is used.

## Mothership deeplinks

`mothership` is the frontmatter table's "verified deeplink list": unique strings `obsidian://open?vault=<V>&file=<F>` with both values encoded by `urllib.parse.quote(value, safe='')`, no other query keys, fragment or path. `V` must be in the runtime allow-list (`Ataraxia`) and equal the basename of `--mothership-root`, an explicit canonical absolute directory (no symlink or `..`) disjoint from the destination vault. `F` is a canonical visible relative path; it is resolved with exact-name `listdir`/`lstat` only — no symlink component, no traversal, no file open or write. `F` without `.md` matches `F` or `F.md` and refuses if both exist. Each verified entry is reported as `{link, file, check: "lstat regular file"}`. Stat runs at preflight only: it proves existence at that moment, not identity, content or later presence, and the CLI never derives a link from a quote, name or search. Without `--mothership-root`, any new entry refuses.

Unknown keys are refused. `catalog`, `methodology`, `citation`, and `optional_links` remain caller context only; no discovery or completeness inference is made from them. Bibliography, author Entities, anchor Concepts and reviewed Map links are caller-authored analysis responsibilities, not invented CLI output.

## Integrity and effect boundary

A new explicit Raw path creates an independent capture even when identity matches an older Raw. An existing designated Raw must match identity, then URL, then locator; explicit differing identities refuse reuse. Reuse appends evidence without guessing Original Content boundaries from headings. All preflight body bytes remain an unchanged prefix; metadata-only updates preserve all body bytes. Unknown YAML keys and unaffected YAML spelling remain byte-identical in existing files. The stdlib reader handles plain, single- and double-quoted scalars and inline/block lists; duplicate top-level keys are refused, and an unparseable value refuses only when the runtime needs it.

Every new capture records its writer-known Original Content `[start,end)` bytes in temporary state; headings inside quoted evidence cannot redefine this extent. Book promotion replaces only the recorded template placeholder span with digest-bound acquired bytes. Preimages are rechecked before the first write and each update; new paths use exclusive create; each write is reread. Competing writers must be paused/drained while applying: byte checks detect observed drift, not races after a check. This is not a crash-atomic transaction or an OS locking protocol.

Git history is opt-in: add `--git` (with `--apply --state S`, or `--apply-state S`) and optionally `--title T` to wrap the writes in exactly one `ingest: T` commit. The fixed order is fetch → `reset --mixed origin/main` → write → exact-path add → commit → push. Before writing, the existence and bytes of every owned path are compared against both the fetched base and the local file. Unrelated staged entries and unpublished local commits refuse. Every git call runs with `--literal-pathspecs` and passes owned paths after `--`, so a filename such as `Raw/*.md` names only itself and never stages a matching human file. On restart after a write, each staged owned entry's index blob (or staged deletion) must already equal the recorded postimage before `reset --mixed`; otherwise it refuses without touching the index, HEAD or disk. A non-fast-forward push is recorded as `committed-local` for republication. See [git provenance](git-provenance.md). Without `--git`, no git command runs.
