# Provenance

Where every part of this repository came from, what rights apply to it, and which
feature owns each implementation in this local candidate.

Three records work together and must agree:

| record | what it holds |
|---|---|
| `source-inventory.json` | the machine-checkable inventory: every source file with its SHA-256 digest, every responsibility unit inside it, the single owning feature, the target file, and the verification mapping |
| `NOTICE` | the third-party notices, verbatim, plus the file-by-file import map |
| this file | the readable lineage: which source, which revision, which rights, which relationship |

Per-change detail lives in each package's `CHANGELOG.md`; skill bodies may summarize attribution. `scripts/audit_inventory.py` enforces the agreement between the
inventory and the tree; `tests/test_inventory.py` covers the audit itself.

## The nine features

Each `skills/obsidian-*` package owns exactly one feature. There is no root skill,
no dispatcher, and no shared runtime.

| id | feature | package | origin | relationship |
|---|---|---|---|---|
| F01 | markdown | `skills/obsidian-markdown` | `obsidian-skills` `skills/obsidian-markdown/` (MIT) | imported, then extended |
| F02 | bases | `skills/obsidian-bases` | `obsidian-skills` `skills/obsidian-bases/` (MIT) | imported, then extended |
| F03 | canvas | `skills/obsidian-canvas` | `obsidian-skills` `skills/json-canvas/` (MIT) | imported, renamed, then extended |
| F04 | mermaid | `skills/obsidian-mermaid` | authored here from public Mermaid and Obsidian documentation | original |
| F05 | visualize | `skills/obsidian-visualize` | original deterministic plugin drawing workflow, extended with MIT pi-extension inspection/layout source | original and adapted |
| F06 | cli | `skills/obsidian-cli` | `obsidian-skills` `skills/obsidian-cli/` (MIT) | imported, then substantially extended |
| F07 | clipper | `skills/obsidian-clipper` | authored here from the official Web Clipper documentation, with schema, enumerations, and import-validation facts checked against the MIT-licensed `obsidianmd/obsidian-clipper` source at `6d56d618b00bd970aa738d6a7a61edee27783e81`; nothing vendored | original |
| F08 | doctor | `skills/obsidian-doctor` | authored here from the requirement that plugin diagnosis be a bounded, evidence-gated pipeline | original |
| F09 | sync | `skills/obsidian-sync` | authored here from the requirement that every sync change be staged, evidenced, and reversible | original |

`imported` means upstream files are present in this repository, modified, and
still covered by the upstream notice. `original` means no upstream file is
present; the package was written here.

## Sources

### obsidian-skills — MIT, imported

- Repository: <https://github.com/kepano/obsidian-skills>
- Revision: `3ccff5338ea700537839b21900aa5358a0402c98`
- Licence evidence: repository-root `LICENSE` at that revision carries the full
  MIT text — copyright line, permission grant, notice-retention condition, and
  warranty disclaimer — with SHA-256
  `64c64d48361edfe8610016441bf593256ea9b67f133b00f47c55aa29ee878567`.
  `.claude-plugin/plugin.json` independently declares `"license": "MIT"`.
- Rights exercised: copy and modify, with the notice retained. `Copyright (c) 2026
  Steph Ango (@kepano)` appears in this repository's root `LICENSE`, in `NOTICE`
  with the full permission text, and in the `LICENSE` file of each of the four
  packages that contain derived files.
- Files imported: nine, listed one by one in `NOTICE` section 1.1 and digest-pinned
  in `source-inventory.json` as `mit-import`.
- Read but not imported: its `README.md` and two plugin manifests, consulted for
  installation and manifest convention only (`mit-reference`; no text copied), and
  its `skills/defuddle/` and `skills/knap/` packages, which are outside these nine
  features and over which no rights are exercised here.

### craft-skills — no licence notice, requirements evidence only

- Repository: <https://github.com/Xia-Ataraxia/craft-skills>
- Revision: `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, read-only.
- Licence evidence: **no** `LICENSE`, `COPYING`, or `NOTICE` file exists at that
  revision, and no inventoried file carries a licence header. The only licence
  statement is the string `MIT` in `.claude-plugin/plugin.json` and
  `.codex-plugin/plugin.json`, and that repository's own README states MIT is
  declared in the plugin manifest with no licence file present. A declaration
  without the copyright line and permission text is not a notice this repository
  can honour or pass on.
- Consequence, applied without exception: **no code, prose, table, checklist,
  example, asset, or corpus prompt/response from that source is copied into or
  redistributed by this repository.** Every behaviour adopted from it was
  re-expressed from the underlying requirement and grounded in public vendor
  documentation, cited per package in that package's `CHANGELOG.md`.
  Source paths, stable unit identifiers, and digests are retained for inventory
  and attribution, not as a redistributed evaluation corpus.
- What was taken: the *requirements*. That source is a single thick Obsidian
  package; reading it answered which problems these nine features must solve, in
  what order, and with what failure behaviour. It did not supply the answers.
- Mechanical guarantee: all 37 inventoried files of that source are marked
  `evidence-only` in `source-inventory.json`, and the audit refuses any unit
  marked `imported` whose source file lacks copy-permitting rights. A future
  attempt to copy from it fails the audit rather than passing silently.
- Downstream lineage claim: that source's own changelog claims a further
  third-party lineage for material predating it, also without a licence notice.
  Because no expression from it is reproduced here, no rights over that
  third-party material are claimed, granted, or implied.

## What the inventory covers

The authenticated native inventory below is preserved. The plugin-first F05
addition is an additive owner-local source map in
`skills/obsidian-visualize/source-map.json`, with exact revision, complete package
tree/digests, retained MIT notice, exclusions and verification paths. It is not
represented as newly authenticated native rows or as part of an earlier release
seal. Package `PROVENANCE.md` and `CHANGELOG.md` record the source-only
implementation revision 0.2.0; collection metadata remains 0.1.0.

Complete, digest-pinned, and audited:

| source | inventoried files | units | coverage rule |
|---|---|---|---|
| craft-skills | 37 | 121 | every file under `skills/obsidian/` and `tests/obsidian/` is inventoried, plus the root policy and distribution files that shaped this repository's own contract, installer, and manifests |
| obsidian-skills | 13 | 14 | every file of the four imported packages, plus the licence, readme, and manifests |
| total | 50 | 135 | 95 functional units with exactly one owner each, 40 shared supporting units |

Functional units per owner: F01 11, F02 7, F03 6, F04 6, F05 15, F06 19, F07 14,
F08 7, F09 10.

Unit granularity follows the shape of the source file. A file serving one feature
is one whole-path unit. A file serving several is split: the thick package's
`SKILL.md` by route row and by section, its changelog by dated record, and the
eval corpus by case and by trigger. A mixed file is never reduced to a single
record, and a shared requirement is never given an invented single owner — it
becomes a supporting unit instead. Both sources declare `partition: true`, so with
a checkout supplied the audit fails if any file in it is neither inventoried nor
covered by a stated exclusion.

## Deliberately not adopted

Six units record behaviour this repository refuses, so the refusal is auditable
rather than invisible:

- mandatory discovery of four external format and CLI packages through the host
  loader, and the two references that deferred Markdown, embed, and canvas
  answers to those packages — here each package owns its own format outright;
- the rule against holding a format or command catalogue locally — inverted here
  by design, keeping only the narrower rule that a package reports a capability
  gap instead of inventing a surface it does not own;
- selective sub-recipe loading — a property of one thick package, meaningless when
  the host loads one small package per task;
- the consolidation of eight packages into one thick package — this repository
  takes the opposite shape on purpose.

## Public sources consulted for facts

Several packages ground a format, command, or schema fact in a public third-party
project. Those readings produced facts, not text: no file from any of them is
vendored here, so none of them imposes a notice obligation and none of them
endorses this repository. Each package cites its own list with exact URLs, and
usually exact revisions, in its `CHANGELOG.md` and attribution section; `NOTICE`
section 2.1 carries the consolidated list.

## Verification mapping

Every functional unit names the target file that now carries the behaviour and at
least two verification references, each of which must resolve to a real path:

- a package section — the owning `SKILL.md` or reference file, usually its
  `Verification` checklist;
- a repository test — `tests/test_packages.py`, `tests/test_contracts.py`,
  `tests/test_install.py`, `tests/test_visualize.py`, `tests/test_doctor.py`, or
  `tests/test_inventory.py`;
- or the cross-package matrix in `docs/verification-matrix.md`.

`python3 scripts/audit_inventory.py` checks the mapping, the single-owner rule,
the owner-to-package match, the rights consistency, and the presence of the
upstream notice. Adding the two checkout flags additionally verifies every digest
and byte count and the exhaustive partition of both sources.

## Local ingest transfer from bstack

This record covers only the two helpers and three tests below, read in full and
transferred from bstack revision `290cb51b48fb0310e58e8bc9c8be0d0d803dc3e6`.
The originals remain in bstack until its separately authorized retirement.

| source path | source SHA-256 | local destination and delta |
|---|---|---|
| `skills/ingest/scripts/web-source-validate.py` | `ba5662061094893f971d269c297df636522c71f5cb845270026bda1b012ff6c1` | same path, byte-identical |
| `skills/ingest/scripts/youtube-transcript-extract.py` | `fd309b4d19781297ba66ac0c75d9e9a77fd11c0e35a41b4ba01f539b3155df85` | same path, byte-identical |
| `tests/ingest/test_metadata_contract.py` | `84e6b27a0045a0eb8a21c3a5c24c82c8fd3bcfbd9d2a31cd3f66a5dbd4e0f36b` | `tests/test_ingest_metadata_contract_ports.py`; import path depth only |
| `tests/ingest/test_web_source_validate.py` | `f156b3546b0dfc6715e49e5c69a5e10c655fa28c6bb70c03711b3afc5df0b238` | `tests/test_ingest_web_source_validate_ports.py`; import path depth only |
| `tests/ingest/test_youtube_transcript_extract.py` | `fb48463d3397b6790d7447807c3e46abd2ccb2590acad9cf147a2b25fbb0978d` | `tests/test_ingest_youtube_transcript_extract_ports.py`; import path depth, two Python 3.8-compatible multi-manager statements, and one test synchronization repair |

The destination gateway-overlap test additionally repairs a pre-existing source
race: a worker now appends its observed completion index before signaling the
dependent worker. The overlap barrier, bounded waits, observed `[2, 1, 0]` order,
stable URL-priority result and every assertion remain intact. The other 26 port
test methods retain their original behavioral AST; AST equality is not claimed
for this one amended method. No bstack original or production extractor changed.

Observed source-repository history records the web helper's creation at
`e6c375ae7f2e5c7b89be40ed1a7e16b5c4b33197` and the transcript helper's creation at
`f674baaba9e8584d764818ed32af0f00f19a20b5`, followed by later source-repository commits.
The current paths and tests were recorded by the restructure commit
`14e93009493f36613cb4faa4625169b46b17a66b`. Commit metadata is observed
provenance, not proof of sole authorship; contributor and PR authorship has not
been exhaustively established.

No vendored third-party code was found on inspection of these five files. This
is an inspection result, not a guarantee about unknown contributors. The source
has no tracked root `LICENSE`, `COPYING` or `NOTICE`, and these files have no
copyright or licence notice. Plugin metadata's MIT string is not treated as a
permission grant. Owner confirmation was not obtained; neither sole authorship
nor a confirmed MIT grant is claimed.

The requested local code preparation and transfer are authorized. External
redistribution remains subject to later exact-tree publication approvals and
resolution of the origin rights; the destination's root MIT notice does not
establish those rights. The helpers invoke optional tools/services rather than
vendoring them. No external extraction, deployment or publication is proved by
this transfer.

Inventory integration for these five files is handed off as a private draft for
serialized integration, not applied concurrently to `source-inventory.json`.
The existing inventory's MIT-import classification must not be used to imply an
unconfirmed grant.

## Native obligation restoration — Unreleased

These additive restorations keep the candidate at `0.1.0`. Requirement lineage
is public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`:
native maintenance and operating requirements, Korean discovery intent, explicit
vault-registry resolution, and append-only plugin evidence. The requirements were
re-expressed, not copied as prose or evaluation-corpus examples. No new source
permission grant is claimed; existing MIT copyright and permission notices and
the local ingest transfer's unresolved origin-rights and redistribution hold
remain unchanged.

- `AGENTS.md` restores native-only official-documentation-first checking,
  installed-version evidence, conflict disclosure and unknown facts; per-change
  source/version records and affected evaluations when either moves; and the
  prospective runtime-change order of documentation, evaluations, recipe,
  version and changelog. It preserves relied-on description triggers, including
  non-English intent, and the seven native operating steps: exact artifact and
  effect, read first, preserve unrelated content, least destructive supported
  selected surface, exact readback, evidence and prerequisites, unknown runtime
  facts. This adds no shared runtime, dependency or write authority.
- `skills/obsidian-markdown/SKILL.md` restores Korean note-cleanup discovery in
  the description only; the existing English scope and body are unchanged.
- `skills/obsidian-cli/SKILL.md` restores Korean backlinks discovery without
  changing the existing description scope or body.
  `skills/obsidian-cli/references/operations.md` adds supported read-only registry
  lookup, task-selected name-to-root mapping and root cross-checking; missing,
  stale or ambiguous registration stops before effects, without default changes
  or fallback surfaces.
- `skills/obsidian-doctor/references/plugins.yaml` changes only the header:
  retired or renamed APIs retain version-scoped evidence and retirement is
  appended, never deletes history. The whole parsed registry data is unchanged.

The new CLI source is <https://help.obsidian.md/cli>, consulted through the
publisher's raw document
<https://raw.githubusercontent.com/obsidianmd/obsidian-help/master/en/Extending%20Obsidian/Obsidian%20CLI.md>:
32,586 bytes, SHA-256
`884d3f36a30ad2dc08bcdc84c1243e17e255677a2bd4a7a1aa0d8f77939fc012`.
Lines 137-148 document explicit vault name/id first; lines 1208-1225 document
`vault info=path` and `vaults verbose`. These are documentation facts, not proof
that an installed build supports or executed them.

Verification established static description/body preservation and whole-registry
parsed-data equality; six existing frontmatter checks passed independently.
Bundle metadata `1.12.7` is not a live CLI version or help response: the current
help/version probes timed out. No current registry execution, live routing or
runtime behavior is proved. Earlier version-specific tests remain historical;
no unchanged suite is rerun for these prose records.

## Knowledge registration and resource corrections — Unreleased

Source baseline: existing local revision
`25f484a63e7278e1864f08b372eea3d96e809289`. These corrections keep version
`0.1.0` and record existing packages and code, not new runtime behavior.

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` now list the
  eleven canonical knowledge names in their existing `knowledgePackages` arrays.
  Native registration, collection identity and all other metadata are unchanged.
- The existing `references/interface.md` in `skills/ingest`, `skills/audit`,
  `skills/lint` and `skills/verify` now declares ten existing package-local helper
  paths and their roles. Their owning changelogs record the details; no helper,
  callable role, protocol, dispatcher or shared runtime was added.

No code or asset was imported, copied, modified or relicensed by these corrections.
Existing source attribution and MIT notices remain intact. The local ingest
transfer's unconfirmed origin rights and public-redistribution hold remain in
force; this registration/documentation change supplies no new permission grant.
No installation, native app execution or model/runtime proof is established.

## Status and limits

The new plugin-first visualization source absorbs inspection/layout/skeleton
material from `Jonghakseo/pi-extension` at
`a4a8107885d2e944d03d8ebc7d9b1cdcf8b7521f`, under the complete MIT grant
`Copyright (c) 2026 Jonghak Seo` retained in `NOTICE` and the owner package.
`scripts/inspect.mjs` and `references/style.md` / `references/skeleton.md` are
adapted; the full-scene adapter and guarded native workbench helper are original.
No standalone app/server/dist, dependency/font bundle or plugin artifact is
redistributed. Official plugin API/loader facts were inspected at
`f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79` (source manifest 2.28.1), not
inferred as an installed version. Source tests do not establish a current
Obsidian plugin load/render; fresh exact-tree release and privacy revalidation
remain necessary before later publication or deployment.

- The local release candidate holds twenty packages: the nine native features
  above and the eleven knowledge packages mapped in `source-inventory.json`.
  Its documentation adds no source, code or asset. The local ingest transfer's
  two helpers and three tests keep their unconfirmed origin rights and
  public-redistribution hold; a local release candidate is not a new grant or a
  publication approval.
- This repository is an unpublished candidate at version `0.1.0`. Nothing recorded
  here installs it on a host, publishes it to a marketplace, or retires, replaces,
  or supersedes any other project — both sources above remain their owners' to
  maintain. `docs/cutover.md` states what a change of ownership would require.
- Provenance records authorship and rights. It is not runtime evidence: what has
  and has not been exercised against a running Obsidian app, CLI, plugin, or sync
  service is recorded in `docs/verification-matrix.md` and in each package's
  `CHANGELOG.md`, and unverified claims stay marked unverified there.
- Only synthetic, public examples appear in shipped files. No credential, account
  identifier, workstation path, private note, or internal planning document is
  reproduced in this repository, including in this record.
