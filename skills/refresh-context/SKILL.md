---
name: refresh-context
description: Re-reads explicitly named Me, policy, and user-instruction sources, binds proposed derived snapshots to exact source and snapshot hashes, and applies only fully or partially approved snapshot paths. Use when derived agent context must be refreshed after source changes. Not for editing Me or policy, inventing personal context, automatic reloads, public context publication, or requiring a counterpart vault.
license: MIT
metadata:
  version: "0.2.0"
---

# Refresh Context

Refresh named derived snapshots from current source context without turning a
snapshot into a competing source of truth.

The workflow is: read Me/policy/user instruction sources, prepare proposed
snapshot bytes, show exact preimages and proposal hashes, record full approval,
partial approval, or rejection, then update only approved snapshot paths.

## Prepare a proposal

Use `scripts/refresh_context.py` with a `refresh-context/request@1` document.
Its approval checks and interruption-safe file publication live in
`scripts/snapshot_io.py`; callers invoke only the main script.

```bash
python3 scripts/refresh_context.py --vault VAULT --request request.json
```

```json
{
  "schema": "refresh-context/request@1",
  "sources": [
    {"name": "owner", "kind": "me", "path": "Me.md"},
    {"name": "policy", "kind": "policy", "path": "90. Settings/Policy.md"}
  ],
  "snapshots": [
    {
      "name": "agent-context",
      "path": "90. Settings/Derived/agent-context.md",
      "content": "Caller-authored proposed bytes."
    }
  ],
  "counterpart_vault": null
}
```

The package never generates personal claims from names, paths, or old
snapshots. The caller prepares `content` only after reading the listed sources.
The helper binds that proposal to current source hashes and exact snapshot
preimages. A null `counterpart_vault` is reported as `not-specified`; a named
path whose directory is missing is reported as `absent-allowed`. Both are
nonblocking for the standalone vault.

Read [the shared contract](references/contract.md) before recording a decision.

## Apply a decision

Pass a separate approval record:

```bash
python3 scripts/refresh_context.py \
  --vault VAULT --request request.json --approval approval.json
```

The approval uses the shared fields plus a per-path proposal binding:

```json
{
  "approval_state": "partially-approved",
  "approval_effect": ["update"],
  "approval_scope": ["90. Settings/Derived/agent-context.md"],
  "approval_basis": "Owner approved this exact snapshot.",
  "approval_preimage": {
    "90. Settings/Derived/agent-context.md": "sha256:..."
  },
  "approval_proposal": {
    "90. Settings/Derived/agent-context.md": "sha256:..."
  }
}
```

`approved` must name every proposed snapshot. `partially-approved` names only
the approved subset. `rejected` writes nothing. A newly absent target requires
the `create` effect; an existing target requires `update`.

Before any write, the helper re-reads every source and every approved target.
Changed sources, stale snapshot bytes, altered proposal content, traversal,
symlinks, source/snapshot overlap, unknown approval paths, or missing effects
refuse the whole request. Successful output lists the exact snapshot paths
materialized; source paths never appear there.

## Boundaries

This package never edits Me, AGENTS, policies, user instructions, another vault,
qmd configuration, or runtime profiles. It does not auto-publish personal
context and does not infer approval from installation, eligibility, or an old
decision. The derived snapshot remains subordinate to the re-read source bytes.

Python 3.8 or newer and the standard library are sufficient.
