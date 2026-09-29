# Ownership cutover

**Status: steps 1–4 have been executed against public and isolated destinations; steps 5–7 remain procedure only. No production consumer, installed profile, or old source owner has been changed.** A published candidate and an isolated canary do not mean ownership transfer is complete.

## Required evidence

Before a concrete effect, record its exact source revision, destination, authorization, consumer pointer, rollback configuration, and responsible owner. The public responsibility inventory measures source units, not just files: a mixed router or evaluation can contain several distinct route/case units. Each functional unit has exactly one candidate feature owner. Shared license notices are supporting obligations, not duplicate implementations.

Consumer-specific policy and exact callsite evidence belong to that consumer's private change record. Keep them out of this public repository. Confirm current source-local authoring/admission and protected-change requirements in the separately authorized source session; a target repository approval cannot waive them. Do not decide an unresolved lifecycle policy on behalf of the owner.

## Ordered transition

1. Validate the complete nine-package candidate and record its content digest. Keep the old owner working.
2. Obtain distinct publication approval, then publish an immutable candidate. Verify the actual public README rendering, images, links, and advertised install paths. Local rendering is not this evidence.
3. Obtain installation/canary approval for an exact disposable or deployed destination. Detect collisions before any write. Stop rather than shadowing an existing identity.
4. Fresh-load the candidate by native package identity. Record runtime/version, discovery path, selected feature, representative behavior, readback, and preservation. An existing session or cache entry is not fresh-load proof.
5. Under exact consumer-change approval, update the consumer pointer to the validated candidate. Preserve private policy locally.
6. Fresh-load again. Only after success and separate source-owner retirement authorization, remove the old implementation and its old callers in the source-root session. Do not leave aliases, fallback routers, or shadow packages.
7. Inventory active identities and callers. Both missing ownership and duplicate ownership fail the cutover. Record active old owner/caller count zero only from actual post-change evidence.

## Where this candidate stands

Evidence for every line below: [`tests/evidence/publication-canary.json`](../tests/evidence/publication-canary.json), published rows in [verification-matrix.md](verification-matrix.md).

| Step | State | What was actually observed |
| --- | --- | --- |
| 1. Candidate and digest | done | the complete nine-package candidate was validated locally; its published content is pinned by the tree and archive digests in row 2 |
| 2. Publication and public rendering | done | tag `v0.1.0` (prerelease) at the immutable commit `0e658b5a09ac4c789392ac634dcff8a195fa3116`, tag object `04f9dfe25157040dd08a8d14158f8a5d2bbc50ca`, tree `10dff62e017df86883d5dd4042f065760e576346`, downloaded archive SHA-256 `74d97b113a590d83bf082ba8c80a8f93b316da5c11cdfbca14d791c556cbb608`, 5 commits / 57 trees / 95 blobs reachable. Both public articles rendered on the repository host in Chromium with both original SVGs and their alt text, and repository-relative links resolved to paths that exist in the commit. The release is immutable and is not retagged — later documentation corrections do not alter it. |
| 3. Destination without collision | done, disposable | an isolated consumer project whose origin is a detached clone of that commit. No existing identity was shadowed and no deployed destination was used. |
| 4. Fresh-load by native identity | done, one runtime | Claude Code: marketplace add and `claude plugin install obsidian-skills@obsidian-skills --scope project` both returned success for version 0.1.0; the runtime then answered fresh `obsidian-skills:obsidian-cli` and `obsidian-skills:obsidian-sync` Skill calls, with `obsidian-skills:obsidian-canvas` in a separate fresh response. A non-target sentinel in that project was unchanged. Not a production user-profile deployment, and no other runtime is claimed. |
| 5. Consumer pointer | outstanding | no consumer pointer has been moved. The deployment that would move it is admitted in the source-local authoring path — a distinct step, not a generic approval this repository can stand in for. |
| 6. Retirement of the old owner | outstanding | the old implementation and its callers are untouched; no retirement authorization has been exercised. |
| 7. Identity and caller audit | outstanding | no post-change inventory exists, so active old owner/caller count zero cannot be recorded. |

Also outstanding, and not blocked by the steps above: account-bound Sync pairing and remote-vault selection (no live account has been used), and deployed recovery (only the disposable simulation below exists). Web Clipper 1.7.1 was installed in a disposable browser profile — an initial no-page-target attach was recovered, the shipped template imported as *General clipping* with *Default* preserved, and the popup extracted a real `example.org` page into the note preview — but *Add to Obsidian* was not activated while the destination read *Last used*, so exact-destination clip delivery and its vault readback stay unverified. None of this is a cutover gate.

## Failure and recovery

Stop further writes, network Sync, and daemon activity at the first discovery, permission, render, or preservation failure. Save the sanitized error class and pre/post hashes. Restore the exact approved previous source/configuration revision and consumer pointer; fresh-load and verify it. Never restore by resetting, mirroring, deleting, or overwriting user notes or metadata. Leave newly created user content intact for explicit reconciliation.

A disposable test can exercise pointer restoration and non-target preservation without authorizing a deployed change. Such a test is **simulation evidence only**. The step-4 canary has been executed, but only against an isolated consumer project — never a deployed destination; retirement, the stale-caller audit, and production recovery remain incomplete until executed under their own approvals.
