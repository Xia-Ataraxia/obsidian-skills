# Canvas Operations Reference

How to change a `.canvas` file that already holds user data, which conditions are errors, and which verification claims are separate. The schema itself lives in [../SKILL.md](../SKILL.md); this reference does not restate node or edge fields.

## Authorization boundary

Resolve the exact target path and the exact authorized effect before writing. Producing a valid document is not permission to change a destination, and a writable surface being available is not an instruction to use it. When the destination, the authorization, or the requested target is missing or ambiguous, keep the operation read-only and report the specific gap.

Optional destination tooling is composed by explicit identity only when the task selects it. The `obsidian-cli` package owns that surface if a CLI operation is the selected owner; its absence is normal, and its presence without selection means it is unused. Canvas authoring itself needs neither that package nor any other.

## Safe graph extension

Extension means adding to a graph, not rewriting it.

1. Read the existing file and parse it once. Work on the parsed structure, never on a textual patch of JSON.
2. Keep every existing `id` exactly as found, for nodes and for edges. Never regenerate, normalize, or renumber IDs to tidy a file; downstream links, edges, and app state are keyed on them.
3. Keep unrelated data. Nodes and edges outside the requested change stay untouched, and any key the schema does not define is carried through unchanged rather than dropped as unknown. Preserve the top-level shape, including an empty `"edges": []`.
4. Keep array order. Node order is z-index (first is bottom, last is top), so append new nodes at the end unless the task asks for a specific stacking, and do not sort or regroup existing entries.
5. Generate new IDs as 16-character lowercase hex and test each against the union of existing node IDs and edge IDs before use.
6. Place new geometry in free space, 50-100px from existing nodes. Do not move, resize, or re-flow existing nodes to make room unless relayout was requested; position changes are user-visible edits.
7. Modify only the targeted objects, then write the whole document back from the validated in-memory structure in a single write. Do not emit a partially updated file.
8. Validate the in-memory result before writing. A file that fails validation is not written at all, so a failed edit leaves the previous content intact.

## Duplicate and dangling IDs are errors

Build an ID map over the union of node IDs and edge IDs. Insert collisions and unresolved references are failures to report, not defects to repair silently.

- **Duplicate ID**: report the colliding ID and both occurrences, and stop. Do not rename one, drop one, or pick a winner; either resolution silently changes which object edges and app state refer to.
- **Dangling edge reference**: an edge whose `fromNode` or `toNode` does not match an existing node ID. Report the edge ID and the missing node ID. Do not invent a placeholder node, and do not delete the edge as a cleanup step that was not requested.
- **Node deletion**: removing a node orphans every edge that references it. Either delete those edges as part of the same requested change, or stop and report the affected edge IDs. Never leave the orphans behind as valid output.
- **Self-referencing or repeated edges** between the same pair are structurally valid; do not report them as errors and do not deduplicate them.

State counts and IDs in the report. "Validation failed" without the offending ID and field is not a usable result.

## Malformed input and missing attachments

- **Unparseable JSON**: report the parse error position and leave the file unchanged. Do not guess a repair of truncated or hand-edited JSON.
- **Structural violations**: `nodes` or `edges` present but not arrays, a node missing `id`/`type`/`x`/`y`/`width`/`height`, a text node without `text`, a file node without `file`, a link node without `url`, an unknown `type`, or an out-of-range value for `fromSide`/`toSide`/`fromEnd`/`toEnd`/`backgroundStyle`/color preset. Report the object's `id` and the exact field. Non-integer or non-numeric geometry is the same class of failure.
- **Escaping**: a text node containing a literal backslash-n instead of a JSON `\n` escape is a content defect that parses successfully. Report it rather than assuming the author wanted a line break.
- **Missing attachment**: a file node whose `file` path does not exist at the destination, or a group whose `background` image is absent. Report the node ID and the path. Do not create the missing file, do not blank the path, and do not convert the node to another type to make the document resolve.
- **Unverifiable destination**: if the destination cannot be inspected, report the attachment leg as unverified. Absence of evidence is not evidence that the attachment exists, and it is not proof that it is missing either.
- **Link nodes**: `url` is validated as a present string only. This package does not fetch URLs, so reachability is never claimed.
- Report every failure found in one pass instead of stopping at the first, so the caller can fix the file once.

## Exact readback, then rendering, as separate claims

Static validation, materialized readback, and rendered verification are three independent claims. Passing one never grants another, and none of them may be inferred from the document held in memory.

**Exact readback.** After writing, re-read the file from its destination path and parse what came back. Compare the parsed result against the intended structure: the full set of node and edge IDs, every field that was supposed to change, and the objects that were supposed to stay identical. A write call that returned success is not readback; the comparison against the re-read bytes is. If the readback path differs from the intended path, report a wrong destination rather than a successful write.

**Rendering.** Open the canvas in the actual application to confirm it renders. If the app, its index, the renderer, or the target vault is unavailable, report the rendering leg as unverified. Never derive rendering from valid JSON or from a successful readback.

**Embedded canvases.** The [official embed documentation](https://help.obsidian.md/embeds) states that an embedded canvas shows shapes only, not the text inside cards. That is documented behavior, not a broken destination and not a failed edit. Open the canvas itself to inspect card content, and never promise readable card text from an embed.

## Markdown embeds, only when needed

Canvas work does not require touching any note. Compose a Markdown change only when the task explicitly asks for the canvas to be linked or embedded from a note; otherwise the canvas file is the whole deliverable.

When it is needed, the `obsidian-markdown` package owns link and embed syntax and owns source-note readback; this reference adds only the Canvas-side constraints:

- Keep the extension in the link target, as [Obsidian's internal-link documentation](https://help.obsidian.md/links) requires: `[[My canvas.canvas]]`, or `[[My canvas.canvas|Overview]]` with display text. A bare same-stem link may resolve to a Markdown note or stay unresolved, and either way it does not prove the `.canvas` file was reached.
- Include the vault-relative folder path when several files share a name.
- After the link change, resolve the destination in the source note's own context through the supported native app surface and compare the returned path with the exact intended vault-relative `.canvas` path. An unresolved result is a failure; a resolved but different path is a wrong destination even when nothing is reported as unresolved.
- Link resolution is not rendering evidence. Check the rendered embed separately, or report that leg as unverified.
- Preserve the note's unrelated content, properties, and links. Editing a note to reference a canvas is not a license to reformat it.

## Verification checklist

- [ ] The exact destination path and authorized effect were resolved before writing, or the operation stayed read-only and the gap was reported.
- [ ] Every pre-existing node and edge ID is unchanged; unrelated objects and undefined keys round-tripped intact; node order preserved.
- [ ] ID uniqueness was checked across the union of node and edge IDs, and duplicates were reported as errors with their IDs.
- [ ] Every `fromNode`/`toNode` resolves, or each dangling reference was reported with its edge ID and missing node ID.
- [ ] Malformed objects and missing attachments were reported with ID, field, and path, and the file was left unchanged on failure.
- [ ] The materialized file was re-read from the intended path and compared field by field with the intended structure.
- [ ] Rendering was checked in the actual application, or that leg was reported as unverified.
- [ ] Markdown link or embed composition happened only because the task required it, kept the `.canvas` extension, and was checked in the source note's context.
