# Properties (Frontmatter) Reference

Properties use YAML frontmatter at the start of a note:

```yaml
---
title: My Note Title
date: 2024-01-15
tags:
  - project
  - important
aliases:
  - My Note
  - Alternative Name
cssclasses:
  - custom-class
status: in-progress
rating: 4.5
completed: false
due: 2024-02-01T14:30:00
---
```

## Placement Rules

- The opening `---` must be the very first line of the file. A blank line, a heading, or a comment above it turns the block into ordinary content.
- The block closes with a line containing exactly `---`.
- The content between the delimiters must be valid YAML; one syntax error drops every property in the note.
- Only one frontmatter block per note. A later `---` line in the body is a horizontal rule, not a second block.
- Indent with spaces. A tab anywhere in the block is a YAML error.

## Property Types

| Type | Example |
|------|---------|
| Text | `title: My Title` |
| Number | `rating: 4.5` |
| Checkbox | `completed: true` |
| Date | `date: 2024-01-15` |
| Date & Time | `due: 2024-01-15T14:30:00` |
| List | `tags: [one, two]` or YAML list |
| Links | `related: "[[Other Note]]"` |

Type notes:

- Dates use `YYYY-MM-DD`; date-and-time values use `YYYY-MM-DDTHH:mm:ss`. A differently shaped value stays text and will not sort or filter as a date.
- Checkbox values are the bare YAML booleans `true` and `false`. `"true"` in quotes is text.
- A number must be unquoted. `rating: "4.5"` is text, and a leading zero (`id: 007`) is safest written as text on purpose.
- An empty value (`status:`) is null, which is different from an absent property and from an empty string (`status: ""`).

## Lists

Both forms are equivalent; block form is easier to edit and diff:

```yaml
tags:
  - project
  - active
```

```yaml
tags: [project, active]
```

Do not mix the two forms for one key. A single-value list can stay a list (`tags: [project]`) so that later additions do not change the type.

## Links in Properties

A wikilink in a property must be quoted, because `[` starts a YAML flow sequence:

```yaml
related: "[[Other Note]]"
sources:
  - "[[Meeting Notes 2024-01-10]]"
  - "[[Project Alpha#Decisions]]"
```

Non-Markdown targets keep their extension here too: `board: "[[Team Board.canvas]]"`. Links in properties participate in link resolution, so a changed property link needs the same source-context readback as a body link (see *Destination readback* in this package's `SKILL.md`).

## Default Properties

- `tags` - Note tags (searchable, shown in graph view)
- `aliases` - Alternative names for the note (used in link suggestions)
- `cssclasses` - CSS classes applied to the note in reading/editing view

All three take a list. `aliases` affects how links to the note resolve by name, and `cssclasses` only changes appearance if a matching snippet or theme rule exists in the vault -- adding the class does not create the styling.

## Tags

```markdown
#tag
#nested/tag
#tag-with-dashes
#tag_with_underscores
```

Tags can contain: letters (any language), numbers (not first character), underscores `_`, hyphens `-`, forward slashes `/` (for nesting).

In frontmatter:

```yaml
---
tags:
  - tag1
  - nested/tag2
---
```

Frontmatter tag rules:

- Write the tag without the leading `#`; both forms are accepted, but one style per vault keeps the property clean.
- A tag cannot contain a space. `project alpha` is two tokens, not a nested tag; use `project-alpha` or `project/alpha`.
- A tag cannot be only digits; `#2024` is not a tag, while `#y2024` is.
- Nesting is just the `/` separator: `project/alpha` is also matched by searches for the `project` parent.

## Editing Properties Safely

1. Read the existing block first. Note its key order, list style, and quoting.
2. Change only the requested key. Leave unknown keys -- plugin state, publication flags, provenance fields -- exactly as they are.
3. Keep the existing order. Do not alphabetize or regroup keys as a side effect.
4. Match the file's existing style for a key you extend: append to a block list as a block item, not as a flow sequence.
5. Do not convert a value's type to make it look tidier; a quoted number or a text date may be deliberate.
6. Re-read the note afterwards and confirm the block still parses and only the intended key changed.

## Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| No properties appear at all | Frontmatter not on line 1, or a YAML error | Move the block to the top; fix the syntax |
| Value truncated at `#` | `#` starts a YAML comment in an unquoted value | Quote the value: `title: "Release #2"` |
| Value truncated or rejected at `:` | Unquoted value contains `: ` | Quote the whole value |
| Property becomes an odd nested structure | Unquoted `[[...]]` read as a YAML sequence | Quote the link |
| Date does not sort | Value is not `YYYY-MM-DD` or `YYYY-MM-DDTHH:mm:ss` | Rewrite the value in the expected shape |
| Checkbox renders as text | Boolean was quoted | Use unquoted `true` / `false` |
| Tag never matches | Space in the tag, or a digits-only tag | Use `-` or `/`, and prefix digits with a letter |
| One key silently wins | Duplicate keys in the block | Keep a single occurrence |
| Whole block breaks after an edit | Tab indentation, or mixed list styles | Indent with spaces; keep one list style per key |

## Verification

- [ ] The block starts on line 1, closes with `---`, and parses as YAML.
- [ ] Only the requested key changed; every other key, its order, and its formatting are untouched.
- [ ] Dates, numbers, and booleans use the shapes above rather than incidental text.
- [ ] Links in properties are quoted, keep non-Markdown extensions, and were resolved from this note or reported as unverified.
- [ ] Tags contain no spaces and are not digits-only.
- [ ] The note was read back after the edit.
