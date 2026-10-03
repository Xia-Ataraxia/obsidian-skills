# Verify helper interface

Run from the package or source checkout:

```bash
python3 scripts/verify.py --vault "$VAULT_ROOT" --request "$REQUEST_JSON"
```

All paths are literal vault-relative Markdown paths.
Hidden components, traversal, symlinks, missing files, and out-of-range line selections are refused.

## Request

```json
{
  "schema": "verify/request@1",
  "page": "Wiki/Attention.md",
  "manifest": [
    "Wiki/Attention.md",
    "Wiki/Focus.md",
    "Raw/Attention study.md"
  ],
  "claims": [
    {
      "id": "attention-is-limited",
      "start_line": 8,
      "end_line": 8,
      "reviewed": true,
      "verdict": "resolved",
      "counterpart": "Wiki/Focus.md",
      "evidence": [
        {"path": "Wiki/Focus.md", "start_line": 10, "end_line": 12}
      ],
      "new_evidence": [
        {"path": "Raw/Attention study.md", "start_line": 4, "end_line": 9}
      ]
    },
    {
      "id": "unreviewed-example",
      "start_line": 12,
      "end_line": 12,
      "reviewed": false,
      "verdict": "unverified",
      "counterpart": "",
      "evidence": [],
      "new_evidence": []
    }
  ],
  "record_target": "Wiki/Attention.md"
}
```

`schema`, `page`, `manifest`, and `claims` are required.
The page must be in the manifest.
Each claim names a unique identifier and inclusive range on that page.
Reviewed claims use `supported`, `disputed`, or `resolved`.
Unreviewed claims must use `unverified` and carry no evidence.
Every evidence or counterpart path must be in the manifest.
`resolved` requires a nonempty `new_evidence` list and a counterpart page.

The helper reads every selected range and returns its current SHA-256 digest and text.
That proves which bytes were reviewed, not that the verdict is semantically correct.

## Proposal and approval

`record_target` is optional and, when present, must equal `page`.
The proposal appends one machine-readable `verify/record@1` JSON block without changing prior bytes.
No approval means zero writes.

Apply a reviewed proposal with:

```json
{
  "approval_state": "approved",
  "approval_effect": ["update"],
  "approval_scope": ["Wiki/Attention.md"],
  "approval_basis": "The owner approved this exact verification record.",
  "approval_preimage": {
    "Wiki/Attention.md": "sha256:<reviewed-page-digest>"
  },
  "approval_proposal": {
    "Wiki/Attention.md": "sha256:<proposal-digest>"
  }
}
```

The proposal digest binds path, preimage, postimage, and unified diff.
The helper rechecks all evidence digests and the target preimage before replacing the target atomically.
It never writes a counterpart page.
`--write-disabled` returns the same proposal with zero mutations.

Exit 0 reports `status: reviewed` or `status: applied`.
Exit 1 reports `verify/error@1`; an unavailable or changed input is never success.
