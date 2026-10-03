# Exact settings approval

The five eligible settings destinations are `.obsidian/app.json`,
`.obsidian/daily-notes.json`, and `data.json` under the `homepage`,
`templater-obsidian`, and `obsidian-excalidraw-plugin` plugin directories.
Eligibility permits a proposal, not a replacement.

Preview selected top-level keys using a JSON selection file, for example:

```json
{".obsidian/app.json": ["newFileLocation"]}
```

```bash
python3 scripts/onboard.py --candidate "$CANDIDATE" --role knowledge --target "$TARGET" --preview --select "$SELECTION"
```

The default preview selects all candidate keys; it still writes nothing.
Review the emitted `changes` with the owner. Each change records `path`, sorted
`keys`, `approval_preimage`, exact UTF-8 `before`/`after` bytes,
`postimage_sha256`, and `recovery`. A missing file has `before: null` and
`approval_preimage: "absent"`. Such a creation includes only selected keys.

The owner-approved document retains those exact changes and sets:

- `approval_state` to `approved` or `partially-approved`;
- `approval_effect` to exactly the effects present (`create` and/or `update`);
- `approval_scope` to exactly the change paths in order;
- `approval_basis` to the owner's statement or its verifiable location.

Never set these fields to manufacture permission. Keep the role and candidate
digest unchanged. Keep the approval private; it contains original settings.

```bash
python3 scripts/onboard.py --candidate "$CANDIDATE" --role knowledge --target "$TARGET" --mode additive --approval "$APPROVAL"
```

The CLI validates every change and preimage before the first write. It derives
the permitted diff independently: only selected top-level JSON values may
change, and missing selected keys may be inserted before the closing brace.
Every byte outside those spans stays unchanged, including unknown keys and
formatting. Nested objects are one top-level value: select that key only if the
owner approved changing the whole object. No unapproved nested-key merge occurs.

Reapplying an approval accepts exact postimages as already applied and reports
zero diffs. Any other current bytes are stale and refused. Multi-file application
is resumable, not a cross-file atomic transaction. Pause other writers first;
external edits racing the final atomic replacement are not serialized by this
CLI. The CLI never starts or stops the application.

Exit codes: `0` means the reported preview or materialized readback succeeded;
`1` means refusal or I/O failure; `2` means invalid command-line usage.
The public CLI output contains relative paths and digests, never source bodies
on apply. Preview deliberately prints exact settings for private review.
