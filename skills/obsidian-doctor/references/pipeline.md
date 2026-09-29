# Diagnosis pipeline and failure branches

Load this reference when a plugin, plugin API, or Templater template misbehaves and you have to say why.
`SKILL.md` owns the diagnosis surface, the script contract, and the change boundary; this file owns the ordered procedure and what to do when a channel is missing, empty, or contradicts another one.

One rule sits under every branch below: **a diagnosis is only as strong as the channel it came from, and a channel nobody looked at is unknown rather than clean.**
A command that returned, an exit code of 0, and an empty error list are each compatible with the defect still being present.

The pipeline is read-only from step 1 to step 7.
Nothing in this package installs, enables, disables, reloads, resets, or writes plugin state; step 8 hands a proposed change to the person who owns the vault.

---

## 1. Scope the case before capturing anything

Answer these before touching a channel:

- **What is the observable symptom?** A rendered note that contains something wrong, a command that did nothing, a modal that opened empty, a console line. "The plugin is broken" is not a symptom.
- **Which surface is involved?** Template render, plugin command, or a call into a plugin's API from a template or script.
- **Which plugin?** By manifest `id`, not display name. If the symptom names no plugin, this package is the wrong owner — vault-wide link rot, orphan notes, frontmatter drift, and core-app behaviour are not plugin-scoped.
- **What is the requested outcome?** An explanation, or an explanation plus an authorized change. These are different jobs, and the second one needs the first anyway.

A symptom is not authorization. Diagnosing a template does not grant permission to edit it.

**Handoff:** one plugin id, one symptom stated as an observable, one named surface.

---

## 2. Capture evidence, read-only

Each channel proves a different thing. Capture what the symptom needs and record which channels you did not get.

| Channel | Where it comes from | Proves | Does not prove |
|---|---|---|---|
| Runtime availability | the app answering at all; the command catalog it reports | whether live probing is possible | anything about the plugin |
| Plugin availability | the plugin directory existing under the vault's configuration folder, and the plugin being enabled | that the symptom can be plugin-caused at all | that the plugin works |
| Manifest | `<config-folder>/plugins/<plugin-id>/manifest.json` | the exact installed `id`, `version`, `minAppVersion` | compatibility on its own |
| App version | the app's own About pane | the exact running app version | which plugin build is loaded |
| Template source | the template note, read verbatim | what the template asks the plugin to do | what happened at render time |
| Rendered output | the produced note, read back from its exact path | what actually reached the vault | why it got there |
| Console errors | the app's developer-tools console | the error text the runtime raised | that an empty capture means no error |

Four rules for this step:

1. **Confirm the configuration folder name before looking for the plugin directory.** `.obsidian` is the default, and a vault can be configured to use another name. A missing directory under the wrong folder name is not an uninstalled plugin.
2. **Read; do not evaluate.** A probe that assigns, saves settings, reloads, enables, or resets is a mutation wearing a diagnosis label. Read-only expressions and read commands only.
3. **Name only probes you have confirmed.** The script reports the read-only probe forms this package is willing to name in `read_only_probes`. Anything outside that list: confirm it against the installed build's own command catalog before relying on it, and report a capability gap rather than substituting a filesystem write for a missing command.
4. **Sanitize before the bundle moves.** Replace absolute paths, home-directory references, machine paths, account identifiers, and anything credential-shaped with vault-relative paths or placeholders. Never attach a raw console dump. The script's `fixture-not-sanitized` check reports offenders by location and never echoes the value, but it runs after the fact — sanitize at capture.

**Handoff:** a sanitized evidence bundle, plus an explicit list of channels that were not captured.

---

## 3. Fix the version facts exactly

Version evidence is the one place where a plausible guess does the most damage, because every later compatibility claim inherits it.

- Read the plugin version from the installed `manifest.json` as an exact string. Do not read it from a changelog, a release page, a settings screen, or a previous case.
- Read the app version from the app's own About pane as an exact string. Do not infer it from a plugin, from a feature you saw working, or from the current date.
- `minAppVersion` in the manifest is the plugin's declared minimum app version. An app older than that value is a confirmed incompatibility; an app newer than it is not a compatibility guarantee.
- Compare plain dotted numeric versions only. A version string carrying a pre-release suffix, a build tag, or a range is not comparable — it stays unknown, and so does the compatibility claim built on it. The script behaves this way on purpose: it reports `unknown` rather than parsing a shape it cannot compare.
- Look the installed version up in [plugins.yaml](plugins.yaml) under `known_versions`. **A version with no entry is untested, not working.** So is a version whose entry carries `evidence: reported` — that is a lead, not a reproduction.
- Scope every behavioural claim to the exact pair of versions it was observed on. Behaviour on one build is not evidence about another.

**Handoff:** exact app version, exact plugin version, exact `minAppVersion`, and the registry verdict for that version.

---

## 4. Classify, then read the findings honestly

Run the classifier over the sanitized bundle (invocation and fixture schema: `SKILL.md`). It reports one finding per check, and the four statuses mean different things:

- **confirmed** — the evidence supports that failure mode. It does not mean it is the only cause.
- **ruled_out** — evidence for that channel was present and contradicts the failure mode.
- **unknown** — the channel exists but the signal needed to decide is missing. The case is not closed while one remains.
- **not_applicable** — that channel was never supplied, so the check had nothing to evaluate. This is not a pass.

Read the exit code as **evidence sufficiency, not health**: a run that confirms three defects from complete evidence exits 0, and a run that finds nothing wrong but is missing a channel exits 1.

Two ways to misread a result, both common:

- Treating a `confirmed` finding as the whole explanation. Several checks confirm at once when a template has several defects; fixing one leaves the rest.
- Treating `not_applicable` or an empty console capture as a clean bill of health. That is a gap in the evidence, and it belongs in the report as one.

**Handoff:** the finding set, plus the unknown list copied into the report verbatim.

---

## 5. Templater command branches

### 5a. Unbound identifier (`templater-reference-error`)

**Signal.** `ReferenceError: <identifier> is not defined` in the console, and/or the interpolation command surviving into the rendered note as literal text because the render aborted at that point.

**Check.** An interpolation command is evaluated as a JavaScript expression in Templater's scope. The identifier needs a binding in the template, or it must be one of the identifiers that resolve there without one (`api_surface.resolves_without_binding` in the registry). Anything else throws.

**Recovery.** Bind the identifier inside an execution block and emit it through `tR`, or read it back with an interpolation command placed after the binding. Neutral example:

```text
<%*
const answer = await tp.system.prompt("Section label");
if (!answer) { return; }
tR += `## ${answer}\n`;
%>
```

**Confirm.** The console line captured before the edit, plus a re-render whose output contains the resolved value and no literal command text. A render that raised no error is not enough — see 5c.

### 5b. Asynchronous call without `await` (`templater-missing-await`)

**Signal.** `[object Promise]` in the rendered note, an empty slot where a value was expected, or a file operation that lands after the surrounding text.

**Check.** Compare each call site against `api_surface.await_required` in the registry. Every call in that list is documented as asynchronous, so without `await` the template interpolates the pending Promise instead of the value — and for a mutating call, the side effect races the rest of the render.

**Recovery.** Add `await` at each such call site, inside an execution block.

**Confirm.** Re-render, then read the output back from its exact path and look for the resolved value. A clean exit code proves nothing here.

### 5c. Computed value never emitted (`templater-missing-output`)

**Signal.** The value the user was prompted for never appears in the note, and nothing errored. This branch is the reason "no console errors" is not a pass criterion.

**Check.** An execution block emits nothing by itself. A binding computed there reaches the note only through `tR` or an interpolation command that reads it back. A binding that is never mentioned again after its declaration reaches neither — the prompt answer is collected and discarded.

A related signal: a rendered note that still contains a literal `<%` command. That means command text reached the note instead of a value, so either the template was never processed by Templater or the render aborted partway.

**Recovery.** Append the value to `tR`, or read it back with an interpolation command.

**Confirm.** Read the rendered note back from its exact path and find the value in it.

---

## 6. Prompt cancellation and a half-applied vault change

This is the branch where a diagnosis mistake costs the user data, so it gets the strictest procedure.

**Signal.** The user cancelled a modal, and afterwards the note is renamed or moved but holds unrendered body text — or it sits at its original path with the template partly applied.

**Check.** Two conditions, both read off the template source:

1. **Ordering.** Does any call from `api_surface.vault_mutating` run before an interactive modal? Templater has no rollback, so a mutation that already landed stays landed when the later modal is cancelled.
2. **Guarding.** Does an interactive modal run before a mutation without a guard? `throw_on_cancel` defaults to false on `tp.system.prompt`, `tp.system.suggester`, and `tp.system.multi_suggester`, so a cancelled modal resolves to null rather than raising. Without a `return` or `throw` between the modal and the mutation, that null flows into the vault change.

**Recovery in the template.** Collect and validate every answer first, return early on a null answer (or pass `throw_on_cancel` as true), and mutate only after every value is validated. Neutral example:

```text
<%*
const label = await tp.system.prompt("Note title");
if (!label) { return; }
const safeLabel = label.replace(/[\\/:*?"<>|]/g, "").trim();
if (!safeLabel) { return; }
await tp.file.rename(safeLabel);
tR += `# ${safeLabel}\n`;
%>
```

**Recovery in the vault — the part that must not be improvised.** After a cancelled run, establish what actually happened before proposing anything:

1. Read the note back by its expected new path.
2. Read it back by its previous path.
3. Record which one resolves. A rename that already landed leaves the note under the new name with unrendered body text; a move whose target folder does not exist leaves it under the old path.

Then classify: nothing applied, fully applied, or partially applied. Only the missing delta is in scope, and applying it is a separate authorized note edit.

Never repair a half-applied render by rewriting the whole note, by re-running the template over the same target, or by deleting and recreating the note.
Each of those discards content that was never part of the requested change, including edits made between the capture and the repair.
If the delta cannot be applied without a whole-body rewrite, stop and report: a whole-body rewrite is a separate authorization.

**Confirm.** Both paths read back, and the untouched regions of the note compared against the pre-change capture.

---

## 7. Unavailable plugin API

**Signal.** `TypeError: ... is not a function`, or `TypeError: Cannot read properties of undefined`, raised from a call into a plugin's API.

**Check.** Probe the symbol with a read-only expression at the installed version, and compare it against the API the plugin's own published documentation describes for that version (`api_surface` and `docs` in the registry). An undocumented internal that happens to exist is not a contract — it can disappear in a patch release without that being a regression.

**Recovery.** Rewrite the call site against the API the installed version documents, or have the vault owner install a version that documents the expected symbol. Both are the owner's decision.

**Never** repair a missing symbol by assigning into plugin internals, by monkey-patching the plugin at runtime, or by editing the plugin's shipped build output. That produces a vault whose behaviour no publisher can support and no later diagnosis can explain.

**Confirm.** The read-only probe result, plus the exact version string the probe ran against. Scope the finding to that version.

---

## 8. Unknown stays unknown

A console line that matches none of the signatures this package records is reported as unclassified and stays `unknown`.

What to do with it:

1. Keep the line verbatim with the case record, sanitized but not paraphrased.
2. Look it up under `failure_signatures` for that plugin in [plugins.yaml](plugins.yaml), then in the plugin's own published issue tracker or release notes recorded there.
3. Report it as unknown, with the plugin and app versions it was seen on.
4. If you later reproduce a cause for it, append a signature to the registry with the evidence value that matches how you learned it.

What never happens:

- **No nearest-neighbour classification.** An unfamiliar message is not assigned to the closest familiar class because the shapes rhyme.
- **No clearing by state change.** Reloading, disabling, re-enabling, reinstalling, or resetting to defaults to make a line disappear destroys the evidence without explaining the failure — and quietly changes the vault while claiming to diagnose it.
- **No confident hedging.** "Probably a version issue" reads as a finding and carries none of a finding's evidence. Say unknown.
- **No closing the case.** An unresolved unknown means the diagnosis is incomplete, and the report says so.

The same discipline applies to an evidence channel supplied in a shape the classifier cannot read: that is a gap to re-capture, not an empty result.

---

## 9. The change boundary

Everything above produces findings and proposed changes. Changes are applied by the person who owns the vault, after review.

**Proposable.** A concrete edit to a template or a script the task is authorized to touch; a specific version change for the owner to perform; a specific settings change for the owner to make through the plugin's own settings interface.

**Never, by this package.** Every item under `registry_contract.forbidden_recoveries` in [plugins.yaml](plugins.yaml), namely:

- hand-editing a plugin's `data.json`
- editing a plugin's `main.js` or any shipped build output
- assigning into plugin internals from an eval or console expression
- calling a plugin's own save-settings routine to persist an injected value
- resetting settings to defaults, reinstalling, or deleting plugin data to "start clean"
- enabling, disabling, or reloading a plugin as a diagnosis step rather than as an approved change
- rewriting a whole note or template to deliver a one-line fix

A blanket reset is the worst of these, because it looks like a fix: it destroys the configuration the user built, destroys the evidence that would have explained the failure, and cannot be undone from a diagnosis report.

Recovery, when one is needed, restores the exact prior content of the affected region and nothing else.
If you do not hold a capture of the content you would have to restore, say so and stop rather than reconstructing it.

---

## 10. Record the outcome

Append what was learned to [plugins.yaml](plugins.yaml), field by field. The registry is the durable record; no separate host- or vault-specific log is written.

Append protocol:

- Add a new plugin as a new key under `plugins`, carrying all of `name`, `repo`, `docs`, `api_surface`, `known_versions`, `failure_signatures` — empty `{}` or `[]` is legal, a missing key is not.
- Append to `known_versions` and `failure_signatures`; never blank a list and never replace a plugin key wholesale.
- Give every appended fact an `evidence` value from `evidence_vocabulary`, and record `observed` only with the exact app and plugin versions it was reproduced on.
- Keep note paths, vault names, account identifiers, machine paths, and raw console dumps out of the file. Cite plugin behaviour.
- Re-parse the file after editing it. A registry that no longer parses has lost every entry it holds, not just the new one.

The report to the user names:

- the plugin id, the exact plugin version, and the exact app version, with the channel each came from;
- which channels were captured and which were not;
- each confirmed finding with the evidence it rests on;
- every unknown, stated as unknown;
- the proposed change, who has to apply it, and what readback will confirm it;
- anything that remains unverified or blocked, and why.

---

## Verification

- [ ] The case named one plugin by manifest `id` and one symptom stated as an observable.
- [ ] Every channel was captured read-only; no probe assigned, saved, reloaded, enabled, or reset anything.
- [ ] The evidence bundle was sanitized before it left the host, and no raw console dump was attached.
- [ ] The app version, plugin version, and `minAppVersion` are exact strings, each with the channel it was read from.
- [ ] An unrecorded or `reported` registry version was treated as untested, not as working.
- [ ] `not_applicable` findings and empty captures were reported as evidence gaps, not as passes.
- [ ] After a cancelled render, both the expected and the previous path were read back before anything was proposed.
- [ ] No unfamiliar console line was mapped to the nearest familiar class, and none was cleared by a state change.
- [ ] No forbidden recovery was proposed: no `data.json` edit, no build-output edit, no internal assignment, no reset, reinstall, or blanket rewrite.
- [ ] Registry appends were field-level, carried an evidence value, and the file still parses.
