# Naming

How packages, their files and the collection are named. The layout is the Agent Skills layout; this page only fixes the names.

## The collection

The collection is `secondbrain-skills`: 9 native Obsidian packages and 17 knowledge packages (11 workflow packages, 4 archival principle packages, `principle-skill-creating` and the optional `secondbrain-mode` stance).

Today the manifests name the collection only as descriptive metadata:

- The Claude plugin and marketplace manifests carry it in the description, a keyword and `metadata.collection`, next to an empty `metadata.knowledgePackages` list that grows as knowledge packages land.
- The Codex plugin manifest carries it in the description and a keyword.
- The `.agents` marketplace carries it in the display name.

Every machine identity is `secondbrain-skills` since 0.3.0: the `name` field of each plugin and marketplace manifest. These fields move together.

The hosted repository is `Xia-Ataraxia/secondbrain-skills`. The native plugin identity is `secondbrain-skills@secondbrain-skills`; the former `obsidian-skills@obsidian-skills` identity (0.1.0–0.2.2) is retired, so uninstall it before installing the new identity.

## Packages

A package is one directory, `skills/<name>/`, whose `SKILL.md` declares the same `name`.

| Kind | Names | Rule |
| --- | --- | --- |
| Native | `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, `obsidian-mermaid`, `obsidian-visualize`, `obsidian-cli`, `obsidian-clipper`, `obsidian-doctor`, `obsidian-sync` | Owns one Obsidian format or tool. The names stay exactly as they are. |
| Knowledge | `capture`, `inbox`, `ingest`, `query`, `verify`, `audit`, `lint`, `status`, `reindex`, `refresh-context`, `onboard` | Owns one knowledge task. No `obsidian-` prefix. |

- A name is one lowercase path segment of letters, digits and single hyphens, at most 64 characters.
- A name says what the package is responsible for. It is a task (`ingest`) or a format (`obsidian-canvas`), never a role, a team or a version.
- There is no root skill, no dispatcher and no alias. An older concept name is not kept as a second name for a package; `compile` and `wiki` are not package names.
- Each capability has exactly one owning package.

## Files inside a package

Name a file for what it covers. The directory already says which package and which kind of resource it is, so the file name does not repeat either.

| Write | Not |
| --- | --- |
| `ingest/SKILL.md` | `ingest/ingest.md` |
| `ingest/references/papers.md` | `ingest/references/paper-ingest.md` |
| `capture/references/sessions.md` | `capture/references/capture-sessions-reference.md` |

- `SKILL.md` holds when to use the package, its inputs and outputs, its permissions, and the branches that need a reference. Detail goes to the reference a branch names.
- `references/<subject>.md` is one subject, read only when its branch is taken. A material type is named by the material in the plural: `articles.md`, `videos.md`, `repositories.md`, `mail.md`, `conversations.md`, `books.md`, `papers.md`.
- `scripts/` holds executable code. `assets/` holds static files that are reused as they are. `templates/` holds output shapes the package fills, and `agents/` holds subagent briefs.
- Use lowercase words joined by hyphens. No spaces, no dates, no version suffixes, no `final` or `new`.

## What is not copied into a package

- Vault policy and the vault's real templates stay in the vault. A package reads them at the destination; it does not ship a second copy as an asset or restate them in several `SKILL.md` files.
- A package links only to files inside itself. Another package is composed by naming its identity in prose, not by a relative path.
- Shared wording has one source. No text is duplicated across packages.
