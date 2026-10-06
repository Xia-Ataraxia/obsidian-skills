---
name: lint
description: Checks an explicitly bounded vault scope for note structure, citations, policy-supplied properties, derived-index drift, broken or orphan links, Persona boundaries, and approved cross-vault targets. Use for vault lint, note health, link checks, or a derived-index repair. Not for claim verification, sampled quality audit, template authoring, or unrestricted whole-vault correction.
license: MIT
metadata:
  version: "0.1.0"
---

# Lint

Diagnose the requested scope against live destination inputs and keep derived-index repair separate from note changes.

## Output contract

Return `lint/result@1` with exact scope, checks run, findings by category, limits, one optional derived-index proposal, zero note-patch proposals, cross-vault coverage, and actual mutations.
Report mode never writes.
Fix mode may change only the named derived index after exact approval.

Read [the shared contract](references/contract.md) and [the helper interface](references/interface.md) before invoking the helper.

## Workflow

1. Resolve the declared vault and exact note or directory scopes. Read live policy for required properties and Persona boundaries; do not copy mutable policy into this package.
2. Open only selected note bodies. Build the local target-name index from path metadata, and report orphan-link coverage as selected-scope coverage unless wider reads were explicitly authorized.
3. Check selected Markdown structure, footnote citations, policy-supplied properties, local links, scoped orphan links, derived-index membership, and declared Persona boundary rules. Keep unsupported or unchecked categories visible as limits.
4. Cross-vault checks require a real target name, target root, and explicit read permission. An encountered cross-vault link with no supplied target, or an unconfirmed supplied target, is a reported limit and blocks fix mode.
5. Return note findings without modifying notes. Derived-index drift is a separate proposal.
6. Apply only the exact approved derived-index proposal and read it back. A note patch, cross-vault write, policy edit, or bulk Wiki repair is never performed.

## Local helper

`python3 scripts/lint.py --vault <declared-vault> --request <request.json>`

The request selects `report` or `fix`.
Fix also needs `--approval <approval.json>`.
Python 3.8 or later and the standard library are sufficient.
Exit 0 returns a report or approved index fix, exit 1 returns `lint/error@1`, and usage errors exit 2.
