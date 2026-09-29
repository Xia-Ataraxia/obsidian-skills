# Embeds Reference

An embed is a wikilink prefixed with `!`: the target's content is rendered inline instead of being linked. Everything that applies to link targeting applies to embeds -- see *Link targets that are not Markdown notes* and *Destination readback* in this package's `SKILL.md`.

## Link or Embed

| Use | Form | When |
|-----|------|------|
| Link | `[[Note Name]]` | The reader should be able to go there; the target is long; the target changes often |
| Embed | `![[Note Name]]` | The content must be read in place; a single figure, table, or definition is the point |

Prefer embedding a specific heading or block over a whole note. A whole-note embed grows silently as the source note grows.

## Embed Notes

```markdown
![[Note Name]]
![[Note Name#Heading]]
![[Note Name#^block-id]]
```

- The heading subpath must match the heading text as written in the target note, without the leading `#` marks.
- Nested headings can be disambiguated by chaining: `![[Note Name#Section#Subsection]]`.
- Never embed a note into itself, and avoid embed cycles between two notes; the renderer cannot expand them.

## Embed Images

```markdown
![[image.png]]
![[image.png|640x480]]    Width x Height
![[image.png|300]]        Width only (maintains aspect ratio)
```

The pipe means "size" only for embedded images and similar sized media. In a plain link (`[[Note Name|Board]]`) the same pipe means display text, so `[[image.png|300]]` without the `!` prefix produces a link labelled `300`.

## External Images

```markdown
![Alt text](https://example.com/image.png)
![Alt text|300](https://example.com/image.png)
```

Wrap the URL in angle brackets when it contains spaces or parentheses: `![Alt text](<https://example.com/my image.png>)`.

## Embed Audio

```markdown
![[audio.mp3]]
![[audio.ogg]]
```

## Embed Video

```markdown
![[clip.mp4]]
![[clip.webm]]
```

A video or audio embed renders a player, so its playable state cannot be judged from the note source; confirm it in reading view.

## Embed PDF

```markdown
![[document.pdf]]
![[document.pdf#page=3]]
![[document.pdf#height=400]]
```

`#page=` and `#height=` are PDF-specific subpaths, not heading links, and are written without the `^` block marker.

## Embed Bases

```markdown
![[BaseFile.base]]
![[BaseFile.base#View Name]]
```

The `#View Name` subpath selects a view defined inside the base file, so it must match a view name that exists there. The base file's own filters, formulas, views, and summaries belong to the `obsidian-bases` skill; this reference defines only how a note embeds one.

## Embed Canvas

```markdown
![[Team Board.canvas]]
```

[Obsidian's embed documentation](https://help.obsidian.md/embeds) states that an embedded canvas displays the shapes only, not the text inside cards. Expect that result: it is not an unresolved link and not a defect to be fixed by rewriting the link. Open the canvas itself when the card text matters.

Canvas node and edge structure belongs to the `obsidian-canvas` skill. This reference defines only the note-side link and embed, plus the readback that proves the `.canvas` file -- and not a same-named Markdown note -- was reached.

## Embed Lists

```markdown
![[Note#^list-id]]
```

Where the list has a block ID:

```markdown
- Item 1
- Item 2
- Item 3

^list-id
```

Block identifiers may use letters, numbers, and hyphens. For a paragraph the identifier goes at the end of the line; for a list, table, or blockquote it goes on its own line after a blank line, as above.

## Embed Search Results

````markdown
```query
tag:#project status:done
```
````

A `query` block is evaluated by the app's search at render time, so its result is not stored in the note and cannot be checked by reading the file. Verify it in reading view.

## External Media and Web Pages

An image-style link to an external media URL (`![](https://...)`) renders an inline player for the services the app supports, and an `<iframe>` element embeds an arbitrary page. Both depend on network access and app settings, so confirm each one in reading view rather than assuming it rendered.

## Paths and Ambiguity

- Include enough of the vault-relative folder path when several files share a basename: `![[Projects/Architecture Diagram.png|600]]`.
- Keep the extension for every non-Markdown target. `![[Team Board]]` embeds a Markdown note, never the canvas.
- Markdown-style embeds work for paths that are awkward in a wikilink: `![](Projects/Architecture%20Diagram.png)`.

## Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Embed renders as plain link text | Missing `!` prefix | Prefix the wikilink with `!` |
| Nothing renders, link shows as unresolved | Wrong path, wrong extension, or missing file | Resolve the destination from the source note |
| Wrong note appears | Bare stem reached a same-named Markdown note | Add the extension and folder path |
| Section embed is empty | Heading text or block ID does not match the target | Copy the heading text exactly; confirm the block ID exists |
| Image ignores the size | Size given on a link instead of an embed, or on an unsupported target | Use `![[file\|width]]` on an image embed |
| Canvas embed shows no card text | Documented behavior | Open the canvas; do not rewrite the link |

## Verification

- [ ] Every embed uses the `!` prefix and keeps the target's extension.
- [ ] Heading and block subpaths match text that exists in the target.
- [ ] Each changed embed destination was resolved from its source note, or reported as unverified.
- [ ] Rendered output was checked in reading view for note, image, PDF, base, canvas, media, and query embeds, or the render leg was reported as unverified.
- [ ] No embed cycle or self-embed was introduced.
