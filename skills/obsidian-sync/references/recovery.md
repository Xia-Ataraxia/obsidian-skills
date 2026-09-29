# Sync incident recovery

Enter here when a sync run did something nobody authorized: an unexplained deletion set, notes reverted, `Merge failed.` on content that matters, a crash loop, `The connected remote vault no longer exists.`, or a pairing that points somewhere other than what the task intended.

The order is fixed: **contain, preserve, classify, restore exactly, re-admit, record.** Skipping straight to a fix is what turns one lost batch into two.

Diagnosing an incident authorizes nothing. Restoring notes, unlinking a pairing, reinstalling the client, changing account state, or touching a separate backup mechanism each need their own explicit authority for the exact effect. Where that authority is missing, name the proposed effect, state that it was not performed, and stop.

## 1. Contain

Stop every writer against the affected root before forming a theory.

- Stop the supervised `ob sync --continuous` with `SIGTERM` and confirm the process is gone.
- Stop any one-shot `ob sync`.
- Close the Obsidian desktop app if it has the same root open.
- Stop any file-sync client or backup job that writes into the root.

Then stop. While the scope is unknown, do **not**:

- re-run `ob sync` "to see if it settles",
- switch modes - especially not to `mirror-remote`,
- run `ob sync-setup` again,
- run `ob sync-unlink`,
- delete `.sync.lock`,
- run `git reset`, `git checkout .`, `git clean`, or any bulk overwrite,
- delete `(Conflicted copy ...)` files.

Every one of those destroys the evidence that would have explained the incident, and several of them cause a second, larger one. A lock that is not stale means a live writer you have not found yet; find it instead of removing the lock.

## 2. Preserve evidence

Capture before anything changes. All of these are local reads.

```bash
: "${OBSIDIAN_VAULT_PATH:?resolve the local root on this host with pwd -P}"
: "${OB_VAULT_ID:?record the vault ID printed by ob sync-list-local}"

OB_HOME="$HOME/.obsidian-headless"                                    # macOS, Windows
[ -d "$OB_HOME" ] || OB_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/obsidian-headless"   # Linux

cp "$OB_HOME/sync/$OB_VAULT_ID/sync.log" "${TMPDIR:-/tmp}/ob-incident-sync.log"
ob sync-list-local
ob sync-status --path "$OBSIDIAN_VAULT_PATH" --json > "${TMPDIR:-/tmp}/ob-incident-config.json"
git -C "$OBSIDIAN_VAULT_PATH" status --short      > "${TMPDIR:-/tmp}/ob-incident-status.txt"
git -C "$OBSIDIAN_VAULT_PATH" diff --binary --    > "${TMPDIR:-/tmp}/ob-incident.patch"
find "$OBSIDIAN_VAULT_PATH" -name '*.md' -not -path '*/.git/*' | wc -l
ob --version; node --version
```

Copying `sync.log` first is not optional. `ob sync-unlink` deletes the entire per-vault client directory - `config.json`, `state.db`, and `sync.log` together - so one unlink removes the only record of what was deleted and when.

The `--json` capture is the safe form of the configuration: it carries the vault ID, root, mode, conflict strategy, device name, config directory, file types, configs, and excluded folders, and it carries no host, key, salt, or token. Use it instead of copying `config.json`.

If that command exits 2 with `End-to-end encryption key missing. Run setup again.` - which is exactly the class that most needs a capture - use `ob sync-config --path "$OBSIDIAN_VAULT_PATH" --json` instead. With no other flags it is a read-only reader, it emits the same payload, and it does not check the encryption key.

Keep every artifact **outside the vault** and owner-readable only, and delete it when the incident closes. The damaged tree itself is evidence: preserve it, and do not treat it as a restore source.

Record the exact client version now. `ob --version` after a reinstall is a different fact from `ob --version` at the time of the incident.

## 3. Classify

Name the failure class before choosing a response. Look-alike symptoms have opposite correct answers.

| Class | Evidence | Response |
|---|---|---|
| Remote deletion propagated | `Deleting <path>` lines in the run log for content nobody deleted here; broad deletions in `git status` after a clean-looking run | Local restoration alone does not hold - see [the remote-safety rule](#remote-safety). Keep the replica offline until the remote is known safe. |
| Wrong local root | `sync-status` `Location:` differs from the intended root by case, a symlink, or a prefix; `sync-list-local` shows two pairings | Unlink only the verified-wrong pairing, then pair the exact root. Matching is lexical - see [commands.md](commands.md#global-behavior). |
| Wrong remote identity | `The connected remote vault no longer exists.`, or `sync-list-remote` does not contain the paired ID | Verify against `sync-list-remote`. Never pair against a similar name and never create a replacement vault to clear the error. |
| Mode was wrong | `Removing local-only file`, `Removing local-only folder`, or `Reverting` in the log - all three are `mirror-remote` only | The mode was `mirror-remote` when it should not have been. Content restore needs its own authority. |
| Concurrent writers | Interleaved uploads and deletions, unexplained conflicts, a desktop app or second client on the same root | Stop both, assess actual damage, then choose exactly one writer. Restore only if damage is real and authorized. |
| Conflict handling | `Merging conflicted file` / `Merge failed.` / `Conflicted copy stored` | Content, not corruption. Surface the paths and let the user decide. Never clean up conflicted copies. |
| Credentials or subscription | `Password not provided.`, `Failed to validate password.`, `No account logged in.`, `Your subscription to Obsidian Sync has expired` | Account state, not vault state. Repair interactively. No mode change, unlink, or restart fixes it. |
| Configuration damage | `Encryption key not found. Run setup again.`, `End-to-end encryption key missing.`, `Encryption version not supported` | The stored config is unusable. Follow [configuration restore](#restore-the-configuration-exactly); never hand-edit `config.json`. |
| Runtime or version skew | A flag rejected that this manual documents, a native-module failure, a binary-path error, crash loops with no vault mutation | Repair the runtime and the version. The vault is not the problem. |

`Deleting` appears in every mode, including `pull-only`. It is the propagation of a remote deletion, and it is the line most often misread as a local mistake.

## 4. Restore exactly

There are three independent restores. Do only the ones the incident actually requires, and keep them separate in the report.

### Restore the client version

Record the version that was running. If the client was upgraded, downgraded, or reinstalled between the last good run and the incident, put it back to the **exact** version that was running, not to "latest":

```bash
npm install -g "obsidian-headless@<exact-version-from-evidence>"
ob --version
```

Then re-run the [version gate](commands.md#version-gate) against that binary. A reinstall is a host change and needs its own authorization; without it, report the version mismatch and stop.

### Restore the configuration exactly

`ob sync-setup` does not repair a configuration - it replaces one. A fresh pairing writes `conflictStrategy: merge`, no stored mode (which means bidirectional), default attachment types, no excluded folders, and no config categories. Any policy the vault had is silently gone, and the next run uploads.

So a configuration restore is capture, re-pair, replay, verify:

1. **Capture** - already done in step 2, as `ob-incident-config.json`. That file holds every field a re-pair discards.
2. **Re-pair as narrowly as the damage requires.**
   - If the remote identity and the root are both correct and only the stored config is damaged, re-run `ob sync-setup` for the **same vault ID and the same resolved root**. This rewrites `config.json` and leaves `state.db` in place, so the client keeps knowing what it had already reconciled.
   - Run `ob sync-unlink` only when classification proved the pairing itself wrong. Unlinking deletes `state.db`, which makes the next run an **initial** reconciliation - and during initial reconciliation `conflictStrategy` is not consulted at all: the newer modification time simply wins and the older side is overwritten. On a damaged tree that is how a recoverable incident becomes an unrecoverable one.
3. **Set the download-only mode before anything else**, in the same phase as the pairing:

   ```bash
   ob sync-config --path "$OBSIDIAN_VAULT_PATH" --mode pull-only
   ```

4. **Replay the remaining fields** from the capture, one flag per recorded value:

   ```bash
   ob sync-config --path "$OBSIDIAN_VAULT_PATH" \
     --conflict-strategy "<conflictStrategy from capture>" \
     --device-name      "<deviceName from capture>" \
     --excluded-folders "<comma-joined excludedFolders, empty string when the capture lists none>" \
     --file-types       "<comma-joined fileTypes>" \
     --configs          "<comma-joined configs, empty string when the capture lists none>"
   ```

   Three things to expect. Replay makes previously implicit defaults explicit - the capture already resolved them, so the effective behavior matches even though the stored keys differ. Changing the scope flags queues every file that newly enters scope for download on the next run, so a scope replay is a scheduled transfer, not a passive setting. And an empty `--file-types` does not disable attachments - it clears the stored list back to the `image, audio, pdf, video` default, which is why a capture never reports an empty `fileTypes` and the replay always passes the recorded list.

   `--config-dir` is replayed only if the capture shows a non-default value.

5. **Verify against the capture**, field by field:

   ```bash
   ob sync-status --path "$OBSIDIAN_VAULT_PATH" --json
   ```

   Every field except `syncMode` must equal the captured value; `syncMode` must read `pull-only`. A mismatch stops the recovery - do not proceed hoping a run will clarify it.

Never hand-edit `config.json` to emulate a flag, and never copy it between hosts. It holds the derived encryption key and salt in cleartext, and `vaultPath` is host-specific. If the incident genuinely requires reading `encryptionVersion` - the one field no command prints - open the file under incident authority, read only that value, and do not copy, print, or commit the file.

### Restore notes - only with authority for the exact content

Note content is user work. Restoring it is a separate authorization naming the exact paths and the exact revision, and it is not implied by permission to repair sync.

The method is additive and path-scoped:

```bash
git -C "$OBSIDIAN_VAULT_PATH" tag --list 'presync-*' --sort=-creatordate
git -C "$OBSIDIAN_VAULT_PATH" diff --stat "<presync-tag>" --
git -C "$OBSIDIAN_VAULT_PATH" restore --source "<presync-tag>" -- "<exact/path/one.md>" "<exact/path/two.md>"
```

Hard rules:

- Restore the **named paths** the incident lost. Never `git reset --hard`, never `git checkout <tag> -- .`, never a whole-tree replacement.
- Never restore by running a sync in `mirror-remote`. That is a deletion tool wearing a restore label: it removes local-only files and overwrites locally modified ones.
- Never delete, move, or rename `(Conflicted copy ...)` files as part of a restore. Each one is the only surviving copy of one side.
- Preserve unrelated working-tree changes. A dirty tree at baseline is user work, and a tag taken over a dirty tree never captured it - say so instead of implying full coverage.
- Verify by reading content back, not by counting files: open a representative restored note and confirm it holds what it should.

If no verified restore source exists, say so. An untested backup is not a restore source, and a tag over uncommitted content is not full coverage.

### Remote safety

Local restoration is not durable while the remote still carries the deletion. A download-only run applies remote deletions locally, so restoring notes and then re-admitting sync against an unchanged remote replays exactly the loss you just repaired.

Before re-admission, establish which side is authoritative for the affected paths and confirm the remote no longer reports them deleted. Until that holds, the replica stays offline. Do not resolve this by uploading from a damaged tree either - that propagates the damage.

## 5. Re-admit sync

Re-admission repeats the staged workflow in [`../SKILL.md`](../SKILL.md). It is not a shortcut back to where things were.

1. Confirm the intended remote exists and matches the recorded ID (`ob sync-list-remote`).
2. Confirm the remote is safe for the affected paths.
3. Confirm exactly one writer will touch the root.
4. Create a **new** named restore point over the post-recovery tree, and record whether it covers uncommitted content.
5. Confirm `sync-status` reports the intended vault, the resolved root, and `pull-only`.
6. Run **one** bounded one-shot sync and capture the log:

   ```bash
   set -o pipefail
   ob sync --path "$OBSIDIAN_VAULT_PATH" 2>&1 | tee "${TMPDIR:-/tmp}/ob-recovery-run.log"
   printf 'exit=%s\n' "$?"
   ```

7. Compare against the post-recovery baseline: file count, `git status`, `git diff --stat` against the new tag, and a representative file opened and read. Every `Deleting` line must be explainable from the remote side.
8. Stop on anything unexplained and return to step 1 of this file. Do not try a different mode to see whether it resolves itself.
9. Promote the mode only on explicit request, and only after this run is accepted.
10. Re-enable the daemon only after a second clean one-shot run - see [daemon.md](daemon.md).

## 6. Evidence receipt

Close the incident with a record that a later reader can act on.

- Affected hosts, vault IDs, and resolved roots.
- First observed symptom, and the **earliest** relevant error line with its timestamp - not the newest.
- Client and Node versions at the time of the incident, and after any reinstall.
- Process and client state at containment: what was running, what was stopped, in what order.
- The classification from step 3, and the evidence that selected it.
- Which of the three restores were performed, and which were not and why.
- For a configuration restore: the captured configuration and the verified post-restore configuration, field by field.
- For a note restore: the exact paths, the exact source revision, and the readback result for each.
- Baseline comparison before and after: file count, `git status` shape, diff against the named tag.
- The one-shot re-admission result, and the daemon state if it was resumed.
- Every unverified claim named as unverified - upload direction, remote backup contents, another host's state, anything not observed.
- Paths of the preserved artifacts, and confirmation that they were removed when the incident closed.

Never record a token, passphrase, encryption key, or salt in a receipt, a changelog, an issue, or a commit message. Redact the vault name, vault ID, absolute root, and device name before sharing a log.
