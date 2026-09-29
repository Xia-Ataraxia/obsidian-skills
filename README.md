<p align="center">
  <img src="assets/brand/hero.svg" alt="Obsidian Skills — nine independent Agent Skills for Obsidian vaults" width="880">
</p>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a>
</p>

# Obsidian Skills

Nine independent Agent Skills for working inside an Obsidian vault: Markdown, Bases, Canvas, Mermaid, visual form selection, the official CLI, Web Clipper, vault diagnosis, and headless Sync.

Every package is a self-contained `SKILL.md` with its own references and scripts. There is no root skill, no dispatcher, no shared runtime, and no compatibility alias — your agent loads the one package the task needs, and nothing else.

> **Status — 0.1.0, local and unreleased.**
> This candidate has not been published to a marketplace or registry and no release archive was produced. Each route below names its documentation or local CLI evidence — but a confirmed route is not a verified install: native installation, loading and advertisement remain unverified. Where a runtime documents a local source (Claude Code, Codex, Grok), the native route can point at your checkout; otherwise use the Agent Skills directory import (`./install.sh copy`).

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

Run `./install.sh skills` to see which of the nine are present in your checkout.

## Install

### 1. Start from a local checkout

This release is local and unpublished, so onboarding begins with the checkout you already have. Nothing below reaches the network.

```sh
cd obsidian-skills
./install.sh skills      # which of the nine packages are present here
./install.sh routes      # every runtime's official route, manifest and skill directory
```

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

`./install.sh native --runtime <id>` prints one runtime's native commands, together with the evidence each route was confirmed from, and executes none of them. `<source>` below is `Xia-Ataraxia/obsidian-skills` once published, or the path to this checkout while 0.1.0 is unreleased.

| Runtime | Route kind | Manifest in this repo | Skill dirs — user / project | Native route (printed, never executed) |
| --- | --- | --- | --- | --- |
| `claude` — Claude Code | plugin-marketplace | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | `~/.claude/skills` / `.claude/skills` | `claude plugin marketplace add <source>` → `claude plugin install obsidian-skills@obsidian-skills` (`--scope user\|project\|local`, default user) |
| `codex` — Codex / ChatGPT desktop app | plugin-marketplace | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | `~/.agents/skills` / `.agents/skills` | `codex plugin marketplace add <source>` → `codex plugin add obsidian-skills@obsidian-skills`; the ChatGPT desktop Plugins Directory is the install surface — restart the app after adding |
| `gjc` — GJC (Gajae Code) | plugin-marketplace | `.claude-plugin/marketplace.json` | `~/.gjc/agent/skills` / `.gjc/skills` | `gjc plugin marketplace add Xia-Ataraxia/obsidian-skills` → `gjc plugin install obsidian-skills@obsidian-skills --scope user`; its help documents only `<source>`, so no local-path form is claimed |
| `grok` — Grok Build | plugin-marketplace (documented Claude Code compatibility) | `.claude-plugin/marketplace.json` — no Grok-specific manifest exists | `~/.grok/skills` / `.grok/skills` | `grok plugin marketplace add <source>`, then install from the TUI Marketplace tab; direct source install is `grok plugin install Xia-Ataraxia/obsidian-skills` (git URL, GitHub shorthand or local path — never `plugin@marketplace`) |
| `hermes` — Hermes Agent | registry-tap (one unit per skill) | none | `~/.hermes/skills` / `.hermes/skills` | `hermes skills tap add Xia-Ataraxia/obsidian-skills` → `hermes skills install Xia-Ataraxia/obsidian-skills/<name>` → `hermes skills update`; without the tap the identifier carries the path: `…/obsidian-skills/skills/<name>`; project skills load only after `hermes skills trust` |
| `cursor` — Cursor | skill-directory | none | `~/.cursor/skills` / `.cursor/skills` | **No self-serve native route:** its Marketplace is submission-reviewed, team marketplaces are Teams/Enterprise, and an Agent Plugin needs a root `plugin.json` this package does not ship. Use the directory import. |
| `agent-skills` — vendor-neutral | skill-directory | none | `~/.agents/skills` / `.agents/skills` | **No native route:** the specification defines the package format only. Codex, Cursor, and Grok all read `~/.agents/skills`, so this is the portable user-level import. |

Two limits apply to every row:

- **Route confirmed is not install verified.** Each row carries its own documentation or local CLI evidence; GJC uses installed CLI evidence, not a public documentation claim. No native installation route has been executed or observed loading this package.
- **Nothing is published.** The `Xia-Ataraxia/obsidian-skills` form assumes a published repository. Until then, use the local-checkout source where the runtime documents one (Claude Code, Codex, Grok) or the directory import, which works for every runtime.

First use after any install: ask your agent for the task in plain language and name the package if it does not pick one, e.g. *"Use `obsidian-canvas` to lay these notes out as a map."* GJC advertises an installed package as `obsidian-skills:<name>`; how other runtimes surface an installed package is not claimed here.

### Requirements

| For | You need | Probed here |
| --- | --- | --- |
| Anything that renders or indexes | Obsidian desktop app | 1.12.7 (isolated neutral profile) |
| `obsidian-cli` | The official `obsidian` CLI on `PATH` | 1.12.7 (installer 1.12.7) |
| `obsidian-doctor`, `obsidian-visualize` scripts | Python 3.9+, standard library only | executed on Python 3.14.7; 3.9 compatibility is not runtime-tested |
| `obsidian-clipper` | Obsidian Web Clipper browser extension | not installed, not exercised |
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

**Passed — local, isolated, neutral fixtures** (report: [tests/evidence/native-app.json](tests/evidence/native-app.json))

- Official CLI 1.12.7 against an isolated synthetic vault: `create` → `search` → `move` → read back at the new path, with the old path gone; a move from a missing source created nothing. A destination collision preserved the source, destination and unrelated note hashes.
- Obsidian 1.12.7 desktop app, isolated profile: a partial Markdown property edit with the unrelated property and body preserved byte-for-byte; `Field.canvas` resolved from `Field.md`; a Bases view applying filter, group, sort, and limit (2 rows, archived note absent, source notes unchanged) and reporting a malformed `.base` as unparseable; a canvas extended to three nodes and two labelled edges with the existing nodes preserved; a Mermaid flowchart rendered as SVG, and an unknown diagram type reported as an error instead of failing silently.
- Both READMEs render locally (markdown-it and Chromium): images load with their alt text and nothing overflows horizontally at 1200 px.

**Limits inside those passes — read them before trusting a green result**

- The CLI exits 0 even when it prints an error, e.g. `Error: Destination file already exists!`. Treat the output and a readback of the destination as proof, never the exit status.
- An invalid Bases expression produced 0 results with an error-class filter indicator rather than a clear parse error; empty rows are not successful validation.
- One app version, one profile, one small synthetic vault, single runs. Rendering on a public repository host has not been executed.

**Not attempted — do not read these as supported**

- No native plugin or marketplace install on any runtime; nothing published anywhere; no proof that a runtime discovers or advertises these packages.
- Web Clipper extension not installed; no page captured.
- Excalidraw plugin not installed; the scene builder is static validation only and proves nothing about rendering.
- No Obsidian Sync pairing, network transfer, daemon run, or recovery.

**Passed — local automated checks**

- Package isolation, format contracts, helper behavior, disposable installer and rollback cases, privacy, source ownership and original asset checks passed. The two pinned source checkouts were audited: 50 files, 135 units and nine unique feature owners. See the verification matrix for reproducible commands and evidence limits.
- Synthetic browser selectors passed and selector drift was detected. A public-page selector failed and capture stopped; this is not extension or live-capture success. Headless 0.0.14 returned exit 3 for an unpaired disposable directory; no account or network operation was run.

## Repository layout

```
skills/obsidian-*/       one self-contained package each (SKILL.md, references/, scripts/)
install.sh               route table, collision-checked copy installer
assets/                  original brand and demo art + asset-ledger.json
docs/                    install matrix, verification matrix, security, cutover
tests/                   isolated candidate test suite (see requirements-dev.txt)
scripts/audit_inventory.py   responsibility-unit audit
AGENTS.md                repository contract for contributors and agents
```

## License and attribution

MIT — see [LICENSE](LICENSE), which carries both copyright notices.

Material in `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, and `obsidian-cli` is imported from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) at commit `3ccff5338ea700537839b21900aa5358a0402c98` (MIT, Copyright © 2026 Steph Ango), then modified. The other five packages are original work authored here. Each package's `CHANGELOG.md` records the exact source revision, the files taken, and every modification made to them.

Brand and demo art in `assets/` is original vector work authored for this repository, with per-file creator, origin, and rights recorded in [assets/asset-ledger.json](assets/asset-ledger.json). No vendor logo, icon set, or application screenshot is included. "Obsidian" names the third-party application these skills target; no affiliation or endorsement is claimed.
