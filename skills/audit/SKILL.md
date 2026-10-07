---
name: audit
description: Samples an explicitly bounded knowledge scope for quality risks, states coverage and limits, compares a prior report when supplied, and saves a report only with exact approval. Use for vault health sampling, periodic knowledge review, or verify follow-up prioritization. Not for exhaustive claim verification, bulk Wiki repair, or quality scoring.
license: MIT
metadata:
  version: "0.2.0"
---

# Audit

Inspect a declared scope through an explicit sample and report risks without presenting a sample as exhaustive verification.

## Output contract

Return `audit/report@1` with requested scope, resolved notes, exact sample, sample method, limits, findings, category counts, follow-up priorities, optional prior-report comparison, and actual mutations.
Counts describe observations; they are not a score, grade, confidence value, or quality certification.
The package never bulk-edits Wiki notes.

Read [the shared contract](references/contract.md) and [the helper interface](references/interface.md) before invoking the helper.

## Workflow

1. Resolve the declared vault and exact note or directory scopes. Do not widen a note, subfolder, or selected set into a whole-vault scan.
2. State how the sample was chosen. The helper accepts an explicit sample only; the caller owns any random, stratified, or risk-based selection.
3. Read every sampled note and record observable risks, partial-source limits, unbound verification markers, and broken local links.
4. Distinguish sample findings from unsampled scope. Audit is not a substitute for `verify` on every ingest.
5. Compare an earlier `audit/report@1` when supplied, using category count changes rather than a pseudo-score.
6. Return the report before saving. Save one JSON report only with exact create approval and an absent preimage.

## Local helper

`python3 scripts/audit.py --vault <declared-vault> --request <request.json>`

Use `--approval <approval.json>` only after reviewing the proposed report.
`--write-disabled` forces zero writes.
Python 3.8 or later and the standard library are sufficient.
Exit 0 returns a report or approved save, exit 1 returns `audit/error@1`, and usage errors exit 2.
