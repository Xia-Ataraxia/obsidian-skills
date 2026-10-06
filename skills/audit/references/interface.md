# Audit helper interface

```bash
python3 scripts/audit.py --vault "$VAULT_ROOT" --request "$REQUEST_JSON"
```

The helper imports two internal modules, with paths relative to this package root: `scripts/audit_core.py` handles scope and sample validation, findings, report assembly, and prior-report comparison; `scripts/audit_io.py` handles path and JSON validation, proposal and approval bindings, and report publication with readback. These are package-local imports, not independent CLIs, a shared runtime, or a root dispatcher.

## Request

```json
{
  "schema": "audit/request@1",
  "scope": ["Wiki", "Raw/Attention study.md"],
  "sample": ["Wiki/Attention.md", "Wiki/Focus.md"],
  "sample_method": "Owner-selected pages touched by the current review.",
  "limits": [
    "Two explicitly selected notes; unsampled notes were not inspected."
  ],
  "previous_report": "Reports/previous-audit.json",
  "report_path": "Reports/current-audit.json"
}
```

`scope`, `sample`, `sample_method`, and `limits` are required.
Scope entries are existing Markdown notes or directories.
The sample is a nonempty, duplicate-free list of Markdown notes resolved by that scope.
The helper never chooses a sample or treats a displayed maximum as scan permission.

The helper reports observable risk categories:

- missing or unterminated frontmatter;
- `fidelity: partial`, `excerpt`, `manifest-only`, or `mixed`;
- `verification_status: verified` without a `verification_manifest`;
- unresolved local wikilinks in the declared vault.

These checks prioritize follow-up; they do not prove semantic truth or completeness.
Embedded text is never executed.

`previous_report` is optional and must name an existing `audit/report@1` JSON file.
Comparison reports count changes by category only.

## Saving

`report_path` is optional and must be a new `.json` file whose parent already exists.
Without approval, the result contains a create proposal and performs zero writes.
Apply with an approval that binds `create`, the exact path, `absent`, and the proposal digest:

```json
{
  "approval_state": "approved",
  "approval_effect": ["create"],
  "approval_scope": ["Reports/current-audit.json"],
  "approval_basis": "The owner approved saving this exact audit report.",
  "approval_preimage": {"Reports/current-audit.json": "absent"},
  "approval_proposal": {
    "Reports/current-audit.json": "sha256:<proposal-digest>"
  }
}
```

The helper creates only the report, using an atomic no-clobber link, then reads it back.
It never edits sampled notes.
`--write-disabled` dominates approval.
