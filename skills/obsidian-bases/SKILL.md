---
name: obsidian-bases
description: Create and edit Obsidian Bases (.base files) with views, filters, formulas, properties, and summaries, preserving unrelated views and reading the changed base back before any claim about what it renders. Use when working with .base files, embedded base code blocks, database-like views of notes, or when the user mentions Bases, table, cards, list, kanban or map views, groupBy, sort, limit, filters, or formulas in Obsidian. Not for Markdown note syntax, .canvas graph structure, Dataview queries, or vault CLI operations.
license: MIT
metadata:
  version: "0.2.0"
---

# Obsidian Bases Skill

This package owns the `.base` file format: the YAML schema, filters, formulas, properties, functions, summaries, view types, row selection and ordering, examples, and validation. It works on its own. Nothing here requires discovering, dispatching to, or loading another skill, and nothing requires fetching a remote page -- the complete function catalog ships in [references/FUNCTIONS_REFERENCE.md](references/FUNCTIONS_REFERENCE.md).

Being able to write a valid base is not authorization to change a vault, and a base that parses is not a base that renders what you intended. Resolve the exact target and the authorized effect before any write, and keep the work read-only when either is missing. See [references/operations.md](references/operations.md) for safe edits, error conditions, empty-result triage, readback, and rendering.

## Scope

Owned here:

- The `.base` schema and every construct inside it: `filters`, `formulas`, `properties`, `summaries`, and `views` with their `type`, `name`, `filters`, `groupBy`, `sort`, `order`, `limit`, and `summaries` keys.
- Expression syntax for filters and formulas, the property namespaces (`note.`, `file.`, `formula.`), `this`, and the function and duration rules that make those expressions valid.
- Static validation of a base document, and the boundary between a document that parses, a file that was written where you meant, and a view that renders the rows you expected.

Not owned here:

- Which notes deserve a base, where the `.base` file belongs, which template frames it, and what provenance it carries. Respect the target vault's applicable policy and the user's exact task. If no policy file exists, use explicit task-bound choices; clarify only missing decisions rather than inventing conventions.
- Markdown note syntax, `.canvas` graph structure, and vault CLI operations. Name the matching package by identity -- `obsidian-markdown`, `obsidian-canvas`, `obsidian-cli` -- only when the task actually reaches that artifact and that package is loaded. When it is not, report the gap rather than improvising.

This package is standalone. Authoring the format needs no vault plugin, mutation server, environment variable, or personal configuration; rendering requires the target app's Bases capability. Applicable live vault policy always governs the task. Optional personal-policy tools and a vault-aware CLI compose only when selected; their absence is normal and unselected tools stay unused.

## Workflow

1. **Resolve the target**: the vault-relative path of the `.base` file (or the note holding an embedded `base` block), the effect (create, add a view, change a filter), and the authority for it. Stay read-only until all three are known. Read the file first when it already exists.
2. **Create or open the file**: a `.base` file in the vault containing valid YAML.
3. **Define scope**: add `filters` to select which notes appear (by tag, folder, property, or date). A base with no filters includes every file in the vault.
4. **Add formulas** (optional): define computed properties in the `formulas` section.
5. **Configure views**: add one or more views (`table`, `cards`, `list`, `kanban`, or `map`) with `order` specifying which properties to display, plus `sort`, `groupBy`, and `limit` when the rows need an order, grouping, or a cap.
6. **Validate**: verify the file is valid YAML with no syntax errors. Check that all referenced properties and formulas exist. Common issues: unquoted strings containing special YAML characters, mismatched quotes in formula expressions, referencing `formula.X` without defining `X` in `formulas`.
7. **Read back, then check the render**: re-read the file from its path and confirm the document you intended is what landed. Then open the base in Obsidian and confirm the view renders the expected rows. These are two separate claims; neither follows from valid YAML. When no app is available, report the render leg as unverified.

## Schema

Base files use the `.base` extension and contain valid YAML.

```yaml
# Global filters apply to ALL views in the base
filters:
  # Can be a single filter string
  # OR a recursive filter object with exactly ONE key: and, or, or not
  and:
    - 'status == "active"'
    - not:
        - 'file.hasTag("archived")'

# Define formula properties that can be used across all views
formulas:
  formula_name: 'expression'

# Configure display names and settings for properties
properties:
  property_name:
    displayName: "Display Name"
  formula.formula_name:
    displayName: "Formula Display Name"
  file.ext:
    displayName: "Extension"

# Define custom summary formulas
summaries:
  custom_summary_name: 'values.mean().round(3)'

# Define one or more views
views:
  - type: table | cards | list | kanban | map
    name: "View Name"
    limit: 10                    # Optional: cap how many rows the view shows
    groupBy:                     # Optional: one property only
      property: property_name
      direction: ASC | DESC
    sort:                        # Optional: row order, first entry wins ties
      - property: property_name
        direction: ASC | DESC
    filters:                     # View-specific filters follow the same rules
      and:
        - 'status == "active"'
    order:                       # Columns to display, left to right
      - file.name
      - property_name
      - formula.formula_name
    summaries:                   # Map properties to summary formulas
      property_name: Average
```

`order` is the display order of columns, not the order of rows -- row order is `sort`. Mixing the two up is the most common reason a base "ignores" a requested ordering.

A view may also carry keys this schema does not list: the app writes view state (for example the layout's own display settings) into the same object. Carry unknown keys through unchanged when editing; deleting them silently resets someone's view.

## Filter Syntax

Filters narrow down results. They can be applied globally or per-view. Global and view filters are both applied to a view, combined with `AND`.

### Filter Structure

```yaml
# Single filter
filters: 'status == "done"'

# AND - all conditions must be true
filters:
  and:
    - 'status == "done"'
    - 'priority > 3'

# OR - any condition can be true
filters:
  or:
    - 'file.hasTag("book")'
    - 'file.hasTag("article")'

# NOT - exclude matching items
filters:
  not:
    - 'file.hasTag("archived")'

# Nested filters
filters:
  or:
    - file.hasTag("tag")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.hasTag("book")
        - file.inFolder("Required Reading")
```

A filter object holds exactly one of `and`, `or`, or `not`, and its value is a list whose entries are either filter strings or further filter objects. A filter string is any expression that evaluates truthy or falsey for a note, so filters and formulas share one syntax and one function set.

### Filter Operators

| Operator | Description |
|----------|-------------|
| `==` | equals |
| `!=` | not equal |
| `>` | greater than |
| `<` | less than |
| `>=` | greater than or equal |
| `<=` | less than or equal |
| `&&` | logical and |
| `\|\|` | logical or |
| <code>!</code> | logical not |

### Arithmetic Operators

| Operator | Description |
|----------|-------------|
| `+` | plus |
| `-` | minus |
| `*` | multiply |
| `/` | divide |
| `%` | modulo |
| `( )` | parenthesis |

## Properties

### Three Types of Properties

1. **Note properties** - From frontmatter: `note.author` or just `author`. Available for Markdown files only.
2. **File properties** - File metadata: `file.name`, `file.mtime`, etc. Available for every file type, including attachments.
3. **Formula properties** - Computed values defined in this base: `formula.my_formula`.

### File Properties Reference

| Property | Type | Description |
|----------|------|-------------|
| `file.name` | String | File name |
| `file.basename` | String | File name without extension |
| `file.path` | String | Full path to file |
| `file.folder` | String | Parent folder path |
| `file.ext` | String | File extension |
| `file.size` | Number | File size in bytes |
| `file.ctime` | Date | Created time |
| `file.mtime` | Date | Modified time |
| `file.tags` | List | All tags in file |
| `file.links` | List | Internal links in file |
| `file.backlinks` | List | Files linking to this file |
| `file.embeds` | List | Embeds in the note |
| `file.properties` | Object | All frontmatter properties |
| `file.file` | File | The file object itself, for functions that take one |

`file.backlinks` is a reverse lookup and is performance heavy; prefer `file.links` from the other side when the query allows it. `file.backlinks` and `file.properties` are not guaranteed to refresh as the vault changes, so a stale row is an index question, not a schema defect.

### The `this` Keyword

- In main content area: refers to the base file itself (`this.file.folder` is the base's own folder)
- When embedded: refers to the embedding file (`this.file.name` is the note or canvas holding the embed, not the base)
- In sidebar: refers to the active file in main content, which is what makes `file.hasLink(this.file)` behave like a backlinks pane

## Formula Syntax

Formulas compute values from properties. Defined in the `formulas` section.

```yaml
formulas:
  # Simple arithmetic
  total: "price * quantity"

  # Conditional logic
  status_icon: 'if(done, "✅", "⏳")'

  # String formatting
  formatted_price: 'if(price, price.toFixed(2) + " dollars")'

  # Date formatting
  created: 'file.ctime.format("YYYY-MM-DD")'

  # Calculate days since created (use .days for Duration)
  days_old: '(now() - file.ctime).days'

  # Calculate days until due date
  days_until_due: 'if(due_date, (date(due_date) - today()).days, "")'
```

A formula may reference another formula as long as the references do not form a cycle. Formula values are written as YAML strings, but the value a formula produces is typed by the data and the functions it uses, so a formula can feed a numeric summary or a date comparison.

## Key Functions

Most commonly used functions. For the complete reference of all types (Date, String, Number, List, File, Link, Object, RegExp), see [FUNCTIONS_REFERENCE.md](references/FUNCTIONS_REFERENCE.md). That file is the whole catalog; no remote lookup is part of this workflow.

| Function | Signature | Description |
|----------|-----------|-------------|
| `date()` | `date(string): date` | Parse string to date (`YYYY-MM-DD HH:mm:ss`) |
| `now()` | `now(): date` | Current date and time |
| `today()` | `today(): date` | Current date (time = 00:00:00) |
| `if()` | `if(condition, trueResult, falseResult?)` | Conditional |
| `duration()` | `duration(string): duration` | Parse duration string |
| `file()` | `file(path): file` | Get file object |
| `link()` | `link(path, display?): Link` | Create a link |

### Duration Type

When subtracting two dates, the result is a **Duration** type (not a number).

**Duration Fields:** `duration.days`, `duration.hours`, `duration.minutes`, `duration.seconds`, `duration.milliseconds`

**IMPORTANT:** Duration does NOT support `.round()`, `.floor()`, `.ceil()` directly. Access a numeric field first (like `.days`), then apply number functions.

```yaml
# CORRECT: Calculate days between dates
"(date(due_date) - today()).days"                    # Returns number of days
"(now() - file.ctime).days"                          # Days since created
"(date(due_date) - today()).days.round(0)"           # Rounded days

# WRONG - will cause error:
# "((date(due) - today()) / 86400000).round(0)"      # Duration doesn't support division then round
```

### Date Arithmetic

```yaml
# Duration units: y/year/years, M/month/months, d/day/days,
#                 w/week/weeks, h/hour/hours, m/minute/minutes, s/second/seconds
"now() + \"1 day\""       # Tomorrow
"today() + \"7d\""        # A week from today
"now() - file.ctime"      # Returns Duration
"(now() - file.ctime).days"  # Get days as number
```

## Rows: Filter, Group, Sort, Limit

Four different keys decide what a view shows. Keep them straight before blaming the data.

| Key | Scope | What it decides |
|-----|-------|-----------------|
| `filters` (top level) | Every view in the base | Which notes are candidates at all |
| `filters` (inside a view) | That view only | Further narrowing, combined with the global filters using `AND` |
| `groupBy` | That view | Which property splits rows into sections; `direction` orders the sections |
| `sort` | That view | Row order within the result; a list of `{property, direction}` entries, first entry primary |
| `limit` | That view | How many rows the view shows |
| `order` | That view | Which columns appear, left to right -- not row order |

```yaml
views:
  - type: table
    name: "Active studies"
    groupBy:
      property: status
      direction: ASC
    sort:
      - property: priority
        direction: ASC
      - property: file.name
        direction: ASC
    limit: 25
    order:
      - file.name
      - priority
```

- `ASC` is the ascending direction for the property's type: A to Z for text, smallest first for numbers, oldest first for dates. `DESC` reverses it.
- Later `sort` entries break ties left by earlier ones. A single entry leaves ties in an order you should not promise.
- Grouping is limited to one property. A second grouping level is not expressible in this schema; use `sort` to order within the group instead.
- Rows whose grouping property is empty are grouped under the empty value rather than dropped.
- `limit` caps the rows the view shows. Which rows survive a cap is a rendered outcome -- read the view before claiming a specific row was excluded by the limit rather than by a filter.

## View Types

### Table View

```yaml
views:
  - type: table
    name: "My Table"
    order:
      - file.name
      - status
      - due_date
    summaries:
      price: Sum
      count: Average
```

### Cards View

```yaml
views:
  - type: cards
    name: "Gallery"
    order:
      - file.name
      - cover_image
      - description
```

### List View

```yaml
views:
  - type: list
    name: "Simple List"
    order:
      - file.name
      - status
```

### Kanban View

Columns come from the grouped property, so a kanban view needs a `groupBy`.

```yaml
views:
  - type: kanban
    name: "Board"
    groupBy:
      property: status
      direction: ASC
    order:
      - file.name
      - due
```

### Map View

Requires latitude/longitude properties and the Maps plugin.

```yaml
views:
  - type: map
    name: "Locations"
    # Map-specific settings for lat/lng properties
```

### Layout availability

| Layout | Introduced in app version | Extra requirement |
|--------|---------------------------|-------------------|
| `table` | 1.9 | -- |
| `cards` | 1.9 | -- |
| `list` | 1.10 | -- |
| `kanban` | 1.14 | Needs a `groupBy` property |
| `map` | 1.10 | Maps plugin |

Community plugins can add further layouts. Availability is a runtime fact of the installed app, not something the YAML can assert: a `type` the installed build does not know does not render, and no amount of valid syntax changes that. Check the installed version and the enabled plugins, or report the layout as unverified.

## Default Summary Formulas

| Name | Input Type | Description |
|------|------------|-------------|
| `Average` | Number | Mathematical mean |
| `Min` | Number | Smallest number |
| `Max` | Number | Largest number |
| `Sum` | Number | Sum of all numbers |
| `Range` | Number | Max - Min |
| `Median` | Number | Mathematical median |
| `Stddev` | Number | Standard deviation |
| `Earliest` | Date | Earliest date |
| `Latest` | Date | Latest date |
| `Range` | Date | Latest - Earliest |
| `Checked` | Boolean | Count of true values |
| `Unchecked` | Boolean | Count of false values |
| `Empty` | Any | Count of empty values |
| `Filled` | Any | Count of non-empty values |
| `Unique` | Any | Count of unique values |

A custom entry in the top-level `summaries` section defines a new named summary; inside it, `values` is the list of that property's values across the result set, and the expression must return a single value. The per-view `summaries` map is a different thing: it assigns a summary name (default or custom) to a property.

```yaml
summaries:
  customAverage: 'values.mean().round(3)'

views:
  - type: table
    name: "Prices"
    order:
      - file.name
      - price
    summaries:
      price: customAverage
```

## Complete Examples

### Task Tracker Base

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'file.ext == "md"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'
  is_overdue: 'if(due, date(due) < today() && status != "done", false)'
  priority_label: 'if(priority == 1, "🔴 High", if(priority == 2, "🟡 Medium", "🟢 Low"))'

properties:
  status:
    displayName: Status
  formula.days_until_due:
    displayName: "Days Until Due"
  formula.priority_label:
    displayName: Priority

views:
  - type: table
    name: "Active Tasks"
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - status
      - formula.priority_label
      - due
      - formula.days_until_due
    groupBy:
      property: status
      direction: ASC
    summaries:
      formula.days_until_due: Average

  - type: table
    name: "Completed"
    filters:
      and:
        - 'status == "done"'
    order:
      - file.name
      - completed_date
```

### Reading List Base

```yaml
filters:
  or:
    - file.hasTag("book")
    - file.hasTag("article")

formulas:
  reading_time: 'if(pages, (pages * 2).toString() + " min", "")'
  status_icon: 'if(status == "reading", "📖", if(status == "done", "✅", "📚"))'
  year_read: 'if(finished_date, date(finished_date).year, "")'

properties:
  author:
    displayName: Author
  formula.status_icon:
    displayName: ""
  formula.reading_time:
    displayName: "Est. Time"

views:
  - type: cards
    name: "Library"
    order:
      - cover
      - file.name
      - author
      - formula.status_icon
    filters:
      not:
        - 'status == "dropped"'

  - type: table
    name: "Reading List"
    filters:
      and:
        - 'status == "to-read"'
    order:
      - file.name
      - author
      - pages
      - formula.reading_time
```

### Daily Notes Index

```yaml
filters:
  and:
    - file.inFolder("Daily Notes")
    - '/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)'

formulas:
  word_estimate: '(file.size / 5).round(0)'
  day_of_week: 'date(file.basename).format("dddd")'

properties:
  formula.day_of_week:
    displayName: "Day"
  formula.word_estimate:
    displayName: "~Words"

views:
  - type: table
    name: "Recent Notes"
    limit: 30
    order:
      - file.name
      - formula.day_of_week
      - formula.word_estimate
      - file.mtime
```

### Worked Example: Expected Rows and Order

Three notes, one base, and the exact result the view should produce. Use this shape to state an expectation *before* opening the app, so a mismatch is a finding instead of a surprise.

`Study-A.md`, `Study-B.md`, `Study-C.md`:

```markdown
---
kind: study
status: active
priority: 2
---
Alpha preserved.
```

```markdown
---
kind: study
status: active
priority: 1
---
Beta preserved.
```

```markdown
---
kind: study
status: archived
priority: 0
---
Gamma preserved.
```

`Studies.base`:

```yaml
filters:
  and:
    - kind == "study"
    - status == "active"
views:
  - type: table
    name: Active studies
    groupBy:
      property: status
      direction: ASC
    sort:
      - property: priority
        direction: ASC
    order:
      - file.name
      - priority
    limit: 2
```

Expected rendered result:

| # | Group | `file.name` | `priority` |
|---|-------|-------------|------------|
| 1 | `status active` | `Study-B` | 1 |
| 2 | `status active` | `Study-A` | 2 |

- `Study-C` is absent because `status == "active"` excludes it, not because of the limit.
- `Study-B` precedes `Study-A` because `sort` orders by `priority` ascending, while `order` only decides that the name column sits left of the priority column.
- One group header appears, because every surviving row shares the same `status` value.
- The toolbar reports the number of results in the view; compare it with the row count you expected rather than reading it as a vault-wide count.

This result was observed in Obsidian 1.12.7 with the Bases core plugin enabled, over exactly these three notes. Scope any behavioural claim to the build you actually ran; another build is a separate observation.

Recording the expectation this way makes two failures distinguishable: a wrong document (the readback does not match what you wrote) and a wrong result (the document is right and the rendered rows still differ).

## Embedding Bases

Embed in Markdown files:

```markdown
![[MyBase.base]]

<!-- Specific view -->
![[MyBase.base#View Name]]
```

Without a selector the first view in the `views` list is used, so reordering views changes every plain embed. With a selector, the view **name** is the key: renaming a view breaks every embed that pointed at the old name, and nothing in the base file records the dangling reference. Rename a view only after checking which notes embed it.

Base syntax can also live in a fenced `base` code block inside a note. The schema is identical; only the container differs. The note is then owned by `obsidian-markdown` and the block content by this package -- do not fork a second schema for blocks.

## YAML Quoting Rules

- Use single quotes for formulas containing double quotes: `'if(done, "Yes", "No")'`
- Use double quotes for simple strings: `"My View Name"`
- Escape nested quotes properly in complex expressions
- Text literals inside an expression must themselves be quoted, which is why the nesting exists in the first place

## Troubleshooting

### YAML Syntax Errors

**Unquoted special characters**: Strings containing `:`, `{`, `}`, `[`, `]`, `,`, `&`, `*`, `#`, `?`, `|`, `-`, `<`, `>`, `=`, `!`, `%`, `@`, `` ` `` must be quoted.

```yaml
# WRONG - colon in unquoted string
displayName: Status: Active

# CORRECT
displayName: "Status: Active"
```

**Mismatched quotes in formulas**: When a formula contains double quotes, wrap the entire formula in single quotes.

```yaml
# WRONG - double quotes inside double quotes
formulas:
  label: "if(done, "Yes", "No")"

# CORRECT - single quotes wrapping double quotes
formulas:
  label: 'if(done, "Yes", "No")'
```

### Common Formula Errors

**Duration math without field access**: Subtracting dates returns a Duration, not a number. Always access `.days`, `.hours`, etc.

```yaml
# WRONG - Duration is not a number
"(now() - file.ctime).round(0)"

# CORRECT - access .days first, then round
"(now() - file.ctime).days.round(0)"
```

**Missing null checks**: Properties may not exist on all notes. Use `if()` to guard.

```yaml
# WRONG - crashes if due_date is empty
"(date(due_date) - today()).days"

# CORRECT - guard with if()
'if(due_date, (date(due_date) - today()).days, "")'
```

**Referencing undefined formulas**: Ensure every `formula.X` in `order` or `properties` has a matching entry in `formulas`.

```yaml
# This will fail silently if 'total' is not defined in formulas
order:
  - formula.total

# Fix: define it
formulas:
  total: "price * quantity"
```

**Circular formulas**: a formula may read another formula, but a cycle (`a` reads `b`, `b` reads `a`) has no value to compute. Break the cycle instead of adding a guard.

### An Empty or Unexpected View Is a Result, Not a Syntax Error

A base that parses and still shows nothing usually has a working filter and a wrong expectation: a property spelled differently in frontmatter, a value that is a string where the filter compares a number, notes outside the folder the filter names, or an index that has not caught up. Diagnose it as a data and runtime question. Do not "fix" it by loosening the schema, deleting filters, or rewriting the file until something appears. [references/operations.md](references/operations.md) has the triage order.

## Operations

[references/operations.md](references/operations.md) covers the authorization boundary and vault policy, safe edits that preserve unrelated views and keys, the error conditions worth reporting, empty-result triage, exact readback versus rendered verification, embedded blocks, and optional composition with neighboring packages.

## Validation Checklist

Static checks on the document you hold, before it goes anywhere:

1. The file parses as YAML.
2. Every filter object has exactly one of `and`, `or`, `not`, and its value is a list.
3. Every `formula.X` referenced in `order`, `properties`, `summaries`, or another formula is defined in `formulas`, with no cycles.
4. Every view has a `type` and a `name`, and `groupBy`/`sort` entries name a real property.
5. Summary names used in a view's `summaries` are default names or entries in the top-level `summaries`.
6. Formulas that subtract dates access a Duration field (`.days`, `.hours`, ...) before applying number functions.
7. Formulas that read optional properties guard with `if()`.

Passing this list proves the document is well formed. It does not prove the file was written where you meant, that any note matches the filters, or that the view renders. Those are separate claims; see [references/operations.md](references/operations.md).

## References

- [Bases Syntax](https://help.obsidian.md/bases/syntax)
- [Functions](https://help.obsidian.md/bases/functions)
- [Views](https://help.obsidian.md/bases/views)
- [Formulas](https://help.obsidian.md/formulas)
- [Complete Functions Reference](references/FUNCTIONS_REFERENCE.md)
- [Operations Reference](references/operations.md)

## Attribution

The format documentation and examples in this package are derived from the `obsidian-bases` skill in [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) at commit `3ccff5338ea700537839b21900aa5358a0402c98`, MIT License, Copyright (c) 2026 Steph Ango (@kepano). That material has been modified here. See [CHANGELOG.md](CHANGELOG.md) for the recorded revision, the modifications, and the evidence behind the additions.
