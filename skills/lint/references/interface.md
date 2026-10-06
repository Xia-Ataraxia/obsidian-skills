# Lint helper interface

```bash
python3 scripts/lint.py --vault "$VAULT_ROOT" --request "$REQUEST_JSON"
```

The helper imports two internal modules, with paths relative to this package root: `scripts/lint_core.py` validates requests, assembles lint results, and prepares derived-index proposals; `scripts/lint_scan.py` handles path validation, scoped note discovery, note-name indexing, and Markdown, link, boundary, and cross-vault checks. These are package-local imports, not independent CLIs, a shared runtime, or a root dispatcher.

## Request

```json
{
  "schema": "lint/request@1",
  "mode": "report",
  "scope": ["Wiki", "Personas"],
  "required_properties": ["type", "created_by", "authorship"],
  "derived_index": "Indexes/Knowledge.md",
  "boundaries": [
    {
      "name": "persona-to-personal-people",
      "root": "Personas",
      "forbidden_roots": ["People"]
    }
  ],
  "cross_vault": {
    "target_name": "research",
    "target_root": "/provided/by/caller",
    "permission_state": "approved",
    "permission_basis": "The owner approved this exact cross-vault read."
  }
}
```

`schema`, `mode`, `scope`, `required_properties`, `derived_index`, and `boundaries` are required.
Scope entries are existing Markdown files or directories.
Required properties and boundaries come from current destination policy; the helper has no built-in vault schema.

Checks are:

- structure: frontmatter delimiter and first level-one heading;
- citations: every footnote reference has a definition;
- properties: each policy-supplied key appears in frontmatter;
- index: the named derived index matches the selected note set;
- links: unresolved local wikilinks and selected notes with no inlinks from other selected notes;
- Persona boundaries: links from a declared root into its forbidden roots;
- cross-vault links: `[[vault:<target-name>/<path>]]` references checked against one confirmed target.

The helper indexes local note names from path metadata without opening unrelated note bodies.
Structure, citations, properties, Persona boundaries, and outgoing links read selected notes only.
Orphan results therefore mean no in-scope inlink; the result reports that coverage limit instead of implying a whole-vault backlink scan.

An encountered cross-vault link with no supplied target adds a limit, remains permission-unconfirmed, performs no cross-vault check, and blocks fix mode.
An explicitly supplied but unconfirmed or unavailable target behaves the same way.
`checks` includes `cross_vault_link` only when a confirmed target was actually checked.
The output never includes the host target path.

## Report and fix

`mode: report` performs zero writes, even if approval is supplied.
It may return a derived-index proposal so the owner can review the exact bytes.
`note_patch_proposals` is always empty.

`mode: fix` applies only the derived-index proposal with approval bound to its exact effect, path, preimage, and proposal digest:

```json
{
  "approval_state": "approved",
  "approval_effect": ["update"],
  "approval_scope": ["Indexes/Knowledge.md"],
  "approval_basis": "The owner approved this exact derived-index replacement.",
  "approval_preimage": {
    "Indexes/Knowledge.md": "sha256:<current-index-digest>"
  },
  "approval_proposal": {
    "Indexes/Knowledge.md": "sha256:<proposal-digest>"
  }
}
```

Use `create` and `absent` when the approved derived index does not exist.
The helper checks the preimage immediately before atomic publication and reads back the exact index.
No note or cross-vault target is changed.
