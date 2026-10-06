# Skeleton ideas for plugin drawings

Adapted from pi-extension at the pin in [../PROVENANCE.md](../PROVENANCE.md);
its MIT grant travels in [../NOTICE](../NOTICE). This is input-design guidance,
not a claim that Obsidian accepts standalone skeleton JSON as a saved drawing.

## Shape, label and binding shorthand

Upstream calls an element without a numeric `version` a skeleton. Its standalone
app normalizes that shorthand with `convertToExcalidrawElements`; that app is not
part of this package. A useful planning form is:

```json
{ "type": "rectangle", "id": "api", "x": 100, "y": 100,
  "width": 200, "height": 72, "backgroundColor": "#a5d8ff",
  "fillStyle": "solid", "label": { "text": "API service" } }
```

An arrow plan can name `start.id` and `end.id`, a label can use newlines, and a
frame plan can list `children` ids. A persisted scene needs actual geometry,
measured text, stable ids, mirrored bound-text/arrow relationships and frameId
membership. Merely retaining the shorthand fields does not create those facts.

## Materialize through the owning workflow

- For fresh drawings, use `Scene.box`, `Scene.text`, `Scene.arrow`, `Scene.frame`,
  `add_to_frame` and `group` from the deterministic package-local generator. Its
  ids derive from namespace/keys rather than random normalization. The generator
  stays the source of truth; never rewrite generated output by hand.
- For existing drawings, copy selected elements into ExcalidrawAutomate with
  `copyViewElementsToEAforEditing`, keep their ids and unknown/custom fields,
  change only the approved fields and persist through `addElementsToView`.
  Do not delete/recreate a container to relabel it, remove its version fields, or
  pass a skeleton into `elementsDict`.
- For Mermaid layout, use the installed plugin's `addMermaid` through the bounded
  workflow in [plugin-workflow.md](plugin-workflow.md). Check returned ids and
  image assets rather than assuming every diagram type becomes editable shapes.
- Import only already-full `.excalidraw` scenes through the new-file adapter.
  Skeleton normalization is not an offline-import capability of that adapter.

The read-only inspection tool recognizes shorthand so it can explain missing
normalization. Its warnings do not establish plugin compatibility. Native C/D
checks remain required, particularly for bound labels, arrow routing, images,
rotations, CJK fonts and frame membership.
