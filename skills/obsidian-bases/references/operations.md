# Bases Operations Reference

How to change a `.base` file that already holds someone's views, which conditions are errors worth reporting, and which verification claims stay separate. The schema itself lives in [../SKILL.md](../SKILL.md); this reference does not restate keys, functions, or view options.

## Authorization boundary

Resolve two things before writing: the exact vault-relative path of the `.base` file (or of the note holding the embedded `base` block), and the exact effect you are authorized to produce -- create the file, add a view, change one filter, rename a formula. Producing valid YAML is not permission to change a vault, and a writable path being reachable is not an instruction to write to it.

When the vault, the authority, or the requested target is missing or ambiguous, keep the operation read-only and name the specific gap. Reuse authority the current task already granted for that file and that effect; do not ask twice for the same approved change, and do not stretch approval for one base to cover its neighbours.

The target vault's own written policy owns what the base is for, where it lives, which naming and template conventions apply, and what provenance it must carry. This package owns none of that. When the vault states no policy, ask rather than inventing one.

When the user selected a vault-aware surface, write through it instead of around it. `obsidian-cli` owns that surface if a CLI operation is the selected owner; its absence is normal, and its presence without selection means it stays unused. Authoring a base needs neither that package nor any other. Never assemble `.base` content with shell redirection or stream editors: they reformat YAML, drop trailing newlines, and mangle the nested quoting that filters and formulas depend on.

## Safe edits to an existing base

A base is configuration a person tuned by hand or through the app's own menus. Editing one is an amendment, not a regeneration.

1. **Read and parse the current file once.** Work on the parsed document, never on a textual patch of YAML, and never by writing a fresh file "with the same content plus the change".
2. **Keep every view you were not asked to touch**, including its `name`, its position in the `views` list, and its own filters, order, sort, groupBy, limit, and summaries. View position is user-visible: the first view is what a plain `![[Base.base]]` embed renders.
3. **Keep unknown keys.** The app stores per-view display state in the same objects, and community layouts add their own. A key this package does not document is still someone's setting; carry it through unchanged rather than dropping it as unrecognized.
4. **Keep the rest of the document**: global `filters`, `formulas` you did not touch, `properties` display names, and top-level `summaries`. Preserve key order and the existing indentation and quoting style so the diff shows only the requested change.
5. **Do not rename to tidy.** A view name is the target of `![[Base.base#View Name]]` embeds, a formula name is referenced by `order`, `properties`, `summaries`, and other formulas. Renaming either is a separate effect with its own approval and its own follow-up search for references.
6. **Validate the in-memory document before writing**, using the checklist in [../SKILL.md](../SKILL.md). A document that fails validation is not written at all, so a failed edit leaves the previous file intact.
7. **Write once, from the validated document.** No partial write, no two-step "write then patch".

### Adding a view

Append it to `views` unless the task asked for a specific position, and say so in the report when the new view lands first, because that changes what existing plain embeds render. Give it a name that no other view in the file uses. A duplicate view name makes `#View Name` embeds ambiguous.

### Changing filters

State which rows the change is meant to add or remove before making it. Narrowing a filter hides rows that were there a moment ago, which looks identical to a broken base to whoever opens it next. Widening one can pull in an entire vault: a base without filters matches every file, including attachments.

## Error conditions

Report these; do not repair them silently, and do not make them disappear by deleting the offending construct.

| Condition | What to report |
|-----------|----------------|
| YAML does not parse | The parser's line and column, and the fact that the file was left unchanged |
| Filter object with zero or several of `and`/`or`/`not` | The view (or top level) and the keys found |
| Filter list holding something that is neither a string nor a filter object | The path to the entry and its type |
| `formula.X` referenced but not defined | Every referencing site: `order`, `properties`, `summaries`, or another formula |
| Circular formula references | The cycle, named formula by formula |
| View without `type` or `name` | The view's index in the `views` list |
| Duplicate view names | Both indices and the shared name |
| `groupBy`/`sort` naming a property that no candidate note has | The property id and where it is referenced |
| Summary name that is neither a default nor an entry in top-level `summaries` | The property and the name used |
| Duration used as a number (`.round()` on a date difference) | The formula name and the expression |
| Unguarded optional property in a formula | The formula name and the property it assumes |
| Unknown view `type` | The type string, reported as a runtime capability question, not a syntax fix |

Report every problem found in one pass, with the exact key path, so the file can be fixed once. "Invalid base" without a location is not a usable result.

A formula that is syntactically valid but references a property no note defines is not an error in the file. It produces empty values, which is a data question -- see the triage below.

## Empty or unexpected results

A base that parses and renders nothing, or renders the wrong rows, is a result to investigate. It is never a licence to loosen the schema until something appears. Work down this order and stop at the first branch that explains the observation:

1. **Wrong file.** Confirm the base you are looking at is the one you edited: compare the vault-relative path shown by the app with the path you wrote. A second base with a similar name is the cheapest explanation and the easiest to miss.
2. **Filters exclude everything.** Re-read the global filters *and* the view filters together -- they combine with `AND`, so a view can be empty while the base looks permissive. Temporarily evaluating a single condition at a time is a diagnostic step, not an edit to leave behind.
3. **Property mismatch.** The filter's spelling, case, or namespace does not match the frontmatter: `status` versus `Status`, a note property shadowed by a file property, a value stored as the string `"2"` compared against the number `2`, or a tag written with a leading `#` in one place and without it in another.
4. **Scope mismatch.** A folder filter that names a path the notes are not in, or a filter that excludes non-Markdown files while the expected rows are attachments.
5. **Index or refresh.** Some properties are documented as not refreshing automatically as the vault changes. A row that is stale rather than missing points here; reopening the base or the app is a legitimate check.
6. **Capability.** The view `type` is not available in the installed build, or a layout needs a plugin that is not enabled. Nothing in the YAML can fix that; report the version and plugin state.

Whatever the branch, describe the outcome in terms of rows: how many were expected, how many appeared, and which specific ones differ. "The base looks wrong" is not a finding.

## Readback and rendering are different claims

Three claims, never inferred from one another:

**1. Static validation.** The document you hold is well formed and internally consistent. Says nothing about the vault.

**2. Exact readback.** After writing, re-read the file from the path you intended and parse what came back. Compare against the document you meant to write: the set of view names in order, the keys you changed, and the constructs that were supposed to stay identical -- other views, other formulas, unknown keys. A write call that returned success is not readback; the comparison against the re-read bytes is. If the file came back from a different path than intended, that is a wrong destination, not a successful write.

**3. Rendered verification.** Open the base in Obsidian and look at the view. Rendering evidence is specific, and all of it comes from the app, not from the file:

- the view that opened is the view you meant (its name in the view menu);
- the number of results the toolbar reports;
- the group headers present, when the view groups;
- the row order, checked against the order your `sort` implies;
- the columns present, checked against `order`;
- summaries, when the view shows them.

State the app version you observed it in and scope the claim to that build. Behaviour seen on one version is not evidence about another.

When the app, the target vault, the renderer, or a required plugin is unavailable, report the rendered leg as unverified. Unverified is a correct outcome; a rendered result inferred from valid YAML is not, and the next reader cannot tell the difference unless you say so. Absence of an app is also not evidence that the base is broken.

## Embedded bases in notes

Base syntax can live in a fenced `base` block inside a note, and a `.base` file can be embedded into a note with `![[Base.base]]` or `![[Base.base#View Name]]`.

- The note is owned by `obsidian-markdown`; this package owns only the base syntax inside the block and the schema behind the embed. Compose that package by identity when the task actually edits a note, and report the gap instead of improvising note syntax when it is not available.
- Editing a block inside a note is a note mutation: preserve the rest of the note exactly, including unrelated blocks, properties, and links.
- Keep the `.base` extension in an embed target. A bare same-stem link is a different target and may reach a Markdown note or stay unresolved.
- A `#View Name` selector is matched by name. Renaming or reordering views changes what existing embeds show, and the base file records nothing about who embeds it. Before renaming, find the notes that reference the view; after renaming, check them.
- Inside an embed, `this` refers to the embedding note rather than the base, so a filter written against `this` behaves differently in the base's own tab and in the note. Verify the form you actually shipped.
- A rendered embed is its own claim. A correct destination does not prove the embedded view renders the rows you expected; check the embed itself or report that leg as unverified.

## Reporting

A complete report of a base operation names:

- the vault-relative path written, and how the target was resolved;
- the effect applied, at the level of views, filters, or formulas;
- what the readback showed, including the constructs that were supposed to stay identical;
- the rendered observation with the app version, or the reason that leg is unverified;
- anything found and not changed, with its key path.

Keep private data out of the report and out of the file: no credentials, account identifiers, workstation paths, or vault contents the request did not ask you to surface.

## Verification checklist

- [ ] The exact vault-relative target and the authorized effect were resolved before writing, or the work stayed read-only and the gap was reported.
- [ ] The existing file was read and parsed before editing, and only the requested construct changed.
- [ ] Unrelated views, their order and names, unrelated formulas and properties, and unknown keys round-tripped unchanged.
- [ ] Validation ran on the in-memory document, and a failing document was not written.
- [ ] Every error condition found was reported with its exact key path, not silently repaired.
- [ ] An empty or unexpected result was triaged as a data, index, or capability question rather than by loosening the schema.
- [ ] The file was re-read from the intended path and compared against the intended document.
- [ ] The rendered view was checked in the app -- view name, result count, groups, row order, columns -- with the app version recorded, or that leg was reported as unverified.
- [ ] Embed and block composition happened only because the task required it, kept the `.base` extension, and left the containing note otherwise unchanged.
