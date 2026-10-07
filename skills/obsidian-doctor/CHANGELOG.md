# Changelog

## 0.2.1 — 2026-10-07

- 2026-10-07 — Collection release `0.2.1`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — Unreleased

- Plugin and Templater failures were being "fixed" by changing state until the symptom disappeared — reloading, re-enabling, resetting settings, reinstalling, rewriting the whole template — which destroys both the user's configuration and the evidence that would have explained the failure → this package makes diagnosis read-only and separates it from repair: [`SKILL.md`](SKILL.md) fixes the evidence channels and what each one does and does not prove, makes app and plugin versions exact-string facts or unknown, and states a change boundary in which findings and proposals come from here and every application belongs to the vault owner.
- The failure family had no owner and no shared vocabulary, so an unfamiliar console line got filed under whichever cause was nearest → ten named checks now each decide one question and report `confirmed`, `ruled_out`, `unknown`, or `not_applicable`, and `console-error-unclassified` exists specifically so a line matching no recorded signature keeps the run indeterminate and the case open instead of being rounded up.
- "It returned, so it worked" was the dominant reporting error → the classifier's exit code reports **evidence sufficiency, not health** (0 determinate, 1 at least one unknown, 2 usage, 3 unreadable fixture), its output always carries `"mutations_performed": []`, and a run that confirms three defects from complete evidence exits 0 on purpose.
- A cancelled prompt could leave a note renamed or moved with unrendered body text, and the obvious repair — re-run the template, or rewrite the note — silently discards content nobody asked to change → [`references/pipeline.md`](references/pipeline.md) adds the ordering rule (no vault mutation before an interactive modal), the guarding rule (`throw_on_cancel` defaults to false, so a cancelled modal resolves to null), a two-path readback that establishes what actually landed, and a recovery limit: only the missing delta, never a whole-note rewrite, never delete-and-recreate.
- Plugin knowledge was re-derived on every occurrence and then lost → [`references/plugins.yaml`](references/plugins.yaml) is an append-only registry keyed by manifest `id`, carrying `api_surface`, `known_versions`, and `failure_signatures`, in which an unlisted plugin and an unrecorded version are both *untested* rather than healthy, and every recorded fact must declare how it was learned (`documented`, `reported`, `observed`).
- [`scripts/diagnose.py`](scripts/diagnose.py) was carried forward and finished rather than replaced. Retained as found: the two-mode CLI (`--fixture PATH` | `--list-checks`), the four-status model, the 0/1/2/3 exit contract, the `obsidian-doctor/evidence@1` → `obsidian-doctor/diagnosis@1` envelope, the Templater source analysis (command scanning, balanced argument splitting, unbound-identifier detection, discarded-binding detection, cancellation-exposure ordering), the numeric-only version comparison that stays unknown rather than guessing at a pre-release string, and the sanitization layer that reports a host-specific or secret-looking value by JSON pointer and never echoes it. Added in this change: `console-error-unclassified`, which classifies the console channel itself — an unreadable channel shape and an unreadable line are reported as evidence gaps, unmatched lines are quoted up to five and then counted, and an empty capture is recorded as bounding what was observed rather than as a clean runtime.

### Grounded facts and sources

Templater surface facts, from the publisher's documentation (the same URLs the findings cite and the registry lists under `api_surface.docs_read`):

- Interpolation `<% … %>` is evaluated as a JavaScript expression, so an identifier with no binding throws — <https://silentvoid13.github.io/Templater/syntax.html>
- An execution block `<%* … %>` emits nothing by itself; a value reaches the note only through `tR` or an interpolation command. `app` and `moment` resolve inside a command without being declared — <https://silentvoid13.github.io/Templater/commands/execution-command.html>
- `tp.system.prompt`, `tp.system.suggester`, and `tp.system.multi_suggester` are documented with `await`, open a modal, and default `throw_on_cancel` to false, so a cancelled modal resolves to null instead of raising — <https://silentvoid13.github.io/Templater/internal-functions/internal-modules/system-module.html>
- `tp.file.create_new`, `tp.file.exists`, `tp.file.include`, `tp.file.move`, and `tp.file.rename` are documented with `await`; `rename`, `move`, and `create_new` change the vault as a side effect of rendering, and Templater offers no rollback — <https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html>

Obsidian facts:

- `minAppVersion` in `manifest.json` is the plugin's declared minimum app version — <https://docs.obsidian.md/Reference/Manifest>
- Plugin anatomy and the API a plugin exposes — <https://docs.obsidian.md/Plugins/Getting+started/Anatomy+of+a+plugin>
- Community plugin install/enable state is vault configuration — <https://help.obsidian.md/community-plugins>
- The configuration folder name is configurable, so `.obsidian` is a default and not an invariant — <https://help.obsidian.md/configuration-folder>
- Where vault and plugin data live, which is why fixtures are sanitized before they move — <https://help.obsidian.md/data-storage>

Authoring-time exercise of the classifier, in this environment, on synthetic fixtures only:

- `--list-checks` returns ten checks and the exit-code contract; exit 0.
- A fixture exercising every Templater branch produced `confirmed` on `plugin-version-mismatch`, `templater-reference-error`, `templater-missing-await`, `templater-missing-output`, `templater-partial-mutation-risk`, and `plugin-api-unavailable`, `unknown` on `console-error-unclassified`, and exit 1.
- The console channel was exercised empty, all-signatures-matched, supplied as a non-list, and holding an entry with no readable message — `ruled_out`, `ruled_out`, `unknown`, `unknown` respectively.
- A fixture carrying an absolute user path and a secret-looking key produced `confirmed` on `fixture-not-sanitized`, reported both by JSON pointer, and echoed neither value anywhere in the output, including `subject.template_path`.
- Missing fixture → exit 3 with an `input_error` envelope on stdout; no mode and both modes → exit 2 with the argparse message on stderr and no JSON.
- The registry's `await_required`, `interactive` (with `throw_on_cancel` argument indices), `vault_mutating`, and `resolves_without_binding` entries were compared against the script's own constants and match exactly; every `check` named in a `failure_signatures` entry resolves to a real check id; the file parses.

No Obsidian installation, vault, plugin, or `obsidian` executable was available while this package was authored. Nothing here was run against a live app, no plugin version was observed first-hand, and no `verified_against` entry is recorded.

### Provenance

- Source-informed by `skills/obsidian/references/doctor.md`, `doctor-pipeline.md`, and `doctor-plugins.yaml` in the craft-skills tree at revision `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, opened read-only as requirement evidence for which failures this package must explain. That tree ships no root license, so nothing from it was carried forward as text.
- No prose, table, checklist, command block, or example was copied. Every rule here was re-derived from the publisher documentation cited above, every example is newly authored and neutral, and the registry schema was reauthored: this package's per-plugin keys are `api_surface`, `known_versions`, and `failure_signatures`, with a required `evidence` value on each recorded fact, in place of the source's untyped pattern and regression lists.
- Two behavioural leads were carried forward as claims rather than facts, both marked `evidence: reported` with their recovery flagged for reproduction before use: the Templater `2.19.3` / `minAppVersion 1.5.0` manifest pair, and a `2.19.1` suggester rendering an empty list.
- Three recoveries the source recommended are deliberately inverted here, and the inversion is the substance of this package rather than an omission: writing plugin settings through an eval expression plus the plugin's own save-settings routine, reloading a plugin as a pipeline step, and handling `data.json` as a repair surface are all listed under `registry_contract.forbidden_recoveries` and refused. The source's own "never hand-edit `data.json`" rule is kept and extended, because routing the same write through an eval expression is the same write.
- `scripts/diagnose.py` was already present in this package and is original work; it was read in full and extended, not regenerated.
- All files in this package are original work covered by the repository's MIT `LICENSE`.

### Limitations

- Evidence level: documentation plus synthetic fixtures. No finding in this package has been reproduced against a running Obsidian app, and no registry entry is `observed`.
- The classifier consumes a fixture that a human captures and sanitizes. It cannot discover evidence, cannot confirm that a supplied value was read from the channel it claims, and cannot detect a channel that was captured from the wrong vault.
- Templater analysis is textual, not an evaluation. It reads command boundaries, call sites, `await`, argument positions, and binding usage; it does not execute the template, so a value computed through indirection, dynamic member access, or a helper module can read as unbound or as discarded when it is neither, and the reverse is possible too. Treat a static finding as a lead confirmed by render readback.
- Version comparison handles plain dotted numeric strings only. Pre-release suffixes, build tags, and ranges stay `unknown` rather than being coerced into an ordering.
- Console classification recognises exactly three signatures (`ReferenceError: … is not defined`, `TypeError: … is not a function`, `TypeError: Cannot read properties of undefined/null`). Everything else is unclassified by design, which is the intended behaviour and also a permanent coverage limit: the registry has to grow for that set to widen.
- Sanitization is pattern-based. It catches home-directory, per-user, temp, and `file://` paths, URL-embedded credentials, and secret-looking key names. It is a safety net, not a guarantee — a host-specific value in an unanticipated shape can still pass, so sanitize at capture.
- The seed registry holds two plugins, one of them with no recorded behaviour at all. That is the honest state of the knowledge, not a gap to be filled with plausible entries.

### Registry retention restoration — Unreleased

- Corrected only the `references/plugins.yaml` header: retired or renamed APIs retain their version-scoped evidence, and retirement is appended rather than deleting historical entries. Whole-document parsed data and all bytes from `schema:` onward are unchanged.
- Requirement lineage: public `Xia-Ataraxia/craft-skills@836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, append-only plugin evidence retention, re-expressed without copying source prose or corpus examples. Existing rights and MIT notices remain unchanged; no new source grant is claimed.
- Independent whole-registry YAML equality and direct header review confirmed retention without schema, key, entry or classifier changes. The seed still has zero observed entries; no plugin/app version or live reproduction is newly asserted. Version remains `0.1.0`; no new test or unchanged-suite rerun accompanies this prose record.
