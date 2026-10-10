# Frontmatter — single source

Based on Properties and 구요한 `/ingest` at commit `863ca43`. One meaning has one field. Read live policy before applying: its field set and `type` values win over the templates; the satellite Common Rules override must be approved; never modify the mothership Properties document.

## Type → role → template

| Role | Template | type (template default) | tags | status |
| --- | --- | --- | --- | --- |
| Raw | raw.md | article/video/paper/book/repo/mail/chat, matching material and live Type Map | reference/{type} | absent |
| Book Index Raw | book-index.md | book | reference/book | absent |
| Book chapter Raw | book-chapter.md | book | reference/book | stub → reading → completed |
| Entity | entity.md | entity | knowledge/entity, plus `person` for a person | absent |
| Concept | concept.md | concept | knowledge/concept | absent |
| Persona | persona.md | note | knowledge/persona | absent |
| Guide | guide.md | guide | knowledge/guide | required: todo/inprogress/done/reviewed/stop |
| Paper hub (non-Raw) | paper-hub.md | paper | reference/paper | required: todo/inprogress/done/reviewed/stop |
| Paper atom | paper-atom.md | note | reference/paper-atom | absent |

Common Rules status override: ordinary Raw, including Book Index, has no status; only Book chapter Raw has progressive status (initial `status: stub`). Guide and non-Raw Paper hub retain Properties-required status. No processing queue field.

This table defines schema, not placement. Paper hubs follow live Apatheia Role Placement with per-paper analyses in `40. Paper Analyses`, atoms beside their hub; do not invent Wiki folders, move existing analyses or duplicate hubs.

## Meaning → field

Common fields: `tags`, `type`, `date_created`, `date_modified`, `created_by`, `authorship` (template default), `model`, `effort`, `aliases`, `description`. Dates are ISO plain dates. Agent-created notes require the runtime-reported model and effort (default when unreported); do not fabricate a model. Quoted YAML wikilinks are lists unless explicitly scalar below.

| Meaning | Field | Applies to | Absorbed/rejected synonyms |
| --- | --- | --- | --- |
| Original author | author (wikilink list) | Raw, hub, books | author string |
| Canonical address | source_url | Raw, hub, books | source as URL |
| Location/range | source_locator | Raw when applicable | selected_range |
| Stable original identity | source_identity | Raw, hub, books | internal matching key |
| Input designation | source_input | Raw, books | — |
| Material kind | source_kind | Raw, books | source-format, category |
| Extraction method | source_extraction | Raw, books | conversion-tool, extraction |
| Acquisition time | source_obtained_at | Raw, books | date ingested, conversion-date |
| Publication date | date_published | Raw, hub, books | date created |
| In-vault evidence notes | source (wikilink list) | Entity, Concept, Persona, Guide, hub | source URL |
| Originals/earlier captures | referenced (wikilink list; a non-book original not yet ingested is linked as its Inbox candidate, whose note name its Raw keeps; a cited book is linked as its Book Index) | secondary Raw, new full capture | traced_from |
| Related knowledge | related (wikilink list) | Entity, Concept, Persona, Guide | — |
| Collection purpose | purpose | Raw, books (inherited) | collectionPurpose, user_intent_interview |
| Purpose basis | purpose_origin (stated/reused/inferred/unknown) | Raw, books | — |
| Retained document | source_attachment | Raw converted from a document file, PDF hub; never a fetched page or media | source-attachment |
| Read-only mothership connection | mothership (verified deeplink list) | Raw, Entity, Concept | mainVaultRelated; reject mainVaultCmds/source-vault |
| Knowledge confidence | confidence: `high`, `medium` or `low` only; the reason is the last item under `## Sources` | Concept | not fidelity |
| Exploration flag | explored | Entity, Concept, Guide | — |
| Persona target | personaOf (scalar Entity link) | Persona | — |
| Persona maturity | personaMaturity (preserve existing) | Persona | — |
| Book identifier | isbn | book Raw/index/chapter | — |
| Paper identifier | doi | paper Raw/hub | — |
| Citation key | citekey (provisional: prefix if unregistered) | paper Raw/hub/atom | separate provisional boolean |
| Publication venue | venue | paper Raw/hub | — |
| Paper type | paperType | atom | — |
| Analysis axis | analysisStep (integer 2–12, exactly one) | atom | analysisStepName |
| Parent hub | paperHub (scalar wikilink) | atom | — |
| Parent book | bookIndex (scalar wikilink) | chapter only | — |
| Chapter number | chapterNumber (integer) | chapter only | — |
| Part in original language | chapterPart | chapter only | — |
| Previous chapter | chapterPrev (scalar wikilink or null) | chapter only | — |
| Next chapter | chapterNext (scalar wikilink or null) | chapter only | — |
| Chapter progress | status | chapter only | ingested |
| Non-Raw processing stage | status | Guide, hub | — |
| Queue | no field; location | Raw | status |
| Fidelity/conversion limitations | body: Ingest Notes | Raw, hub, books | fidelity*, conversion-fidelity |
| Capture roles | body: Captures | hub | full/current, excerpt/earlier |

Identity matching: `source_identity`, then canonical `source_url`/`source_locator`; titles never prove sameness. New evidence gets a new Raw if it is a better extraction; retain earlier captures in `referenced`. The hub `source` list includes current full and earlier excerpt Raw, with roles explained in Captures. Unknown applicable metadata stays unknown, never invented. Optional fields are omitted when inapplicable.
