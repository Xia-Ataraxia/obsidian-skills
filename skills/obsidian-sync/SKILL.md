---
name: obsidian-sync
description: Operates the headless `ob` client (npm package `obsidian-headless`) for Obsidian Sync from a terminal with no desktop app - pairing one exact local vault path to one exact remote vault, choosing `pull-only`/`bidirectional`/`mirror-remote`, running one-shot or `--continuous` sync under a supervisor, and containing sync incidents. Use when the user asks to set up, inspect, or repair headless sync on a server, VPS, or replica machine, says notes disappeared or were reverted after a sync, hits `The connected remote vault no longer exists`, `Failed to validate password`, `No sync configuration found`, `Encryption version not supported`, or `Another sync instance is already running`, finds `(Conflicted copy ...)` files, or needs a sync daemon started, stopped, restarted, or supervised. Not for GUI Sync settings, not for the official `obsidian` desktop CLI, and not for Obsidian Publish.
license: MIT
metadata:
  version: "0.3.0"
---

# Obsidian Headless Sync

Drive the `ob` headless client so that every sync run has a named local root, a named remote vault, a known direction, and a reversible outcome. Success is not "the command exited 0" - it is that the observed file changes match the direction you authorized, and that a wrong outcome can still be undone.

Two properties of this client shape everything below:

- **Download modes delete.** `pull-only` and `mirror-remote` both apply remote deletions to the local vault. Neither is read-only.
- **Pairing resets policy.** `ob sync-setup` writes a fresh config whose mode is `bidirectional` and whose conflict strategy is `merge`. Pairing therefore *arms* uploads; it never leaves an earlier `pull-only` choice in place.

## Binary identity and version gate

The executable is `ob`, installed by the npm package `obsidian-headless`. It requires Node.js 22 or later and talks directly to the Obsidian Sync service - it does **not** need or use a running desktop app.

```bash
node --version      # must be >= v22
ob --version        # or: ob -V
ob --help           # authoritative command list for this build
```

This manual was written against **`obsidian-headless` 0.0.14**. `--help` is the authority, not this document.

Fail closed on skew. Before any command that changes something, read the `--help` of that exact subcommand. If a command, flag, or flag value named here is missing from the installed build's help, stop and report version skew. Never substitute a plausible-looking alternative flag, never fall back to editing the client's config files by hand to emulate a missing flag, and never assume an undocumented flag is merely undocumented. The machine-checkable gate is in [references/commands.md](references/commands.md#version-gate).

`ob` is not the official `obsidian` desktop CLI and not the unrelated third-party binary published as `obsidian-cli`. Three different programs, three different guarantees. If `ob` is absent, report the gap; do not install it as a side effect of a diagnosis, and do not reach for another tool.

## Identity: resolve both ends before anything else

Every command in this package acts on a pair. Write both halves down explicitly and keep them verbatim for the whole task.

### Exact local root

`--path` accepts a directory and is resolved with ordinary path resolution (`path.resolve`), then compared as a **string** against the stored `vaultPath`. Consequences:

- Omitting `--path` silently targets the current working directory. Always pass `--path` explicitly.
- Matching is lexical, so `.`, `..`, and trailing slashes normalize away and are safe - but letter case and symlinks do not. A different letter case on a case-insensitive filesystem, a symlinked parent, or `/tmp/x` where the config stored `/private/tmp/x` is a *different* vault to `ob`. The symptom is `No sync configuration found for <path>` with exit code 3, not a warning.
- Never copy an absolute vault path from one machine into another machine's command or supervisor definition. Resolve it independently on each host.

Pin the literal root once per host and reuse the variable:

```bash
OBSIDIAN_VAULT_PATH=$(cd /srv/vaults/example-vault && pwd -P)
printf '%s\n' "$OBSIDIAN_VAULT_PATH"
```

### Exact remote identity

`--vault` accepts a remote vault **ID** or **name**. ID is matched first; only if no ID matches is an exact name compared.

- Two remote vaults sharing a name → `Multiple vaults named "<name>". Use the vault ID instead:` plus the candidate IDs, exit 1.
- No match → `Vault "<name>" not found.`, exit 3.
- Shared vaults appear in a separate list but are selectable by the same `--vault` value.

Prefer the ID. A name is a display label that the account owner can change or duplicate; an ID is the thing the pairing actually stores.

### Identity is not isolation

Distinct vault IDs, local paths, device names, or supervisor processes do **not** imply distinct credentials or permissions. One `ob` login on a host reaches every vault that account can see, and the stored token is account-wide. If a task requires credential separation, that must be established at the account level and verified; a per-vault pairing never provides it. Report the gap instead of implying it.

## Prerequisites

All of these are local and read-only. Complete them before requesting any network or mutation authorization.

- [ ] `node --version` is v22 or later.
- [ ] `ob --version` answers, and the subcommand `--help` output contains every flag this task will use.
- [ ] The exact local root is resolved on this host with `pwd -P` and recorded.
- [ ] The exact remote vault ID is recorded, or the task explicitly ends after inspection.
- [ ] A point-in-time restore source exists for the local root and has been verified to contain current content - a Git repository with a clean-enough status, or a tested file-level backup. An untested backup is not a restore source.
- [ ] The intended direction of change is written down in one sentence ("remote is authoritative, local is a fresh empty replica").
- [ ] No other writer is active against the root (see below).
- [ ] For continuous operation only: the supervisor that already exists on this host is identified by name, and its authority to add or change a process is confirmed.

Missing prerequisites are a stop, not a risk to absorb. Report which one is missing.

## Effects require individual authorization

`ob` mixes read-only local inspection with account-wide network writes and irreversible local deletion in one small command set. Treat each class separately; authorization for one never implies another.

| Class | Commands | Needs |
|---|---|---|
| Local read | `ob --version`, `ob --help`, `ob sync-list-local`, `ob sync-status` | Nothing beyond the task. Safe to run first. |
| Network read | `ob sync-list-remote`, `ob login` with no arguments (status only) | Explicit approval to contact the service with the stored token. |
| Credential write | `ob login` with credentials, `ob logout` | Explicit approval, interactive terminal, per invocation. `logout` clears the token for every vault on the host. |
| Remote create | `ob sync-create-remote` | Explicit approval naming the vault; it adds a vault to the account and may affect the subscription. |
| Pairing write | `ob sync-setup` | Explicit approval naming root **and** remote ID. Overwrites any existing config for that vault ID, including its mode and conflict strategy. |
| Config write | `ob sync-config` | Explicit approval naming the exact setting and value. |
| Vault mutation | `ob sync`, `ob sync --continuous` | Explicit approval naming the root, the mode, and whether continuous. This is the command that can delete notes. |
| Credential deletion | `ob sync-unlink` | Explicit approval naming the exact path. Recursively removes that vault's stored config, sync state, and log with no undo. |
| Daemon lifecycle | supervisor start/stop/restart/delete | Explicit approval per action, naming the registered process. |

A restart is not a reconfiguration, and a reconfiguration is not a restart. Do not bundle them.

The `publish-*` family shares the binary and the login but is a different product surface with its own effects. It is out of scope here; do not run it to satisfy a sync request.

## Desktop versus headless, and the one-writer rule

| | Obsidian desktop app | `ob` headless client |
|---|---|---|
| Needs a GUI session | Yes | No |
| Sync settings surface | GUI panel | `ob sync-config` only |
| Version history / restore UI | Yes | No such command exists |
| Selective per-folder GUI choices | Yes | `--excluded-folders`, `--file-types`, `--configs` |
| Suitable for a headless server | No | Yes |

Choose exactly one sync writer per vault directory at a time. Two writers produce interleaved uploads, spurious conflicts, and deletions that neither side can explain.

`ob sync` takes a lock at `<vault-root>/<config-dir>/.sync.lock` (a directory, mtime-refreshed about every second, considered stale after 5 seconds). A second `ob sync` against the same root exits 1 with `Another sync instance is already running for this vault.` and is safely blocked. Understand its limits:

- It arbitrates **between `ob sync` processes only**. Do not treat it as protection against the desktop app, a file-sync tool, an editor plugin, or a backup job writing into the same directory.
- After a hard kill (`SIGKILL`, power loss) the lock directory remains until it goes stale, then the next run reclaims it automatically. Do not delete `.sync.lock` by hand to "unstick" a vault; a live lock means a live writer you have not found yet.
- The lock lives inside the vault but is excluded from config syncing, so it is not propagated.

Before any run: confirm no desktop app has this root open, and no supervisor process is already running `ob sync` against it.

## Workflow

### Phase 0 - Baseline, with no network and no pairing

Capture what "before" looks like, from the local side only.

```bash
ob sync-list-local
ob sync-status --path "$OBSIDIAN_VAULT_PATH"
find "$OBSIDIAN_VAULT_PATH" -name '*.md' -not -path '*/.git/*' | wc -l
git -C "$OBSIDIAN_VAULT_PATH" status --short
git -C "$OBSIDIAN_VAULT_PATH" rev-parse HEAD
```

Read the results as identity evidence:

- `No vaults configured.` or `No sync configuration found for <path>` (exit 3) - this root is unpaired. A first pairing, not a repair.
- A config comes back with a *different* `Location:` than your resolved root - you have a path-spelling mismatch or a second pairing. Resolve which is intended before touching either.
- `Not logged in.` printed above the configuration - the stored config is intact but no token is present. That is a credential gap, not a broken pairing.

Create the named restore point on every affected root, and record its name:

```bash
git -C "$OBSIDIAN_VAULT_PATH" tag "presync-$(date -u +%Y%m%dT%H%M%SZ)"
git -C "$OBSIDIAN_VAULT_PATH" tag --list 'presync-*' --sort=-creatordate
```

Do not stage, commit, or clean unrelated working-tree changes to make the snapshot look tidy. If the tree is dirty, the dirt is user work; record it in the baseline and leave it alone. A tag over a dirty tree does not capture uncommitted content - say so explicitly rather than treating the tag as a full restore point.

### Phase 1 - Pair in isolation

"Isolated" means: one root, one remote ID, nothing else running, and no sync executed yet.

1. Confirm the remote exists (network read, authorized separately):

   ```bash
   ob sync-list-remote
   ```

   Record the exact ID of the intended vault. If the expected vault is absent, stop - do not pair against a similar name and do not create a replacement vault to make the error go away.

2. Pair the exact root to the exact ID, in a real terminal:

   ```bash
   ob sync-setup \
     --vault "<remote-vault-id>" \
     --path "$OBSIDIAN_VAULT_PATH" \
     --device-name "example-replica-01"
   ```

   End-to-end encrypted vaults prompt for the encryption password. That prompt needs a TTY: piping, `< /dev/null`, `--json`, or a non-interactive `ssh host 'ob sync-setup ...'` cannot answer it and fails with `Password not provided.` or `Failed to validate password.` (exit 2). Never put the passphrase in the command line, a script, an environment file, or a supervisor definition.

   If the local root already contains notes, setup prints a merge warning and continues - there is no confirmation prompt. That warning is the moment to stop and reconsider if the root was not supposed to contain content.

3. **Immediately set the download-only mode, before any sync run:**

   ```bash
   ob sync-config --path "$OBSIDIAN_VAULT_PATH" --mode pull-only
   ob sync-status --path "$OBSIDIAN_VAULT_PATH"
   ```

   This step is mandatory, not a precaution. A fresh pairing is `bidirectional`; running `ob sync` between step 2 and step 3 uploads local state to the remote.

4. Verify the pairing describes what you intended - `Vault:` is the intended name and ID, `Location:` is the resolved root character for character, `Sync mode:` is `pull-only`, `Device name:` is the label you chose.

If step 4 disagrees with intent, fix the configuration or stop. Do not proceed hoping the run will clarify it.

### Phase 2 - One bounded pull-only run

```bash
set -o pipefail
ob sync --path "$OBSIDIAN_VAULT_PATH" 2>&1 | tee "${TMPDIR:-/tmp}/ob-first-run.log"
printf 'exit=%s\n' "$?"
```

Never add `--continuous` here. The one-shot run in a download-only mode ends by itself after it reports `Fully synced`; continuous mode would keep applying changes while you are still deciding whether the first batch was correct.

`pull-only` downloads remote changes, keeps local-only files, and **applies remote deletions locally**. If the remote lost content before you paired, this run removes it here too. That is why Phase 0 is not optional.

### Phase 3 - Compare before believing

Compare against the Phase 0 baseline, not against expectations.

```bash
find "$OBSIDIAN_VAULT_PATH" -name '*.md' -not -path '*/.git/*' | wc -l
git -C "$OBSIDIAN_VAULT_PATH" status --short
git -C "$OBSIDIAN_VAULT_PATH" diff --stat "<presync-tag>" --
ob sync-status --path "$OBSIDIAN_VAULT_PATH"
```

Accept only when all of these hold:

- The run log ends with `Fully synced` and contains no repeated transport or authentication errors.
- Every `Deleting` line in the log corresponds to a deletion you can explain from the remote side.
- The file-count delta and `git status` shape match the direction you authorized: for a fresh replica, additions; for an established vault, a small explainable set.
- No `Renaming conflicted file`, `Merge failed.`, or `Rejected server change` lines are unexplained.
- At least one representative changed file opens and contains the content you expected - not just a plausible filename.
- `sync-status` still reports the intended vault, root, and `pull-only`.

Any unexplained result ends the workflow and moves to [references/recovery.md](references/recovery.md). Do not try `bidirectional`, `mirror-remote`, re-pairing, or a second run to see whether the anomaly resolves itself; each of those destroys the evidence that would explain it.

### Phase 4 - Promote only on request

Promotion is a separate authorization with its own named effect: local edits start leaving this machine.

```bash
ob sync-config --path "$OBSIDIAN_VAULT_PATH" --mode bidirectional
ob sync --path "$OBSIDIAN_VAULT_PATH"
```

Re-run Phase 3 against the new baseline. Only after a second clean one-shot run does continuous operation become a candidate - see [references/daemon.md](references/daemon.md).

A pull-only run proves nothing about the upload direction. If a round-trip must actually be demonstrated, that requires separate authority for a specific note and a specific reversible change, plus readback on both machines. Without that authority, report the upload direction as unverified rather than inferring it.

`mirror-remote` is never part of this workflow. It reverts local-only additions and overwrites locally modified files with the remote copy. It is a deliberate "discard this machine's work" operation requiring its own approval and its own tested restore point - never a conflict-resolution shortcut and never a repair step.

## Conflict preservation

Conflicts are data. The default strategy silently rewrites files; the alternative keeps both sides.

| `conflictStrategy` | Behavior | Evidence in the run output |
|---|---|---|
| `merge` (default) | Merges the two versions of a Markdown or JSON file in place. Most-recent content wins where the merge cannot reconcile. | `Merging conflicted file`, then `Merge successful` or `Merge failed.` |
| `conflict` | Writes the local version beside the original as `<name> (Conflicted copy <device-name> <YYYYMMDDHHMM>).<ext>` and puts the remote version at the original path, preserving both. | `Merging conflicted file`, then `Conflicted copy stored` |

Rules:

- When a task's notes must not be silently rewritten, set `--conflict-strategy conflict` **before** the run that could conflict, not after. It changes future behavior only.
- `Merge failed.` means the reconciliation did not complete. Treat it as an incident signal, not a transient log line.
- Never delete or "clean up" `(Conflicted copy ...)` files as housekeeping. They are the only surviving copy of one side. Surface them to the user, with paths, and let the user decide.
- A conflicted copy is a regular note in the vault: it will itself sync. Resolve it where you found it rather than moving it out to a temporary location.
- The strategy does not apply to first contact. While a pairing is still in its initial state, the newer modification time wins outright and no conflicted copy is written - which is what the setup warning means by "the most recent version of the note will be preserved". Only the Phase 0 restore point protects the first run; see [references/commands.md](references/commands.md#conflict-mechanics).
- `ob sync-setup` resets the strategy to `merge`. Any re-pairing silently discards a `conflict` choice - re-apply it in the same phase.

## Partial network failure

Continuous mode reconnects on its own with exponential backoff (jittered, starting around 5 seconds, capped at 5 minutes). A run that logs `Waiting to connect to server` or `Disconnected from server` and later resumes is behaving correctly; do not restart it to speed that up.

Distinguish three outcomes of an interrupted run:

- **Interrupted transport, consistent vault** - the log shows reconnection and eventually `Fully synced`. No action. File-level retries are tracked internally.
- **Interrupted transport, partial application** - a one-shot run exited non-zero, or was killed, after some `Downloading`/`Deleting` lines. The vault is now in an intermediate state that is neither the baseline nor the target. Do not "finish" it with a different mode. Re-run the same command in the same mode, then compare against the Phase 0 baseline exactly as in Phase 3.
- **Not a transport problem at all** - `The connected remote vault no longer exists.`, `Your subscription to Obsidian Sync has expired`, or a password/token error. These stop the client deliberately. Retrying cannot fix them and a retry loop only replays the failure; go to [references/recovery.md](references/recovery.md).

Never resolve a network failure by unlinking, re-pairing, or switching modes. Those are vault-state changes being used to treat a connectivity symptom.

## Secrets

- The account token lives either in the `OBSIDIAN_AUTH_TOKEN` environment variable (checked first) or in the client's private config directory, written owner-only. Pass it via the environment for unattended runs; never inline it in a command, a committed file, or a supervisor definition stored in a repository.
- The end-to-end encryption passphrase is **only** ever typed into an interactive prompt. `--password` exposes it to the process table and shell history; `--json` disables the prompt and forces that exposure. Use neither for setup.
- `ob sync` tees its console output to the per-vault `sync.log`. It does not print the token, the encryption key, or the salt - but it does record the vault name, vault ID, absolute root, and device name. Redact those before sharing a log.
- Never copy, print, or commit the token file, `config.json`, or `state.db`. `config.json` contains the derived encryption key and salt. When a copy is needed for recovery, keep it outside the vault, owner-readable only, and delete it when the incident closes.
- Never record a token, passphrase, key, or salt in an evidence report, changelog, issue, or commit message.

## Composition and boundaries

This package is self-contained and owns headless `ob` operation: identity resolution, pairing, mode policy, run evidence, daemon lifecycle, and sync incident recovery.

It does not own note content, Markdown syntax, where a note belongs, or permission to edit a note. Sync access is transport authority, never content authority.

- For desktop-app concerns - GUI Sync settings, Sync version history and restore, reading or writing a note through the running app - an official-CLI skill for the `obsidian` binary is the right owner, and only for those concerns. It is optional: not installed is the normal case, and installed-but-not-selected stays unused. Compose it by explicit identity when the task needs a desktop-side action; never treat `ob` as a substitute for it, and never treat it as a substitute for `ob`.
- An optional vault-policy or second-brain toolchain participates only when the task explicitly selects it. Its absence is normal and is never a degraded state, and it never grants the write authority this package lacks.
- A composed skill does not re-specify the commands documented here, and no composition converts a usable tool into permission to change a vault.

Out of scope: Obsidian Publish, GUI settings, third-party CLIs with similar names, raw filesystem edits inside a vault, note authoring, and filing decisions.

## References

- [references/commands.md](references/commands.md) - exact command surface, flag defaults, mode semantics, exit codes, error strings, on-disk layout, run-output vocabulary, version gate.
- [references/daemon.md](references/daemon.md) - supervision preconditions, start, graceful stop, restart scope, log growth, health evidence, crash-loop containment.
- [references/recovery.md](references/recovery.md) - containment, classification, exact-version restore of configuration and client, safe re-admission, evidence receipt.

## Verification

- [ ] `node --version` and `ob --version` were read, and every flag used appeared in that build's `--help`.
- [ ] The local root was resolved on the acting host with `pwd -P`; no path was copied from another machine.
- [ ] The remote vault was identified by ID, confirmed present in `sync-list-remote`, and never substituted by a similar name.
- [ ] A named restore point existed before the first run, and its coverage of uncommitted content was stated.
- [ ] `pull-only` was set after pairing and confirmed by `sync-status` before the first `ob sync`.
- [ ] The first run was one-shot; `--continuous` appeared only after two clean one-shot runs.
- [ ] Every `Deleting` and `Reverting` line in the run output was explained, not assumed benign.
- [ ] File count, `git status`, `git diff --stat` against the tag, and a representative file's content were all compared to the Phase 0 baseline.
- [ ] Only one sync writer touched the root; no desktop app and no second `ob sync`.
- [ ] `(Conflicted copy ...)` files were reported with paths and left in place.
- [ ] No passphrase was passed as an argument; no token, key, or salt appears in any output kept as evidence.
- [ ] Network, pairing, config, sync, unlink, and daemon effects each had their own authorization, and unauthorized ones were reported as not performed.
- [ ] Anything not observed - upload direction after a pull-only run, remote backup content, another host's state - was reported as unverified rather than inferred.

## Attribution

Original work for this repository, written against the installed `obsidian-headless` 0.0.14 command help, its bundled README, and its observable behavior. No text was carried over from any third-party skill; the consulted source tree published no license notice, so it was used only to scope which failure modes an operator needs covered. Released under its bundled [LICENSE](LICENSE). See [CHANGELOG.md](CHANGELOG.md) for what was verified and what was not.
