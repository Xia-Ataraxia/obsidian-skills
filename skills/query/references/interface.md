# Query helper interface

Run from the package or source checkout, supplying paths as flags:

```bash
python3 scripts/query.py --vault "$VAULT_ROOT" --vault-name "$VAULT_NAME" --request "$REQUEST_JSON"
```

From a repository checkout, the executable is `skills/query/scripts/query.py`.
The helper has no dependency on another package and no network or app side effects.
All JSON inputs are UTF-8; paths are literal, vault-relative, forward-slash names.
Hidden paths, traversal, symlink roots/targets, and ambiguous `#` anchor filenames are refused.
Hidden and symlink entries within a selected directory are excluded from retrieval.

## Request

```json
{
  "schema": "query/request@1",
  "question": "What does the article say about attention?",
  "scope": ["Raw", "Wiki"],
  "terms": ["attention"]
}
```

`schema`, `question`, and `scope` are required.
`scope` is a nonempty list of existing Markdown notes or directories; there is no default whole-vault scan.
Optional `terms` supplies explicit lexical hints; without it the question's Unicode words are used.
All matching paragraphs are returned, ranked by distinct term coverage, then path and line.
The helper reads complete selected notes, excludes frontmatter from matching, and returns the exact paragraph bytes as text with one-based inclusive line ranges.
It does not follow wikilinks, resolve synonyms, infer contradictions, or claim exhaustive semantic coverage.
Empty results have `status: insufficient_evidence`, not a fabricated answer.

Optional `claims` is a nonempty list of `{"text": "...", "citations": [1, 2]}`.
Each identifier refers to an existing citation in this same result.
The synthesis is labelled separately from extractive evidence.
The answering agent reviews semantic support against full notes before supplying claims; citation membership is not an entailment check.

## Save proposal

Add `"save": "30. Queries/Attention answer.md"` to request a new answer-note proposal.
No approval means a proposed diff and zero mutations, even if the question says to save.
No citations means saving is refused.
The parent must already exist; an existing destination is a collision, never an implicit update.
The generic note records agent authorship and separates the question, agent synthesis (if supplied), quotations, and inherited citation anchors.
Its generic layout is not a replacement for a designated destination template.

## Reinforcement proposal

Instead of `save`, add:

```json
{
  "reinforcement": {
    "target": "Wiki/Attention.md",
    "kind": "gap",
    "reason": "The reviewed article supplies missing support for this topic.",
    "append": "The evidence describes attention as a limited resource.",
    "citations": [1]
  }
}
```

`kind` is `gap` or `conflict`.
All five fields are required; the target must be an existing note in the selected scope.
The append is labelled reinforcement and inherits the selected evidence anchors.
The proposal contains the target, effect, preimage/postimage hashes, unified diff, complete resulting content, reason, and `proposal_sha256`.
The proposal digest binds the canonical JSON of path, preimage, postimage, and diff.
The helper makes no automatic semantic conflict decision.

## Approval and application

Review the proposal, then supply `--approval "$APPROVAL_JSON"` with the owner's actual decision:

```json
{
  "approval_state": "approved",
  "approval_effect": ["create"],
  "approval_scope": ["30. Queries/Attention answer.md"],
  "approval_basis": "The owner approved this exact answer proposal for this task.",
  "approval_preimage": {"30. Queries/Attention answer.md": "absent"},
  "approval_proposal": {"30. Queries/Attention answer.md": "sha256:<reviewed-proposal-digest>"}
}
```

Use `update` and the proposed `sha256:<preimage>` for reinforcement.
`partially-approved` works only for the named item; mismatched scope, effect, digest, or preimage refuses application.
`approval_proposal` is a query-specific binding supplement to the generated shared contract.
It is not an authentication token or proof of an owner's decision.
No approval file is a normal read-only invocation.
`--write-disabled` dominates even a supplied approval and returns proposals without touching the vault.

Apply one effect per invocation; save and reinforcement cannot be requested together.
Before application, every cited note's current digest is compared to the retrieved bytes.
Create uses a staged file and atomic no-clobber link; update stages complete bytes, rechecks the preimage, preserves the existing mode, and replaces only the exact target.
The helper leaves no staging files after success or failure.
There is no cross-process transaction with an uncooperative writer: coordinate exclusive access to the exact target during application.
If a live editor can change the note concurrently, keep the helper in proposal mode and use the destination's approved mutation surface.

After application, `status` is `applied` only following exact byte readback, and `mutations_performed` names the one target.
Keep the preimage bytes privately before approved updates.
Restore an approved appended reinforcement only with separate permission, checking that the current digest equals the proposal's postimage and restoring the preimage bytes; do not overwrite later user changes.
Creation cleanup also requires separately authorized deletion of the exact created note.

Exit 0 means a completed read/proposal/application with the result's stated evidence level, not app verification.
Exit 1 means refusal or I/O failure; `query/error@1` gives a machine code.
Exit 2 is argparse usage failure.
An I/O failure after attempting a write explicitly leaves materialization unconfirmed; inspect the exact target before retrying.
