// Stateful API-boundary tests, NOT execution of Obsidian or its plugin.
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
  "../../skills/obsidian-visualize/scripts/plugin-workbench.js"), "utf8");
const callerModule = { exports: { retain: "caller module" } };
const deadlines = new Map();
let deadlineId = 0;
const workbench = vm.runInNewContext(source, {
  module: callerModule, crypto: globalThis.crypto, TextEncoder,
  setTimeout: (callback, milliseconds) => {
    assert.equal(milliseconds, 30000);
    deadlines.set(++deadlineId, callback);
    return deadlineId;
  },
  clearTimeout: (id) => deadlines.delete(id),
});
const copy = (value) => JSON.parse(JSON.stringify(value));
const file = { path: "Diagrams/Flow.excalidraw.md", extension: "md" };
const initial = [
  { id: "left", type: "rectangle", x: 0, y: 0, width: 100, height: 50, version: 1,
    customData: { retain: "user", version: 7 } },
  { id: "right", type: "rectangle", x: 200, y: 0, width: 100, height: 50, version: 1 },
  { id: "picture", type: "image", fileId: "asset", x: 200, y: 100,
    width: 100, height: 50, version: 1, customData: { retain: "image user" } },
  { id: "label", type: "text", text: "Control label", x: 200, y: 160,
    width: 100, height: 20, version: 1, customData: { baseFontSize: 17 } },
];
const initialFiles = { asset: { id: "asset", dataURL: "data:image/png;base64,AA==", created: 1 } };
test("evaluating helpers returns operations without modifying the caller module", () => {
  assert.equal(typeof workbench.update, "function");
  assert.deepEqual(callerModule.exports, { retain: "caller module" });
});
function document(elements, extra = "", files = initialFiles) {
  return "---\nexcalidraw-plugin: parsed\nkeep: user\n---\nUser prose.\n\n" +
    "# Excalidraw Data\n\n## Text Elements\n" +
    elements.filter((element) => element.type === "text")
      .map((element) => element.text + " ^" + element.id + "\n\n").join("") +
    "\n## Embedded Files\nasset: [[Attachments/User.png]]\n\n" +
    "%%\n## Drawing\n```json\n" + JSON.stringify({ elements, files }) +
    "\n```\n%%\n" + extra;
}
function fixture() {
  const listeners = new Set();
  const state = { live: copy(initial), files: copy(initialFiles),
    document: document(initial), commits: 0, exports: 0, destroyed: 0,
    attachments: [{ path: "Attachments/User.png", extension: "png" }], attachmentByte: 0 };
  const api = { getSceneElementsIncludingDeleted: () => state.live, getFiles: () => state.files };
  const view = { file, forceSave: async (silent, wait) => {
    assert.equal(silent, true);
    assert.equal(wait, true);
    assert.equal(state.flushed, true); // Writer cannot capture the preceding frame.
    const saved = copy(state.live);
    if (state.savedDrift === "unexpected") saved.push({ ...copy(initial[0]), id: "unexpected" });
    if (state.savedDrift === "duplicate") saved.push(copy(saved[0]));
    let savedDocument = document(saved, state.extra ?? "", state.savedFiles ?? state.files);
    if (state.transformDocument) savedDocument = state.transformDocument(savedDocument);
    if (state.failPersistence) {
      for (const callback of deadlines.values()) callback();
    } else {
      if (state.deferSave) await state.deferSave();
      state.document = savedDocument;
      for (const callback of listeners) callback(file);
    }
  } };
  const automation = {
    getSceneFromFile: async () => ({ elements: JSON.parse(
      state.document.match(/```json\n([\s\S]*?)\n```/)[1]).elements }),
    getAPI: () => {
      const elements = {};
      return {
        imagesDict: {}, setView: () => {}, clear: () => {},
        getExcalidrawAPI: () => api,
        copyViewElementsToEAforEditing: (selected) => {
          for (const element of selected) elements[element.id] = copy(element);
        },
        getElement: (id) => elements[id],
        getElements: () => Object.values(elements),
        viewUpdateScene: (update) => {
          assert.deepEqual(copy(update), { appState: {} });
          state.flushed = true;
        },
        getEmbeddedFilesLoader: () => ({
          terminalState: "idle", emptyPDFDocsMap: () => {},
          async loadSceneFiles(options) {
            assert.equal(options.cacheValidation, "validated");
            assert.deepEqual([...options.forceReloadFileIDs], ["asset"]);
            if (state.onAssetLoad) await state.onAssetLoad(options);
            this.terminalState = state.assetLoadState ?? "completed";
          },
        }),
        createSVG: async (path, _font, _settings, loader) => {
          assert.equal(path, file.path);
          if (!state.noAssetReadback) {
            const scene = JSON.parse(state.document.match(/```json\n([\s\S]*?)\n```/)[1]);
            await loader.loadSceneFiles({ excalidrawData: { file, scene } });
          }
          return {}; // Boundary-only; no native rendering is claimed.
        },
        addMermaid: async () => {
          if (state.onMermaid) await state.onMermaid();
          const element = { id: "mermaid", type: "rectangle", x: 400, y: 0,
            width: 100, height: 50, version: 1 };
          elements[element.id] = element;
          return state.mermaidError ?? ["mermaid"];
        },
        addElementsToView: async (_cursor, save) => {
          assert.equal(save, false);
          assert.equal(listeners.size, 1); // Exact event subscribed before mutation.
          state.commits++;
          if (state.commitFails) return false;
          for (const element of Object.values(elements)) {
            const index = state.live.findIndex((item) => item.id === element.id);
            if (index < 0) state.live.push(copy(element));
            else state.live[index] = copy(element);
          }
          if (state.corruptNonTarget) state.live.find((item) => item.id === "right").x = 999;
          if (state.corruptTarget) delete state.live.find((item) => item.id === "left").customData;
          if (state.onCommit) state.onCommit();
          if (state.liveDrift === "unexpected") state.live.push({ ...copy(initial[0]), id: "unexpected" });
          if (state.liveDrift === "duplicate") state.live.push(copy(state.live[0]));
          return true;
        },
        createPNG: async (path) => {
          assert.equal(path, file.path);
          state.exports++;
          return new Blob(["fixture-only-not-a-render"]);
        },
        destroy: () => { state.destroyed++; },
      };
    },
  };
  const app = {
    plugins: { getPlugin: () => state.disabled ? null : { manifest: { version: "fixture-only" } } },
    workspace: { getLeavesOfType: () => state.closed ? [] : [{ view }] },
    metadataCache: { getFirstLinkpathDest: (link) => state.attachments.find((attachment) =>
      attachment.path === link || attachment.path.endsWith("/" + link)) },
    vault: { getAbstractFileByPath: (path) => path === file.path ? file : null,
      on: (event, callback) => {
        assert.equal(event, "modify");
        listeners.add(callback);
        return callback;
      },
      offref: (callback) => listeners.delete(callback),
      getFiles: () => state.attachments,
      readBinary: async () => new Uint8Array([state.attachmentByte]).buffer,
      read: async () => state.document },
  };
  return { state, context: { app, automation } };
}
test("fixture reload reads persisted bytes independently of live elements", async () => {
  const { state, context } = fixture();
  state.live[0].x = 123;
  assert.equal((await context.automation.getSceneFromFile(file)).elements[0].x, 0);
});
test("selected native update preserves other elements assets and document prose", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  const result = await workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } });
  assert.equal(state.live[0].x, 80);
  assert.deepEqual(state.live[1], initial[1]);
  assert.deepEqual(state.live[0].customData, initial[0].customData);
  assert.deepEqual(state.files, initialFiles);
  assert.deepEqual(copy(result.targetIds), ["left"]);
  assert.equal(result.renderInspected, false);
  assert.equal(state.commits, 1);
});
test("evidenced native defaults and unique same-target link shortening preserve content", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.onCommit = () => {
    Object.assign(state.live.find((element) => element.id === "label"),
      { labelPosition: null, baseFontSize: null });
    state.live.find((element) => element.id === "picture").status = "pending";
  };
  state.transformDocument = (text) => text.replace("[[Attachments/User.png]]", "[[User.png]]")
    .replace("\n\n\n## Embedded", "\n\n## Embedded");
  const result = await workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } });
  assert.equal(state.commits, 1);
  assert.equal(result.evidence, "plugin-persisted-readback");
  assert.deepEqual(state.live.find((element) => element.id === "label").customData,
    { baseFontSize: 17 });
  assert.deepEqual(state.files, initialFiles);
});
test("pending to saved image status retains independently bound bytes", async () => {
  const { state, context } = fixture();
  state.live.find((element) => element.id === "picture").status = "pending";
  state.document = document(state.live);
  const baseline = await workbench.snapshot(context, file.path);
  state.onCommit = () => { state.live.find((element) => element.id === "picture").status = "saved"; };
  await workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } });
});
test("native queued save completion gates independent readback without sleeps", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  let entered, release;
  const entry = new Promise((resolve) => { entered = resolve; });
  const barrier = new Promise((resolve) => { release = resolve; });
  state.deferSave = async () => { entered(); await barrier; };
  let completed = false;
  const pending = workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }).then((result) => { completed = true; return result; });
  await entry;
  assert.equal(completed, false);
  release();
  assert.equal((await pending).evidence, "plugin-persisted-readback");
  assert.equal(deadlines.size, 0);
});
for (const drift of ["label-value", "nested-custom", "text-content", "style", "image-status",
  "attachment-bytes", "same-bytes-other-target", "ambiguous-short-link", "frontmatter",
  "prose", "unrelated-index"]) {
  test(`content normalization does not authorize ${drift}`, async () => {
    const { state, context } = fixture();
    const baseline = await workbench.snapshot(context, file.path);
    state.onCommit = () => {
      const label = state.live.find((element) => element.id === "label");
      if (drift === "label-value") label.baseFontSize = 18;
      if (drift === "nested-custom") label.customData.baseFontSize = null;
      if (drift === "text-content") label.text = "Changed content";
      if (drift === "style") label.strokeColor = "red";
      if (drift === "image-status") state.live.find((element) => element.id === "picture").status = "error";
      if (drift === "attachment-bytes") state.attachmentByte = 1;
      if (drift === "same-bytes-other-target")
        state.attachments = [{ path: "Elsewhere/User.png", extension: "png" }];
      if (drift === "ambiguous-short-link")
        state.attachments.push({ path: "Elsewhere/User.png", extension: "png" });
    };
    state.transformDocument = (text) => {
      if (drift === "same-bytes-other-target")
        return text.replace("[[Attachments/User.png]]", "[[Elsewhere/User.png]]");
      if (drift === "ambiguous-short-link")
        return text.replace("[[Attachments/User.png]]", "[[User.png]]");
      if (drift === "frontmatter") return text.replace("keep: user", "keep: changed");
      if (drift === "prose") return text.replace("User prose.", "Changed prose.");
      if (drift === "unrelated-index")
        return text.replace("Control label ^label", "Changed index ^label");
      return text;
    };
    await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
      patches: { left: { x: 80 } } }), (error) => error.partialEffect === true);
    assert.equal(state.commits, 1);
  });
}
test("geometry-only selected text patch keeps its text-index content", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.transformDocument = (text) => text.replace("Control label ^label", "Wrong text ^label");
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { label: { x: 300 } } }), (error) => error.partialEffect === true);
});
test("ambiguous existing attachment refuses before commit even with identical bytes", async () => {
  const { state, context } = fixture();
  state.document = state.document.replace("[[Attachments/User.png]]", "[[User.png]]");
  state.attachments.push({ path: "Elsewhere/User.png", extension: "png" });
  await assert.rejects(workbench.snapshot(context, file.path), /ambiguous attachment/);
  assert.equal(state.commits, 0);
});
test("changed disk preimage refuses before native commit", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.document += "Concurrent edit.\n";
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
  assert.equal(state.commits, 0);
});
test("unsaved live user edit refuses before native commit", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.live[1].customData = { userEdit: "retained" };
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
  assert.equal(state.commits, 0);
  assert.deepEqual(state.live[1].customData, { userEdit: "retained" });
});
test("user edit during async Mermaid preparation refuses without timing luck", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  let entered, release;
  const entry = new Promise((resolve) => { entered = resolve; });
  const barrier = new Promise((resolve) => { release = resolve; });
  state.onMermaid = async () => { entered(); await barrier; };
  const pending = workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    mermaid: "flowchart LR\n A --> B" });
  await entry;
  state.live[0].x = 321;
  release();
  await assert.rejects(pending);
  assert.equal(state.commits, 0);
  assert.equal(state.live[0].x, 321);
});
test("Mermaid adds through native workbench and independent persisted reload", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  const result = await workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    mermaid: "flowchart LR\n A --> B" });
  assert.deepEqual(copy(result.addedIds), ["mermaid"]);
  assert.deepEqual(state.live.slice(0, initial.length), initial);
});
for (const corruption of ["removed", "changed"]) {
  test(`saved asset ${corruption} while live files stay intact reports partial effect`, async () => {
    const { state, context } = fixture();
    const baseline = await workbench.snapshot(context, file.path);
    state.savedFiles = corruption === "removed" ? {} : copy(initialFiles);
    if (corruption === "changed") state.savedFiles.asset.dataURL = "data:image/png;base64,BB==";
    await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
      patches: { left: { x: 80 } } }), (error) => error.partialEffect === true);
    assert.equal(state.commits, 1);
    assert.equal(state.live[0].x, 80);
    assert.deepEqual(state.files, initialFiles);
    const saved = JSON.parse(state.document.match(/```json\n([\s\S]*?)\n```/)[1]);
    assert.deepEqual(saved.files, state.savedFiles); // No rollback or replay.
  });
}
for (const surface of ["no-callback", "failed-loader"]) {
  test(`native saved asset readback ${surface} after commit cannot report success`, async () => {
    const { state, context } = fixture();
    const baseline = await workbench.snapshot(context, file.path);
    if (surface === "no-callback") state.noAssetReadback = true;
    else state.assetLoadState = "failed";
    await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
      patches: { left: { x: 80 } } }), (error) => error.partialEffect === true);
    assert.equal(state.commits, 1);
    assert.equal(state.live[0].x, 80);
  });
}
test("native asset completion is awaited before a persisted receipt", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  let entered, release;
  const entry = new Promise((resolve) => { entered = resolve; });
  const barrier = new Promise((resolve) => { release = resolve; });
  state.onAssetLoad = async (options) => {
    entered();
    await barrier;
    options.excalidrawData.scene.files.asset.dataURL = "data:image/png;base64,BB==";
  };
  const pending = workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } });
  const rejected = assert.rejects(pending, (error) => error.partialEffect === true);
  await entry;
  assert.equal(state.commits, 1);
  release();
  await rejected;
  assert.deepEqual(state.files, initialFiles);
});
for (const [store, drift] of [["live", "unexpected"], ["saved", "unexpected"],
  ["live", "duplicate"], ["saved", "duplicate"]]) {
  test(`${store} ${drift} element ID after commit reports partial drift`, async () => {
    const { state, context } = fixture();
    const baseline = await workbench.snapshot(context, file.path);
    state[`${store}Drift`] = drift;
    await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
      patches: { left: { x: 80 } } }), (error) => error.partialEffect === true);
    assert.equal(state.commits, 1);
    const saved = JSON.parse(state.document.match(/```json\n([\s\S]*?)\n```/)[1]).elements;
    const affected = store === "live" ? state.live : saved;
    assert.equal(affected.length, initial.length + 1);
    if (drift === "duplicate") assert.equal(affected.filter((element) => element.id === "left").length, 2);
    else assert.equal(affected.at(-1).id, "unexpected");
  });
}
test("approved Mermaid additions do not authorize other persisted IDs", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.savedDrift = "unexpected";
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    mermaid: "flowchart LR\n A --> B" }), (error) => error.partialEffect === true);
  assert.equal(state.commits, 1);
  assert.equal(state.live.at(-1).id, "mermaid");
});
test("duplicate native Mermaid addition IDs refuse before commit", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.mermaidError = ["mermaid", "mermaid"];
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    mermaid: "flowchart LR\n A --> B" }));
  assert.equal(state.commits, 0);
});
test("old snapshots without native saved assets refuse before commit", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  delete baseline.savedAssets;
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
  assert.equal(state.commits, 0);
});
test("failed persistence cannot become a successful update receipt", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.failPersistence = true;
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
  assert.equal(state.commits, 1); // Partial native effect; no automatic rollback.
});
test("unexpected non-target drift is reported after native commit", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.corruptNonTarget = true;
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
});
test("unselected custom fields on a selected element are also preserved", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.corruptTarget = true;
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
});
test("unrelated Markdown drift is not hidden by scene readback", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  state.extra = "Unexpected appended prose.\n";
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { x: 80 } } }));
});
test("identity replacement and stale render preimage have no effects", async () => {
  const { state, context } = fixture();
  const baseline = await workbench.snapshot(context, file.path);
  await assert.rejects(workbench.update(context, { baseline, expectedSha256: baseline.sha256,
    patches: { left: { id: "replacement" } } }));
  await assert.rejects(workbench.renderPNG(context, { path: file.path, expectedSha256: "0".repeat(64) }));
  assert.equal(state.commits, 0);
  assert.equal(state.exports, 0);
});
test("disabled plugin and unopened exact target refuse snapshot", async () => {
  const { state, context } = fixture();
  state.disabled = true;
  await assert.rejects(workbench.snapshot(context, file.path));
  state.disabled = false;
  state.closed = true;
  await assert.rejects(workbench.snapshot(context, file.path));
});
