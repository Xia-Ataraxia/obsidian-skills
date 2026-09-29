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
| F05 | visualize | `skills/obsidian-visualize` | authored here from the requirement that a drawing is a file, not a live plugin object | original |
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

## Status and limits

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
