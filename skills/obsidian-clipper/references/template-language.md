# Web Clipper Template Language

Variables, filters, and logic as they behave inside a Web Clipper template. The JSON container that holds these strings is documented in [../SKILL.md](../SKILL.md); this reference does not restate the schema.

Web Clipper renders templates with [Knap](https://github.com/obsidianmd/knap), an AST-based engine that interprets templates without evaluating JavaScript. Page data reaches the template only as variable values; it is not re-parsed as template syntax.

## Four compiled surfaces

Every one of these fields is compiled with the full language — variables, filters, and logic all work in all four. Three of them are compiled verbatim; property values are un-escaped one level first.

| Surface | Field | Pre-processing before compile |
| --- | --- | --- |
| Note body | `noteContentFormat` | none |
| Filename | `noteNameFormat` | none, then the rendered result is sanitized as a filename |
| Destination folder | `path` | none |
| Frontmatter values | `properties[].value` | `\"` becomes `"` and `\n` becomes a newline, then compile |

Because `path` is compiled, a dated or grouped destination is expressible directly: `Clippings/{{date|date:"YYYY"}}`. Because `noteNameFormat` is compiled and then sanitized, a filename cannot keep `#`, `|`, `^`, `[`, or `]` regardless of what the template produced.

## Variables

Five kinds, distinguished by prefix: none (preset), `"quoted"` (prompt), `meta:`, `selector:` / `selectorHtml:`, and `schema:`. A variable that resolves to nothing renders as an empty string.

### Preset variables

| Variable | Value |
| --- | --- |
| `{{title}}` | Page title |
| `{{author}}` | Detected author |
| `{{content}}` | Main content, highlights, or selection — already Markdown |
| `{{contentHtml}}` | The same content as HTML |
| `{{selection}}` | Current selection as Markdown |
| `{{selectionHtml}}` | Current selection as HTML |
| `{{highlights}}` | Highlight records with text and timestamps |
| `{{fullHtml}}` | Unprocessed HTML of the whole page |
| `{{description}}` | Description or excerpt |
| `{{url}}` | Page URL |
| `{{domain}}` | Registrable domain |
| `{{site}}` | Site name or publisher |
| `{{favicon}}` | Favicon URL |
| `{{image}}` | Social share image URL |
| `{{language}}` | Page language |
| `{{published}}` | Detected publication date |
| `{{date}}` | Clip time |
| `{{time}}` | Clip time |
| `{{words}}` | Word count |
| `{{noteName}}` | Title after filename sanitization |
| `{{model}}`, `{{modelId}}`, `{{modelProvider}}` | Interpreter model identity, resolved only when Interpreter runs |

Use the extension's **More** menu on a real page to see the resolved values before committing to any of them.

### Preset values that surprise

- **`{{date}}` and `{{time}}` are the same full timestamp**, in `YYYY-MM-DDTHH:mm:ssZ` form. A date-only value needs `{{date|date:"YYYY-MM-DD"}}`; the bare variable puts a time and an offset in the note.
- **`{{published}}` is truncated at the first comma.** Sites that emit several dates in one field contribute only the first.
- **`{{url}}` drops a `#:~:text=` text fragment.** Clipping from a highlighted-text link does not leak the fragment into the note, and a template cannot recover it from `{{url}}`.
- **`{{content}}` is already Markdown.** It is the product of content extraction, so it is also the variable most likely to be missing part of the page.
- **`{{highlights}}` is structured, not prose.** Render it through `map` and a collection filter: `{{highlights|map: item => item.text|join:"\n\n"}}`.

### Meta variables

The name and the property namespaces are separate, and both require their keyword:

- `{{meta:name:description}}` reads `<meta name="description">`.
- `{{meta:property:og:title}}` reads `<meta property="og:title">`.

`{{meta:description}}` and `{{meta:og:title}}` resolve to nothing. Only the two-part forms are registered.

### Selector variables

`{{selector:cssSelector}}` returns text content; `{{selector:cssSelector?attribute}}` returns an attribute; `{{selectorHtml:cssSelector}}` returns markup.

- One matching element yields a plain string. Several matching elements yield an array, which a collection filter such as `join`, `first`, or `unique` turns into text.
- Zero matches yield an empty string. An invalid selector also yields an empty string.
- A selector may be used directly as a loop source, a condition, or the right side of `set`: `{% for c in selector:.comment %}`, `{% if selector:.paywall %}`, `{% set items = selector:.list-item %}`.
- Nested selectors and combinators are supported. Prefer attribute and role selectors over generated class chains; see [workflows.md](workflows.md) for how to verify one and what drift looks like.

### Schema.org variables

Read JSON-LD on the page. Two addressing styles:

| Form | Meaning |
| --- | --- |
| `{{schema:@Recipe:name}}` | `name` on the `Recipe` type |
| `{{schema:name}}` | first `name` found in any type on the page |
| `{{schema:@Recipe:author.name}}` | nested property |
| `{{schema:@Recipe:author[0].name}}` | item at an index |
| `{{schema:@Recipe:author[*].name}}` | that property from every item |
| `{{schema:@Recipe:recipeIngredient}}` | an array, serialized |

Objects and arrays arrive serialized as JSON text. Collection and formatting filters read that text, so `{{schema:@Recipe:recipeIngredient|list}}` works on it directly. A `multitext` property also parses a serialized array. The `@type` key is part of the object, so it appears in output derived from `object:` or `table`; drop it with `replace` when it is unwanted.

The typed form is precise but fails when a site nests the data under a different type. The shorthand is resilient but picks whichever type comes first. Choose per field, not per template.

### Prompt variables

`{{"a three point summary"}}` sends the prompt to Interpreter's configured model. Filters apply to the response: `{{"a three point summary"|blockquote}}`.

- They need Interpreter enabled and a configured provider, so a template that depends on them fails quietly on any install without one.
- They are resolved **after** all other logic. Prompt results cannot be tested in a condition, iterated in a loop, or assigned with `set`.
- The page context is sent to the provider. Restrict it with the template's `context` field, e.g. `{{selectorHtml:#main}}`, and read [workflows.md](workflows.md) before pointing one at a page that may contain something the user did not intend to send anywhere.
- Prefer a selector or schema variable whenever the data has a stable shape. Reach for a prompt only when the shape varies across the sites the template must cover.

## Filters

Apply with `|`; chain left to right: `{{variable|filter1|filter2}}`. Parameters follow a colon, and several parameters are wrapped in parentheses: `callout:("info", "Source", false)`.

Clipper's registry is Knap's standard filters, Knap's HTML filters, and two Clipper additions — `markdown` and `fragment_link`. The exact set tracks the bundled engine version, so an unfamiliar name belongs in the template editor for confirmation, not in a delivered template on faith.

| Job | Filters |
| --- | --- |
| Dates and durations | `date`, `date_modify`, `duration` |
| Case and shape | `upper`, `lower`, `title`, `capitalize`, `camel`, `pascal`, `kebab`, `snake`, `uncamel`, `trim`, `replace`, `safe_name`, `decode_uri`, `unescape` |
| Markdown structure | `blockquote`, `callout`, `list`, `table`, `link`, `wikilink`, `image`, `footnote`, `fragment_link` |
| Numbers | `calc`, `round`, `number_format`, `length` |
| HTML to Markdown | `markdown` |
| HTML cleanup | `strip_tags`, `strip_attr`, `remove_tags`, `remove_attr`, `replace_tags`, `remove_html`, `strip_md`, `html_to_json` |
| Collections | `first`, `last`, `slice`, `split`, `join`, `map`, `merge`, `nth`, `object`, `reverse`, `unique`, `template` |

Knap's catalog is wider than the list the Web Clipper help page documents — heading filters, `bold`, `italic`, `truncate`, `sort`, `where`, `sum`, `compact`, `parse_json`, `encode_uri`, `indent`, and `comment` among them. Treat those as available-but-unconfirmed until the editor accepts them.

### Filter rules worth knowing before writing a chain

- **`markdown` is for HTML inputs only.** `{{contentHtml|markdown}}`, `{{selectorHtml:…|markdown}}`, and `{{fullHtml|markdown}}` are correct. `{{content|markdown}}` double-converts Markdown that is already Markdown and mangles tables, fences, and nested lists.
- **`selector` returns text, `selectorHtml` returns markup.** The first rarely needs `markdown`; the second usually does.
- **`list` has variants:** `list`, `list:task`, `list:numbered`, `list:numbered-task`.
- **`map` cannot call other filters.** `map:item => item.text` selects; it cannot trim or format each element. Do the per-item shaping with `template`, or the whole-collection shaping after `join`.
- **`join` defaults to a comma** and accepts an escaped newline: `join:"\n"`.
- **`replace` needs its special characters escaped** in the search term — `: | { } ( ) ' "` each take a backslash — and accepts JavaScript regular expressions with flags. Multiple pairs go in parentheses: `replace:("e":"a","o":"0")`.
- **`number` typing already strips non-numeric characters** from a property value, so `{{schema:@Recipe:recipeYield|first}}` on a `number` property is enough to turn `4 servings` into `4`.
- **`safe_name` is belt and braces on a filename**, because the extension sanitizes the rendered note name anyway. It matters when the value lands somewhere that is *not* the filename.

## Logic

### Conditionals

```
{% if author %}Author: {{author}}{% endif %}
{% if status == "published" %}Live{% elseif status == "draft" %}Draft{% else %}Unknown{% endif %}
```

Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`, `contains`. Logical: `and`/`&&`, `or`/`||`, `not`/`!`. Parentheses group: `{% if (premium or featured) and published %}`.

Falsy values are `false`, `null`, `undefined`, `""`, `0`, and the empty array. Everything else is truthy. A missing selector or absent schema key is therefore falsy, which is exactly what makes optional blocks work.

### Fallbacks

`??` returns the first truthy value and can be chained: `{{title ?? headline ?? "Untitled"}}`.

**Filters bind tighter than `??`.** This is the rule that most often produces a template that looks right and behaves wrong:

| Expression | Effect |
| --- | --- |
| `{{title\|safe_name ?? "Untitled"}}` | sanitize `title`, fall back to `Untitled` |
| `{{title ?? "Untitled"\|lower}}` | use `title` as-is; the fallback gets lowercased |
| `{{a\|safe_name ?? b\|safe_name}}` | both branches sanitized |

Because `0` and `false` are falsy, `??` replaces them too. Use an explicit `{% if %}` when zero is a legitimate value.

### Variable assignment

```
{% set slug = title|lower|replace:" ":"-" %}
{% set comments = selector:.comment %}
```

Assigned names are usable in later logic and in `{{ }}` output. Use `set` to name a long selector or filter chain once instead of repeating it — repetition is where two copies of a chain drift apart. Properties have no `set`, so a value needed in both a property and the body is either duplicated deliberately or kept only in the body.

### Loops

```
{% for step in schema:@Recipe:recipeInstructions %}{{loop.index}}. {{step.text ?? step}}
{% endfor %}
```

Sources are arrays: schema arrays, selector results, or a name from `set`. Iterations are separated by a line break, and a blank line left before `{% endfor %}` is preserved, which is how paragraphs rather than list items are produced.

| Loop value | Meaning |
| --- | --- |
| `loop.index` | 1-based iteration |
| `loop.index0` | 0-based iteration |
| `loop.first`, `loop.last` | boundary flags |
| `loop.length` | item count |
| `item_index` | 0-based index named after the iterator, kept for compatibility |

Bracket notation reads a specific element or an object key: `{{items[0]}}`, `{{items[loop.index0]}}`, `{{data["my-key"]}}`. Two parallel arrays are walked together by indexing the second with `loop.index0`. Loops nest.

### Comments and whitespace

`{# … #}` is a template comment: removed from output, and its contents are never evaluated. It does not nest, and an unclosed comment is a syntax error. To put an Obsidian `%%` comment in the rendered note, use the `comment` filter instead. `{{- variable -}}` trims adjacent whitespace.

### Evaluation order

1. Logic, variables, and filters render.
2. Prompt variables and Interpreter model variables resolve.

## Quoting and escaping

Three layers stack, and mixing them up is the usual cause of a template that imports but renders literal punctuation.

1. **JSON.** The template file is JSON, so every `"` inside a template string is written `\"`, and every newline in the note body is written `\n`.
2. **Filter arguments.** A filter that takes an escaped newline wants the two characters `\n` in the template, which is `\\n` in the JSON file. `join:"\n\n"` in the template is `join:\"\\n\\n\"` in the file.
3. **Property values only.** They pass through one un-escaping step before compiling, so a double quote inside a property value may be written `\"` in the template (`\\\"` in the JSON file), and a literal `\n` intended for a filter argument needs `\\n` in the template (`\\\\n` in the file). A selector containing quoted attributes is the common case: `{{selector:[data-testid=\"item\"]}}`.

Regular-expression triggers add a fourth layer: the pattern is wrapped in forward slashes, regex metacharacters take a backslash, and each of those backslashes is doubled for JSON.

## How the language fails

- **Rendering never aborts.** Template errors and unknown filters are reported as diagnostics and logged to the browser console; the render returns whatever it produced. A note can therefore be created from a broken template, missing exactly the part that failed.
- **A missing variable is indistinguishable from an empty one.** Both render as nothing. Absence in the output is not evidence about which one happened.
- **The template editor validates syntax.** That check covers the template, not the page: it cannot tell you that a selector no longer matches.

Because of the first two points, a template is never finished on the strength of valid syntax. Verify against a real page as [workflows.md](workflows.md) describes.

## Official documentation

- [Variables](https://help.obsidian.md/web-clipper/variables)
- [Filters](https://help.obsidian.md/web-clipper/filters)
- [Logic](https://help.obsidian.md/web-clipper/logic)
- [Templates](https://help.obsidian.md/web-clipper/templates)
- [Interpreter](https://help.obsidian.md/web-clipper/interpreter)
- [Knap filter and logic reference](https://knap.md/)
