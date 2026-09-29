# Install matrix

Every route below comes from one place: the route table in `install.sh` (`route_load`) and the native command block (`cmd_native`). Each row carries a `confirmed by` field naming the evidence it rests on — the runtime's published documentation plus its observed CLI help. A runtime outside the table has no route at all; the installer refuses it instead of guessing.

**Route confirmed is not install verified.** Confirming a route means the commands and directories are the ones the runtime documents. It does not mean this package was installed, loaded, or advertised anywhere — that has not happened on any runtime.

The rows were re-confirmed by running `./install.sh routes`, `./install.sh skills`, `./install.sh native --runtime <id>` for all seven ids, and dry-run `copy` plans in this checkout on 2026-09-29. Those commands only print; none installs anything.

## Status legend

| Status | Meaning |
| --- | --- |
| `route confirmed` | Commands, manifests, and skill directories match the runtime's documentation and observed CLI help. |
| `install unverified` | The route has never been executed. Applies to every runtime, without exception. |
| `unreleased` | The `Xia-Ataraxia/obsidian-skills` source form assumes an accessible published repository. This candidate has not been published; remote availability has not been established. Where the runtime documents a local source, point the same command at this checkout. |
| `no self-serve route` | The runtime offers no native plugin/marketplace route this package can use. The Agent Skills directory import is the route, and it is never presented as a plugin install. |

## Runtime routes

| Runtime id | Label | Route kind | Manifest in this repo | Skill dirs — user / project | Reference | Confirmed by | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `claude` | Claude Code | plugin-marketplace | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | `~/.claude/skills` / `.claude/skills` | <https://code.claude.com/docs/en/plugins/create-marketplace> | published doc + observed help of `claude plugin marketplace add` (source: URL, path, or GitHub repo) and `claude plugin install` (`plugin@marketplace`, `--scope user\|project\|local`) | route confirmed · install unverified · unreleased |
| `codex` | Codex / ChatGPT desktop app | plugin-marketplace | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | `~/.agents/skills` / `.agents/skills` | <https://developers.openai.com/plugins/build/plugins> | published doc names `$REPO_ROOT/.agents/plugins/marketplace.json` as the repo marketplace and `.codex-plugin/plugin.json` as the supported compatibility manifest; observed help of `codex plugin marketplace add` and `codex plugin add` | route confirmed · install unverified · unreleased |
| `gjc` | GJC (Gajae Code) | plugin-marketplace | `.claude-plugin/marketplace.json` | `~/.gjc/agent/skills` / `.gjc/skills` | installed CLI help: `gjc plugin --help` | observed on gjc v0.18.0: `gjc plugin` actions include install and marketplace with `--scope user\|project`; the binary resolves `.claude-plugin/marketplace.json`, `~/.gjc/agent/skills`, and `.gjc/skills`. No public documentation URL is published, so none is claimed | route confirmed · install unverified · unreleased |
| `grok` | Grok Build | plugin-marketplace (documented Claude Code compatibility) | `.claude-plugin/marketplace.json`; no Grok-specific manifest exists | `~/.grok/skills` / `.grok/skills` | <https://docs.x.ai/build/features/skills-plugins-marketplaces> | published doc states Grok reads Claude Code marketplaces, plugins, and skills with zero configuration, discovers skills from `~/.grok/skills`, `./.grok/skills`, and `~/.agents/skills`, and installs marketplace plugins under `~/.grok/plugins/marketplaces/`; observed help of `grok plugin marketplace add` and `grok plugin install` | route confirmed · install unverified · unreleased |
| `hermes` | Hermes Agent | registry-tap (one unit per skill) | none | `~/.hermes/skills` / `.hermes/skills` | <https://hermes-agent.nousresearch.com/docs/user-guide/features/skills> | published doc documents `hermes skills tap add <owner/repo>` (default tap path `skills/`), per-skill install, and `~/.hermes/skills` as the source of truth; observed help of `hermes skills tap add` and `hermes skills install` | route confirmed · install unverified · unreleased |
| `cursor` | Cursor | skill-directory | none | `~/.cursor/skills` / `.cursor/skills` | <https://cursor.com/docs/skills> | <https://cursor.com/docs/plugins> documents the Cursor Marketplace as review-and-submission only and team marketplaces as Teams/Enterprise dashboard features; an Agent Plugin additionally needs a root `plugin.json`, which this package does not ship | no self-serve route · directory import works today |
| `agent-skills` | Agent Skills (vendor-neutral) | skill-directory | none | `~/.agents/skills` / `.agents/skills` | <https://agentskills.io/specification> | the specification defines the `SKILL.md` package format, naming rules, and optional directories only; it defines no install, plugin, or marketplace route | no self-serve route · directory import works today |

Route kinds, as the installer defines them:

- **plugin-marketplace** — a native plugin install backed by a manifest shipped in this repository.
- **registry-tap** — a native per-skill registry install; no plugin manifest is read from this repository.
- **skill-directory** — no self-serve native plugin route; the Agent Skills directory import is the only route.

Notes carried by the table itself: the marketplace root is this repository root, so Claude Code auto-discovers `skills/`; the OpenAI doc names the ChatGPT desktop app Plugins Directory as the install surface for a local or repo marketplace, and the app must be restarted after adding one; GJC advertises an installed package as `<plugin>:<skill>`, i.e. `obsidian-skills:<name>` — no equivalent claim is made for any other runtime; Grok needs no Grok-specific manifest and exposes the added source through its TUI Marketplace tab; Hermes installs one unit per skill, never a bundle, and repo-local project skills load only after `hermes skills trust`; Cursor also loads `~/.agents/skills`, `.agents/skills`, and for compatibility `.claude/skills` and `.codex/skills`; Codex, Cursor, and Grok all read `~/.agents/skills`, which makes that scope the portable user-level import.

## Native commands per runtime

`./install.sh native --runtime <id>` prints these and executes none of them. `<source>` is `Xia-Ataraxia/obsidian-skills` once published, or the absolute path of this checkout while 0.1.0 is unreleased.

```sh
# claude — 1. register the marketplace, 2. install the plugin
claude plugin marketplace add <source>
claude plugin install obsidian-skills@obsidian-skills      # --scope user|project|local, user is the default
# in a session: /plugin marketplace add, then /plugin install

# codex — the ChatGPT desktop app Plugins Directory is the install/test surface
codex plugin marketplace add <source>                      # restart the app afterwards
codex plugin add obsidian-skills@obsidian-skills

# gjc — no local-path form is claimed: its help documents only <source>
gjc plugin marketplace add Xia-Ataraxia/obsidian-skills
gjc plugin install obsidian-skills@obsidian-skills --scope user      # or --scope project

# grok — marketplace route, then install from the TUI Marketplace tab
grok plugin marketplace add <source>
grok plugin marketplace list                               # shows the source and the plugins it exposes
# direct source install instead (git URL, GitHub shorthand or local path — never plugin@marketplace):
grok plugin install Xia-Ataraxia/obsidian-skills

# hermes — tapped form, one package at a time
hermes skills tap add Xia-Ataraxia/obsidian-skills
hermes skills install Xia-Ataraxia/obsidian-skills/<name>  # tapped: no skills/ segment
hermes skills update
# without the tap, the identifier carries the in-repo path:
hermes skills install Xia-Ataraxia/obsidian-skills/skills/<name>
# repo-local project skills load only after: hermes skills trust

# cursor, agent-skills
# UNSUPPORTED: no self-serve native plugin or marketplace route. Use the directory import below.
```

Every `native` run ends with the same line: *"Route confirmed is not install verified. Nothing above has been executed, and no runtime has loaded this package as a result of running this script."*

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
| Interruption | `INT`/`TERM` stop the run where it is and the status is 128 plus the signal number. An interrupted copy never reports success and never publishes the package it was working on. The private staging it retains is named in the report with its `SKILL.md` quarantined as `SKILL.unpublished`; cleanup of that staging may be incomplete, and packages reported as installed before the signal stay published. |
| Writes | Anchored route directories, private staging and selected package destinations only. No profile configuration, marketplace registry, tap list, plugin cache or lockfile is changed. |
| Network | None. The installer never reaches the network and never runs a runtime CLI. |
| Naming | A directory copy is always labelled a generic Agent Skills import, never a native plugin install. |

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Completed: `routes`/`skills`/`native` printed, or a copy plan that is clean (dry run) or fully applied and read back. |
| 1 | Refused: unknown runtime, illegal or undeclared skill name, symlinked source package, path escape, destination-root violation, a collision in the pre-flight report, a package that failed post-copy verification, or a missing python3/copier. |
| 2 | Usage error: conflicting, repeated, misplaced, or empty-valued options. |
| 128+N | Interrupted by signal N (130 for `INT`, 143 for `TERM`). The package in progress is never published; retained private staging is named on stderr, cleanup of it may be incomplete, and earlier published packages remain. |

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

`./install.sh skills` reports each of the nine declared packages as `[present]`, `[BROKEN ]` (a directory without `SKILL.md`), or `[absent ]`, prints how many are installable from the checkout, and closes by restating that each package stands alone — no router, no dispatcher, no shared runtime. The nine declared names are fixed in the installer, and a name outside that list is refused:

`obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, `obsidian-mermaid`, `obsidian-visualize`, `obsidian-cli`, `obsidian-clipper`, `obsidian-doctor`, `obsidian-sync`.

Presence is a property of the checkout you are holding. At the time this file was written the command reported **9 of 9** installable, every package `[present]`. Run it yourself rather than trusting that number; a release is complete only when all nine still report `[present]` in the tree being published.

## Support limits

- **No native install has been executed or verified on any runtime.** Every `plugin-marketplace` and `registry-tap` row is a confirmed route, not a verified install. No runtime has been observed discovering, loading, or advertising these packages.
- **Nothing is published.** No marketplace entry, registry tap, release archive, or remote source exists for this candidate, so the published-repository command form cannot resolve yet.
- **Local tests are not deployed installation evidence.** The installer suite exercises disposable roots, collision and path-boundary cases, byte readback and failure preservation. No native runtime was installed or fresh-loaded.
- **Platform.** `install.sh` is POSIX `sh` and was exercised on macOS (arm64). Windows and other shells are untested. `copy` additionally needs python3 3.8+ and the `openat`-style calls it exposes (`os.open(..., dir_fd=)`, `O_NOFOLLOW`, `O_DIRECTORY`); the copier checks for them at startup and refuses on a platform that lacks them instead of writing unanchored. That refusal path has not been exercised on such a platform, because none was available here.
- A directory import copies package files. Whether a runtime then discovers, loads, and advertises them is a property of that runtime and has not been verified here — see [verification-matrix.md](verification-matrix.md).

## Reproducing this matrix

```sh
./install.sh routes
./install.sh skills
for r in claude codex gjc grok hermes cursor agent-skills; do ./install.sh native --runtime "$r"; done
./install.sh copy --runtime cursor --skill all --scope project --project-root "$(mktemp -d)"   # dry run
```

These commands print absolute paths for your own home directory and checkout; this document uses `~`, `<source>`, and `<project-root>` placeholders instead.
