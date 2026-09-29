# Callouts Reference

## Basic Callout

```markdown
> [!note]
> This is a note callout.

> [!info] Custom Title
> This callout has a custom title.

> [!tip] Title Only
```

## Structure Rules

A callout is a blockquote whose first line starts with `[!type]`:

```markdown
> [!type][fold marker] [Custom title]
> Body line
> Body line
```

- `[!type]` must be the first thing on the first line of the blockquote, directly after `> `.
- The type identifier is matched without regard to case, so `[!NOTE]` and `[!note]` select the same callout.
- Omitting the title uses the type name as the title, capitalized by the renderer.
- The optional fold marker (`+` or `-`) comes immediately after `]`, before the title -- `> [!tip]- Title`, never `> [!tip] Title-`.
- Every continuation line needs its own `>`. A line without `>` ends the callout and becomes ordinary content.
- To separate paragraphs inside a callout, use a line containing only `>`:

```markdown
> [!note] Two paragraphs
> First paragraph.
>
> Second paragraph.
```

- A title-only callout (`> [!tip] Title Only`) is valid and renders as an empty-body callout.

## Content Inside Callouts

Standard Markdown works inside a callout as long as every line keeps the `>` prefix -- lists, tables, code fences, math, images, wikilinks, and embeds:

```markdown
> [!example] Checklist and code
> - [x] First step
> - [ ] Second step
>
> ```bash
> echo "runs inside a callout"
> ```
>
> Linked context: [[Release Checklist#Rollback]]
> ![[Architecture Diagram.png|400]]
```

The title accepts inline Markdown, including links and code spans:

```markdown
> [!info] See [[Release Checklist]] for the `--dry-run` path
> The title renders its inline Markdown.
```

## Foldable Callouts

```markdown
> [!faq]- Collapsed by default
> This content is hidden until expanded.

> [!faq]+ Expanded by default
> This content is visible but can be collapsed.
```

A callout without a fold marker is not foldable at all. Folding is per callout: in a nested structure each callout carries its own marker.

## Nested Callouts

```markdown
> [!question] Outer callout
> > [!note] Inner callout
> > Nested content
```

Add one `>` per nesting level, on every line of the inner callout. Nested callouts may each be foldable:

```markdown
> [!question]- Outer, collapsed
> Outer body.
>
> > [!note]+ Inner, expanded
> > Inner body.
```

## Supported Callout Types

| Type | Aliases | Color / Icon |
|------|---------|-------------|
| `note` | - | Blue, pencil |
| `abstract` | `summary`, `tldr` | Teal, clipboard |
| `info` | - | Blue, info |
| `todo` | - | Blue, checkbox |
| `tip` | `hint`, `important` | Cyan, flame |
| `success` | `check`, `done` | Green, checkmark |
| `question` | `help`, `faq` | Yellow, question mark |
| `warning` | `caution`, `attention` | Orange, warning |
| `failure` | `fail`, `missing` | Red, X |
| `danger` | `error` | Red, zap |
| `bug` | - | Red, bug |
| `example` | - | Purple, list |
| `quote` | `cite` | Gray, quote |

An alias is a different name for the same appearance, not a distinct type: `[!faq]` and `[!question]` render identically, so pick one per note and stay consistent.

## Choosing a Type

| Intent | Type |
|--------|------|
| Neutral aside, background | `note`, `info` |
| Short summary at the top of a long note | `abstract` |
| Actionable advice, the recommended path | `tip` |
| Consequence if ignored, risk of data loss | `warning`, `danger` |
| Known defect or reproduction | `bug`, `failure` |
| Verified result, completed migration | `success` |
| Open question, unresolved decision | `question` |
| Worked sample, command transcript | `example` |
| Cited external text | `quote` |
| Outstanding items in a working note | `todo` |

Avoid stacking several high-severity callouts in one section; when everything is a `warning`, nothing reads as one.

## Unrecognized Types

An identifier outside the table above still renders as a callout, with the default styling and the identifier as its title. That makes a typo (`[!waring]`) look plausible in source and wrong in reading view, so confirm any non-standard type in reading view before relying on it -- or define it in CSS.

## Custom Callouts (CSS)

```css
.callout[data-callout="custom-type"] {
  --callout-color: 255, 0, 0;
  --callout-icon: lucide-alert-circle;
}
```

- `--callout-color` takes comma-separated RGB channels, not a hex string or a `rgb()` function call.
- `--callout-icon` takes an icon identifier available to the app, or inline SVG.
- The `data-callout` value is the lowercase identifier written in `[!...]`.
- The CSS belongs in a vault snippet or theme, which is a separate vault change from writing the note; the note itself only carries the `[!custom-type]` identifier.

## Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Renders as a plain blockquote | `[!type]` is not on the first line of the blockquote | Move it to the first line, directly after `> ` |
| Callout stops mid-way | A continuation line lost its `>` | Prefix every line, including blank separators, with `>` |
| Title shows a stray `+` or `-` | Fold marker placed after the title | Put the marker immediately after `]` |
| Callout cannot be collapsed | No fold marker | Add `-` or `+` |
| Inner callout renders as text | Inner lines have only one `>` | Use `> >` on every inner line |
| Unexpected default styling | Type identifier typo or unsupported type | Correct the identifier or define the type in CSS |
| Code fence inside a callout leaks out | Fence lines missing `>` | Prefix the opening fence, body, and closing fence |

## Verification

- [ ] Every callout line, including blank separators and closing code fences, starts with `>`.
- [ ] The type identifier exists in the table above, or is intentionally custom and defined in CSS.
- [ ] Fold markers sit immediately after `]` and match the intended default state.
- [ ] Nested callouts carry one `>` per level on every line.
- [ ] Reading view was checked, since a malformed callout still renders as valid Markdown.
