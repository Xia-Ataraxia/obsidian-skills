# Verification matrix

What this candidate has actually been shown to do, how it was shown, and — just as important — what each result does not prove. A row is upgraded only by new evidence of the named kind. A plausible-looking run is not evidence, a passing parse is not a render, and an exit code is not a result.

The machine-readable report for the application and CLI rows is tracked at [`tests/evidence/native-app.json`](../tests/evidence/native-app.json).

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
| Host | macOS, arm64 |
| Date | 2026-09-29 |
| Scope | not a deployed consumer and not an agent-native installation |

Screenshots and automation detail stay in untracked local test evidence; no personal vault, account, or profile was used, and none is published.

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

## False-success hazards found while verifying

These are the reasons a green-looking run can still be wrong. They are findings, not caveats bolted on afterwards.

| Hazard | What was observed | What to do instead |
| --- | --- | --- |
| Exit status lies | The official CLI exited **0** while printing `Error: Destination file already exists!` | Parse the output and read the destination back. Never accept an exit code as proof of a write. |
| Empty results look like validation | An invalid Bases expression produced **0 results** and an error-class filter indicator, not a clear full-page parse error (`F02-invalid-expression`, recorded as *limited*) | Treat an empty view as unproven, not as a passing filter. Confirm with a fixture that must match. |
| Parse is not render | A diagram that parses can still fail in the app's pinned Mermaid build | Keep static validation and render QA as separate gates. |
| Whole-vault counts are not per-file proof | `unresolved` reports the vault, not the note you changed | Read back the exact destination and compare non-target hashes. |

## Passed — documentation rendering

| Claim | Method | Observed | Limit |
| --- | --- | --- | --- |
| Both READMEs render locally | markdown-it parse plus Chromium rendering, English and Korean | original images loaded with their alt text; no horizontal overflow at 1200 px; the Korean page and the hero banner were visually inspected | local rendering only |

Rendering on a public repository host has **not** been executed. Per [cutover.md](cutover.md) step 2, the actual public README rendering, images, links, and advertised install paths are separate evidence that local rendering does not provide.

## Routes confirmed, installs not verified

All seven runtime routes in [install-matrix.md](install-matrix.md) carry route-specific documentation or observed CLI evidence. GJC has installed CLI evidence, not a public-documentation claim. No native route has been executed: no marketplace was added, no plugin installed, and no runtime has been observed discovering, loading, or advertising these packages. `./install.sh native` states this in its closing line.

## Not attempted — do not read any of these as supported

| Area | State | Consequence |
| --- | --- | --- |
| Excalidraw drawings | plugin not installed | the `.excalidraw.md` builder reaches static validation only; it proves nothing about rendering |
| Web Clipper extension | extension not installed; no capture into a vault | JSON templates and browser DOM selectors were checked; extension import, filters, logic and note readback remain unverified |
| Headless Sync network effects | no pairing, network transfer, daemon run or remote recovery | `ob` 0.0.14 rejected an empty disposable directory with exit 3; this local failure branch does not prove any remote effect |
| Plugin/Templater diagnosis against a live failure | no plugin was installed, reloaded, or broken on purpose | `obsidian-doctor` classifies sanitized evidence fixtures; it has not been run against a real incident |
| Agent-native install and discovery | no runtime install, load, or advertisement | every native route is confirmed, not verified |
| Publication and deployed cutover | this candidate has not been published; no consumer pointer moved | remote availability is unverified; public rendering, canary, retirement and deployed recovery evidence do not exist |
| Other platforms | Windows and non-macOS hosts not exercised | `install.sh` is POSIX `sh`; portability is unverified |

## Passed — local package, helper and inventory checks

| Area | Evidence and limit |
| --- | --- |
| Package structure and isolation | `tests/test_packages.py`: nine identities, isolated resource closure, privacy and metadata checks; no root router. This is not native agent discovery. |
| Installer behavior | `tests/test_install.py`: disposable HOME/project roots, dry-run and apply, collisions, malformed arguments, preservation and exact-config rollback simulation. This is not a deployed install or cutover. |
| Drawing helper | `tests/test_visualize.py`: 84 tests for Unicode, deterministic IDs/geometry, malformed scenes, bindings, guarded writes and non-target preservation. No Excalidraw plugin render is claimed. |
| Diagnostic helper | `tests/test_doctor.py`: 70 subprocess tests for diagnostic evidence, malformed input, unknowns, cancellation risks and privacy; additional contracts in `tests/test_contracts.py`. Not a reproduced live plugin incident. |
| Format semantics | `tests/test_contracts.py`: actual JSON/YAML parsing and schema checks on neutral good/bad cases and shipped examples. These do not execute Clipper's template engine or replace native app checks. |
| Source ownership and rights | `scripts/audit_inventory.py` checked both pinned source trees: 50 files, 135 responsibility units, 95 functional single-owner units, 40 supporting units. `tests/test_inventory.py` exercises omission, duplication, rights and digest tampering. |
| Original assets | `tests/test_assets.py` checks every SVG against its rights ledger, exact hashes/bytes, safe XML and bilingual image references. |
| Native metadata | `claude plugin validate . --strict` and validation of `.claude-plugin/plugin.json` passed; actual invocations and observed results are in [native-manifests.json](../tests/evidence/native-manifests.json). Other native JSON manifests parsed; loading remains unverified. |

The integrated suite is run with `python3 -m unittest discover -s tests -t . -v`.
Supply `OBSIDIAN_SKILLS_CRAFT_SOURCE` and `OBSIDIAN_SKILLS_UPSTREAM_SOURCE` pointing
at the exact read-only source checkouts to exercise the otherwise opt-in real-digest
test. No formatter is configured; syntax, semantic tests and whitespace checks
are separate from formatting.

Browser selector checks are recorded in [clipper-selectors.json](../tests/evidence/clipper-selectors.json):
synthetic selectors returned expected values and class-name drift returned no match.
The public-page selector assertion failed because the expected heading was absent;
no capture was attempted and this is not a successful live capture claim.
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

## Updating this file

1. Run the check; keep raw output out of the public tree if it contains anything from a real vault.
2. Record the claim, the exact command or observation, the result, and the evidence level.
3. State the limit of the result in the same row or section. A result without its limit is not usable evidence.
4. Move a row between sections only with fresh evidence of the level that section requires. Publication, deployed installation, and ownership cutover each have their own approval and procedure — see [cutover.md](cutover.md).
