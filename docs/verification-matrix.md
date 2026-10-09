# Verification matrix

> **Evidence boundary:** Hermes native installs resolved public main at `c22ce26bae518e7973f078cac972ea88707b8e79`; installed bytes were compared afterwards. A local clone checkout does not pin remote tap/install commands. The operator reports 45 installations in five existing local user profiles and a downstream consumer update; fresh task responses cover only CLI/Sync. The immutable `v0.1.0` refusal was two `skills-guard-v6` `credential_exposure` false positives on fake nonce strings, not real credentials or a semantic execution verdict. No scanner bypass was used.

What this candidate has actually been shown to do, how it was shown, and — just as important — what each result does not prove. A row is upgraded only by new evidence of the named kind. A plausible-looking run is not evidence, a passing parse is not a render, and an exit code is not a result.

The machine-readable report for the application and CLI rows is tracked at [`tests/evidence/native-app.json`](../tests/evidence/native-app.json). The publication, native canary, Hermes install, isolated-plugin, and Web Clipper rows come from [`tests/evidence/publication-canary.json`](../tests/evidence/publication-canary.json).

## Evidence ladder

| Level | Means | Does not mean |
| --- | --- | --- |
| Authored | The content exists and is internally consistent. | Anything about a machine. |
| Static validation | A parser, schema, or script accepted the file. | The application accepted it. |
| Materialized readback | The exact destination path was read back after the change, and non-target hashes were compared. | It renders, or the app indexed it. |
| Rendered verification | The target application displayed the intended result. | It works on another version, another profile, or at scale. |

## Environment probed

| Item | Value |
| --- | --- |
| Obsidian desktop app | 1.12.7, fresh isolated profile |
| Official CLI | 1.12.7 (installer 1.12.7), explicit `vault=` targeting with an exact vault-path pre-flight |
| Vault | isolated synthetic vault; fixtures only (`Field.md`, `Field.canvas`, `Studies.base`, `Welcome.md`, CLI fixtures) |
| Plugins | Templater 2.19.3 and Excalidraw 2.27.3, installed in that isolated vault |
| Host | macOS, arm64 |
| Date | 2026-09-29 |
| Scope | isolated synthetic vault and fresh app profile for the rows below; a separate isolated consumer project for the Claude Code canary; five generic operator profiles for the Hermes install; a separate disposable browser profile for the Web Clipper run. Real local Hermes user profiles were deployed; no protected or production vault or live Sync account was exercised. |
| Revisions | `0e658b5a09ac4c789392ac634dcff8a195fa3116` (tag `v0.1.0`) for the publication and Claude Code rows; `c22ce26bae518e7973f078cac972ea88707b8e79` for the Hermes rows |

Screenshots and automation details stay in private evidence. Hermes used existing local user profiles; no profile identities, private paths, account details or raw logs are published.

## Passed — application and CLI behavior

| id | Claim | Method | Observed | Level |
| --- | --- | --- | --- | --- |
| `F01-partial-edit` | A partial Markdown edit changes only its target | native vault read → modify → read | `status` went from `draft` to `reviewed`; the `keep` property and the rest of the body were preserved byte-for-byte | rendered verification |
| `F01-destination` | A wikilink resolves to an exact destination | `metadataCache.getFirstLinkpathDest` | `Field.canvas` resolved from `Field.md` to exactly `Field.canvas` | runtime destination resolution, not embed rendering |
| `F02-filter-group-sort-limit` | A Base view applies filter, group, sort, and limit | native Bases view | 2 results, `active` group, `Study-B` before `Study-A`; archived `Study-C` absent; source notes unchanged | rendered verification |
| `F02-malformed-yaml` | A malformed `.base` fails loudly | native Bases view | an unterminated flow sequence reported *Unable to parse your base file*; `Study-B` remained unchanged | rendered verification |
| `F03-extension` | A canvas can be extended without losing what exists | native Canvas view + JSON readback | existing `question`/`evidence` nodes preserved; `experiment` node and `informs` edge added; three nodes and two labelled edges visibly rendered | rendered verification |
| `F04-render` | A Mermaid block renders in the bundled build | native Markdown reading view | the `flowchart` rendered as SVG with the `Question` and `Evidence` labels | rendered verification |
| `F04-unsupported` | An unsupported diagram type is reported, not swallowed | native Markdown reading view | unknown diagram type reported *Error parsing Mermaid diagram* and *No diagram type detected* | rendered verification |
| `F06-create-search-move-readback` | The official CLI creates, finds, moves, and reads back | official CLI, explicit vault + exact vault-path pre-flight | created `CLI-fixture.md`; search found the needle; moved to `CLI-moved.md`; the old path was gone; destination content read back | materialized readback |
| `F06-missing-source` | A move from a missing source has no side effects | official CLI move from a nonexistent source | `Never-created.md` absent; unrelated `Welcome.md` digest unchanged | materialized readback |
| `F06-collision` | A move onto an existing destination changes nothing | official CLI move onto an existing synthetic destination | source, destination, and `Welcome.md` hashes all unchanged — **and the CLI exited 0 while printing `Error: Destination file already exists!`** | materialized readback |

Non-target control for every row above: `Welcome.md`, SHA-256 `d1b27bcb…39ed8f`, unchanged throughout.

### Supporting CLI surface probes

Recorded in an untracked local probe log during the same session: `obsidian version` → `1.12.7 (installer 1.12.7)`; `vault=<fixture> vault info=path` resolved the exact fixture vault; `help move|create|search|unresolved` returned the parameter surface the package documents (`file=`/`path=`, `to=`, `content=`, `format=text|json`, `total`, `counts`, `verbose`); `search query=<needle> format=json` returned `["CLI-fixture.md"]`; `unresolved format=json` returned `No unresolved links found.`

## Passed — publication and public rendering

Recorded in [publication-canary.json](../tests/evidence/publication-canary.json). The release is immutable and is not retagged, so every row here is pinned to that one revision.

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| The candidate is public at an immutable pin | tag and reachable-object inspection of the published repository | tag `v0.1.0` (prerelease) at commit `0e658b5a09ac4c789392ac634dcff8a195fa3116`, tag object `04f9dfe25157040dd08a8d14158f8a5d2bbc50ca`, tree `10dff62e017df86883d5dd4042f065760e576346`; 5 commits, 57 trees and 95 blobs reachable and scanned | published artifact identity |
| A corrected revision supersedes that tag for installation | commit-level comparison of the two published revisions | `c22ce26bae518e7973f078cac972ea88707b8e79` is a later public commit on the same repository, carries no tag, and differs from the tagged tree only in `obsidian-visualize`; the other eight package trees are byte-identical. No retag and no version bump were made | published artifact identity |
| The archive that was downloaded is that revision | SHA-256 of the downloaded release archive | `74d97b113a590d83bf082ba8c80a8f93b316da5c11cdfbca14d791c556cbb608` | materialized readback |
| Both public articles render on the repository host | the English and the Korean article opened on the host in Chromium | both rendered; `assets/brand/hero.svg` and `assets/demo/workflow.svg` loaded with their alt text; repository-relative links resolved to paths that exist in the published commit | rendered verification |

Limit: one host, one browser, one commit — nothing is claimed for another browser, another host, or any later revision. The public rendering was performed against the tagged tree only; it is not re-claimed for `c22ce26ba…`. The published 0.1.0 tree predates the corrections in this file and in [install-matrix.md](install-matrix.md), and it is not rewritten to match them.

## Passed — native canary: Claude Code, isolated consumer project

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| A published package installs by native plugin identity | Claude Code marketplace add, then `claude plugin install obsidian-skills@obsidian-skills --scope project`, run in an isolated consumer project whose origin is a detached clone of the published commit above | both the marketplace add and the install returned success; `obsidian-skills@obsidian-skills` version 0.1.0 installed | native install |
| The runtime fresh-loads the installed packages | fresh Skill tool calls in that runtime | `obsidian-skills:obsidian-cli` and `obsidian-skills:obsidian-sync` answered as fresh calls; `obsidian-skills:obsidian-canvas` answered in a separate fresh response | fresh-load discovery |
| The loaded packages keep their evidence lines | the recorded false-success checks exercised through the installed packages | a CLI collision exiting 0 was not read as success; a missing headless configuration was not read as healthy network Sync; a dangling Canvas edge was rejected without inventing a node; parsing stayed distinct from rendering | behavior under the installed identity |
| Unrelated content in that project survives | non-target sentinel compared after the run | sentinel unchanged | materialized readback |

Limits recorded with the run: this is not a production deployment, no consumer retirement is claimed, and this row speaks only for Claude Code. An existing session or cache entry would not have counted; each call above is a fresh load. This canary stays pinned to `0e658b5a…` and is not re-run against the corrected commit.

## Passed — Hermes native install into five generic operator profiles

Installed from `c22ce26bae518e7973f078cac972ea88707b8e79` by the native registry-tap route. Operator profiles are named nowhere in this repository; only their count is reported.

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| The corrected pin installs by native registry identity | `hermes skills tap add`, then one `hermes skills install` per package, repeated across five generic operator profiles | all nine packages registered in every profile — **45/45** | native install |
| The skill guard admits every package without an override | `skills-guard-v6` classification recorded per package per profile | 45/45 **SAFE**; no force or override flag was used anywhere | guard admission |
| What the registry holds is the pinned tree | recursive comparison of each installed package tree against the source pin, over non-hidden entries | every compared file matched byte-for-byte; no mutated or partially written copy | materialized readback |
| Both registration identifier forms resolve | resolution of the tapped and untapped identifiers | tap-qualified `Xia-Ataraxia/obsidian-skills/<name>` and source-qualified `Xia-Ataraxia/obsidian-skills/skills/<name>` both resolved | native registration |
| The installed packages keep the Sync-surface distinction | five fresh read-only sessions, `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills` | each session kept the desktop app / official-CLI surface distinct from the headless `ob` client instead of collapsing them into one "sync" answer | behavior under the installed identity |
| Nothing outside the registry was touched | session scope recorded per run | no app, vault, network, or account operation in any of the five sessions | read-only scope |

**Finding: an exit code is not an install.** The `v0.1.0` tree ships the `obsidian-visualize` step-4 handshake eval snippets with a hardcoded placeholder run identity; skills-guard-v6 reported two credential_exposure false positives on these fake nonce strings, with no real credentials or semantic execution verdict. Installing that package from the tag on the same route flagged it as **dangerous** and left a registry state of **`Not installed`** — while the CLI exited **0**. That is why this file recommends `c22ce26ba…`, which requires the caller to substitute a freshly generated run identity, and not the tag for a Hermes install. The tag is immutable, is not retagged, and no version was bumped.

Limits recorded with the run: **only `obsidian-cli` and `obsidian-sync` were exercised as tasks.** The other seven packages registered and were never invoked, so registration is the whole claim for them — registration is not invocation. `hermes skills trust`, which repo-local project skills require, was not exercised. Actual local user profiles and a downstream consumer update are reported; no protected vault operation or complete ownership cutover is established.

## Passed — plugins in an isolated app profile

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| Templater runs and fails loudly in the app | Templater 2.19.3 loaded in an isolated synthetic vault on Obsidian 1.12.7 | a synthetic template produced `Synthetic templater result`; a deliberately broken one failed with `missingSyntheticVariable is not defined`; non-target notes unchanged | rendered verification |
| An Excalidraw scene opens and draws | Excalidraw 2.27.3, same vault, actual plugin view plus screenshot inspection | a five-element scene rendered: *Study* and *Evidence* text boxes connected by an arrow | rendered verification |

Version note: Templater 2.25.1's manifest requires app 1.13.0, so the compatible 2.19.3 was installed instead of forcing a version. Limits: a single isolated synthetic vault, one version of each plugin; no production plugin incident was reproduced and no account or plugin configuration on a real profile was changed. `obsidian-doctor` still classifies sanitized evidence — a synthetic error is not a live incident.

## Passed — Web Clipper extraction; delivery not established

Web Clipper 1.7.1, taken from the official Chrome release archive and installed into a separate disposable browser profile.

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| A failed browser attach was recovered, not reported as success | first attachment had no page target; an isolated inspection page was created and the extension loaded natively | `Extensions.loadUnpacked` succeeded, the background service worker appeared, and the actual settings UI rendered | runtime load |
| The shipped template imports without displacing the built-in one | extension settings UI | `clipping-template.json` imported as *General clipping*; the built-in *Default* template preserved alongside it | rendered verification |
| The extension extracts a real page | actual extension action popup on `example.org`, with *General clipping* selected | the *Example Domain* title, the source URL, and the source text were extracted into the note preview | rendered verification |

**Not activated: *Add to Obsidian*.** The destination still read *Last used*, so no clip was delivered: delivery into an exact vault and a readback of the created note are unverified. That is the one open Clipper surface — extension execution, template import, and extraction are established. No user browser profile and no vault note was changed.

The synthetic and public-page selector work in [clipper-selectors.json](../tests/evidence/clipper-selectors.json) stays separate: it is a DOM-selector check, and the extension evidence above is what proves execution.

## False-success hazards found while verifying

These are the reasons a green-looking run can still be wrong. They are findings, not caveats bolted on afterwards.

| Hazard | What was observed | What to do instead |
| --- | --- | --- |
| Exit status lies | The official CLI exited **0** while printing `Error: Destination file already exists!` | Parse the output and read the destination back. Never accept an exit code as proof of a write. |
| Exit status lies about installs too | Installing `obsidian-visualize` from the `v0.1.0` tree on Hermes exited **0** while the package was flagged **dangerous** and the registry reported **`Not installed`** | Read the registry state after an install. An installer's exit code says nothing about what is registered. |
| A refused package can hide behind an aggregate result | One package out of a nine-package set was left unregistered while the command that installed them still reported success | Count registrations per package and per profile against what was requested. One aggregate "success" is not per-package evidence. |
| Empty results look like validation | An invalid Bases expression produced **0 results** and an error-class filter indicator, not a clear full-page parse error (`F02-invalid-expression`, recorded as *limited*) | Treat an empty view as unproven, not as a passing filter. Confirm with a fixture that must match. |
| Parse is not render | A diagram that parses can still fail in the app's pinned Mermaid build | Keep static validation and render QA as separate gates. |
| Whole-vault counts are not per-file proof | `unresolved` reports the vault, not the note you changed | Read back the exact destination and compare non-target hashes. |

## Passed — documentation rendering

| Claim | Method | Observed | Limit |
| --- | --- | --- | --- |
| Both READMEs render locally | markdown-it parse plus Chromium rendering, English and Korean | original images loaded with their alt text; no horizontal overflow at 1200 px; the Korean page and the hero banner were visually inspected | local rendering only |

This is the pre-publication record and is kept as history. The public-host rendering that [cutover.md](cutover.md) step 2 requires — the actual articles, images, and links on the repository host — has since been executed and is recorded above under *Passed — publication and public rendering*; local rendering never provided it.

## Routes confirmed; two native installs verified, three native routes unrun, two runtimes without a native route

All seven runtime rows in [install-matrix.md](install-matrix.md) carry route-specific documentation or observed CLI evidence. GJC has installed CLI evidence, not a public-documentation claim. Five rows are native routes; two of them have been executed — Claude Code, in one isolated consumer project, and Hermes, into five generic operator profiles, both as recorded above. The three other native routes (Codex, GJC, Grok) have never been run, and no runtime other than Claude Code and Hermes has been observed discovering, loading, or advertising these packages. Cursor and vendor-neutral Agent Skills have no native route at all, so there is nothing native to verify for them: their route is the Agent Skills directory copy, which `tests/test_install.py` exercises in disposable roots. Copying files is not runtime discovery.

`./install.sh native` prints routes and executes nothing, so its output is never install evidence; it names the two executed routes separately from the three unrun native routes, and prints the directory import for the two runtimes without a native one. The immutable 0.1.0 tree predates that wording and is not retagged.

## Not attempted — do not read any of these as supported

| Area | State | Consequence |
| --- | --- | --- |
| Excalidraw beyond one scene | one five-element scene rendered in the plugin view; no other scene, version, or vault | the builder is proven for that case only; scale, other scene shapes and other plugin versions stay unverified |
| Web Clipper delivery into a vault | *Add to Obsidian* deliberately not activated while the destination read *Last used* | extraction is proven above; clip delivery, the destination decision and the created-note readback are unverified |
| Headless Sync network effects | no account pairing, remote-vault selection, network transfer, daemon run or remote recovery | `ob` 0.0.14 rejected an empty disposable directory with exit 3; this local failure branch does not prove any remote effect, and a live account has never been used |
| Plugin/Templater diagnosis against a production incident | Templater 2.19.3 produced a real success and a real error in an isolated synthetic vault; no production profile was involved | `obsidian-doctor` classifies sanitized evidence fixtures; a synthetic failure is not a reproduced live incident |
| Native install on Codex, GJC and Grok | those three native routes have never been executed | they are confirmed routes, not verified installs; these three runtime installs remain unverified |
| Native discovery for Cursor and vendor-neutral Agent Skills | neither runtime has a native route to execute; only the directory copy was exercised, in disposable roots | a copied directory is not proof that either runtime discovered, loaded, or advertised these packages |
| Package task exercise beyond the named few | the Claude Code canary fresh-loaded `obsidian-cli`, `obsidian-sync` and `obsidian-canvas`; the Hermes sessions exercised `obsidian-cli` and `obsidian-sync` only | the remaining packages were never invoked inside a native runtime. On Hermes they are registered, and registration is not invocation — `obsidian-markdown`, `obsidian-bases`, `obsidian-mermaid`, `obsidian-visualize`, `obsidian-clipper` and `obsidian-doctor` have no task evidence on any runtime |
| Hermes project-scope loading | `hermes skills trust`, which repo-local project skills require, was not exercised | only user-scope registry installs are verified for that runtime |
| Cross-revision coverage | the Claude Code canary exists only at `0e658b5a…`; the Hermes install exists only at `c22ce26ba…` | the two results are not evidence about each other. No Claude Code install or fresh-load has been run at the corrected pin, and the only Hermes observation at the tag is the refused `obsidian-visualize` finding |
| Writes against a protected or production vault | none attempted; every vault used was isolated and synthetic | vault policy enforcement against a real protected destination is unverified |
| Deployed cutover | published, canaried, and installed into operator profiles; a downstream consumer update is reported, but no old owner retired, no post-change caller audit, no deployed rollback | steps 5–7 of [cutover.md](cutover.md) are outstanding, and a deployed consumer change is admitted in the source-local authoring path, separately from anything in this repository |
| Other platforms | Windows and non-macOS hosts not exercised | `install.sh` is POSIX `sh`; portability is unverified |

## Local candidate: twenty-six packages

The current local inventory adds four archival principles: `principle-respect-des-fonds`, `principle-original-order`, `principle-hierarchical-management`, and `principle-collective-description`; `principle-skill-creating` and `secondbrain-mode` were added later and are registered through `scripts/audit_inventory.py` only. `tests/test_packages.py::DeclaredPackagesTest::test_twenty_four_packages` checks exact registration; `test_principles_install_without_siblings_or_contract_copies` copies each alone from a checkout with no siblings and verifies exact bytes, apply-when, citation, and absence of `contract.md`. `tests/test_inventory.py::RealManifestTest::test_four_principles_have_distinct_owners_and_local_resources` checks independent ownership. These checks are local evidence, not runtime discovery or publication. The historical twenty-package results below remain unchanged.

The nine native packages and the eleven knowledge packages are checked together on the local candidate. Every row below is local; none is publication, installation or runtime evidence.

| Claim | Method | Observed | Level |
| --- | --- | --- | --- |
| The 0.3.0 collection declared twenty packages (historical row; the pin is now `test_twenty_four_packages`) | `tests/test_packages.py::test_twenty_packages` at the 0.3.0 run, manifests and inventory | nine native and eleven knowledge names, one directory and one owning package each; the Claude manifests list both groups | static registration |
| The directory copy materializes all twenty | `./install.sh copy --runtime claude --skill all --scope project --apply` into a disposable project | exactly twenty package directories; every copied file byte-identical to the checkout | temporary materialization |
| A symlinked destination refuses the copy | a symlink at one package destination in a disposable project | exit 1; the disposable tree, the link and its target unchanged | materialized readback |
| Knowledge scenarios run end to end | package scripts in temporary vaults: onboarding, direct ingest with a query deeplink, capture through Inbox to ingest, additive onboarding with collision refusals | scenarios passed; refusals left their fixtures unchanged | local behavior |

Not established: a runtime load of any knowledge package, automatic discovery, app or plugin execution, Sync, deployment, or a deeplink opening in the app. A future actual runtime load is a separate step. The two transferred `ingest` helpers keep the origin-rights and redistribution hold recorded in [PROVENANCE.md](../PROVENANCE.md).

## Passed — local package, helper and inventory checks

| Area | Evidence and limit |
| --- | --- |
| Package structure and isolation | `tests/test_packages.py`: nine identities, isolated resource closure, privacy and metadata checks; no root router. This is not native agent discovery. |
| Installer behavior | `tests/test_install.py`: disposable HOME/project roots, dry-run and apply, collisions, malformed arguments, preservation and exact-config rollback simulation. This is not a deployed install or cutover. |
| Drawing helper | `tests/test_visualize.py`: 84 tests on the `0e658b5a…` tree for Unicode, deterministic IDs/geometry, malformed scenes, bindings, guarded writes and non-target preservation. `c22ce26ba…` adds caller-nonce cases that require the eval examples to substitute a caller-generated run token; that tree's count is not re-recorded here. The suite itself claims no plugin render; the one rendered scene is the separate Excalidraw 2.27.3 row above. |
| Diagnostic helper | `tests/test_doctor.py`: 70 subprocess tests for diagnostic evidence, malformed input, unknowns, cancellation risks and privacy; additional contracts in `tests/test_contracts.py`. Not a reproduced live plugin incident. |
| Format semantics | `tests/test_contracts.py`: actual JSON/YAML parsing and schema checks on neutral good/bad cases and shipped examples. These do not execute Clipper's template engine or replace native app checks. |
| Source ownership and rights | `scripts/audit_inventory.py` checked both pinned source trees: 50 files, 135 responsibility units, 95 functional single-owner units, 40 supporting units. `tests/test_inventory.py` exercises omission, duplication, rights and digest tampering. |
| Original assets | `tests/test_assets.py` checks every SVG against its rights ledger, exact hashes/bytes, safe XML and bilingual image references. |
| Native metadata | `claude plugin validate . --strict` and validation of `.claude-plugin/plugin.json` passed; actual invocations and observed results are in [native-manifests.json](../tests/evidence/native-manifests.json). The other native JSON manifests parsed only. Loading is verified for Claude Code, in the canary above, and for Hermes, which reads no manifest from this repository and registers one unit per skill; it remains unverified for Codex, GJC, Grok, Cursor and vendor-neutral Agent Skills. |

The `tests/test_*.py` rows above record what ran for the 0.3.0 release; the suite was removed afterwards. The remaining checks are `claude plugin validate . --strict`, `python3 scripts/sync_contracts.py --check` and `python3 scripts/audit_inventory.py`.

Browser selector checks are recorded in [clipper-selectors.json](../tests/evidence/clipper-selectors.json):
synthetic selectors returned expected values and class-name drift returned no match.
The public-page selector assertion failed because the expected heading was absent;
no clip was delivered in that check. It is a DOM-selector probe, not the extension
evidence — actual extension execution and extraction are recorded in their own
section above, and clip delivery remains unverified there too.
The local Headless failure is recorded in [headless-local.json](../tests/evidence/headless-local.json).

Optional-policy absence and unselected presence are supported by independent package
closure and explicit skill contracts. The diagnostic helper's missing-evidence
states are not substitutes for a live agent's optional-policy composition test.
Full agent-driven policy scenarios remain unverified, not silently counted as passed.

## Reproducing the passed rows

```sh
# CLI rows, against a disposable vault you create for the purpose:
obsidian version
obsidian vault=<fixture-vault> create path=CLI-fixture.md content='---\nstatus: draft\nkeep: untouched\n---\n# CLI fixture\n\nNeutralNeedle7342\n'
obsidian vault=<fixture-vault> search query=NeutralNeedle7342 format=json
obsidian vault=<fixture-vault> move   path=CLI-fixture.md to=CLI-moved.md
obsidian vault=<fixture-vault> read   path=CLI-moved.md
obsidian vault=<fixture-vault> move   path=missing-neutral.md to=Never-created.md   # must error, create nothing
obsidian vault=<fixture-vault> move   path=CLI-moved.md to=<existing-file>.md       # must error; note it still exits 0
shasum -a 256 <fixture-vault>/Welcome.md                                            # must match the pre-run digest
```

Application rows are observed in a running app with an isolated profile: the preserved property and body, the resolved canvas link, the Bases view and its malformed-file error, the extended canvas, and the rendered and failing Mermaid blocks. Use a disposable vault — never a personal one.

```sh
# Hermes rows, against a profile you are willing to install into:
git clone https://github.com/Xia-Ataraxia/secondbrain-skills && cd secondbrain-skills
git checkout c22ce26bae518e7973f078cac972ea88707b8e79   # not the v0.1.0 tag
hermes skills tap add Xia-Ataraxia/secondbrain-skills
hermes skills install Xia-Ataraxia/secondbrain-skills/<name>   # once per package; no force flag
# then read the registry itself for each package: the guard classification and the
# registered/not-registered state are the result. The command's exit code is not.
diff -r -x '.*' skills/<name> <installed-skill-dir>/<name>   # must report no differences
hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills   # read-only; ask nothing that writes
```

The last command must stay read-only: ask the session to explain the two Sync surfaces, not to touch a vault, an account, or the network. If any package is anything other than cleanly registered, stop and record the guard classification and the registry state — not the exit status.

## Updating this file

1. Run the check; keep raw output out of the public tree if it contains anything from a real vault.
2. Record the claim, the exact command or observation, the result, and the evidence level.
3. State the limit of the result in the same row or section. A result without its limit is not usable evidence.
4. Move a row between sections only with fresh evidence of the level that section requires. Publication, deployed installation, and ownership cutover each have their own approval and procedure — see [cutover.md](cutover.md).
