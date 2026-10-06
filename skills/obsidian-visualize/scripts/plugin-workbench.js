/* Original package-local ExcalidrawAutomate helpers. No installation or file-system access.
 * Evaluate this file in the selected Obsidian context, then call one named operation.
 * See references/plugin-workflow.md for authorization, versions and evidence limits.
 */
(() => {
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const volatile = new Set(["version", "versionNonce", "updated", "index"]);
  const canonical = (value, omitVolatile = false) => {
    if (Array.isArray(value)) return value.map((item) => canonical(item));
    if (value && typeof value === "object") return Object.fromEntries(
      Object.keys(value).sort().filter((key) => !omitVolatile || !volatile.has(key))
        .map((key) => [key, canonical(value[key])]),
    );
    return value;
  };
  const same = (a, b, omitVolatile = false) =>
    JSON.stringify(canonical(a, omitVolatile)) === JSON.stringify(canonical(b, omitVolatile));
  const digest = async (text) => Array.from(new Uint8Array(
    await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
  )).map((byte) => byte.toString(16).padStart(2, "0")).join("");
  const exactPath = (path) => {
    if (typeof path !== "string" || !path || path.includes("\\") || path.startsWith("/") ||
        path.split("/").some((part) => !part || part === "." || part === "..") ||
        !path.endsWith(".excalidraw.md"))
      throw new Error("an exact vault-relative drawing path is required");
    return path;
  };
  const methods = (api, names) => {
    for (const name of names) if (typeof api?.[name] !== "function")
      throw new Error(`unavailable method: ${name}`);
  };
  const probe = ({ app, automation }) => {
    const plugin = app.plugins.getPlugin("obsidian-excalidraw-plugin");
    if (!plugin) throw new Error("Excalidraw plugin is not enabled in this target");
    methods(automation, ["getAPI", "getSceneFromFile"]);
    return { pluginVersion: plugin.manifest?.version ?? null,
      openDrawings: app.workspace.getLeavesOfType("excalidraw")
        .map((leaf) => leaf.view.file?.path ?? null) };
  };
  const getFile = (app, path) => {
    const file = app.vault.getAbstractFileByPath(path);
    if (!file || file.path !== path || file.extension === undefined)
      throw new Error("exact drawing file is unavailable");
    return file;
  };
  const viewFor = (app, path) => {
    const leaves = app.workspace.getLeavesOfType("excalidraw")
      .filter((leaf) => leaf.view.file?.path === path);
    if (leaves.length !== 1) throw new Error("open exactly one view of the selected drawing");
    return leaves[0].view;
  };
  // The user prose/frontmatter and the plugin's asset records are separate from
  // the scene codec. Never decode or hand-patch compressed drawing data.
  const protectedParts = (document, targetIds = new Set()) => {
    if (!document.includes("# Excalidraw Data")) throw new Error("not a plugin Markdown drawing");
    const drawing = /^## Drawing\r?\n```(?:json|compressed-json)\r?\n[\s\S]*?\r?\n```/gm;
    const fences = [...document.matchAll(drawing)];
    if (fences.length !== 1) throw new Error("one plugin Drawing fence is required");
    let protectedDocument = document.replace(drawing, "## Drawing\n<plugin-managed-scene>");
    const index = /^## Text Elements\r?\n([\s\S]*?)(?=^## |^%%|(?![\s\S]))/m;
    const indexed = {};
    protectedDocument = protectedDocument.replace(index, (_section, entries) => {
      const remainder = entries.replace(/([\s\S]*?) \^([^\s]+)(\r?\n|$)/g,
        (_entry, body, id) => {
          if (id in indexed) throw new Error("duplicate text-index id");
          if (!targetIds.has(id)) indexed[id] = body.replace(/^(?:\r?\n)+|(?:\r?\n)+$/g, "");
          return "";
        });
      if (remainder.trim()) throw new Error("unrecognized text-index content");
      return "## Text Elements\n<plugin-managed-index>\n\n";
    });
    const embedded = {};
    protectedDocument = protectedDocument.replace(
      /^## Embedded Files\r?\n([\s\S]*?)(?=^## |^%%|(?![\s\S]))/m,
      (_section, entries) => {
        for (const line of entries.split(/\r?\n/)) {
          if (!line.trim()) continue;
          const record = /^([^\s:]+): (.+)$/.exec(line);
          if (!record || record[1] in embedded) throw new Error("invalid embedded-file record");
          embedded[record[1]] = record[2];
        }
        return "## Embedded Files\n<plugin-managed-asset-index>\n\n";
      });
    return { document: protectedDocument, indexed, embedded };
  };
  const attachmentBindings = async (context, path, document) => {
    const bindings = {};
    for (const [id, record] of Object.entries(protectedParts(document).embedded)) {
      const link = /^\[\[([^\]#|]+)\]\]$/.exec(record);
      if (!link) {
        if (record.includes("[[")) throw new Error("exact plain vault attachment link required");
        bindings[id] = { record }; // Non-file records retain their exact native spelling.
        continue;
      }
      methods(context.app.metadataCache, ["getFirstLinkpathDest"]);
      methods(context.app.vault, ["getFiles", "readBinary"]);
      const target = context.app.metadataCache.getFirstLinkpathDest(link[1], path);
      const candidates = context.app.vault.getFiles().filter((file) =>
        file.path === link[1] || file.path.endsWith("/" + link[1]));
      if (!target || candidates.length !== 1 || candidates[0].path !== target.path)
        throw new Error(`unresolved or ambiguous attachment: ${id}`);
      bindings[id] = { record, target: target.path,
        sha256: await globalThis.crypto.subtle.digest("SHA-256",
          await context.app.vault.readBinary(target)).then((hash) =>
          Array.from(new Uint8Array(hash)).map((byte) => byte.toString(16).padStart(2, "0")).join("")) };
    }
    return bindings;
  };
  const persistedAssets = async (context, path) => {
    const reader = context.automation.getAPI();
    let loader;
    try {
      methods(reader, ["clear", "getEmbeddedFilesLoader", "createSVG"]);
      reader.clear();
      loader = reader.getEmbeddedFilesLoader();
      methods(loader, ["loadSceneFiles", "emptyPDFDocsMap"]);
      const load = loader.loadSceneFiles.bind(loader);
      let assets;
      // Decorate only this fresh native loader. The template parser owns the
      // codec; capture its saved-file data, never the live view's file cache.
      loader.loadSceneFiles = async (options) => {
        const data = options.excalidrawData;
        if (data.file?.path !== path) return load(options);
        if (!data.scene?.files || typeof data.scene.files !== "object" ||
            Array.isArray(data.scene.files)) throw new Error("native saved assets unavailable");
        const serialized = clone(data.scene.files);
        const imageIds = data.scene.elements.filter((element) => element.type === "image")
          .map((element) => element.fileId);
        await load({ ...options, cacheValidation: "validated",
          forceReloadFileIDs: new Set([...Object.keys(serialized), ...imageIds]) });
        if (loader.terminalState !== "completed")
          throw new Error("native saved asset loading did not complete");
        assets = { serialized, loaded: clone(data.scene.files) };
      };
      await reader.createSVG(path, false, undefined, loader);
      if (!assets) throw new Error("native saved asset readback unavailable");
      return assets;
    } finally {
      if (loader) {
        loader.terminate = true;
        if (typeof loader.emptyPDFDocsMap === "function") loader.emptyPDFDocsMap();
      }
      if (typeof reader.destroy === "function") reader.destroy();
    }
  };
  const assertUnchanged = (before, after, patches, addedIds, verifiedImages) => {
    const beforeIds = new Set(before.map((element) => element.id));
    const afterIds = new Set(after.map((element) => element.id));
    const expectedIds = new Set([...beforeIds, ...addedIds]);
    if (beforeIds.size !== before.length || afterIds.size !== after.length ||
        expectedIds.size !== beforeIds.size + addedIds.length ||
        afterIds.size !== expectedIds.size ||
        [...expectedIds].some((id) => !afterIds.has(id)))
      throw new Error("unexpected or duplicate element ids after commit");
    const byId = new Map(after.map((element) => [element.id, element]));
    for (const element of before) {
      const expected = { ...element, ...(patches[element.id] ?? {}) };
      const actual = clone(byId.get(element.id));
      // Only these observed top-level native defaults are content-equivalent.
      // In particular, nested custom fields and non-null label values stay strict.
      if (expected.type === "text") for (const key of ["labelPosition", "baseFontSize"])
        if (!(key in expected) && actual[key] === null) delete actual[key];
      const imageStates = new Set([undefined, "pending", "saved"]);
      if (expected.type === "image" && expected.fileId === actual.fileId &&
          verifiedImages.has(expected.fileId) &&
          !("status" in (patches[element.id] ?? {})) &&
          imageStates.has(expected.status) && imageStates.has(actual.status))
        if ("status" in expected) actual.status = expected.status;
        else delete actual.status;
      if (!same(expected, actual, true))
        throw new Error(`unapproved element field changed: ${element.id}`);
    }
  };
  const snapshot = async (context, path) => {
    const { app, automation } = context;
    const admission = probe(context);
    exactPath(path);
    const file = getFile(app, path);
    const view = viewFor(app, path);
    const ea = automation.getAPI(view);
    try {
      methods(ea, ["setView", "getExcalidrawAPI"]);
      ea.setView(view);
      const api = ea.getExcalidrawAPI();
      methods(api, ["getSceneElementsIncludingDeleted", "getFiles"]);
      const document = await app.vault.read(file);
      const persisted = await automation.getSceneFromFile(file);
      if (!persisted?.elements) throw new Error("plugin did not reload a scene");
      const savedAssets = await persistedAssets(context, path);
      const live = clone(api.getSceneElementsIncludingDeleted());
      const files = clone(api.getFiles());
      for (const [id, asset] of Object.entries(files))
        if (!same(asset.dataURL, savedAssets.loaded[id]?.dataURL))
          throw new Error(`native saved asset differs from live asset: ${id}`);
      protectedParts(document);
      const attachments = await attachmentBindings(context, path, document);
      if (await app.vault.read(file) !== document) throw new Error("drawing changed during snapshot");
      return { path, sha256: await digest(document), document,
        persisted: clone(persisted.elements), savedAssets, attachments, live, files, ...admission };
    } finally {
      if (typeof ea.destroy === "function") ea.destroy();
    }
  };
  const assertPreimage = async (context, baseline, api) => {
    const document = await context.app.vault.read(getFile(context.app, baseline.path));
    if (document !== baseline.document || await digest(document) !== baseline.sha256)
      throw new Error("drawing preimage changed");
    if (!same(api.getSceneElementsIncludingDeleted(), baseline.live))
      throw new Error("live user edit changed since snapshot");
    if (!same(api.getFiles(), baseline.files)) throw new Error("live assets changed since snapshot");
    if (!baseline.attachments || !same(baseline.attachments,
      await attachmentBindings(context, baseline.path, document)))
      throw new Error("resolved attachment preimage changed");
  };
  const update = async (context, { baseline, expectedSha256, patches = {}, mermaid }) => {
    probe(context);
    exactPath(baseline.path);
    if (!/^[a-f0-9]{64}$/.test(expectedSha256 ?? "") || expectedSha256 !== baseline.sha256)
      throw new Error("inspected SHA-256 required");
    if (!baseline.savedAssets?.serialized || !baseline.savedAssets?.loaded)
      throw new Error("a fresh native saved-asset snapshot is required");
    if (!patches || typeof patches !== "object" || Array.isArray(patches))
      throw new Error("patches must map exact element ids to changed fields");
    const view = viewFor(context.app, baseline.path);
    const ea = context.automation.getAPI(view);
    let commitAttempted = false;
    let saveListener, saveDeadline;
    try {
      methods(context.app.vault, ["on", "offref"]);
      methods(ea, ["setView", "clear", "getExcalidrawAPI", "copyViewElementsToEAforEditing",
        "getElement", "getElements", "addElementsToView", "viewUpdateScene"]);
      methods(view, ["forceSave"]);
      ea.setView(view);
      ea.clear();
      const api = ea.getExcalidrawAPI();
      methods(api, ["getSceneElementsIncludingDeleted", "getFiles"]);
      await assertPreimage(context, baseline, api);
      const byId = new Map(baseline.live.map((element) => [element.id, element]));
      const targetIds = new Set(Object.keys(patches));
      for (const id of targetIds) {
        if (!byId.has(id)) throw new Error(`missing selected element: ${id}`);
        const patch = patches[id];
        if (!patch || typeof patch !== "object" || Array.isArray(patch) ||
            ["id", "type", "version", "versionNonce", "updated", "index"].some((key) => key in patch))
          throw new Error("patch cannot replace element identity or bookkeeping");
        for (const key of ["x", "y", "width", "height", "fontSize"])
          if (key in patch && (typeof patch[key] !== "number" || !Number.isFinite(patch[key]) ||
              ["width", "height", "fontSize"].includes(key) && patch[key] < 0))
            throw new Error("patch contains invalid geometry");
      }
      ea.copyViewElementsToEAforEditing([...targetIds].map((id) => byId.get(id)), true);
      for (const id of targetIds) Object.assign(ea.getElement(id), clone(patches[id]));
      let addedIds = [];
      if (mermaid !== undefined) {
        methods(ea, ["addMermaid"]);
        if (typeof mermaid !== "string" || !mermaid.trim()) throw new Error("Mermaid source required");
        addedIds = await ea.addMermaid(mermaid, true);
        if (!Array.isArray(addedIds) || !addedIds.length ||
            addedIds.some((id) => typeof id !== "string" || !id) ||
            new Set(addedIds).size !== addedIds.length)
          throw new Error("plugin Mermaid import failed");
        if (addedIds.some((id) => byId.has(id))) throw new Error("Mermaid id collision");
        for (const id of Object.keys(baseline.files)) if (ea.imagesDict?.[id] &&
            !same(ea.imagesDict[id].dataURL, baseline.files[id].dataURL))
          throw new Error("Mermaid asset collision");
      }
      if (!targetIds.size && !addedIds.length) throw new Error("no selected change");
      // Async preparation may have let a user edit the same drawing. Recheck both
      // disk and live preimages before the one native persistent commit.
      await assertPreimage(context, baseline, api);
      // Native addElementsToView can return before its queued file write. Subscribe
      // before triggering it, then read independently after the exact file event.
      const saved = new Promise((resolve) => {
        saveListener = context.app.vault.on("modify", (file) => {
          if (file.path === baseline.path) resolve(true);
        });
        saveDeadline = setTimeout(() => resolve(false), 30000);
      });
      commitAttempted = true;
      if (!await ea.addElementsToView(false, false, true)) throw new Error("plugin commit failed");
      // The pinned native view force-flushes scene updates when appState is
      // supplied. An empty state changes no content, but lets the native writer
      // capture the new scene rather than its preceding rendered revision.
      ea.viewUpdateScene({ appState: {} });
      await view.forceSave(true, true);
      if (!await saved) throw new Error("native file save event unavailable");
      const file = getFile(context.app, baseline.path);
      const document = await context.app.vault.read(file);
      const reloaded = await context.automation.getSceneFromFile(file);
      if (!reloaded?.elements) throw new Error("plugin readback failed after commit");
      const savedAssets = await persistedAssets(context, baseline.path);
      if (await context.app.vault.read(file) !== document)
        throw new Error("drawing changed during native readback");
      for (const [id, asset] of Object.entries(baseline.files))
        if (!same(asset, api.getFiles()[id])) throw new Error(`asset changed after commit: ${id}`);
      for (const store of ["serialized", "loaded"])
        for (const [id, asset] of Object.entries(baseline.savedAssets[store]))
          if (!same(asset, savedAssets[store][id]))
            throw new Error(`saved asset changed after commit: ${id}`);
      const attachments = await attachmentBindings(context, baseline.path, document);
      for (const [id, before] of Object.entries(baseline.attachments)) {
        const after = attachments[id];
        if (before.target && after?.target === before.target && after.sha256 === before.sha256 &&
            before.record !== after.record) {
          const oldLink = before.record.slice(2, -2);
          const newLink = after.record.slice(2, -2);
          if (oldLink.endsWith("/" + newLink)) after.record = before.record;
        }
      }
      if (!same(baseline.attachments, attachments))
        throw new Error("resolved attachment target or bytes changed after commit");
      if (await context.app.vault.read(file) !== document)
        throw new Error("drawing changed during attachment readback");
      // Status normalization is admitted only after independent image-byte checks.
      const verifiedImages = new Set(Object.keys(baseline.savedAssets.loaded).filter((id) =>
        typeof baseline.savedAssets.loaded[id]?.dataURL === "string" &&
        baseline.savedAssets.loaded[id].dataURL === savedAssets.loaded[id]?.dataURL &&
        baseline.savedAssets.loaded[id].dataURL === baseline.files[id]?.dataURL));
      assertUnchanged(baseline.live, api.getSceneElementsIncludingDeleted(), patches, addedIds, verifiedImages);
      assertUnchanged(baseline.persisted, reloaded.elements, patches, addedIds, verifiedImages);
      const selected = new Set([...targetIds].filter((id) =>
        ["text", "rawText", "originalText"].some((key) => key in patches[id])).concat(addedIds));
      const beforeParts = protectedParts(baseline.document, selected);
      const afterParts = protectedParts(document, selected);
      // File-link spelling is compared by its independently bound native target
      // and bytes; all other embedded records remain exact in attachmentBindings.
      delete beforeParts.embedded;
      delete afterParts.embedded;
      if (!same(beforeParts, afterParts))
        throw new Error("non-target Markdown or embedded-file records changed after commit");
      const persistedById = new Map(reloaded.elements.map((element) => [element.id, element]));
      for (const id of targetIds) for (const [key, value] of Object.entries(patches[id]))
        if (!same(value, persistedById.get(id)?.[key])) throw new Error(`target readback differs: ${id}.${key}`);
      if (addedIds.some((id) => !persistedById.has(id))) throw new Error("Mermaid ids missing from readback");
      return { path: baseline.path, sha256: await digest(document), targetIds: [...targetIds],
        addedIds, evidence: "plugin-persisted-readback", renderInspected: false };
    } catch (error) {
      if (!commitAttempted) throw error;
      const partial = new Error(`native commit attempted; partial effect possible: ${error.message}`);
      partial.cause = error;
      partial.partialEffect = true;
      throw partial; // No rollback or replay; preserve the actual native result.
    } finally {
      if (saveListener) context.app.vault.offref(saveListener);
      if (saveDeadline !== undefined) clearTimeout(saveDeadline);
      if (typeof ea.destroy === "function") ea.destroy();
    }
  };
  const renderPNG = async (context, { path, expectedSha256 }) => {
    probe(context);
    exactPath(path);
    const file = getFile(context.app, path);
    const document = await context.app.vault.read(file);
    if (await digest(document) !== expectedSha256) throw new Error("render preimage changed");
    const ea = context.automation.getAPI();
    try {
      methods(ea, ["clear", "createPNG"]);
      ea.clear();
      // Reload through the plugin's template/asset loader; do not render stale
      // workbench elements or copy a standalone PNG and call it plugin evidence.
      const blob = await ea.createPNG(path, 1, undefined, undefined, "light", 24);
      if (!blob || typeof blob.arrayBuffer !== "function") throw new Error("plugin PNG export failed");
      if (await context.app.vault.read(file) !== document) throw new Error("drawing changed during render");
      return blob; // Caller owns the explicit image destination and must inspect it.
    } finally {
      if (typeof ea.destroy === "function") ea.destroy();
    }
  };
  const api = { probe, snapshot, update, renderPNG };
  return api;
})();
