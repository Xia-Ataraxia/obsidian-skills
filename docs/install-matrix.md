# Install matrix

> **Evidence boundary:** Hermes native installs resolved public main at `c22ce26bae518e7973f078cac972ea88707b8e79`; installed bytes were compared afterwards. A local clone checkout does not pin remote tap/install commands. The operator reports 45 installations in five existing local user profiles and a downstream consumer update; fresh task responses cover only CLI/Sync. The immutable `v0.1.0` refusal was two `skills-guard-v6` `credential_exposure` false positives on fake nonce strings, not real credentials or a semantic execution verdict. No scanner bypass was used.

Current source: `Xia-Ataraxia/secondbrain-skills` at `c8c3a63d71a732eb7e5bcc39124fac5313937ddc` is the 0.3.0 release merge commit: twenty packages, the qmd parser fix, the Hermes skills_guard install fixes the ingest Book branch and the `secondbrain-skills` plugin identity. Older pins and results below retain their historical provenance. Repository naming does not change the existing `obsidian-skills@obsidian-skills` plugin identity.

Every route below comes from one place: the route table in `install.sh` (`route_load`) and the native command block (`cmd_native`). Each row carries a `confirmed by` field naming the evidence it rests on — the runtime's published documentation plus its observed CLI help. A runtime outside the table has no route at all; the installer refuses it instead of guessing.

**Route confirmed is not install verified — with exactly two exceptions.** Confirming a route means the commands and directories are the ones the runtime documents. It does not mean this package was installed, loaded, or advertised. That has now happened on two runtimes.

- **Claude Code**, in an isolated consumer project, installed from a detached clone of the published commit `0e658b5a09ac4c789392ac634dcff8a195fa3116` (tag `v0.1.0`, prerelease). Inside that canary the runtime fresh-loaded 3 of the 9 packages (`obsidian-cli`, `obsidian-sync`, `obsidian-canvas`); discovery of the other six is not claimed. This is the historical canary and stays pinned to that commit.
- **Hermes**, installed from the corrected public commit `c22ce26bae518e7973f078cac972ea88707b8e79` by the native registry-tap route — `hermes skills tap add`, then one `hermes skills install` per package. All nine packages registered into five generic operator profiles: 45/45 reported SAFE by the skills guard (`skills-guard-v6`), with no force or override flag. Each installed package tree was compared against the source pin over a recursive walk of non-hidden entries and matched byte-for-byte, and both the tap-qualified and the source-qualified registration identifiers resolved. Five fresh read-only `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills` sessions then kept the desktop app / official-CLI Sync surface distinct from the headless `ob` client, with no app, vault, network, or account operation. **Only those two packages were exercised as tasks; the other seven registered and were never invoked.** `hermes skills trust`, which repo-local project skills require, was not exercised.

Three native routes — Codex, GJC, Grok — have never been executed. The remaining two runtimes, Cursor and vendor-neutral Agent Skills, have no native route to execute at all; their route is the Agent Skills directory copy, which the installer suite exercises in disposable roots. Actual Hermes local user-profile deployment and a downstream consumer update are operator-reported; full migration is not established. Evidence: [verification-matrix.md](verification-matrix.md).

**Use `c22ce26bae518e7973f078cac972ea88707b8e79`, not the `v0.1.0` tag.** That 0.1.0 release is immutable and is not retagged. In the separate immutable-tag installation attempt, `skills-guard-v6` reported two `credential_exposure` false positives on the fake quoted nonce strings in `obsidian-visualize`. No real credentials were present; this was not a semantic execution verdict. That attempt classified the package **DANGEROUS** and left it **`Not installed`** — while the CLI exited **0**. Read the registry, not the exit status. Only `obsidian-visualize` differs between the two commits; the other eight package trees are byte-identical, and no retag or version bump was made. The published tree also predates these corrections and still carries the pre-publication route wording; the updated guidance below records evidence about the corrected pin, not to the artifact anyone downloads from that tag.

The rows were re-confirmed by running `./install.sh routes`, `./install.sh skills`, `./install.sh native --runtime <id>` for all seven ids, and dry-run `copy` plans in this checkout on 2026-09-29. Those commands only print; none installs anything.

## Status legend

| Status | Meaning |
| --- | --- |
| `route confirmed` | Commands, manifests, and skill directories match the runtime's documentation and observed CLI help. |
| `install unverified` | The native route has never been executed. Applies to Codex, GJC and Grok. |
| `install verified (isolated project)` | The route was executed end to end in an isolated consumer project, and the runtime fresh-loaded 3 of the 9 packages there — `obsidian-cli`, `obsidian-sync`, `obsidian-canvas`. Discovery of the other six packages is not claimed, and this is not a production deployment. |
| `install verified (operator profiles)` | The route was executed end to end against the corrected pin into five generic operator profiles: all nine packages registered, 45/45 SAFE under the skills guard (`skills-guard-v6`) with no force or override, each installed tree byte-identical to the pin on a recursive non-hidden comparison, and both registration identifier forms resolved. Two packages were then exercised in read-only sessions. This is local user-profile deployment; registration of the other seven is not invocation of them. |
| `published` | The `Xia-Ataraxia/obsidian-skills` source form resolves: the candidate is public at commit `c22ce26bae518e7973f078cac972ea88707b8e79` (the verified installation source revision), and the earlier prerelease is public at tag `v0.1.0`, commit `0e658b5a09ac4c789392ac634dcff8a195fa3116`. Install from the corrected commit; do not use the tag for a Hermes install. Where the runtime documents a local source, point the same command at a clone checked out at that commit. |
| `no self-serve route` | The runtime offers no native plugin/marketplace route this package can use, so there is no native route to verify. The Agent Skills directory import is the route — exercised by the installer suite in disposable roots — and it is never presented as a plugin install. |

## Runtime routes

| Runtime id | Label | Route kind | Manifest in this repo | Skill dirs — user / project | Reference | Confirmed by | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `claude` | Claude Code | plugin-marketplace | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | `~/.claude/skills` / `.claude/skills` | <https://code.claude.com/docs/en/plugins/create-marketplace> | published doc + observed help of `claude plugin marketplace add` (source: URL, path, or GitHub repo) and `claude plugin install` (`plugin@marketplace`, `--scope user\|project\|local`) | route confirmed · install verified (isolated project) · published |
| `codex` | Codex / ChatGPT desktop app | plugin-marketplace | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | `~/.agents/skills` / `.agents/skills` | <https://developers.openai.com/plugins/build/plugins> | published doc names `$REPO_ROOT/.agents/plugins/marketplace.json` as the repo marketplace and `.codex-plugin/plugin.json` as the supported compatibility manifest; observed help of `codex plugin marketplace add` and `codex plugin add` | route confirmed · install unverified · published |
| `gjc` | GJC (Gajae Code) | plugin-marketplace | `.claude-plugin/marketplace.json` | `~/.gjc/agent/skills` / `.gjc/skills` | installed CLI help: `gjc plugin --help` | observed on gjc v0.18.0: `gjc plugin` actions include install and marketplace with `--scope user\|project`; the binary resolves `.claude-plugin/marketplace.json`, `~/.gjc/agent/skills`, and `.gjc/skills`. No public documentation URL is published, so none is claimed | route confirmed · install unverified · published |
| `grok` | Grok Build | plugin-marketplace (documented Claude Code compatibility) | `.claude-plugin/marketplace.json`; no Grok-specific manifest exists | `~/.grok/skills` / `.grok/skills` | <https://docs.x.ai/build/features/skills-plugins-marketplaces> | published doc states Grok reads Claude Code marketplaces, plugins, and skills with zero configuration, discovers skills from `~/.grok/skills`, `./.grok/skills`, and `~/.agents/skills`, and installs marketplace plugins under `~/.grok/plugins/marketplaces/`; observed help of `grok plugin marketplace add` and `grok plugin install` | route confirmed · install unverified · published |
| `hermes` | Hermes Agent | registry-tap (one unit per skill) | none | `~/.hermes/skills` / `.hermes/skills` | <https://hermes-agent.nousresearch.com/docs/user-guide/features/skills> | published doc documents `hermes skills tap add <owner/repo>` (default tap path `skills/`), per-skill install, and `~/.hermes/skills` as the source of truth; observed help of `hermes skills tap add` and `hermes skills install`; **plus an executed install** of all nine packages from `c22ce26ba…` into five generic operator profiles | route confirmed · install verified (operator profiles) · published |
| `cursor` | Cursor | skill-directory | none | `~/.cursor/skills` / `.cursor/skills` | <https://cursor.com/docs/skills> | <https://cursor.com/docs/plugins> documents the Cursor Marketplace as review-and-submission only and team marketplaces as Teams/Enterprise dashboard features; an Agent Plugin additionally needs a root `plugin.json`, which this package does not ship | no self-serve route · directory import works today |
| `agent-skills` | Agent Skills (vendor-neutral) | skill-directory | none | `~/.agents/skills` / `.agents/skills` | <https://agentskills.io/specification> | the specification defines the `SKILL.md` package format, naming rules, and optional directories only; it defines no install, plugin, or marketplace route | no self-serve route · directory import works today |

Route kinds, as the installer defines them:

- **plugin-marketplace** — a native plugin install backed by a manifest shipped in this repository.
- **registry-tap** — a native per-skill registry install; no plugin manifest is read from this repository.
- **skill-directory** — no self-serve native plugin route; the Agent Skills directory import is the only route.

Notes carried by the table itself: the marketplace root is this repository root, so Claude Code auto-discovers `skills/`; the OpenAI doc names the ChatGPT desktop app Plugins Directory as the install surface for a local or repo marketplace, and the app must be restarted after adding one; GJC advertises an installed package as `<plugin>:<skill>`, i.e. `obsidian-skills:<name>`, from installed CLI evidence, and Claude Code was observed using the same form in the executed canary — no equivalent claim is made for the remaining runtimes; Grok needs no Grok-specific manifest and exposes the added source through its TUI Marketplace tab; Hermes installs one unit per skill, never a bundle, addresses each package by its own registry identifier rather than a `<plugin>:<skill>` pair, selects packages in a session by bare name via `hermes chat --skills <name>[,<name>] --toolsets skills`, and loads repo-local project skills only after `hermes skills trust` — which was confirmed in the executed install for the identifier and session forms, and left unexercised for `trust`; Cursor also loads `~/.agents/skills`, `.agents/skills`, and for compatibility `.claude/skills` and `.codex/skills`; Codex, Cursor, and Grok all read `~/.agents/skills`, which makes that scope the portable user-level import.

## Native commands per runtime

`./install.sh native --runtime <id>` prints these and executes none of them. `<source>` is the published `Xia-Ataraxia/secondbrain-skills`, or the absolute path of a clone checked out at the pinned commit. Two of the blocks below were actually run by hand: the Claude Code pair, in an isolated consumer project against a detached clone of `0e658b5a…`; and the Hermes block, against `c22ce26ba…`, into five generic operator profiles. Do not run the Hermes block against the `v0.1.0` tag — `obsidian-visualize` is refused as dangerous there and reports `Not installed` despite exit 0.

```sh
# claude — 1. register the marketplace, 2. install the plugin
claude plugin marketplace add <source>
claude plugin install secondbrain-skills@secondbrain-skills      # --scope user|project|local, user is the default
# in a session: /plugin marketplace add, then /plugin install

# codex — the ChatGPT desktop app Plugins Directory is the install/test surface
codex plugin marketplace add <source>                      # restart the app afterwards
codex plugin add secondbrain-skills@secondbrain-skills

# gjc — no local-path form is claimed: its help documents only <source>
gjc plugin marketplace add Xia-Ataraxia/secondbrain-skills
gjc plugin install secondbrain-skills@secondbrain-skills --scope user      # or --scope project

# grok — marketplace route, then install from the TUI Marketplace tab
grok plugin marketplace add <source>
grok plugin marketplace list                               # shows the source and the plugins it exposes
# direct source install instead (git URL, GitHub shorthand or local path — never plugin@marketplace):
grok plugin install Xia-Ataraxia/secondbrain-skills

# hermes — tapped form, one package at a time
hermes skills tap add Xia-Ataraxia/secondbrain-skills
hermes skills install Xia-Ataraxia/secondbrain-skills/<name>  # tapped: no skills/ segment
hermes skills update
# without the tap, the identifier carries the in-repo path:
hermes skills install Xia-Ataraxia/secondbrain-skills/skills/<name>
# repo-local project skills load only after: hermes skills trust

# cursor, agent-skills
# UNSUPPORTED: no self-serve native plugin or marketplace route. Use the directory import below.
```

Every `native` run still ends the same way: *"Nothing above has been executed, and no runtime has loaded this package as a result of running this script."* The script prints and never installs, so nothing it shows is install evidence. It then splits: the Claude Code route adds that the commands above were run by hand against a clone of the published tag and that the runtime installed and fresh-loaded this package in an isolated project scope only; the Hermes route adds that its commands were run by hand against the corrected pin, that all nine packages registered into five generic operator profiles, and that only `obsidian-cli` and `obsidian-sync` were exercised in read-only sessions; while the three other native rows — Codex, GJC, Grok — say no install of theirs has been observed. Cursor and Agent Skills print the directory import instead, because they have no native route at all.

## Agent Skills directory import — the route that works today

```sh
./install.sh copy --runtime <id> --skill <name>|all --scope user|project [--apply]
```

| Property | Behavior |
| --- | --- |
| Default mode | Dry run. It prints the plan, the selection, and the collision report, and writes nothing; `--apply` is required to copy. |
| Requirements | `copy` runs its filesystem work through `scripts/install_packages.py` under **python3 3.8+ (standard library only)**; without it the command refuses rather than falling back to an unanchored copy. `routes`, `skills`, `native`, and `--help` are plain POSIX `sh` and need nothing else. The copier is part of this checkout, not an installed dependency — nothing is fetched. |
| Source | `skills/<name>` in this checkout. A package directory that is itself a symlink is refused, not copied through. |
| Destination | `--scope user` → the runtime's user skill dir; `--scope project` → `<project-root>/<runtime project dir>`, default project root `$PWD`. An explicitly empty `--project-root ''` is a usage error, not a silent fallback to that default. |
| Root guards | The route below the approved root is opened one component at a time, each through a handle on the component just opened; missing components are created relative to that handle, never with `mkdir -p`. A symlink on the route is refused by the open that would otherwise have followed it, so a component swapped after the check cannot redirect the next create. Containment is then proved from filesystem object identity — the root's real parent chain must reach the approved root without passing through this checkout — rather than by comparing path strings. |
| Pre-flight | Every selected package is checked first. Any existing file, directory, symlink, or dangling symlink at a destination refuses the whole operation — there is no partial copy. |
| Publication | A package is built in private staging under held directory handles. After verification, a macOS/Linux atomic no-replace rename publishes it. Any existing public destination wins and remains untouched; unsupported publication primitives fail closed. Failed publication leaves named staging for explicit recovery. |
| Post-copy verification | Same paths and types, every regular file byte-identical, `SKILL.md` present. Source symlinks are refused. Failed verification cannot publish a partial package; already published packages remain intact. |
| Rollback | Only the entries this run recorded creating are removed, each re-identified by (device, inode) first. A destination that is no longer this run's own reservation, or one somebody has added content to, is reported and left exactly as found — it is never recursively deleted. |
| Generated caches | `__pycache__`, `*.pyc`, `*.pyo`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.DS_Store` are never copied, so there is no prune step that could fail unnoticed. One found in a destination is a readback failure, not an exclusion. |
| Interruption | `INT`/`TERM` stop the run with status 128 plus the signal number. Partial/unverified packages are never published. Complete packages may already be published even if their installed report was interrupted. Inspect public destinations and retained staging named in the stdout report; staging entrypoints are quarantined as `SKILL.unpublished`, with warnings if quarantine fails. Cleanup may be incomplete. |
| Writes | Anchored route directories, private staging and selected package destinations only. No profile configuration, marketplace registry, tap list, plugin cache or lockfile is changed. |
| Network | None. The installer never reaches the network and never runs a runtime CLI. |
| Naming | A directory copy is always labelled a generic Agent Skills import, never a native plugin install. |

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Completed: `routes`/`skills`/`native` printed, or a copy plan that is clean (dry run) or fully applied and read back. |
| 1 | Refused: unknown runtime, illegal or undeclared skill name, symlinked source package, path escape, destination-root violation, a collision in the pre-flight report, a package that failed post-copy verification, or a missing python3/copier. |
| 2 | Usage error: conflicting, repeated, misplaced, or empty-valued options. |
| 128+N | Interrupted by signal N (130 for `INT`, 143 for `TERM`). Partial/unverified packages are never published, but complete packages may remain. Retained staging is named in the stdout report; stderr carries the interruption summary. Inspect both streams and destinations; cleanup may be incomplete. |

### Observed refusals and usage errors

Run from this checkout on 2026-09-29, against the `sh` front end. No file was created in any case; the dry-run destination root was confirmed still absent afterwards.

**These rows predate the extraction of the filesystem work into `scripts/install_packages.py`.** The usage errors are produced by the unchanged option grammar; the two `copy` rows are produced by the copier and their wording is unchanged by construction, but they have not been re-observed since. Re-run them before quoting them as current evidence.

| Command fragment | Result |
| --- | --- |
| `native --runtime vscode` | `REFUSED: unknown runtime 'vscode'. Known: claude codex gjc grok hermes cursor agent-skills. No route is guessed.` (1) |
| `copy --runtime claude --skill ../escape --scope user` | `REFUSED: illegal skill name '../escape': not a single lowercase Agent Skills path segment.` (1) |
| `copy --runtime claude --skill all --skill obsidian-cli --scope user` | `USAGE ERROR: --skill all cannot be combined with named packages; choose one form` (2) |
| `copy … --apply --dry-run` | `USAGE ERROR: --dry-run conflicts with --apply` (2) |
| `copy … --scope user --project-root /tmp` | `USAGE ERROR: --project-root applies to --scope project only (scope is 'user')` (2) |
| `native --runtime claude --scope user` | `USAGE ERROR: 'native' does not take --scope; use 'copy'` (2) |
| `copy --runtime claude --runtime codex …` | `USAGE ERROR: --runtime was given twice with different values ('claude' then 'codex')` (2) |
| `copy --runtime cursor --skill obsidian-markdown --skill obsidian-canvas --scope project --project-root <empty dir>` | `selection obsidian-markdown obsidian-canvas` → `2 copyable, 0 refused` → `Dry run only — nothing was written.` (0) |

The same class of refusal also covers a repeated `--scope` or `--project-root` with a different value, an empty selection, and `routes`/`skills` given `--project-root` or `--apply`.

## Package presence

`./install.sh skills` reports each declared package as `[present]`, `[BROKEN ]` (a directory without `SKILL.md`), or `[absent ]`, prints how many are installable from the checkout, and closes by restating that each package stands alone, with no router, no dispatcher and no shared runtime. Twenty names are fixed in the installer, and a name outside them is refused:

- native: `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, `obsidian-mermaid`, `obsidian-visualize`, `obsidian-cli`, `obsidian-clipper`, `obsidian-doctor`, `obsidian-sync`;
- knowledge: `capture`, `inbox`, `ingest`, `query`, `verify`, `audit`, `lint`, `status`, `reindex`, `refresh-context`, `onboard`, `principle-respect-des-fonds`, `principle-original-order`, `principle-hierarchical-management`, `principle-collective-description`.

The current local candidate declares twenty-six packages. Each principle can be selected alone with `copy --runtime claude --skill <name> --scope project --apply`; it needs no sibling directory or shared contract copy. `tests/test_packages.py::DeclaredPackagesTest::test_principles_install_without_siblings_or_contract_copies` checks isolated temporary materialization and byte readback. Historical pins and runtime observations below still concern their original package sets; no new runtime load is claimed.

`--skill all` selects the nine native packages plus every knowledge package present in the checkout.

Presence is a property of the checkout you're holding. In the local release candidate the command reported **9 of 9** native and **11 of 11** knowledge packages installable. Run it yourself rather than trusting those numbers.

In the same candidate, `copy --runtime claude --skill all --scope project --apply` into a disposable project produced exactly twenty package directories whose files all matched the checkout byte for byte, and a symlink at one package destination refused the run with exit 1 and left that tree unchanged. That's temporary materialization. The knowledge packages aren't in the published pin, and no runtime has loaded them; the native route evidence above covers the nine published packages only.

## Support limits

- **Two native routes executed, three unrun, two runtimes without a native route.** Claude Code was installed and fresh-loaded in an isolated consumer project: the marketplace add and `claude plugin install obsidian-skills@obsidian-skills --scope project` both returned success for version 0.1.0, and the runtime then answered fresh `obsidian-skills:obsidian-cli` and `obsidian-skills:obsidian-sync` Skill calls, with `obsidian-skills:obsidian-canvas` answering in a separate fresh response — 3 of the 9 packages, not all nine. Hermes was installed from `c22ce26ba…` into five generic operator profiles — all nine packages, 45/45 SAFE under the skills guard (`skills-guard-v6`), no force or override, every installed tree byte-identical to the pin, both registration identifier forms resolved — and then answered five fresh read-only `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills` sessions. The Codex, GJC and Grok native routes are confirmed and never executed; no runtime other than Claude Code and Hermes has been observed discovering, loading, or advertising these packages. Cursor and vendor-neutral Agent Skills have no native route to execute; their directory import copies files, which is not runtime discovery.
- **Registration is not invocation.** Nine packages registered on Hermes; two were exercised. The other seven have no task evidence on that runtime, and six of the nine have no task evidence on any native runtime.
- **Local deployment is not complete migration.** Claude used an isolated consumer project; Hermes was deployed to five existing local user profiles. The operator also reports a native downstream consumer update. Retirement, zero-old-caller evidence and deployed rollback remain outstanding; private admission details stay in the consumer record.
- **The publication is a pin, not a moving target.** The release archive downloaded from tag `v0.1.0` has SHA-256 `74d97b113a590d83bf082ba8c80a8f93b316da5c11cdfbca14d791c556cbb608`; the tag object is `04f9dfe25157040dd08a8d14158f8a5d2bbc50ca` and the tree is `10dff62e017df86883d5dd4042f065760e576346`. The release is immutable and is not retagged. The corrected pin `c22ce26bae518e7973f078cac972ea88707b8e79` is a later public commit on the same repository; it carries no tag and none was created for it. Pin to a commit, never to `main`.
- **A zero exit is not an install.** Installing `obsidian-visualize` from the `v0.1.0` tree on Hermes flagged the package as **dangerous** and left a registry state of **`Not installed`** while the CLI exited **0**. Check the registry after any install; the corrected pin is what to install.
- **Local tests are not deployed installation evidence.** The installer suite exercises disposable roots, collision and path-boundary cases, byte readback and failure preservation. It installs no native runtime and fresh-loads nothing.
- **Platform.** `install.sh` is POSIX `sh` and was exercised on macOS (arm64). Windows and other shells are untested. `copy` additionally needs python3 3.8+ and the `openat`-style calls it exposes (`os.open(..., dir_fd=)`, `O_NOFOLLOW`, `O_DIRECTORY`); the copier checks for them at startup and refuses on a platform that lacks them instead of writing unanchored. That refusal path has not been exercised on such a platform, because none was available here.
- A directory import copies package files. Whether a runtime then discovers, loads, and advertises them is a property of that runtime and has not been verified for any runtime: both verified installs came through a native route — a plugin marketplace and a registry tap — not a directory import. See [verification-matrix.md](verification-matrix.md).

## Reproducing this matrix

```sh
./install.sh routes
./install.sh skills
for r in claude codex gjc grok hermes cursor agent-skills; do ./install.sh native --runtime "$r"; done
./install.sh copy --runtime cursor --skill all --scope project --project-root "$(mktemp -d)"   # dry run
```

These commands print absolute paths for your own home directory and checkout; this document uses `~`, `<source>`, and `<project-root>` placeholders instead.
