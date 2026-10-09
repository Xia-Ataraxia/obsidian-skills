<p align="center">
  <img src="assets/brand/hero.svg" alt="secondbrain-skills: twenty-six independent Agent Skills for Obsidian vaults, nine native and seventeen knowledge packages" width="880">
</p>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a>
</p>

# secondbrain-skills

Twenty-six Agent Skills that let an agent run an Obsidian vault as a second brain: collect a source, keep the original, compile it into a wiki, and answer from it with citations.

Each package is one `SKILL.md` that owns one job. There is no root skill, no dispatcher and no shared runtime. Your agent loads the package the task needs and nothing else.

```sh
git clone https://github.com/Xia-Ataraxia/secondbrain-skills
cd secondbrain-skills
./install.sh copy --runtime claude --skill all --scope user --apply
```

Then ask in plain language: *"Ingest this article."*

## How it works

<p align="center">
  <img src="assets/demo/workflow.svg" alt="Three-step workflow: inspect a synthetic field note, select the independent format owner, verify structure and read the result back" width="880">
</p>

<p align="center"><sub>Synthetic illustration drawn for this repository. It is not a screenshot.</sub></p>

- **The skill carries the judgment.** What to select, how to classify and when to stop are written in Markdown. Scripts answer a single question and never gate a run.
- **The original survives.** A source is preserved verbatim as a Raw note before anything is written about it.
- **Knowing a format is not permission.** A package writes only to an exact destination the task authorized, then reads the result back.
- **Missing evidence is never success.** A parse is not a render, and an exit code is not a write. Each package says which level it reached.

## Knowledge packages

The loop: `capture` → `inbox` → `ingest` → `query`.

| Package | What it does |
| --- | --- |
| `capture` | Saves selected tabs, URLs, files, conversations or agent sessions as Inbox candidates. |
| `inbox` | Lists, previews and counts Inbox candidates, then hands a selection to `ingest`. |
| `ingest` | Preserves one source as a Raw note and compiles Wiki pages, Maps and an index from it. |
| `query` | Answers from existing notes with checked quotations and Obsidian deeplinks. |
| `verify` | Reviews selected claims against their sources. |
| `audit` | Samples a bounded scope for quality risks and states its coverage. |
| `lint` | Checks a bounded scope for structure, citations, properties and links. |
| `status` | Reports read-only counts, backlog and snapshot age. |
| `reindex` | Refreshes the search index for one audited collection. |
| `refresh-context` | Re-derives agent context snapshots from named sources. |
| `onboard` | Sets up a new vault, or previews additive changes to an existing one. |

Six more packages hold the stance that the eleven above work from.

| Package | What it holds |
| --- | --- |
| `principle-respect-des-fonds` | Who created a source, and whether it is primary or secondary. |
| `principle-original-order` | Keeping source sequence and verbatim content. |
| `principle-hierarchical-management` | Placing a record from collection down to item. |
| `principle-collective-description` | Describing a group, a Map or coverage. |
| `principle-skill-creating` | What a skill keeps in Markdown and what it hands to templates, thin scripts and agents. |
| `secondbrain-mode` | Optional stance for multi-package work: delegate to subagents, then review independently. |

## Obsidian packages

| Package | What it owns |
| --- | --- |
| `obsidian-markdown` | Obsidian Flavored Markdown: wikilinks, embeds, callouts, properties, tags, block references. |
| `obsidian-bases` | `.base` database views: filters, formulas, summaries, grouping and the function reference. |
| `obsidian-canvas` | JSON Canvas `.canvas` files: nodes, edges, geometry and stable IDs. |
| `obsidian-mermaid` | Mermaid blocks that render in the build your app ships. |
| `obsidian-visualize` | Choosing the visual form for a note and building `.excalidraw.md` scenes. |
| `obsidian-cli` | The official `obsidian` binary: read, create, search, move and audit. |
| `obsidian-clipper` | Web Clipper templates, selectors and variables. |
| `obsidian-doctor` | Plugin and Templater failure diagnosis from sanitized evidence. |
| `obsidian-sync` | The headless `ob` client for Obsidian Sync. |

## Install

`install.sh` copies packages into a runtime's skill directory. A dry run is the default, it never reaches the network, and an existing file at any destination refuses the whole run.

```sh
./install.sh skills                                        # the packages in this checkout
./install.sh copy --runtime cursor --skill all --scope user        # dry run
./install.sh copy --runtime claude --skill ingest \
  --scope project --project-root ~/work/notes --apply      # one package, one project
./install.sh native --runtime hermes                       # print the native route
```

Supported runtimes are `claude`, `codex`, `gjc`, `grok`, `hermes`, `cursor` and `agent-skills`. Native plugin and tap commands, skill directories and requirements for each are in [docs/install-matrix.md](docs/install-matrix.md).

## What is verified

The nine Obsidian packages were installed natively on Claude Code and on Hermes, and exercised against an isolated Obsidian 1.12.7 profile. The knowledge packages pass the local format checks only; no runtime load of them is recorded. Do not install the `v0.1.0` tag on Hermes.

Every result, its revision and its limits are in [docs/verification-matrix.md](docs/verification-matrix.md). Safety and data handling are in [docs/security-and-privacy.md](docs/security-and-privacy.md).

## Repository layout

```
skills/<name>/SKILL.md   one package; everything else sits in a subfolder beside it
install.sh               collision-checked copy installer and route table
scripts/                 inventory audit and contract sync
docs/                    naming, contracts, install and verification matrices, security
AGENTS.md                repository contract for contributors and agents
```

## Acknowledgements

- **[Yohan Koo (구요한)](https://github.com/johnfkoo951/cmds-llm-wiki)**, cmds-llm-wiki. The knowledge packages take their operation set and LLM-wiki workflow from it. This is design inspiration only; no file or text was copied.
- **[Andrej Karpathy](https://github.com/karpathy)**, the LLM Wiki pattern that cmds-llm-wiki builds on.
- **[Steph Ango (kepano)](https://github.com/kepano/obsidian-skills)**, obsidian-skills (MIT). `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas` and `obsidian-cli` started from it and were modified.
- **[Jonghak Seo](https://github.com/Jonghakseo/pi-extension)**, pi-extension (MIT). The inspection lint and the skeleton and style references in `obsidian-visualize` are adapted from it.

No endorsement by any of them is claimed. "Obsidian" names the third-party application these skills target.

## License

MIT. See [LICENSE](LICENSE); upstream grants are reproduced in [NOTICE](NOTICE), and source revisions and open rights questions are in [PROVENANCE.md](PROVENANCE.md). Art in `assets/` is original work recorded in [assets/asset-ledger.json](assets/asset-ledger.json).
