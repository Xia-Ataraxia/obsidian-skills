<!-- generated from docs/contracts.md; do not edit -->
# Shared field contract

Every knowledge package states approval, purpose, source and fidelity with the fields below. The contract is authored once, in `docs/contracts.md` of the source repository. Each knowledge package carries a generated, byte-identical copy at `references/contract.md`, because a package is installed on its own and cannot read anything outside itself. Change the source and regenerate; never edit a copy.

A field is a record of something that happened or was decided. Writing a field does not grant the permission, establish the fact, or perform the check it names.

## Approval

Approval is an explicit statement by the vault owner about one concrete effect. It is never inferred from a question, from the arrival of material, from an earlier and different approval, or from a package being installed.

| Field | Value | Meaning |
| --- | --- | --- |
| `approval_state` | `not-requested`, `requested`, `approved`, `partially-approved`, `rejected` | Where the decision stands. `not-requested` is the default and permits reading and reporting only. |
| `approval_effect` | list of `read`, `report`, `create`, `update`, `convert`, `move`, `delete`, `send` | The effects that were approved. An effect that is not listed is not approved. |
| `approval_scope` | list of vault-relative paths or exact item identifiers | The items the approval covers. Anything outside the list is untouched. |
| `approval_basis` | one sentence quoting or locating the owner's statement | Where the approval came from, so it can be checked later. |
| `approval_preimage` | per item: `sha256:<hex>` of the bytes before the change, or `absent` | What the approved change starts from, so a changed or newly appeared item is noticed and the change can be undone. |

Rules:

- `delete` and `send` are always approved separately. Neither is implied by any other effect, and neither is a default step of any package.
- Eligibility is not approval. A path that a package may write, an output list, an allowlist or a template's destination list makes an item eligible; it never approves changing that item. Changing an item that already exists needs `update` approval naming that exact item, with its `approval_preimage`, the proposed diff and how to restore it. When the item no longer matches its `approval_preimage`, the approval no longer applies.
- An approved change to an existing item changes only the approved keys or lines. Unknown keys and every other byte, name and link are preserved; an existing item is never replaced by, or merged from, a freshly generated copy.
- `partially-approved` requires `approval_scope` to name exactly the approved items. The rest keep `not-requested`.
- A rejection is recorded and respected. The same request is not repeated in the same task.
- An approval covers the effect, the scope and the task it was given for. A new task, a wider scope or a different effect needs its own approval.
- A report of what would change is not the change. Report and applied change are recorded as separate outcomes.

## Purpose

Purpose says why the material is being handled, in the owner's words. It decides what is worth extracting and what counts as done.

| Field | Value | Meaning |
| --- | --- | --- |
| `purpose` | one or two sentences | Why this material is handled now. |
| `purpose_origin` | `stated`, `reused`, `unknown` | `stated`: the owner gave it for this item. `reused`: the owner gave it for a batch or an earlier step of the same task. `unknown`: nobody gave one. |

Rules:

- A purpose the owner has already stated is not asked for again. Reuse it and record `reused`.
- `unknown` is a legitimate value. Never invent a purpose, a quantity target or a quota to fill the field.
- The presence of a `purpose` field does not show that the purpose was met.

## Source

Source identifies the original material and how it was obtained, on three separate axes. They are never merged into one category.

| Field | Value | Meaning |
| --- | --- | --- |
| `source_input` | `tabs`, `url`, `file`, `text`, `session`, `candidate` | How the material was designated. |
| `source_kind` | `article`, `video`, `repository`, `mail`, `conversation`, `book`, `paper`, `other` | What the material is. |
| `source_extraction` | `browser`, `reader`, `transcript`, `document-conversion`, `runtime-query`, `direct-read`, `none` | How the content was obtained. |
| `source_locator` | canonical URL, vault-relative path, or stable identifier | Where the original is. |
| `source_identity` | DOI, full citation key, commit hash, message identifier, or content digest | What makes two items the same source. Empty when none is known. |
| `source_obtained_at` | ISO 8601 date or date-time | When the content was obtained. |

Rules:

- Sameness is decided by `source_identity` or by a matching `source_locator`. A title, a folder, an author, or a surname with a year is a search hint, not proof that two items are one source.
- An answer or a summary produced from sources inherits those sources. It is not a new, independent source.
- A list of sources is not the content of those sources. Record it as a list.
- A relative `source_locator` resolves against the base its input format declares, which is not necessarily the directory holding the manifest that names it. Record locators relative to that declared base, and refuse a locator that leaves it.
- Host paths, account names and credentials never appear in a source field. Use vault-relative paths and public identifiers.

## Fidelity

Fidelity says how much of the original was actually obtained and what happened to it on the way.

| Field | Value | Meaning |
| --- | --- | --- |
| `fidelity` | `full`, `partial`, `excerpt`, `manifest-only`, `mixed` | How much of the original content is present. |
| `fidelity_omissions` | list of short statements | What is missing, truncated, inaccessible or deleted. Empty only when nothing is known to be missing. |
| `fidelity_conversion` | list of `tool`, `from`, `to` entries | Each conversion applied, in order. Empty when the content was read directly. |
| `fidelity_checked` | `not-checked`, `spot-checked`, `compared-to-original` | What comparison against the original was really made. |

Rules:

- Original content and anything written about it are kept in separate, labelled sections. Analysis never overwrites or rewords the original.
- Content that was not obtained is recorded as not obtained. No placeholder body is written to make a note look complete.
- `compared-to-original` is recorded only when that comparison was performed in this task, over the range it names.
- A range that was not reviewed is never recorded as reviewed, verified or complete.

## Evidence levels

A package reports the level it actually reached, and no higher.

| Level | What it shows |
| --- | --- |
| `authored` | Text or a plan was written. Nothing was checked. |
| `static` | The bytes were parsed or validated without running the application. |
| `materialized` | The result was written and read back from the exact destination. |
| `runtime` | The application, plugin or tool was observed doing it. |

A missing application, plugin, tool or network result is reported as `unavailable`. It is never converted into success.
