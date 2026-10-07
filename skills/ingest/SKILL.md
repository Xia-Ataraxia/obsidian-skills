---
name: ingest
description: Preserves and compiles explicitly selected source evidence into Raw and source-grounded Wiki knowledge. Use for ingest this URL, compile this file, ingest pasted text, create or update a book note from a Yes24/Aladin URL, ISBN or title (책 노트, 독서 노트, 목차 넣어줘), process selected book chapters, analyze a paper, or append an attributed Persona stance. Direct ingest does not require capture. Not for automatic source collection, knowledge queries, corpus indexing, creating personal profiles, or editing undesignated research questions.
metadata:
  version: "0.3.0"
---

# Ingest

Turn the selected evidence into reusable knowledge while retaining the original, its limits, and its identity.

## Output contract

Return the exact Raw path, source identity, purpose, obtained range, fidelity and known missing ranges, plus the actually written or reused Wiki/hub, analyses, Concept connections and readback hashes.
Follow the shared [field contract](references/contract.md).
Original Content remains evidence, and agent interpretation stays in separate labelled sections or notes.
Unknown purpose permits preservation, not automatic compilation.
An incomplete source stays incomplete; file existence and successful extraction are not coverage proof.

Re-ingestion reuses a proven source, never a surname/year or title match.
Additional selected evidence can be appended under exact update approval without replacing the earlier Raw body.
Report planned effects separately from materialized writes and partial failures.
An unavailable extractor, converter, template, source, permission or app check remains an explicit gap.

## Resolve the invocation

Read the destination vault's actual AGENTS, property, placement, relationship and template owners.
Resolve exact source scope, output paths, creation effects and existing-note append diffs from those owners and the request; a package does not grant authority.
Reuse the task's stated purpose instead of asking for it again.
Do not require a capture prerequisite, a counterpart vault, a policy plugin or an installed shared runtime.

Keep input designation, material kind and extraction method on separate axes.
Read only the branch in this table:

| Material | Reference |
| --- | --- |
| Article, news, static HTML | [articles](references/articles.md) |
| Video, timestamps, transcript | [videos](references/videos.md) |
| Repository, pinned revision, selected tool | [repositories](references/repositories.md) |
| Mail, thread, attachment | [mail](references/mail.md) |
| Messenger, web AI conversation, selected session | [conversations](references/conversations.md) |
| Book note, bibliography, TOC, selected chapters | [books](references/books.md) |
| Paper, methodology, citation, hub/atoms/Concept | [papers](references/papers.md) |

## Compile selected evidence

Read the obtained material and preserve code, quotations, image/attachment references and conversions.
Identify claims, independent reusable information, counterevidence and gaps against the owner's purpose.
Write semantic synthesis as an agent, not a string-matching summary or an extraction-size score.
Every analysis names its actual source and citation location; the helper checks quote presence, not entailment.
Review the claims against the complete selected range before reporting them as supported.

Inspect bounded existing-source and Concept candidates before choosing new identities.
Reuse an existing Concept through an exact approved append; preserve its unknown metadata and human sections.
Resolve existing Entity, Guide, Map or MOC relationships only when relevant and designated, never manufacture bridge notes or index/log effects.
For Book and Paper keep incomplete coverage visible instead of substituting a fixed output count for analysis.

Connect only a user-designated existing RQ, manuscript or Wiki Persona.
Never create an RQ, Persona, People note or operational profile as an ingest side effect.
Append each attributed Persona citation and stance with date, source identity, quotation and anchor; preserve earlier or conflicting stances rather than asserting a timeless belief.

## Local filesystem surface

Use `python3 scripts/ingest.py --vault "$VAULT" --request "$REQUEST"` to plan, then add `--apply` only with exact approval.
Read [the interface](references/interface.md) first.
For one selected Inbox batch, use `--handoff "$HANDOFF" --request "$MAPPING"` with the actual `inbox/handoff@1` and [explicit batch mappings](references/batches.md).
The common purpose arrives once, every member stays digest-bound, and all output effects are planned and authorized before any write.
The CLI handles direct UTF-8 URL/file/text inputs and the actual capture candidate format.
It requires existing destination parents and accepts only caller-designated bounded catalog paths.
It creates Raw/hub/analysis artifacts and performs approved additive appends; it does not synthesize meaning, authenticate an approval, execute templates, query private runtimes or perform app operations.

The local candidate includes a [web source validator](scripts/web-source-validate.py) and a [YouTube transcript extractor](scripts/youtube-transcript-extract.py) transferred from bstack.
Read the article or video reference before invoking them; neither grants vault writes or proves whole-source completeness.
The Book branch adds two bibliographic fetchers transferred from bstack, [Yes24 metadata](scripts/fetch_yes24.py) and [Aladin TOC images](scripts/fetch_aladin_toc.py); read the books reference before invoking them.
Their local transfer is authorized, but origin redistribution rights are unconfirmed. The source repository's provenance record identifies the five transferred files and their exact revision; no blanket package licence is asserted here.
For live app-managed mutations compose `obsidian-cli` by identity and use its actual approved surface rather than treating this filesystem helper as an app adapter.
Compose capture/inbox for requested candidate selection, query for requested retrieval or answers, and reindex for a separately requested index change.

## Verification

Inspect the actual JSON status and exact destination readback, not exit 0 alone.
Check non-target preservation, same-source reuse, citation anchors, incomplete ranges and the Book/Paper branch state.
A materialized local fixture result is not an installed skill load, Obsidian render, Sync result or permission for live writes.
Stop with the requested outputs and exact remaining gaps; do not delete sources or trigger indexing, reporting, sending or deployment.

## Requirements

The local helper uses Python 3.8 or later and the standard library.
URL reads support UTF-8 static HTML/plain text/Markdown and have a bounded network timeout.
Unsupported documents need an actually performed conversion with original attachment retention; login and JavaScript pages need a separately authorized acquisition tool or supplied export.
The web validator uses only the standard library. The transcript extractor optionally invokes `defuddle` and `yt-dlp` and contacts the public Defuddle gateway and YouTube oEmbed for the designated video.
The book fetchers run through `uv` with their declared dependencies and contact the public Yes24 or Aladin storefront for the selected book only.
Those acquisitions require the actual selected source and authorization; no install, login or network acquisition happens merely by loading the skill. Missing dependencies and unexercised external extraction remain unavailable or unverified, not a pass.
