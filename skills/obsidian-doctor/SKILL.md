---
name: obsidian-doctor
description: Diagnoses Obsidian community-plugin and Templater failures from captured read-only evidence — unbound identifiers and `ReferenceError`, async calls used without `await`, execution blocks whose value never reaches the note, cancelled prompts leaving a half-applied rename or move, plugin API symbols missing at the installed version, and plugin/app version incompatibility — classifying each as confirmed, ruled out, or unknown against a plugin registry. Use when a template renders a literal `<% ... %>` command or `[object Promise]`, a prompt answer disappears, a plugin command throws or does nothing, a cancelled run leaves a note renamed, or the user asks whether the installed plugin version has a known failure. Not for link rot, orphan notes, or frontmatter drift, not for core-app defects, and not for writing, reloading, reinstalling, or resetting plugin state — this package proposes changes and never applies them.
license: MIT
metadata:
  version: "0.2.2"
---

# Obsidian Doctor

Explain why a community plugin or a Templater template failed, from evidence, without changing anything to find out.

Success is a diagnosis whose every claim names the channel it came from, whose unknowns are still labelled unknown, and whose proposed fix the vault owner can review before it touches a vault. Success is **not** a plugin that starts working because state was reset until the symptom disappeared.

Three properties hold throughout:

- **Read-only.** No install, enable, disable, reload, reset, settings write, or plugin-data edit happens here. Changes are proposed; the owner applies them.
- **Channel-bound.** A command that returned, an exit code of 0, and an empty error list are each compatible with the defect still being present. Every finding names its evidence.
- **Unknown-preserving.** An error this package cannot classify stays unclassified. It is never rounded up to the nearest familiar cause and never cleared by a state change.

## Scope

**Owns:** plugin availability and version compatibility, Obsidian plugin API availability at an installed version, and the Templater failure family — unbound identifiers, missing `await`, unemitted execution-block values, and prompt cancellation leaving a half-applied vault change. Also owns the evidence contract, the classifier, and the plugin registry.

**Does not own:** vault-wide link rot, orphan notes, frontmatter schema drift, core-app behaviour unrelated to a plugin, Markdown or note-format questions, and write authorization of any kind. A diagnosis is not permission to edit the template it diagnosed.

## Evidence channels

Capture read-only, and record which channels you did not get. Each proves something different:

| Channel | Source | Proves |
|---|---|---|
| Runtime availability | the app answering, and the command catalog it reports | whether live probing is possible at all |
| Plugin availability | the plugin directory under the vault's configuration folder, and whether the plugin is enabled | whether the symptom can be plugin-caused |
| Manifest | `<config-folder>/plugins/<plugin-id>/manifest.json` | the exact installed `id`, `version`, `minAppVersion` |
| App version | the app's own About pane | the exact running app version |
| Template source | the template note, read verbatim | what the template asks the plugin to do |
| Rendered output | the produced note, read back from its exact path | what actually reached the vault |
| Console errors | the app's developer-tools console | the error text the runtime raised |

Confirm the vault's real configuration folder name before looking for a plugin directory — `.obsidian` is only the default, and a missing directory under the wrong folder name is not an uninstalled plugin.

These read-only probe forms are the ones this package is willing to name, and the classifier echoes them back in `read_only_probes`:

```bash
obsidian help
obsidian dev:errors
obsidian dev:console level=error
obsidian read path=<vault-relative-path>
```

Anything outside that list: confirm it against the installed build's own command catalog before relying on it. If the app, the bridge, or a needed command is unavailable, report the capability gap — never substitute a filesystem write for a missing command, and never describe an intended result as an observed one.

Sanitize before evidence leaves the host: vault-relative paths or placeholders instead of absolute paths, home-directory references, machine paths, and account identifiers; no credential-shaped values; no raw console dumps.

Details and per-channel failure handling: [references/pipeline.md](references/pipeline.md).

## Version evidence

Compatibility claims inherit whatever the version facts got wrong, so these are exact-string facts or they are unknown:

- Plugin version and `minAppVersion` come from the installed `manifest.json` — not a changelog, a release page, or a previous case.
- App version comes from the app's About pane — never inferred from a plugin, a working feature, or the date.
- An app older than `minAppVersion` is a confirmed incompatibility. An app newer than it is **not** a compatibility guarantee.
- Only plain dotted numeric versions are compared. A pre-release suffix, build tag, or range is not comparable, so the compatibility claim built on it stays unknown.
- A version with no [registry](references/plugins.yaml) entry is **untested, not working**. So is one whose entry is `evidence: reported`.
- Scope every behavioural claim to the exact app-and-plugin version pair it was observed on.

## Classifier

`scripts/diagnose.py` classifies one sanitized evidence bundle. It is stdlib-only, Python 3.9+, and reads exactly one file: the fixture path you pass. It never discovers a vault, opens a configuration folder, or touches plugin state, and its output always carries `"mutations_performed": []`.

### Command line

```bash
python3 scripts/diagnose.py --fixture PATH   # classify one evidence bundle
python3 scripts/diagnose.py --list-checks    # print the check catalog and exit-code contract
python3 scripts/diagnose.py --help           # argparse usage
```

`--fixture` and `--list-checks` are mutually exclusive, and exactly one is required. There are no other options and no environment variables.

Exit codes report **evidence sufficiency, not health**:

| Exit | Status | Meaning |
|---|---|---|
| `0` | `ok` | every check reached a determinate state — including a run that confirmed defects |
| `1` | `indeterminate` | at least one check stayed `unknown` for lack of data |
| `2` | — | invalid command line; argparse message on stderr, no JSON |
| `3` | `input_error` | fixture missing, unreadable, not JSON, or not an evidence bundle; the JSON envelope is still printed on stdout |

Read `findings[].status` to learn what was wrong. A run that confirms three defects from complete evidence exits 0; a run that finds nothing wrong but is missing a channel exits 1.

### Fixture schema

One JSON object, `schema` exactly `obsidian-doctor/evidence@1`. Every other field is optional — an omitted channel makes its checks `not_applicable`, which is an evidence gap, not a pass.

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | required, exactly `obsidian-doctor/evidence@1` |
| `case_id` | string | free-form case label, echoed into `subject` |
| `runtime.app_running` | boolean | whether the app was observed running |
| `runtime.cli_available` | boolean | whether the `obsidian` executable was observed available |
| `runtime.app_version` | string | exact app version read from the About pane |
| `runtime.cli_commands_confirmed` | array of strings | command names confirmed present in the installed build |
| `plugin.id` | string | manifest `id`, not the display name |
| `plugin.installed` | boolean | whether the plugin directory was found |
| `plugin.enabled` | boolean | whether the plugin is enabled |
| `plugin.manifest.id` | string | `id` as read from `manifest.json` |
| `plugin.manifest.version` | string | exact installed plugin version |
| `plugin.manifest.minAppVersion` | string | declared minimum app version |
| `plugin.api_probe.symbol` | string | the symbol a read-only probe looked for |
| `plugin.api_probe.observed` | string | `present` or `missing`; any other value stays `unknown` |
| `template.path` | string | vault-relative path of the template |
| `template.source` | string | the template body, verbatim |
| `rendered_output.content` | string | the produced note body, read back from its exact path |
| `console_errors` | array | strings, or objects with a string `message` |

Neutral example:

```json
{
  "schema": "obsidian-doctor/evidence@1",
  "case_id": "meeting-template-001",
  "runtime": {
    "app_running": true,
    "cli_available": true,
    "app_version": "1.6.0",
    "cli_commands_confirmed": ["help", "read", "dev:errors"]
  },
  "plugin": {
    "id": "templater-obsidian",
    "installed": true,
    "enabled": true,
    "manifest": {"id": "templater-obsidian", "version": "2.19.3", "minAppVersion": "1.5.0"}
  },
  "template": {"path": "Templates/Meeting.md", "source": "# <% meetingTitle %>\n"},
  "console_errors": ["ReferenceError: meetingTitle is not defined"]
}
```

### Output envelope

One JSON object on stdout, `schema` `obsidian-doctor/diagnosis@1`:

| Field | Meaning |
|---|---|
| `status` | `ok`, `indeterminate`, or `input_error` |
| `fixture` | the fixture path, or the redaction marker if that path names a host |
| `evidence_schema` | the `schema` value the fixture declared |
| `subject` | `case_id`, `plugin_id`, `plugin_version`, `min_app_version`, `app_version`, `template_path` |
| `findings` | one object per check, in catalog order |
| `unknowns` | `"<check-id>: <summary>"` for every check that stayed `unknown` |
| `mutations_performed` | always `[]` |
| `read_only_probes` | the probe forms named above |

On `input_error` the envelope carries `reason` instead of `subject`, with `findings` and `unknowns` empty.

Each finding carries `id`, `title`, `status`, `summary`, `evidence[]`, `next_actions[]`, `docs[]`, and — where a registry entry applies — `registry_lookup` as `{file, plugin_id, keys}`, which resolves as `plugins["<plugin_id>"].<key>` in [references/plugins.yaml](references/plugins.yaml).

Statuses: `confirmed` (evidence supports it), `ruled_out` (evidence was present and contradicts it), `unknown` (the channel exists, the deciding signal is missing), `not_applicable` (the channel was never supplied).

Next-action kinds, each carrying an explicit `mutates` field:

| `kind` | `mutates` | Meaning |
|---|---|---|
| `observe` | `no` | read, capture, or record something |
| `consult` | `no` | look a fact up in the registry or published documentation |
| `propose-change` | `yes-after-human-approval` | a source or setting change a human must review, approve, and apply |

Evidence strings are whitespace-collapsed and capped at 300 characters. A fixture value that names a host is replaced by the redaction marker rather than echoed, and a secret-looking key is reported by JSON pointer with its value withheld.

Running the example above:

```console
$ python3 scripts/diagnose.py --fixture meeting-template-001.json
{
  "schema": "obsidian-doctor/diagnosis@1",
  "status": "ok",
  ...
  "findings": [
    ...
    {
      "id": "templater-reference-error",
      "title": "Templater command references an unbound identifier",
      "status": "confirmed",
      "summary": "Templater evaluates a `<% ... %>` command as a JavaScript expression, so an identifier with no binding throws and aborts the render. Unbound: meetingTitle.",
      "evidence": [
        "console: ReferenceError: meetingTitle is not defined",
        "`<% meetingTitle %>` has no const/let/var/function binding in the template and is not a documented Templater or JavaScript global"
      ],
      ...
      "registry_lookup": {
        "file": "references/plugins.yaml",
        "plugin_id": "templater-obsidian",
        "keys": ["failure_signatures"]
      }
    }
  ],
  "unknowns": [],
  "mutations_performed": []
}
$ echo $?
0
```

Exit 0 with a confirmed defect is the contract working as specified: the evidence was complete enough to decide.

### Checks

`--list-checks` prints this catalog as `obsidian-doctor/checks@1`, with `statuses`, `exit_codes`, and each check's `evidence_required`.

| Check id | Decides | Evidence required |
|---|---|---|
| `runtime-unavailable` | whether live diagnosis is possible at all | `runtime.app_running`, `runtime.cli_available`, `runtime.cli_commands_confirmed` |
| `plugin-unavailable` | whether the plugin is installed and enabled | `plugin.id`, `plugin.installed`, `plugin.enabled` |
| `plugin-version-mismatch` | whether the running app satisfies the manifest's `minAppVersion` | `runtime.app_version`, `plugin.manifest.minAppVersion`, `plugin.manifest.version` |
| `templater-reference-error` | whether a command references an identifier with no binding | `template.source`, `console_errors` |
| `templater-missing-await` | whether a documented asynchronous call is used without `await` | `template.source` |
| `templater-missing-output` | whether an execution block computes a value it never emits | `template.source`, `rendered_output.content` |
| `templater-partial-mutation-risk` | whether a cancelled prompt can leave a half-applied rename or move | `template.source` |
| `plugin-api-unavailable` | whether a call site expects a symbol the installed build does not expose | `plugin.api_probe`, `console_errors` |
| `console-error-unclassified` | whether the capture holds a line matching no recorded signature | `console_errors` |
| `fixture-not-sanitized` | whether the bundle still carries host-specific or secret-looking values | the whole bundle |

`console-error-unclassified` is where unknown stays unknown. A line that matches none of the recorded signatures keeps the run `indeterminate` and the case open; the finding quotes up to five such lines, counts the rest, and asks for a registry lookup — never for a reload, a reinstall, or a reset to make the line go away.

## Registry

[references/plugins.yaml](references/plugins.yaml) is the durable record, keyed by manifest `id` under `plugins`, with `name`, `repo`, `docs`, `api_surface`, `known_versions`, and `failure_signatures` per entry. The classifier never reads or writes it; it emits a `registry_lookup` pointer and a human resolves it.

- Empty `{}` or `[]` means nothing is recorded yet — never that there is nothing to find.
- An unlisted plugin and an unrecorded version are both **untested**, not healthy.
- Every recorded fact carries an `evidence` value: `documented` (read from a publisher page), `reported` (a third-party claim, not reproduced), `observed` (reproduced first-hand against named app and plugin versions). No entry in the shipped seed is `observed`.
- Appends are field-level and append-only; never blank a list, replace a plugin key wholesale, or regenerate the file. Re-parse it after every edit.
- No note paths, vault names, account identifiers, machine paths, or raw console dumps. Cite plugin behaviour.

Append protocol: [pipeline.md § 10](references/pipeline.md#10-record-the-outcome).

## Change boundary

Findings and proposed changes come from this package; changes are applied by whoever owns the vault, after review.

**Proposable:** a concrete edit to a template or script the task is authorized to touch; a specific version change for the owner to perform; a specific settings change the owner makes through the plugin's own settings interface.

**Never, by this package:**

- hand-editing a plugin's `data.json`
- editing a plugin's `main.js` or any shipped build output
- assigning into plugin internals from an eval or console expression
- calling a plugin's own save-settings routine to persist an injected value
- resetting settings to defaults, reinstalling, or deleting plugin data to "start clean"
- enabling, disabling, or reloading a plugin as a diagnosis step rather than as an approved change
- rewriting a whole note or template to deliver a one-line fix

A blanket reset is the worst of these because it looks like a fix: it destroys the configuration the user built and the evidence that would have explained the failure, and a diagnosis report cannot undo it.

After a cancelled or failed render, read the note back by its expected path **and** by its previous path before proposing anything, then apply only the missing delta. Never repair a half-applied render by rewriting the whole note, re-running the template over the same target, or deleting and recreating the note. Recovery restores the exact prior content of the affected region and nothing else; without a capture of that content, stop and report.

## Composition and boundaries

This package works standalone. It owns the evidence contract, the classifier, the check catalog, and the registry, and it depends on no other package to produce a diagnosis.

Compose a neighbouring package by explicit identity only when the request needs it — a CLI package to run the read-only probes against a live app, a Markdown or format package for note-content questions, a vault-policy package for filing decisions. None being installed is the normal case, not a degraded one; one being installed but not selected stays unused. A composed package never converts a usable tool into authorization to change a vault.

Out of scope: vault-wide link and frontmatter audits, core-app defects, plugin development and building, and any live mutation of plugin state.

## Failure branches

Load [references/pipeline.md](references/pipeline.md) for the ordered procedure and the recovery rules:

- [Scope the case](references/pipeline.md#1-scope-the-case-before-capturing-anything) — one plugin, one observable symptom.
- [Capture evidence, read-only](references/pipeline.md#2-capture-evidence-read-only) — channels, probe discipline, sanitization.
- [Fix the version facts](references/pipeline.md#3-fix-the-version-facts-exactly) — exact strings, untested versions.
- [Classify and read findings honestly](references/pipeline.md#4-classify-then-read-the-findings-honestly) — statuses, exit codes, misreadings.
- [Templater command branches](references/pipeline.md#5-templater-command-branches) — [`ReferenceError`](references/pipeline.md#5a-unbound-identifier-templater-reference-error), [missing `await`](references/pipeline.md#5b-asynchronous-call-without-await-templater-missing-await), [unemitted value](references/pipeline.md#5c-computed-value-never-emitted-templater-missing-output).
- [Prompt cancellation](references/pipeline.md#6-prompt-cancellation-and-a-half-applied-vault-change) — ordering, guarding, two-path readback, recovery limits.
- [Unavailable plugin API](references/pipeline.md#7-unavailable-plugin-api) — read-only probes, version-scoped claims.
- [Unknown stays unknown](references/pipeline.md#8-unknown-stays-unknown) — what an unclassified line does and does not license.
- [The change boundary](references/pipeline.md#9-the-change-boundary) — proposable versus forbidden.
- [Record the outcome](references/pipeline.md#10-record-the-outcome) — registry appends, report shape.

## Verification

- [ ] The case named one plugin by manifest `id` and one symptom stated as an observable.
- [ ] Every channel was captured read-only; no probe assigned, saved, reloaded, enabled, or reset anything.
- [ ] Evidence was sanitized before it left the host, and no raw console dump was attached.
- [ ] App version, plugin version, and `minAppVersion` are exact strings, each with the channel it came from.
- [ ] An unrecorded or `reported` registry version was treated as untested, not as working.
- [ ] `not_applicable` findings and empty captures were reported as evidence gaps, never as passes.
- [ ] Every unknown appears in the report as unknown, and no unfamiliar error was mapped to the nearest familiar class.
- [ ] After a cancelled render, both the expected and the previous path were read back before anything was proposed.
- [ ] No forbidden recovery was proposed: no `data.json` edit, no build-output edit, no internal assignment, no reset, reinstall, or blanket rewrite.
- [ ] Registry appends were field-level, carried an evidence value, and the file still parses.

## Attribution

All files in this package are original work covered by the repository's MIT `LICENSE`. No upstream MIT-licensed file is included, so no upstream notice applies. Templater and Obsidian behavioural facts are cited to the publisher pages listed in [references/plugins.yaml](references/plugins.yaml) and echoed in each finding's `docs` array. The requirement evidence reviewed while authoring, and this package's limitations, are recorded in [CHANGELOG.md](CHANGELOG.md).
