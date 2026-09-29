# Operations and failure branches

Load this reference when an `obsidian` command mutates the vault, fails, or returns something you cannot interpret.
`SKILL.md` owns the command surface and the mutation contract; this file owns what to do when reality does not match them.
Each branch below states the signal, the check that distinguishes look-alike causes, and the recovery that does not damage unrelated content.

The rule behind all five branches: an operation is only as real as its readback.
The CLI reports on a live app, so exit status, stdout, and the filesystem can each be right while the other two are stale.

## 1. Vault resolution

Without `vault=`, commands follow the most recently focused vault.
That focus is app state nobody in this task set, and it changes whenever the user clicks another window.
The dangerous outcome is not an error — it is a command that succeeds against a vault the task never meant to touch.

Resolve in this order and stop at the first that holds:

1. A vault the user named for this task.
2. A vault name the task already verified with a read-only probe in this session.
3. Nothing — stay read-only and ask.

`vault=` takes the vault name as Obsidian displays it, not a filesystem path, and it must be the first parameter.

Probe before mutating, using the same `vault=` value the write will use:

```bash
obsidian vault="My Vault" read path="Projects/Roadmap.md"
```

Read the outcome this way:

- The expected note comes back — the vault and the path are both confirmed for that exact spelling.
- A not-found or unknown-vault error — the name is wrong or that vault is not open; report the name you tried instead of trying near-miss spellings.
- Content comes back but it is not the note under discussion — you reached a different vault or a same-named note elsewhere. Stop; a write here overwrites someone else's note.
- Empty output with exit code 0 — indeterminate, not absence. Go to [branch 2](#2-app-or-runtime-unavailable).

Two or more candidate vaults, or a vault name that only appears in an old message, are ambiguity, not a default.
Report the candidates and let the user choose.
Never resolve ambiguity by picking the most recently focused vault, and never hardcode a vault name, workstation path, or account identifier into anything reusable.

## 2. App or runtime unavailable

The binary is a client for a running app, so "unavailable" has several distinct causes with different fixes.
Diagnose before reporting, because the wrong diagnosis leads to the wrong substitution.

| Signal | Cause | Action |
|---|---|---|
| `obsidian` not found on `PATH` | The CLI is not installed or not exposed | Report the missing binary. Do not install it, and do not substitute another tool. |
| `obsidian version` fails or hangs | The app is not running or is not accepting connections | Ask for the app to be opened. Everything vault-related stays blocked until it answers. |
| `version` answers but a command returns empty with exit 0 | The app bridge answered without a result, or the index is not ready | Retry the same command a bounded number of times with a short pause, then treat it as indeterminate. |
| A command errors as unknown | The installed build does not have it | Go to [branch 4](#4-version-skew). |
| Commands work but content looks wrong | Wrong vault | Go to [branch 1](#1-vault-resolution). |

Empty output with exit code 0 is the trap worth naming twice.
It has been observed for a search term that was present in the vault, which means empty output proves nothing about the vault's contents.
Never convert it into "no results", "note does not exist", or "the change was not applied".

Do not declare a capability unavailable after one failed probe.
Confirm with a second, different probe — a `version` check plus a read of a note you already know exists tells you far more than repeating the same failing call.
If both fail, report the capability gap and stop.

Never respond to an unavailable app by writing vault files with shell tools, by switching to an unrelated binary, or by describing the intended result as if it happened.
A blocked operation reported honestly is a correct outcome; a fabricated one is not recoverable by the next agent.

## 3. Write and move failures

### Partial writes

A write is partial when the command reported failure but content was already materialized, when a multi-step mutation (create, then `property:set`, then `append`) stopped midway, or when the readback shows only some of the requested change.

Readback decides what actually happened, in this order:

1. Re-read the exact path you wrote.
2. Compare against the pre-change snapshot taken before the write.
3. Classify: nothing applied, fully applied, or partially applied.

Recovery depends on the classification:

- **Nothing applied** — re-run the original command once, after confirming from the readback that it really did not apply.
- **Fully applied** — the failure was in reporting, not in the write. Record it and move on.
- **Partially applied** — complete only the missing delta with the narrowest additive command.

Never "reset" a partially written note with `create ... overwrite`, and never delete and recreate it.
Both discard content that was not part of the requested change, including edits the user made between your read and your write.
If the missing delta cannot be applied without a whole-body rewrite, stop and report; a whole-body rewrite is a separate authorization.

### Retry hazards

Additive commands are not idempotent.
A retried `append` or `prepend` after an ambiguous result appends twice, and the duplicate looks like content the user wrote.
Always re-read before retrying a mutating command, and only retry when the readback shows the effect is absent.

`property:set` is idempotent only while the inspected property and authorization remain unchanged. Re-read before retrying: a concurrent user edit must not be overwritten just because the original value was fixed.

### Moves

A move can half-succeed in three places at once: the destination, the old path, and every inbound link.
Check all three, in this order:

The isolated 1.12.7 collision check returned exit code 0 with `Error: Destination file already exists!`; both files were preserved. Inspect error text and materialized state, not only the exit status.

1. Read the destination path — the note must be there with its content intact.
2. Read the old path — it must no longer resolve.
3. Audit links with `obsidian backlinks file="<moved note>"` and `obsidian unresolved`, compared against the pre-move audit.

Common outcomes:

- **Destination exists, source gone, links resolve** — the move completed.
- **Both paths hold a copy** — the move duplicated instead of moving. Report both paths; do not delete either copy on your own initiative, because you cannot tell from here which one the user has since edited.
- **Destination missing, source intact** — nothing happened; re-run after confirming the parameters against `obsidian help`.
- **Destination exists but links now appear in `unresolved`** — the content moved and the links did not follow. Report the unresolved set; repairing links is a separate note mutation with its own readback.
- **Destination path was already occupied** — stop. Do not overwrite, merge, or auto-rename. Report the collision with both paths and let the user decide.

### Non-target preservation

The only acceptable difference between the pre-change and post-change readback is the requested change.
Frontmatter you did not target, other sections, block IDs, attachments, and link text all count as non-target content.
If the diff contains anything else, treat the operation as failed even when the requested change is present, and report the unexpected difference before doing anything else.

### Bulk operations

Do not loop a mutation over an unbounded search result.
Work from an explicit list of paths, read back after each item, and stop at the first unexpected diff with the completed and remaining items named.
A partially completed bulk run that is reported precisely is recoverable; one that ran to the end past an unnoticed error is not.

## 4. Version skew

`obsidian help` is the catalog of the installed build.
This package is a snapshot written against evidence available when it was authored, so the two can drift.

Skew shows up as a command in this package that `help` does not list, a command that errors as unknown, a parameter the build rejects, or output whose shape no longer matches what a step parses.

Resolve it in this order:

1. Re-read `obsidian help` for the installed build and use what it documents.
2. Check the official CLI documentation at https://help.obsidian.md/cli for the current form.
3. Report the mismatch so this package can be corrected.

Never bridge skew by approximating.
A near-miss command name, a guessed parameter spelling, or a shell substitute for a missing command turns a clear capability gap into an unpredictable effect on a real vault.

Record the version you actually observed with `obsidian version` next to any behavioral claim you report, and scope the claim to that build.
Behavior observed on one build is not evidence about another, and an unobserved build is unknown rather than assumed compatible.

Plugin-provided commands are a separate axis of skew: they exist only while that plugin is installed and enabled, and their parameters follow the plugin's own release cycle.
Their absence is plugin state to report, not a CLI defect to work around.

## 5. Failure safety

### Destructive set

Treat these as destructive and require explicit approved scope naming exact paths before running them:

- `delete`
- `create ... overwrite` on an existing note
- a move onto an occupied destination
- any bulk replacement across multiple notes
- anything that touches `.obsidian/` or plugin data
- `eval` that assigns, saves, or deletes

Default to read-only when authorization is missing or ambiguous.
Reuse authorization the task already granted for that note and effect; do not demand consent again for the same approved change, and do not stretch consent for one note to cover its neighbors.

### Recovery discipline

Recovery restores the exact prior content of the affected region and nothing else.
Never resolve a failed mutation by resetting a note to a template, mirroring another note over it, or deleting it to start clean.
If you do not hold a pre-change snapshot of the content you would need to restore, say so and stop rather than reconstructing it from memory.

Clean up probe notes this task created, by their exact paths, and only those.

### Reporting

Do not report a check you did not run.
A command that was blocked, an audit that could not run because the app was closed, or a rendered result nobody looked at is unverified, and labeling it that way is part of a successful outcome.

Keep private data out of what you report and out of what you write into the vault: no tokens, workstation paths, account identifiers, or vault contents that the request did not ask you to surface.

A failure report is complete when it names:

- the binary and the version it reported;
- the vault targeted and how it was resolved;
- the commands run, with private values redacted;
- what the readback showed, including untouched regions;
- what remains unverified or blocked, and why.

## Verification

- [ ] The vault was resolved explicitly, and ambiguity was reported instead of defaulting to focus.
- [ ] An unavailable capability was confirmed by a second, different probe before being reported.
- [ ] Empty output with exit code 0 was retried and then treated as indeterminate.
- [ ] Every mutation was classified by readback as not applied, partially applied, or fully applied before any retry.
- [ ] A move was verified at the destination, the old path, and the link audit.
- [ ] The post-change diff contained only the requested change.
- [ ] Missing commands or parameters were reported as skew, never approximated.
- [ ] Destructive operations had explicit approved scope, or were skipped and reported.
