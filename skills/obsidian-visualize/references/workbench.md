# Live Plugin Edits (Exception Path)

Use this path for the authorized native plugin edits in [`../SKILL.md`](../SKILL.md): selected edits of a plugin-managed drawing, Mermaid addition and embedding through the plugin's file store. Fresh geometry remains a deterministic file from [`../scripts/excalidraw_scene.py`](../scripts/excalidraw_scene.py); element count is never the reason to switch.

[`plugin-workflow.md`](plugin-workflow.md) gives the pinned implementation facts
and the executable helper with full live/disk/asset preimages and preservation
checks. The older illustrative snapshot below covers only its enumerated fields;
it does not by itself establish whole-element, Markdown or asset preservation.
Use the executable helper for the strengthened transaction. No snippet here has
been verified in a current installed plugin by this source change.

This path trades a deterministic, re-runnable file for a mutation against live app state. It needs an installed plugin, an open drawing, and its own proof that the result reached disk. Nothing here installs, enables, or updates anything.

## Contents

1. [Admission](#1-admission)
2. [Snapshot before touching anything](#2-snapshot-before-touching-anything)
3. [Build and persist](#3-build-and-persist)
4. [Completing an async call through a synchronous eval](#4-completing-an-async-call-through-a-synchronous-eval)
5. [Reload, then render](#5-reload-then-render)
6. [Reporting this path](#6-reporting-this-path)

## 1. Admission

Probe the plugin, the automation object, and every method the task will actually call. Package discovery, a skill being loaded, or a plugin appearing in a list of *available* plugins are none of them an installation check.

```javascript
JSON.stringify((() => {
  const plugin = app.plugins.getPlugin("obsidian-excalidraw-plugin");
  const api = typeof ExcalidrawAutomate === "undefined" ? null : ExcalidrawAutomate;
  const needed = ["getAPI", "getSceneFromFile"];
  return {
    pluginEnabled: Boolean(plugin),
    version: plugin?.manifest?.version ?? null,
    apiPresent: Boolean(api),
    missingMethods: api ? needed.filter((name) => typeof api[name] !== "function") : needed,
    openDrawings: app.workspace.getLeavesOfType("excalidraw").map((leaf) => leaf.view.file?.path ?? null),
  };
})());
```

Read the result as a gate:

| Result | Action |
| --- | --- |
| `pluginEnabled: false` | Report the missing layer and stop. Do not install or enable it, and do not guess a command that might. |
| `apiPresent: false` | Same. The plugin can be enabled while the automation object is unavailable in this context. |
| `missingMethods` non-empty | Stop. Name the methods; the installed version does not expose what the task needs. |
| The target path is absent from `openDrawings` | This exception path does not apply. Either ask the user to open the drawing, or generate a file instead. |

Verify method names against the plugin's published [API surface](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/master/docs/API/ExcalidrawAutomate.d.ts) for the installed version rather than from memory. A method that is absent is a stop, not an invitation to improvise a substitute.

## 2. Snapshot before touching anything

An additive edit has to be provable later, which means recording what "unchanged" means *before* the mutation.

```javascript
async function snapshotDrawing(drawingPath) {
  const file = app.vault.getAbstractFileByPath(drawingPath);
  const leaf = app.workspace.getLeavesOfType("excalidraw")
    .find((candidate) => candidate.view.file?.path === drawingPath);
  if (!file) throw new Error(`No such file: ${drawingPath}`);
  if (!leaf) throw new Error(`Open the drawing first: ${drawingPath}`);
  const scene = await ExcalidrawAutomate.getSceneFromFile(file);
  const baseline = new Map(scene.elements.map((element) => [element.id, {
    x: element.x, y: element.y, width: element.width, height: element.height,
    text: element.text ?? null, link: element.link ?? null,
    frameId: element.frameId ?? null, groupIds: [...(element.groupIds ?? [])],
    containerId: element.containerId ?? null,
    startBinding: element.startBinding?.elementId ?? null,
    endBinding: element.endBinding?.elementId ?? null,
  }]));
  return {file, leaf, baseline};
}
```

Keep the baseline outside the workbench. Step 5 compares the *reloaded* file against it; a snapshot taken from the same live object it is meant to police proves nothing.

## 3. Build and persist

Acquire a workbench, build, then commit to the view:

```javascript
const ea = ExcalidrawAutomate.getAPI();
ea.reset();
// build with ea.addFrame / addRect / addText / addArrow / connectObjects / addToGroup
ea.setView(leaf.view);
const applied = await ea.addElementsToView(false, true, true);
if (!applied) throw new Error("addElementsToView did not apply the scene");
```

- Set `ea.style.roundness = null` before an orthogonal multi-segment arrow — a rounded route can bow outside its frame — and restore the previous value afterwards.
- To change an existing element, copy it into the workbench for editing, mutate the copy the workbench hands back, and commit through the same `addElementsToView` call. Deleting and re-adding is not an additive update; it changes ids and breaks every binding that pointed at the old one.
- A truthy return means the *live scene* accepted the elements. It is not a save. The file on disk can still hold the previous version, which is why step 5 exists.

## 4. Completing an async call through a synchronous eval

The official CLI's `eval` returns synchronous values only, so an `await` inside it resolves after the value has already been returned. Drive the async call through a two-step handshake whose identity the caller owns.

`CALLER_RUN_ID` is not defined by either snippet. Generate one fresh opaque nonce outside the page — never from the DOM, the scene, the plugin, or an earlier eval's output — and substitute the same JSON-quoted string literal (quotes included) for `CALLER_RUN_ID` in **both** evals before sending them. Left unreplaced it is an undeclared identifier: in a normal eval scope — no `with` block, no scope proxy inventing names — it throws `ReferenceError` on the first line, before `performTheMutation()` runs and before a poll can report an earlier run's state. That refusal is the point; a hard-coded literal shipped with the snippet would launch a mutation, and poll it, under a token that is not this run's.

First eval — launch, using a nonce generated and kept by the caller, never read back from the page:

```javascript
(() => {
  const token = CALLER_RUN_ID;
  if (window.__visualizeRun?.token === token) throw new Error("this token was already launched");
  const run = {token, state: "running", value: null, error: null};
  window.__visualizeRun = run;
  Promise.resolve()
    .then(() => performTheMutation())            // the single async operation for this run
    .then((value) => { run.state = "done"; run.value = value; },
          (error) => { run.state = "failed"; run.error = error?.stack ?? String(error); });
  return token;
})();
```

Second eval — poll with the same token:

```javascript
JSON.stringify((() => {
  const token = CALLER_RUN_ID;
  const run = window.__visualizeRun;
  if (!run || run.token !== token) return {state: "absent-or-stale", token};
  return {state: run.state, value: run.value ?? null, error: run.error};
})());
```

- A launch eval that never executed, and a leftover result from an earlier run, both surface as `absent-or-stale`. That is never this run's result.
- `failed`, a poll timeout, and a token mismatch are each a precise incomplete outcome. Report which one happened.
- A retry needs a fresh token *and* fresh authorization for another mutation. Never replay a launch.
- One token launches one operation. Batching two mutations under one token makes a partial failure unattributable.

## 5. Reload, then render

Prove persistence from the file, not from the view:

1. Reload independently: `await ExcalidrawAutomate.getSceneFromFile(file)`.
2. For an additive edit, assert every id in the step-2 baseline is still present with identical geometry, text, links, frame and group membership, and binding targets. Report any drift as a blocker; do not "repair" it.
3. Then check the new elements separately: unique ids, `frameId` pointing at a real frame, group membership as intended, arrow bindings resolving and mirrored on both endpoints, and every wikilink resolving to a note that exists.

Only then render, and render from the reloaded scene:

- Use a fresh automation instance, load the reloaded elements into it, set the theme and background explicitly, and export an image through the plugin's own export call.
- Write the returned bytes to a temporary file and **look at the image**: overlapping cards, clipped labels, unreadable text, wrong hierarchy, wrong semantics.
- Fix, persist, reload, re-render until clean. Then focus the view on the changed elements using the view's own zoom-to-elements or zoom-to-fit method.
- The export is asynchronous, so it needs its own handshake from step 4 with its own token.

An export that was produced but not inspected is not render QA. Say "exported, not inspected" if that is what happened.

## 6. Reporting this path

State: the plugin version the probe returned, that this exception path was used and which of the two cases justified it, the element ids added, the baseline comparison result, and whether the render was inspected. Level C and D from the ladder in [`../SKILL.md`](../SKILL.md) apply here exactly as they do to a generated file — a live scene that "looks right" is not level C, and an uninspected export is not level D.
