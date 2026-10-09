<p align="center">

> **Evidence boundary:** Hermes native installs resolved public main at `c22ce26bae518e7973f078cac972ea88707b8e79`; installed bytes were compared afterwards. A local clone checkout does not pin remote tap/install commands. The operator reports 45 installations in five existing local user profiles and a downstream consumer update; fresh task responses cover only CLI/Sync. The immutable `v0.1.0` refusal was two `skills-guard-v6` `credential_exposure` false positives on fake nonce strings, not real credentials or a semantic execution verdict. No scanner bypass was used.
  <img src="assets/brand/hero.svg" alt="Obsidian Skills: twenty-four independent Agent Skills for Obsidian vaults, nine native and fifteen knowledge packages" width="880">
</p>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a>
</p>

# Obsidian Skills

Twenty-four independent Agent Skills, the `secondbrain-skills` collection. Nine native packages work with Obsidian itself. Fifteen knowledge packages include the eleven task owners below and four independently usable archival principles. The four new principles are local candidate additions, not part of the historical published pin or runtime evidence.

> **Current published source.** All twenty packages, including the qmd parser fix, are public in the 0.3.0 release merge commit `c8c3a63d71a732eb7e5bcc39124fac5313937ddc` in <https://github.com/Xia-Ataraxia/secondbrain-skills>. The older pins and runtime results below are historical evidence, not verification of this current source. The historical `v0.1.0` tag is unchanged; the current collection release identity is `0.2.1`, carried by every plugin manifest so that a host which installed `0.1.0` sees the upgrade. The recommended source pin is moved to each release's merge commit by a follow-up docs-only commit, because a commit cannot name its own hash.

Every package is a self-contained `SKILL.md` with its own references and scripts. There is no root skill, no dispatcher, no shared runtime, and no compatibility alias — your agent loads the one package the task needs, and nothing else.

> **History — 0.1.0 public prerelease, superseded by a corrected public pin. The current release is 0.3.0 (see above).**
> Published at <https://github.com/Xia-Ataraxia/obsidian-skills>. Tag `v0.1.0` (prerelease) sits at the immutable commit `0e658b5a09ac4c789392ac634dcff8a195fa3116`; it stays immutable and is **not** retagged. **Install from the corrected commit `c22ce26bae518e7973f078cac972ea88707b8e79`** — the verified installation source revision — and not from the tag: the `v0.1.0` tree still ships the old `obsidian-visualize` eval snippets with a hardcoded placeholder run identity — the quoted strings caused two skills-guard-v6 credential_exposure false positives, with no real credentials or semantic execution verdict — and a real Hermes install flagged that package as **dangerous** and left it **`Not installed`** while the CLI still exited **0**. Only `obsidian-visualize` differs between the two commits; the other eight package trees are byte-identical. Verified since publication: both public articles render on the repository host with the two original SVGs loaded and their alt text intact; **two native routes have now been executed** — Claude Code, **isolated consumer project scope only**, from a detached clone of `0e658b5a…`, where 3 of the 9 packages were exercised; and Hermes, from `c22ce26ba…`, into five generic operator profiles, where all nine packages registered **45/45 SAFE** under the skills guard (`skills-guard-v6`) with no force or override, every installed package tree matched the pin byte-for-byte on a recursive non-hidden comparison, both the tap-qualified and the source-qualified registration identifiers resolved, and five fresh read-only `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills` sessions kept the desktop app/official-CLI Sync surface distinct from the headless `ob` client with no app, vault, network, or account operation. In an isolated app profile Templater 2.19.3 and Excalidraw 2.27.3 produced real plugin output. Web Clipper 1.7.1 was installed in a disposable browser profile — an initial no-page-target attach was recovered — and its popup extracted a real page into the note preview; only delivery into a vault stays unverified, because *Add to Obsidian* was never fired while the destination read *Last used*. Still unverified: the three unrun native routes (Codex, GJC, Grok), native discovery for Cursor and vendor-neutral Agent Skills — which have no native route at all — task exercise of the seven packages that were registered on Hermes but never invoked, Hermes project-scope loading after `hermes skills trust`, any write against a protected or production vault, complete ownership migration, retirement of an old owner, and any live Sync account. For every route except those two, a confirmed route is still not a verified install, and a registration is not an invocation. Where a runtime documents a local source (Claude Code, Codex, Grok), the native route can point at a clone pinned to `c22ce26ba…`; otherwise use the Agent Skills directory import (`./install.sh copy`).

---

## Why it exists

- **One owner per format.** A wikilink question goes to `obsidian-markdown`; a `.canvas` graph goes to `obsidian-canvas`. No package silently answers for another, so its answer is auditable.
- **Capability is not permission.** Knowing a format never authorizes a write. Each package requires an exact destination, an authorized effect, and a readback from the path that was actually changed.
- **Evidence levels stay separate.** A parse is not a render, a file on disk is not proof the app indexed it, and an exit code is not proof of a write. Packages say which level they reached.
- **Unrelated content survives.** Partial edits preserve non-target notes, frontmatter, IDs, and attachments — and say so with hashes rather than assurance.

<p align="center">
  <img src="assets/demo/workflow.svg" alt="Three-step workflow: inspect a synthetic field note, select the independent format owner, verify structure and read the result back" width="880">
</p>

<p align="center"><sub>Synthetic illustration drawn for this repository — not a screenshot, and not a claim of live rendering.</sub></p>

## The nine packages

| Package | What it owns | First use |
| --- | --- | --- |
| `obsidian-markdown` | Obsidian Flavored Markdown: wikilinks, embeds, callouts, properties, tags, block references, math, footnotes; exact partial edits with non-target preservation and readback. | *"Fix the properties and callouts in `Notes/Inbox.md` without touching the rest."* |
| `obsidian-bases` | `.base` database views: the YAML schema, filters, formulas, summaries, table/cards/list/kanban/map views, grouping, sort and limit, plus the complete local function reference. | *"Build a Base view over my project notes grouped by status."* |
| `obsidian-canvas` | JSON Canvas 1.0 `.canvas` documents: node and edge schemas, geometry, colors, stable IDs, validation. | *"Turn these five notes into a canvas map with labelled edges."* |
| `obsidian-mermaid` | Mermaid blocks that render in the Mermaid build your app actually ships: family choice, version-gated syntax, fallbacks, render QA. | *"This mermaid block shows a parse error in Reading view — fix it."* |
| `obsidian-visualize` | Choosing the visual form for a note (table, canvas, Mermaid, Excalidraw) and building deterministic `.excalidraw.md` scenes with a stdlib script. | *"What is the right visual for this comparison, and draw it."* |
| `obsidian-cli` | The official `obsidian` binary: read, create, search, move, append, audit properties/tasks/tags/links, and the plugin/theme develop-test loop. | *"Create a note from the terminal and read it back from the exact path."* |
| `obsidian-clipper` | Obsidian Web Clipper capture: templates, selectors, variables, and page-to-note mapping. | *"Make a Clipper template that saves articles with source and author."* |
| `obsidian-doctor` | Plugin and Templater failure diagnosis from sanitized evidence, with a read-only classifier script. | *"Templater stopped firing on new notes — classify the evidence."* |
| `obsidian-sync` | The headless `ob` client (npm `obsidian-headless`) for Obsidian Sync: pairing, direction, one-shot or continuous runs, incident containment. | *"Set up pull-only headless sync on a server and keep it reversible."* |

## The fifteen knowledge packages

The eleven task packages are included in the published pin; the four principles are local additions. Historical runtime evidence remains bound to its original revisions.

| Package | What it owns |
| --- | --- |
| `capture` | Saves explicitly selected tabs, URLs, files, conversations, or session spans as Inbox candidates. |
| `inbox` | Lists, previews, and counts Inbox candidates, then hands a selected scope to `ingest`. |
| `ingest` | Preserves selected source evidence in Raw and compiles source-grounded Wiki notes. Direct ingest doesn't need `capture`. |
| `query` | Answers from existing notes with checked quotations, inherited sources, and exact Obsidian deeplinks. |
| `verify` | Reviews selected claims against checked evidence and prepares an approval-bound record. |
| `audit` | Samples a bounded scope for quality risks and states its coverage and limits. |
| `lint` | Checks a bounded scope for structure, citations, properties, links, and derived-index drift. |
| `status` | Reports read-only counts, backlog, and snapshot age from named roots. |
| `reindex` | Refreshes search derivations for one audited collection in an isolated named index. |
| `refresh-context` | Binds proposed derived context snapshots to exact source hashes and applies only approved paths. |
| `onboard` | Initializes an independent personal or knowledge vault from a reviewed candidate, or previews additive settings changes. |
| `principle-respect-des-fonds` | Distinguishes creators and keeps primary and secondary sources as separately attributed Raw captures. |
| `principle-original-order` | Preserves meaningful source sequence and verbatim captured content. |
| `principle-hierarchical-management` | Arranges records from collection to item using live destination policy. |
| `principle-collective-description` | Describes aggregate structure, context, coverage, and history. |

Each principle installs alone, carries no shared contract copy, and grants no write permission. Run `./install.sh skills` to see which of the twenty-four are present.

## Install

### 1. Start from the published pin, or the checkout you already have

```sh
git clone https://github.com/Xia-Ataraxia/secondbrain-skills
cd secondbrain-skills
git checkout c8c3a63d71a732eb7e5bcc39124fac5313937ddc   # current 0.3.0 release source (twenty packages)
./install.sh skills      # which of the twenty packages are present here
./install.sh routes      # every runtime's official route, manifest and skill directory
```

The current source pin above includes all twenty packages and the qmd parser fix. The older `c22ce26bae518e7973f078cac972ea88707b8e79` pin below records the nine-package Hermes installation; it is not the current collection. The historical `v0.1.0` tag is immutable and is not retagged.

The clone is the only step that reaches the network: `install.sh` never does, and never runs a runtime's own install or marketplace command. An existing local checkout works exactly the same way — the publication changes which sources resolve, not how onboarding works.

### 2. Copy packages into a runtime's skill directory (works today)

```sh
# Dry run is the default: prints a collision report, writes nothing.
./install.sh copy --runtime cursor --skill all --scope user

# Same plan, actually copied.
./install.sh copy --runtime cursor --skill all --scope user --apply

# One package into a consumer project instead of your user profile.
./install.sh copy --runtime claude --skill obsidian-markdown \
  --scope project --project-root ~/work/notes --apply
```

`--scope user` targets that runtime's user skill directory; `--scope project` targets `<project-root>/<runtime skill dir>` and refuses to target this checkout. A directory copy is a generic Agent Skills import — the installer never presents it as a native plugin install.

### 3. Native route per runtime

`./install.sh native --runtime <id>` prints one runtime's native commands, together with the evidence each route was confirmed from, and executes none of them. `<source>` below is the published `Xia-Ataraxia/secondbrain-skills`, or the path to a local clone checked out at the pinned commit.

| Runtime | Route kind | Manifest in this repo | Skill dirs — user / project | Native route (printed, never executed) |
| --- | --- | --- | --- | --- |
| `claude` — Claude Code | plugin-marketplace | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | `~/.claude/skills` / `.claude/skills` | `claude plugin marketplace add <source>` → `claude plugin install secondbrain-skills@secondbrain-skills` (`--scope user\|project\|local`, default user) |
| `codex` — Codex / ChatGPT desktop app | plugin-marketplace | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | `~/.agents/skills` / `.agents/skills` | `codex plugin marketplace add <source>` → `codex plugin add secondbrain-skills@secondbrain-skills`; the ChatGPT desktop Plugins Directory is the install surface — restart the app after adding |
| `gjc` — GJC (Gajae Code) | plugin-marketplace | `.claude-plugin/marketplace.json` | `~/.gjc/agent/skills` / `.gjc/skills` | `gjc plugin marketplace add Xia-Ataraxia/secondbrain-skills` → `gjc plugin install secondbrain-skills@secondbrain-skills --scope user`; its help documents only `<source>`, so no local-path form is claimed |
| `grok` — Grok Build | plugin-marketplace (documented Claude Code compatibility) | `.claude-plugin/marketplace.json` — no Grok-specific manifest exists | `~/.grok/skills` / `.grok/skills` | `grok plugin marketplace add <source>`, then install from the TUI Marketplace tab; direct source install is `grok plugin install Xia-Ataraxia/secondbrain-skills` (git URL, GitHub shorthand or local path — never `plugin@marketplace`) |
| `hermes` — Hermes Agent | registry-tap (one unit per skill) | none | `~/.hermes/skills` / `.hermes/skills` | `hermes skills tap add Xia-Ataraxia/secondbrain-skills` → `hermes skills install Xia-Ataraxia/secondbrain-skills/<name>` → `hermes skills update`; without the tap the identifier carries the path: `…/secondbrain-skills/skills/<name>`; project skills load only after `hermes skills trust` |
| `cursor` — Cursor | skill-directory | none | `~/.cursor/skills` / `.cursor/skills` | **No self-serve native route:** its Marketplace is submission-reviewed, team marketplaces are Teams/Enterprise, and an Agent Plugin needs a root `plugin.json` this package does not ship. Use the directory import. |
| `agent-skills` — vendor-neutral | skill-directory | none | `~/.agents/skills` / `.agents/skills` | **No native route:** the specification defines the package format only. Codex, Cursor, and Grok all read `~/.agents/skills`, so this is the portable user-level import. |

Four limits apply to this table:

- **Route confirmed is not install verified — with exactly two exceptions.** Each row carries its own documentation or local CLI evidence; GJC uses installed CLI evidence, not a public documentation claim. Two native rows have actually been executed. *Claude Code*, in an isolated consumer project: the marketplace add and `claude plugin install obsidian-skills@obsidian-skills --scope project` both returned success for version 0.1.0, installed from a detached clone of `0e658b5a…`, and 3 of the 9 packages answered fresh calls there. *Hermes*, from `c22ce26ba…`: `hermes skills tap add` followed by per-package `hermes skills install` registered all nine packages across five generic operator profiles — 45/45 reported SAFE by the skills guard (`skills-guard-v6`), with no force or override flag — each installed package tree compared byte-for-byte against the pin over a recursive non-hidden walk, and both the tap-qualified `Xia-Ataraxia/obsidian-skills/<name>` and the source-qualified `Xia-Ataraxia/obsidian-skills/skills/<name>` identifiers resolved. The three other native routes — Codex, GJC, Grok — have never been run. Cursor and vendor-neutral Agent Skills have no native route to run at all; their directory import copies files, which is not runtime discovery.
- **Registration is not invocation.** On Hermes, five fresh read-only sessions were run as `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills`; they kept the desktop app / official-CLI Sync surface distinct from the headless `ob` client, and performed no app, vault, network, or account operation. Only those two packages were exercised as tasks. The other seven registered cleanly and were never invoked, so their behavior under Hermes is unverified. Project-scope loading after `hermes skills trust` was not exercised either.
- **The published source resolves now, but not every published revision is installable everywhere.** `Xia-Ataraxia/obsidian-skills` points at a real public repository. Use the corrected pin `c22ce26bae518e7973f078cac972ea88707b8e79` from the status block. **Do not use the `v0.1.0` tag for a Hermes install:** that tree still carries the old `obsidian-visualize` eval snippets with a hardcoded placeholder run identity, the install flagged the package as dangerous, and the registry reported it `Not installed` even though the CLI exited 0 — one more case where an exit status is not a result. The tag is not retagged and no version was bumped to paper over this; the corrected commit is the pin. A clone pinned at that commit, or the directory import, still works for every runtime.
- **Printing a route is not installing it.** `./install.sh native` only prints the commands; it runs none of them, registers no marketplace or tap, and closes by saying so. Its two exceptions — the Claude Code and Hermes routes that were executed by hand — are stated there, in [docs/install-matrix.md](docs/install-matrix.md), and in [docs/verification-matrix.md](docs/verification-matrix.md). The published 0.1.0 artifact is immutable and is not retagged, so corrections made after that pin do not change what the tag contains.

First use after any install: ask your agent for the task in plain language and name the package if it does not pick one, e.g. *"Use `obsidian-canvas` to lay these notes out as a map."* In that isolated-project Claude Code install, the runtime advertised the packages as `obsidian-skills:<name>`: fresh `obsidian-skills:obsidian-cli` and `obsidian-skills:obsidian-sync` Skill calls were captured, and `obsidian-skills:obsidian-canvas` answered in a separate fresh response. Hermes addresses each package by its own registry identifier instead — one unit per skill, never a bundle — and `hermes chat --skills <name>[,<name>] --toolsets skills` selects them by bare package name. GJC documents the same `obsidian-skills:<name>` form from installed CLI evidence; how the remaining runtimes surface an installed package is not claimed here.

### Requirements

| For | You need | Probed here |
| --- | --- | --- |
| Anything that renders or indexes | Obsidian desktop app | 1.12.7 (isolated neutral profile) |
| `obsidian-cli` | The official `obsidian` CLI on `PATH` | 1.12.7 (installer 1.12.7) |
| `obsidian-doctor`, `obsidian-visualize` scripts | Python 3.9+, standard library only | executed on Python 3.14.7; 3.9 compatibility is not runtime-tested |
| `obsidian-doctor` against real plugin output | Templater plugin in the vault | 2.19.3 in an isolated synthetic vault: one synthetic success and one synthetic `is not defined` failure observed |
| `obsidian-visualize` rendered scenes | Excalidraw plugin in the vault | 2.27.3 in the same isolated vault: a five-element scene rendered in the actual plugin view |
| `obsidian-clipper` | Obsidian Web Clipper browser extension | 1.7.1 in a disposable browser profile: settings rendered, the shipped template imported, and a live page extracted in the popup; delivery into a vault is unverified |
| `obsidian-sync` | npm `obsidian-headless` (`ob`) and an Obsidian Sync account | existing 0.0.14: help and local unpaired-directory refusal only |
| Running the candidate test suite | `pip install -r requirements-dev.txt` (PyYAML) | Python 3.14.7 / PyYAML 6.0.3; local suite passed |

The installer front end is POSIX `sh`; `copy` requires Python 3.8+ and anchored filesystem operations. Atomic publication supports macOS/Linux, refusing unsupported platforms. Tested here on macOS arm64 with Python 3.14.7; Linux and Python 3.8 runtime behavior remain unverified.

## Safety

**The installer**

- Dry run is the default; copying requires `--apply`.
- It never reaches the network and never runs a runtime's own install, marketplace, or clone command.
- It never changes profile configuration: no `settings.json`, `config.toml`, tap list, registry, or lockfile. Writes include anchored route directories, private staging and selected package destinations. Verified staging is published atomically without replacement; generated caches are excluded.
- Every selected package is pre-flighted. An existing file, directory, symlink, or dangling symlink at any destination refuses the whole operation, and nothing is written — no partial copy.
- A later publication failure can retain named staging for recovery; its `SKILL.md` is quarantined as `SKILL.unpublished`. Warnings identify incomplete quarantine or cleanup. Earlier published packages remain. These protections address ordinary concurrent consumers, not hostile same-account interference with private staging.
- Path guards require a single lowercase skill-name segment, a destination contained in the resolved root, and a destination outside this source checkout.
- An unknown runtime is refused, never guessed (`REFUSED`, exit 1). Usage errors exit 2.

**The skills**

- A format skill is not write authorization. Resolve the exact vault, relative target, applicable live vault policy, and authorized effect first. No policy file is required, but missing authority or unresolved conflicts keep the work read-only.
- Missing app, plugin, CLI, or network evidence is never converted into success, and never justifies substituting an unrelated writer.
- Changes are read back from the exact destination; unrelated notes, frontmatter, IDs, and attachments are preserved and reported by hash.
- Examples are synthetic and no telemetry is shipped. Local helpers do not upload vault content. An explicitly authorized Sync or other network operation has its own data-transfer boundary; these skills do not promise that such an operation stays offline.
- Recovery restores approved source and configuration only. User notes are never reset, mirrored, deleted, or overwritten as a shortcut.

Details: [docs/security-and-privacy.md](docs/security-and-privacy.md).

## What is actually verified

Full matrix: [docs/verification-matrix.md](docs/verification-matrix.md). Route-by-route detail: [docs/install-matrix.md](docs/install-matrix.md).

### Local release candidate: twenty packages

These checks ran on the local candidate, not on a published revision. Each one says what level it reached.

- **Static registration.** The Claude plugin and marketplace manifests list the nine native packages and the eleven knowledge packages. A manifest entry is a declaration. It doesn't show that any runtime discovered or loaded a package.
- **Temporary materialization.** `./install.sh copy --runtime claude --skill all --scope project --apply` into a disposable project produced exactly twenty package directories, and every copied file matched the checkout byte for byte. A symlink at one package destination refused the whole run with exit 1, and the disposable tree was unchanged. A copy is a filesystem fact, not an install.
- **Local behavior.** The test suite and the inventory audit pass on an exact export of the candidate. Knowledge scenarios ran as scripts in temporary vaults: onboarding, direct ingest with a query deeplink, capture through Inbox to ingest, and additive onboarding with collision refusals.
- **Not established.** No runtime has loaded a knowledge package, and the native evidence below is the earlier, separate record for the nine published packages. Nothing here shows automatic discovery, app or plugin execution, Sync, deployment, or a deeplink opening in the app. A future runtime load is its own step with its own evidence.
- **Rights hold.** `ingest` carries two helpers and their tests transferred from a private source. Their origin rights are unconfirmed and public redistribution stays on hold, as [PROVENANCE.md](PROVENANCE.md) records.

### Earlier evidence for the nine native packages

**Passed — local, isolated, neutral fixtures** (report: [tests/evidence/native-app.json](tests/evidence/native-app.json))

- Official CLI 1.12.7 against an isolated synthetic vault: `create` → `search` → `move` → read back at the new path, with the old path gone; a move from a missing source created nothing. A destination collision preserved the source, destination and unrelated note hashes.
- Obsidian 1.12.7 desktop app, isolated profile: a partial Markdown property edit with the unrelated property and body preserved byte-for-byte; `Field.canvas` resolved from `Field.md`; a Bases view applying filter, group, sort, and limit (2 rows, archived note absent, source notes unchanged) and reporting a malformed `.base` as unparseable; a canvas extended to three nodes and two labelled edges with the existing nodes preserved; a Mermaid flowchart rendered as SVG, and an unknown diagram type reported as an error instead of failing silently.
- Both READMEs render locally (markdown-it and Chromium): images load with their alt text and nothing overflows horizontally at 1200 px. This is the prepublication record and is kept as history; the public-host evidence is separate, below.

**Passed — publication, public rendering and two native routes** (report: [tests/evidence/publication-canary.json](tests/evidence/publication-canary.json))

- The prerelease is public at the immutable commit `0e658b5a09ac4c789392ac634dcff8a195fa3116` that `v0.1.0` tags: tag object `04f9dfe25157040dd08a8d14158f8a5d2bbc50ca`, tree `10dff62e017df86883d5dd4042f065760e576346`, a downloaded release archive with SHA-256 `74d97b113a590d83bf082ba8c80a8f93b316da5c11cdfbca14d791c556cbb608`, and 5 commits / 57 trees / 95 blobs reachable and scanned. The corrected pin recommended above, `c22ce26bae518e7973f078cac972ea88707b8e79`, is a later public commit on the same repository; it carries no tag and none was created for it.
- Both the English and the Korean article were opened on the repository host in Chromium: each rendered, `assets/brand/hero.svg` and `assets/demo/workflow.svg` both loaded with their alt text present, and the repository-relative links resolved to paths that exist in the published commit. This is the public rendering that local rendering could not prove.
- Claude Code, **isolated consumer project** scope, installed from a detached clone of the `0e658b5a…` public commit: the native marketplace add and `claude plugin install obsidian-skills@obsidian-skills --scope project` both returned success for version 0.1.0, and the runtime then answered fresh `obsidian-skills:obsidian-cli` and `obsidian-skills:obsidian-sync` Skill calls, with `obsidian-skills:obsidian-canvas` answering in a separate fresh response. Those answers held the lines this repository claims: a CLI collision exiting 0 was not read as success, a missing headless configuration was not read as healthy network Sync, a dangling Canvas edge was rejected without inventing a node, and parsing stayed distinct from rendering. A non-target sentinel in the same project was unchanged afterwards. This remains the historical canary and stays pinned to `0e658b5a…`.

**Passed — Hermes native install and read-only sessions** (same report)

- The native Hermes registry-tap route was executed against the corrected public pin `c22ce26bae518e7973f078cac972ea88707b8e79`: `hermes skills tap add`, then one `hermes skills install` per package. All nine packages registered into each of **five generic operator profiles** — **45/45 reported SAFE** by the skills guard (`skills-guard-v6`), with no force or override flag used anywhere. This is the first install of these packages into real operator profiles rather than a disposable clone, and establishes actual local user-profile deployment, not complete ownership migration.
- Each installed package tree was compared against the source pin by a recursive walk over non-hidden entries; every file matched byte-for-byte, so what the registry holds is the pinned tree and not a mutated or partially written copy.
- Both registration identifier forms resolved: the tap-qualified `Xia-Ataraxia/obsidian-skills/<name>` and the source-qualified `Xia-Ataraxia/obsidian-skills/skills/<name>`.
- Five fresh **read-only** sessions were then run as `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills`. Each one kept the two Sync surfaces apart — the desktop app and official CLI on one side, the headless `ob` client on the other — instead of collapsing them into a single "sync" answer. **No app, vault, network, or account operation was performed in any of them.**
- **Only `obsidian-cli` and `obsidian-sync` were exercised as tasks.** The other seven packages registered and were never invoked; registration is not invocation, and their behavior under Hermes is unverified. `hermes skills trust`, which repo-local project skills require, was not exercised.
- **Finding — do not install `v0.1.0` on Hermes.** The immutable tag still ships the old `obsidian-visualize` step-4 handshake eval snippets with a hardcoded placeholder run identity. skills-guard-v6 reported two credential_exposure false positives on those fake nonce strings. No real credentials were present, and the scanner did not establish a semantic execution defect. The install flagged that package as **dangerous** and left it **`Not installed`** — while the CLI exited **0**. Read the registry state, never the exit status. `c22ce26ba…` requires the caller to substitute a freshly generated run identity instead; the other eight package trees are byte-identical between the two commits, and no retag or version bump was made.

**Passed — plugins in an isolated app profile** (same report)

- Templater 2.19.3, loaded in an isolated synthetic vault on Obsidian 1.12.7: a synthetic template produced `Synthetic templater result`, and a deliberately broken one failed with `missingSyntheticVariable is not defined`. Both the success and the error are real plugin output, and non-target notes were unchanged. Templater 2.25.1's manifest requires app 1.13.0, so the compatible 2.19.3 was installed rather than forcing a version.
- Excalidraw 2.27.3, same vault: a five-element scene opened in the actual plugin view — *Study* and *Evidence* text boxes connected by an arrow — and both the view and a screenshot of it were inspected. For that one scene the drawing helper reached rendered verification instead of static validation.

**Passed — Web Clipper extraction, with delivery still unverified** (same report)

- Web Clipper 1.7.1, taken from the official Chrome release archive, was installed into a separate disposable browser profile. The first browser attachment had no page target; that was recovered by creating an isolated inspection page, after which the native `Extensions.loadUnpacked` succeeded, the background service worker appeared, and the actual settings UI rendered.
- The shipped `clipping-template.json` imported as the *General clipping* template, and the built-in *Default* template was preserved alongside it.
- On `example.org`, the actual extension action popup selected *General clipping* and extracted the *Example Domain* title, the source URL, and the source text into the note preview. That is real extension execution against a real page, not a selector rehearsal.
- **Not activated: *Add to Obsidian*.** The destination still read *Last used*, so the clip was never delivered. Delivery into an exact vault and a readback of the created note remain unverified. No user browser profile and no vault note was changed.

**Limits inside those passes — read them before trusting a green result**

- The CLI exits 0 even when it prints an error, e.g. `Error: Destination file already exists!`. Treat the output and a readback of the destination as proof, never the exit status.
- An invalid Bases expression produced 0 results with an error-class filter indicator rather than a clear parse error; empty rows are not successful validation.
- One app version, one profile, one small synthetic vault, single runs.
- The public rendering is one host, one browser, one commit. It says nothing about other browsers, other hosts, or any later revision.
- The Claude Code fresh-load is one runtime in one isolated consumer project, installed from a disposable detached clone. It is not a production deployment, not another runtime, and not a consumer switch.
- The Hermes result is install, registration, and byte verification across five generic operator profiles, plus five read-only chat sessions that touched two packages. It establishes local deployment, not a vault or account operation, and not evidence for the seven packages that were never invoked.
- The plugin results are one app version, one isolated synthetic vault, and one version of each plugin. No production vault, plugin configuration, or account was involved.

**Not attempted — do not read these as supported**

- Beyond the Claude Code fresh-load and the Hermes install described above: the Codex, GJC and Grok native routes have never been run, and Cursor and vendor-neutral Agent Skills have no native route to run — their directory import copies files, which is not runtime discovery. Hermes was installed into existing local user profiles; universal production readiness is not claimed. Package-level exercise stays narrow: `obsidian-cli`, `obsidian-sync` and `obsidian-canvas` on Claude Code, and `obsidian-cli` and `obsidian-sync` on Hermes. No other package has been invoked inside a native runtime, on any runtime.
- No task run of `obsidian-markdown`, `obsidian-bases`, `obsidian-mermaid`, `obsidian-visualize`, `obsidian-clipper` or `obsidian-doctor` inside Hermes. They are registered there, and that is all that is claimed.
- The two native results sit at different revisions and are not evidence about each other. The Claude Code canary exists only at `0e658b5a…`; the Hermes install exists only at `c22ce26ba…`. No Claude Code install or fresh-load has been run at the corrected pin, and the only Hermes observation at the tag is the refused `obsidian-visualize` finding.
- A native downstream consumer update is reported; no old owner was retired, and no post-change audit of active old owners and callers exists — steps 5–7 of [docs/cutover.md](docs/cutover.md) are outstanding. A deployed consumer change is admitted in the source-local authoring path; that admission is its own step and is not covered by anything in this repository.
- No Obsidian Sync account pairing, remote-vault selection, network transfer, daemon run, or deployed recovery. A live account has still never been used.
- No production plugin incident was reproduced: the Templater and Excalidraw results come from a synthetic vault, not from a real failure on a real profile.
- Web Clipper delivery into a vault: *Add to Obsidian* was deliberately not activated while the destination read *Last used*, so clip delivery and the note readback that would prove it are unverified. Extraction is proven; delivery is not.

**Passed — local automated checks**

- Package isolation, format contracts, helper behavior, disposable installer and rollback cases, privacy, source ownership and original asset checks passed — 371 tests on the `0e658b5a…` tree that `v0.1.0` tags. `c22ce26ba…` adds caller-nonce cases to the drawing-helper suite; that tree's count has not been re-recorded here. The two pinned source checkouts were audited: 50 files, 135 units and nine unique feature owners. See the verification matrix for reproducible commands and evidence limits.
- Synthetic browser selectors passed and selector drift was detected. A public-page selector failed and that check stopped; it is a DOM-selector probe, not the extension evidence — the actual extension run is recorded above, and clip delivery stays unverified. Headless 0.0.14 returned exit 3 for an unpaired disposable directory; no account or network operation was run.

## Repository layout

```
skills/<name>/           one self-contained package each (SKILL.md, references/, scripts/)
install.sh               route table, collision-checked copy installer
assets/                  original brand and demo art + asset-ledger.json
docs/                    install matrix, verification matrix, security, cutover
tests/                   isolated candidate test suite (see requirements-dev.txt)
scripts/audit_inventory.py   responsibility-unit audit
AGENTS.md                repository contract for contributors and agents
```

## License and attribution

MIT — see [LICENSE](LICENSE), which carries both copyright notices.

Material in `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, and `obsidian-cli` is imported from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) at commit `3ccff5338ea700537839b21900aa5358a0402c98` (MIT, Copyright © 2026 Steph Ango), then modified. The other five native packages and the eleven knowledge packages are authored here, except for two `ingest` helpers and their tests, which were transferred from a private source with origin rights still unconfirmed; see [PROVENANCE.md](PROVENANCE.md). Each package's `CHANGELOG.md` records the exact source revision, the files taken, and every modification made to them.

The eleven knowledge packages take their operation set and LLM-wiki workflow from Yohan Koo (구요한)'s [cmds-llm-wiki](https://github.com/johnfkoo951/cmds-llm-wiki), which itself credits Andrej Karpathy's LLM Wiki pattern. This is design inspiration only: no files or text were copied, and because that repository publishes no license, nothing from it is redistributed here. No endorsement is claimed. See [PROVENANCE.md](PROVENANCE.md).

Brand and demo art in `assets/` is original vector work authored for this repository, with per-file creator, origin, and rights recorded in [assets/asset-ledger.json](assets/asset-ledger.json). No vendor logo, icon set, or application screenshot is included. "Obsidian" names the third-party application these skills target; no affiliation or endorsement is claimed.
