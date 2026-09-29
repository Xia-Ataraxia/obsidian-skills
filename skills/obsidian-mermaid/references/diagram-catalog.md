# Diagram catalog

Copy-ready starting points for the families this package supports. Replace labels and data; leave the grammar alone.

**Status of these entries:** each block is authored against the current upstream Mermaid grammar documentation. None of them is renderer-verified against your target vault — that is level D in the SKILL's evidence ladder and only opening the note in the target Obsidian produces it. Run the compatibility gate in [`compatibility.md`](compatibility.md) before using anything from the version-gated section.

All examples are synthetic and describe a fictional public library branch.

## Contents

- Conservative core — [flowchart](#flowchart), [sequence](#sequence-diagram), [class](#class-diagram), [state](#state-diagram), [entity relationship](#entity-relationship-diagram), [gantt](#gantt), [journey](#user-journey), [pie](#pie), [mindmap](#mindmap), [timeline](#timeline)
- Version-gated — [sankey](#sankey), [kanban](#kanban), [treemap](#treemap), [architecture](#architecture), [xy chart](#xy-chart)
- [Fallbacks that keep the meaning](#fallbacks-that-keep-the-meaning)

## Conservative core

These families have been part of Mermaid long enough that any bundle new enough to render diagrams at all is expected to accept them. Prefer them whenever they can carry the meaning.

### Flowchart

Ordered steps with branches. The default choice, and the fallback for any structural diagram.

```mermaid
flowchart LR
  A[Hold request] --> B{Copy on shelf?}
  B -->|Yes| C[Reserve copy]
  B -->|No| D[Add to queue]
  D --> E[Notify when returned]
  C --> F[Hold shelf]
  E --> F
```

`TD` swaps to top-down. Group related nodes with `subgraph <name> ... end`; remember that lowercase `end` as a node label breaks the parser.

### Sequence diagram

Who sends what to whom, in order. Declare participants so the column order is deliberate rather than accidental.

```mermaid
sequenceDiagram
    participant Reader
    participant Catalog
    participant Branch
    Reader->>Catalog: Search title
    Catalog-->>Reader: Availability by branch
    Reader->>Catalog: Place hold
    Catalog->>Branch: Reserve copy
    Branch-->>Catalog: Copy reserved
    Catalog-->>Reader: Pickup notice
```

`->>` draws a solid arrow (a call), `-->>` a dotted one (conventionally a reply). Use `Note over A,B: text` for context that is not a message.

### Class diagram

Types, their members, and cardinality. A domain model, not a runtime path.

```mermaid
classDiagram
    direction LR
    class Title {
        +String name
        +String author
    }
    class Copy {
        +String barcode
        +boolean available
    }
    class Member {
        +String cardNumber
        +int activeLoans
        +borrow(copy)
    }
    Title "1" --> "*" Copy : printed as
    Member "1" --> "*" Copy : borrows
```

### State diagram

The lifecycle of one thing. The `-v2` suffix is part of the keyword.

```mermaid
stateDiagram-v2
    [*] --> OnShelf
    OnShelf --> OnLoan : checked out
    OnLoan --> OnShelf : returned
    OnLoan --> Overdue : due date passed
    Overdue --> OnShelf : returned
    OnShelf --> Withdrawn : removed from collection
    Withdrawn --> [*]
```

### Entity relationship diagram

Stored entities, their attributes, and how they relate.

```mermaid
erDiagram
    MEMBER ||--o{ LOAN : places
    LOAN ||--|| COPY : covers
    TITLE ||--o{ COPY : "is printed as"
    MEMBER {
        string card_number
        string name
    }
    COPY {
        string barcode
        string shelf_location
    }
```

Cardinality is encoded in the connector: `||` exactly one, `o{` zero or more, `|{` one or more.

### Gantt

Dated work with real durations. `dateFormat` describes the dates you write, `axisFormat` the axis labels.

```mermaid
gantt
    title Exhibit installation
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    section Build
    Frame assembly   :a1, 2026-03-02, 5d
    Lighting rig     :a2, after a1, 3d
    section Content
    Panel printing   :b1, 2026-03-04, 4d
    Install panels   :b2, after a2, 2d
```

### User journey

A step-by-step experience with a score and the actors involved. The score is 1–5 and precedes the actor list.

```mermaid
journey
    title First visit to the branch
    section Arrive
      Find the entrance: 4: Visitor
      Ask at the desk: 5: Visitor, Staff
    section Borrow
      Search the catalog: 3: Visitor
      Check out: 4: Visitor, Staff
```

### Pie

Parts of one whole, single level. Quote every label.

```mermaid
pie title Collection by format
    "Print" : 62
    "Digital" : 20
    "Audio" : 18
```

### Mindmap

A branching outline of one topic. Indentation is the entire grammar — keep it consistent and never mix tabs with spaces.

```mermaid
mindmap
  root((Reading program))
    Audience
      Children
      Adults
    Materials
      Booklists
      Activity sheets
    Schedule
      Weekly sessions
      Closing event
```

### Timeline

Dated milestones in order. A period may carry several events on the same line, separated by colons.

```mermaid
timeline
    title Branch milestones
    2019 : Building survey
    2021 : Renovation approved
    2023 : Reopening : Community archive launched
```

## Version-gated

Each family below needs the compatibility gate first, and each entry names the fallback to use when the target bundle rejects it.

### Sankey

Quantified flow between stages, written as three-column CSV: source, target, value.

```mermaid
sankey-beta

Arrivals,Reading room,120
Arrivals,Computer area,60
Arrivals,Leaves immediately,20
Reading room,Borrows,70
Reading room,Leaves,50
Computer area,Leaves,60
```

Current Mermaid accepts `sankey` and `sankey-beta`; older bundles accept only `sankey-beta`, so the suffixed form is the compatible one. Wrap any value containing a comma in double quotes.

**Fallback:** a `flowchart LR` whose edge labels carry the quantities.

### Kanban

Work items grouped by workflow column. Columns are top level, tasks are indented beneath them.

```mermaid
kanban
  backlog[Backlog]
    signage[Replace aisle signage]
    localhistory[Recatalog local history shelf]
  active[In progress]
    periodicals[Audit periodicals]@{ assigned: 'Branch team', priority: 'High' }
  done[Done]
    inventory[Annual inventory]
```

Metadata keys are `assigned`, `ticket`, and `priority`; `priority` accepts only `Very High`, `High`, `Low`, and `Very Low`.

**Fallback:** a Markdown table with one column per stage, or headings with task lists. Both keep every item and its stage.

### Treemap

Nested proportions. Quoted names, indentation for hierarchy, `: value` on leaves.

```mermaid
treemap-beta
"Floor space"
    "Collections"
        "Print": 40
        "Media": 15
    "Public areas"
        "Reading room": 25
        "Study rooms": 10
    "Staff areas": 10
```

Upstream marks this as a new diagram type whose syntax may still change, so pin the exact spelling you verified.

**Fallback:** `pie` for a single level, plus a table or nested list for the levels `pie` cannot show. Do not ship the `pie` alone if the hierarchy was the point.

### Architecture

Services, the groups that contain them, and directed links between them.

```mermaid
architecture-beta
    group branch(cloud)[Branch systems]
    service kiosk(server)[Self checkout] in branch
    service catalog(server)[Catalog service] in branch
    service store(database)[Loan database] in branch
    kiosk:R --> L:catalog
    catalog:R --> L:store
```

Service and group ids are bare keys — do not quote them. Labels go in `[]`, icons in `()`. Built-in icons are `cloud`, `database`, `disk`, `internet`, and `server`; anything else needs a registered icon pack the bundled renderer may not have.

**Fallback:** the flowchart under [Fallbacks](#fallbacks-that-keep-the-meaning), which keeps the topology and loses only the icons.

### XY chart

Numeric series over categories, as bars, lines, or both.

```mermaid
xychart-beta
    title "Loans per month"
    x-axis ["Jan", "Feb", "Mar", "Apr", "May"]
    y-axis "Loans" 0 --> 1200
    bar [820, 910, 1040, 980, 1130]
    line [800, 880, 1000, 960, 1100]
```

Current Mermaid accepts `xychart` and `xychart-beta`; older bundles accept only `xychart-beta`. Keep every series the same length as the x-axis category list.

**Fallback:** a Markdown table of the same numbers. It keeps every value and loses only the shape — say so when you ship it.

## Fallbacks that keep the meaning

A fallback replaces the drawing, never the information. Worked example — the architecture diagram above, expressed with the conservative core:

```mermaid
flowchart LR
  subgraph Branch systems
    kiosk[Self checkout]
    catalog[Catalog service]
    store[(Loan database)]
  end
  kiosk --> catalog
  catalog --> store
```

Every service, the group boundary, and both links survive; only the icon set is gone, which is the kind of loss worth one sentence of disclosure.

| Gated family | Fallback | What the fallback drops |
| --- | --- | --- |
| `sankey` | `flowchart LR` with quantities in edge labels | Width-proportional flow |
| `kanban` | Table with one column per stage | Card metadata styling |
| `treemap-beta` | `pie` plus a nested list | Area proportionality across levels |
| `architecture-beta` | `flowchart LR` with a subgraph per group | Icons and port-level edge anchoring |
| `xychart-beta` | Table of values | The visual shape of the series |

When the dropped column above matters to the reader, keep it in prose or a table beside the fallback rather than deleting it.
