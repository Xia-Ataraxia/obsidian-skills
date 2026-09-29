# `ob` command surface

The manual for `obsidian-headless` **0.0.14**. [`../SKILL.md`](../SKILL.md) owns the workflow and the authorization boundary; this file owns what each command actually accepts, what it writes, what it prints, and how it fails.

Everything here is checkable on the acting host without an account, without network access, and without a pairing: `--help` output, the package's bundled README, the bundled `cli.js`, and error paths that a non-vault directory triggers. Nothing here depends on a remote vault existing.

`--help` on the installed build outranks this file. When the two disagree, the build is right and the task stops - see [Version gate](#version-gate).

## Version gate

Run this before the first command that changes anything. It fails closed: a missing flag or flag value is version skew, not a naming detail to work around.

```bash
#!/usr/bin/env bash
# Read-only. No account, no network, no pairing.
set -euo pipefail

node_version=$(node --version)
node_major=${node_version#v}; node_major=${node_major%%.*}
[ "$node_major" -ge 22 ] || { printf 'gate: node %s is older than v22\n' "$node_version" >&2; exit 1; }

ob_version=$(ob --version)
printf 'gate: ob %s on node %s\n' "$ob_version" "$node_version"

gate() {                               # gate <subcommand> <literal>...
  local sub=$1 help literal rc=0
  shift
  help=$(ob "$sub" --help) || { printf 'gate: no help for %s\n' "$sub" >&2; return 1; }
  for literal in "$@"; do
    case $help in
      *"$literal"*) ;;
      *) printf 'gate: %s --help does not mention %s\n' "$sub" "$literal" >&2; rc=1 ;;
    esac
  done
  return "$rc"
}

gate sync-list-local  --json
gate sync-list-remote --json
gate sync-status      --path --json
gate sync-unlink      --path
gate sync             --path --continuous
gate sync-setup       --vault --path --password --device-name --config-dir --json
gate sync-config      --path --config-dir --json --device-name \
                      --mode bidirectional pull-only mirror-remote \
                      --conflict-strategy merge conflict \
                      --excluded-folders --file-types --configs

printf 'gate: ok\n'
```

Record `ob --version` and `node --version` in the task evidence. A gate failure is reported as version skew with the exact subcommand and literal that was missing; it is never resolved by guessing a replacement flag, by hand-editing `config.json`, or by installing a different version mid-task.

## Reach: which commands leave the machine

Authorize by class, not by command name. The left column needs nothing but a local filesystem read; the right column needs a stored token and a live connection.

| Local only - no token, no network | Account and network |
|---|---|
| `sync-list-local` | `login`, `logout` |
| `sync-status` | `sync-list-remote` |
| `sync-config` | `sync-create-remote` |
| `sync-unlink` | `sync-setup` |
| | `sync` |
| | `publish-*` |

`sync-status` reads the token only to decide whether to print `Not logged in.`; it never validates it against the service. `sync-unlink` is local but destructive - see its entry below.

Commands that need a token and find none stop with `No account logged in. Run "ob login" first.` and exit 2, before any network call.

## Global behavior

**`--path` matching is lexical.** The value (default: the current working directory) is passed through `path.resolve`, and every stored `config.json` is re-resolved the same way and compared as a string. The first configured vault whose resolved `vaultPath` matches wins.

- `.`, `..`, and trailing slashes normalize away - they are safe.
- Letter case does not normalize. On a case-insensitive filesystem, `/srv/Vaults/example` and `/srv/vaults/example` are the same directory and two different vaults to `ob`.
- Symlinks do not resolve. `path.resolve` is purely textual, so a symlinked parent, or `/tmp/x` where the config stored `/private/tmp/x`, is a different vault.
- The failure is `No sync configuration found for <resolved-path>` with exit 3, never a warning and never a fallback to a near match.

Resolve the root once per host with `pwd -P` and reuse the variable. Never copy an absolute path between machines.

**`--json`** is accepted by `sync-list-remote`, `sync-list-local`, `sync-setup`, `sync-config`, `sync-status`, and the publish family. It is **not** accepted by `login`, `logout`, `sync-create-remote`, `sync-unlink`, or `sync`. In JSON mode the client suppresses progress messages, writes errors to stderr with a non-zero exit, and **disables every interactive prompt** - which is why it must not be used for `sync-setup` on an end-to-end encrypted vault.

The JSON configuration payload is redacted by construction. It carries `vaultId`, `vaultName`, `vaultPath`, `syncMode`, `conflictStrategy`, `deviceName`, `configDir`, `fileTypes`, `configs`, and `excludedFolders`, with defaults already resolved. It never carries the host, the encryption key, the salt, or the token. That makes `ob sync-status --path "$ROOT" --json` the correct way to capture a configuration for evidence.

**Token resolution** checks `OBSIDIAN_AUTH_TOKEN` first and falls back to the token file. The environment variable is the mechanism for unattended runs; the passphrase has no equivalent and is never supplied non-interactively.

## Command reference

### `ob login` / `ob logout`

```
ob login [--email <email>] [--password <password>] [--mfa <code>]
ob logout
```

With a valid stored token and no `--email`/`--password`, `login` only reports status as `Logged in as <name> (<email>)`. Supplying either credential flag discards the stored token first and performs a real login. Two-factor is prompted on demand; an incorrect code is not re-prompted. Failure prints `Login failed:` and exits **2**.

`logout` revokes and deletes the stored token. With no token it prints `No account logged in.` and exits 0.

Credential flags put secrets in the process table and shell history. Prompt instead.

### `ob sync-list-remote`

```
ob sync-list-remote [--json]
```

Network read. Prints `Fetching vaults...`, then:

```
Vaults:
  <vault-id>  "<vault-name>"  (<region>)

Shared vaults:
  <vault-id>  "<vault-name>"  (<region>)
```

Empty account: `No vaults found.`, exit 0. Failure: `Failed to list vaults:` plus the error, exit 1.

Own and shared vaults are listed separately but are selectable by the same `--vault` value. Record the **ID**; a name is a mutable, duplicable display label.

### `ob sync-list-local`

```
ob sync-list-local [--json]
```

Pure filesystem read of the client's private config directory - no token, no network. Safe as the first command of any diagnosis.

```
Configured vaults:
  <vault-id>
    Path: <absolute-local-root>
    Host: <sync-host>
```

No configuration at all: `No vaults configured.`, exit 0. This is identity evidence: it enumerates every pairing this account's client knows on this host, which is how a second pairing against a differently-spelled path is discovered.

### `ob sync-create-remote`

```
ob sync-create-remote --name <name> [--encryption <standard|end-to-end>]
                      [--password <passphrase>] [--region <region>]
```

Creates a new remote vault. `--name` is required. Unless `--encryption standard` is passed, the command prompts for an end-to-end passphrase and treats an empty answer as standard encryption. An unknown `--region` prints `Invalid region: "<region>". Available regions:` with the valid values and exits 1.

This is a remote mutation on the account, not a sync operation. It is never the right response to `Vault "<name>" not found.` - that error means the identity was wrong, and creating a replacement hides the mistake.

### `ob sync-setup`

```
ob sync-setup --vault <id-or-name> [--path <local-path>] [--password <passphrase>]
              [--device-name <name>] [--config-dir <name>] [--json]
```

Pairs one resolved local root to one remote vault and writes `config.json`. `--vault` is required; omitting it is a usage error (`error: required option '--vault <vault>' not specified`, exit 1) raised before any network call.

Selection order: exact **ID** match across own and shared vaults first; only if no ID matches is an exact **name** compared.

| Outcome | Output | Exit |
|---|---|---|
| Exactly one match | proceeds | - |
| Several vaults share the name | `Multiple vaults named "<name>". Use the vault ID instead:` followed by each `  <id>  "<name>"` | 1 |
| No match | `Vault "<name>" not found.` | 3 |

The passphrase prompt (`End-to-end encryption password: `) needs a real TTY. Piping, `< /dev/null`, `--json`, and a non-interactive `ssh host 'ob sync-setup ...'` all fail it: no password reaches the client and it stops with `Password not provided.` (exit 2). A wrong passphrase fails validation against the service with `Failed to validate password.` (exit 2). Never pass `--password`.

If the local root already contains any non-dot entry, setup prints a warning and continues - there is no confirmation prompt:

```
Warning: Your local vault already contains some notes.
If you start syncing, notes in your local vault will be merged with notes from your remote vault.
In case of conflicts, the most recent version of the note will be preserved.
```

That last line is literally true and is the reason first contact is staged in `pull-only` - see [Conflict mechanics](#conflict-mechanics). If the root does not exist, setup creates it.

`--config-dir` must be a dotfolder name with no path separator, or setup fails with `Invalid config directory: "<name>". Must be a dotfolder name (e.g. .obsidian).`

**Setup writes a fresh policy.** The config it writes contains `vaultId`, `vaultName`, `vaultPath`, `host`, `encryptionVersion`, `encryptionKey`, `encryptionSalt`, `conflictStrategy: "merge"`, `deviceName`, and `configDir`. It writes no `syncMode`, no `allowTypes`, no `allowSpecialFiles`, and no `ignoreFolders`. Every earlier `sync-config` choice is gone: the pairing is now bidirectional with merge conflicts and default attachment types. Re-apply the intended policy in the same phase, before any `ob sync`.

Re-running setup for a vault ID that is already configured overwrites `config.json` but leaves `state.db` in place. `sync-unlink` followed by `sync-setup` removes the state database as well, so the next run re-reconciles from scratch as an initial sync.

### `ob sync-config`

```
ob sync-config [--path <local-path>] [--mode <mode>] [--conflict-strategy <strategy>]
               [--excluded-folders <folders>] [--file-types <types>] [--configs <settings>]
               [--device-name <name>] [--config-dir <name>] [--json]
```

With no options it is a **reader**: `No options provided. Current configuration:` followed by the same block `sync-status` prints. With options it applies them and prints `Configuration updated:`.

| Option | Accepted values | Cleared by | Effective default |
|---|---|---|---|
| `--mode` | `bidirectional`, `pull-only`, `mirror-remote` | - | `bidirectional` |
| `--conflict-strategy` | `merge`, `conflict` | - | `merge` (written at setup) |
| `--excluded-folders` | comma-separated vault-relative paths | `""` | none |
| `--file-types` | `image`, `audio`, `video`, `pdf`, `unsupported` | `""` | `image, audio, pdf, video` |
| `--configs` | `app`, `appearance`, `appearance-data`, `hotkey`, `core-plugin`, `core-plugin-data`, `community-plugin`, `community-plugin-data` | `""` | none - config syncing disabled |
| `--device-name` | any string | - | `<hostname> (macOS\|Windows\|Linux)` |
| `--config-dir` | dotfolder name | - | `.obsidian` |

Validation is strict and happens before the write:

- `Invalid sync mode: "<value>". Must be "bidirectional", "pull-only", or "mirror-remote".` - exit 1
- `Invalid conflict strategy: "<value>". Must be "merge" or "conflict".` - exit 1
- `Config update failed: Error: Invalid file type: "<value>". Valid values: image, audio, video, pdf, unsupported` - exit 1
- `Config update failed: Error: Invalid config: "<value>". Valid values: app, appearance, appearance-data, hotkey, core-plugin, core-plugin-data, community-plugin, community-plugin-data` - exit 1

Two behaviors are not visible in `--help`:

- `--mode bidirectional` does not store the word `bidirectional`; it **removes** the stored mode. Absence of `syncMode` is what "bidirectional" means on disk, so a config with no mode key is an armed uploader, not an unconfigured one.
- Changing `--excluded-folders`, `--file-types`, or `--configs` recomputes the scope against the state database and **queues every file that newly enters scope** for download on the next run. Widening scope is therefore a scheduled transfer, not a passive setting.

`--config-dir` changes only this client's idea of which in-vault folder holds app configuration. It does not move or create anything.

### `ob sync-status`

```
ob sync-status [--path <local-path>] [--json]
```

Local read. Prints `Not logged in.` first when no token is present - that is a credential gap, not a broken pairing - then:

```
Sync Configuration:
  Vault: <vault-name> (<vault-id>)
  Location: <absolute-local-root>
  Sync mode: <bidirectional|pull-only|mirror-remote>
  Conflict strategy: <merge|conflict>
  Device name: <device-name>
  Config directory: <name>          # only when --config-dir was set
  File types: image, audio, pdf, video
  Configs: none (config syncing disabled)
  Excluded folders: <a, b>          # only when non-empty
```

`Location:` must match the resolved root character for character, and `Vault:` must carry the intended ID. Failures: `No sync configuration found for <path>` (exit 3); `End-to-end encryption key missing. Run setup again.` (exit 2).

This command reports **stored configuration only**. It does not contact the service, does not report queue depth, last-success time, or drift, and a healthy block is not evidence that the last run worked.

### `ob sync-unlink`

```
ob sync-unlink [--path <local-path>]
```

Local and destructive to client state. It deletes the entire per-vault directory - `config.json`, `state.db`, **and `sync.log`** - then prints `Sync configuration removed for <path>`. Notes in the vault are untouched.

Copy `sync.log` out of that directory before unlinking anything. Unlinking during an incident destroys the only run record that explains what was deleted.

Unlink exactly the verified-wrong pairing, identified by `sync-list-local`, and never as a remedy for a transport error or a failed login.

### `ob sync`

```
ob sync [--path <local-path>] [--continuous]
```

Preconditions checked in order: a config for the resolved path (`No sync configuration found for <path>` / `Run 'ob sync-setup' first.`, exit 3), a stored token (exit 2), a usable encryption key (`Encryption key not found. Run setup again.`, exit 2), and the vault lock.

The run announces itself with `Starting sync:` and the same configuration block as `sync-status`. Read it: it is the last chance to catch a wrong mode before changes land.

**Lock.** `ob sync` creates a lock **directory** at `<vault-root>/<config-dir>/.sync.lock`, refreshes its mtime once a second, and treats a lock older than 5 seconds as stale and reclaimable. A second `ob sync` against the same root exits 1 with `Another sync instance is already running for this vault.`; a graceful exit removes the directory. After `SIGKILL` or power loss the directory survives until it goes stale and the next run reclaims it automatically - never delete it by hand, because a lock that is not stale means a live writer you have not found. The lock arbitrates between `ob sync` processes only; it does not see the desktop app, a file-sync tool, or a backup job. It sits under the config directory as a dot-entry, so it is never itself synced.

**Termination.** A one-shot run ends when reconciliation reports `Fully synced` and the client stops itself. It does **not** end because the network is down: an unreachable or failing server drops the client into a reconnect loop that retries roughly every 30 seconds and logs `Waiting to connect to server`, in one-shot mode exactly as in continuous mode. Bound one-shot runs with an external timeout rather than assuming the command returns.

`SIGINT` and `SIGTERM` are handled: the client prints `Received signal to shut down...`, disconnects, closes the state database, stops the watcher, and releases the lock.

**Reconnect.** Backoff is exponential from a 5-second base with 50% jitter, capped at 5 minutes, and reset on a successful connection. The socket is checked every 20 seconds: it pings after 10 seconds of silence and disconnects after 120 seconds of it. `Disconnected from server` followed by a later `Fully synced` is correct behavior, not an incident.

Two errors deliberately stop the client instead of retrying - `The connected remote vault no longer exists.` and `Your subscription to Obsidian Sync has expired`. Both surface as `Sync failed:` with exit 1. Retrying either only replays it.

### `publish-*`

`publish-list-sites`, `publish-create-site`, `publish-setup`, `publish`, `publish-config`, `publish-site-options`, `publish-unlink` share the binary and the login but target Obsidian Publish, with their own config directory and their own effects. Out of scope here. Never run one to satisfy a sync request.

## Mode semantics

The stored mode decides what reconciliation is allowed to do to the local root.

| Mode | Remote change arrives | Remote deletion | Local-only file | Locally modified file | Local edits upload |
|---|---|---|---|---|---|
| `bidirectional` | downloaded | applied locally | kept and uploaded | merged or conflict-copied | yes |
| `pull-only` | downloaded | **applied locally** | kept, never uploaded | overwritten by the remote copy | no |
| `mirror-remote` | downloaded | **applied locally** | **deleted** | **reverted to the remote copy** | no |

Neither download-only mode is read-only. `pull-only` is the safe staging mode because it preserves local-only files and uploads nothing - not because it cannot delete.

`mirror-remote` is a deliberate "discard this machine's work" operation. It needs its own approval and its own tested restore point, and it is never a conflict-resolution shortcut or a repair step.

## Conflict mechanics

Reconciliation only reaches the merge path for a **Markdown** file that exists on both sides with differing content, in a mode that uploads. Canvas, Bases, attachments, and configuration JSON never produce conflicted copies.

| `conflictStrategy` | What happens | Log lines |
|---|---|---|
| `merge` (default) | Three-way merge against the last synced version, written in place. With no common base: the remote copy wins outright if the local file was created within the last 3 minutes, otherwise it wins only if its mtime is newer. | `Merging conflicted file`, then `Merge successful`, `Merge failed. <error>`, or `Downloading <path>` for the no-base case |
| `conflict` | The **local** version is written beside the original as `<name> (Conflicted copy <device-name> <YYYYMMDDHHMM>).<ext>`, and the **remote** version takes the original path. Both survive. | `Merging conflicted file`, then `Conflicted copy stored` |

The timestamp is local wall-clock time on the machine that stored the copy, to the minute.

Three consequences that `--help` does not state:

- **The initial reconciliation ignores `conflictStrategy` entirely.** While a pairing is still in its initial state, a remote file with a newer mtime simply overwrites the local one - no merge, no conflicted copy. That is exactly what the setup warning means by "the most recent version of the note will be preserved". `--conflict-strategy conflict` protects later runs, not first contact. Only an existing restore point protects first contact.
- Configuration JSON under the config directory is reconciled key-by-key: `Merging conflicted file`, then `Merge successful`, or `Merge failed. <error>` followed by the remote file being downloaded whole.
- Anything else that cannot be reconciled is skipped with `Rejected server change` and stays skipped.

`(Conflicted copy ...)` files are ordinary notes: they sync, and they are the only surviving copy of one side. Report them with paths and leave them where they are.

## Sync scope

The filter runs before any transfer and is not configurable beyond the flags above.

- `.md`, `.canvas`, and `.base` are **always** synced. `--file-types` controls attachments only.
- Attachments map to categories: `image` = `bmp png jpg jpeg gif svg webp avif`; `audio` = `mp3 wav m4a 3gp flac ogg oga opus`; `video` = `mp4 webm ogv mov mkv`; `pdf` = `pdf`; `unsupported` = every other extension. `webm` counts as audio or video, whichever is enabled.
- Any path segment starting with `.` is excluded outside the config directory. A `.git` directory inside a vault is never synced, which is why a Git restore point is not itself at risk from a sync run.
- Inside the config directory, `node_modules` and dot-entries are excluded, `workspace.json` and `workspace-mobile.json` are never synced, and everything else must map to an enabled `--configs` category: `app.json`/`types.json` → `app`; `appearance.json` → `appearance`; `hotkeys.json` → `hotkey`; `core-plugins.json`/`core-plugins-migration.json` → `core-plugin`; `community-plugins.json` → `community-plugin`; `themes/<name>/theme.css`/`manifest.json` and `snippets/*.css` → `appearance-data`; other top-level `*.json` → `core-plugin-data`; `plugins/<id>/{manifest.json,main.js,styles.css,data.json}` → `community-plugin-data`.
- `--excluded-folders` entries match a folder exactly or as a path prefix.

## Exit codes

| Code | Class | Raised by |
|---|---|---|
| 0 | Success, including "nothing configured" reports | all |
| 1 | Generic failure, invalid enum value, ambiguous vault name, lock already held, usage error | `Setup failed:`, `Config update failed:`, `Status check failed:`, `Unlink failed:`, `Sync failed:`, `Failed to list vaults:`, `Failed to create vault:`, `Logout failed:`, `Invalid sync mode`, `Invalid conflict strategy`, `Invalid region`, `Multiple vaults named`, `Another sync instance is already running`, `error: required option ... not specified`, `error: unknown option`, `error: unknown command` |
| 2 | Credentials and encryption | `No account logged in.`, `Login failed:`, `Password not provided.`, `Failed to validate password.`, `Encryption key not found.`, `End-to-end encryption key missing.` |
| 3 | Identity | `No sync configuration found for <path>`, `Vault "<name>" not found.` |

Exit 2 and exit 3 are terminal for an unattended run. Restarting on either is a retry loop that cannot succeed.

## Error strings

| String | Meaning | Correct response |
|---|---|---|
| `No sync configuration found for <path>` | No stored config resolves to that exact path string | Compare with `sync-list-local`; fix the spelling. Do not pair again to make it go away. |
| `Vault "<name>" not found.` | No remote ID or exact name matched | Re-read `sync-list-remote`. Do not pair against a similar name and do not create a replacement vault. |
| `Multiple vaults named "<name>". Use the vault ID instead:` | Ambiguous display name | Use the printed ID. |
| `Password not provided.` | Prompt could not run - piped, `--json`, or no TTY | Re-run in a real terminal. Never add `--password`. |
| `Failed to validate password.` | Passphrase rejected by the service | Confirm the passphrase with the account owner. Repeated attempts do not change the result. |
| `Encryption key not found. Run setup again.` / `End-to-end encryption key missing. Run setup again.` | Stored config lacks key, salt, or version | Configuration damage. Go to [recovery.md](recovery.md) before re-pairing - re-pairing resets policy. |
| `Encryption version not supported` | Stored `encryptionVersion` is outside the supported set | Report version skew or config damage. Do not edit the value by hand. |
| `No account logged in. Run "ob login" first.` | No token in environment or token file | Supply the token via `OBSIDIAN_AUTH_TOKEN`, or log in interactively. |
| `Another sync instance is already running for this vault.` | A live `ob sync` holds the lock | Find the other writer. Do not delete `.sync.lock`. |
| `The connected remote vault no longer exists.` | Server reports the paired vault as gone | Stop. Verify against `sync-list-remote` and preserve local state; this is an identity incident. |
| `Your subscription to Obsidian Sync has expired` | Account-level block | Report it. No client-side change fixes it. |
| `Sync error: <error>` | Per-attempt transport or file error inside a run | Read the following lines: a later `Fully synced` means it recovered. |

## Run-output vocabulary

Each line is `<Message> <vault-relative-path>` on stdout, mirrored into `sync.log`.

| Line | Meaning | Modes |
|---|---|---|
| `Starting sync:` | Configuration echo before any change | all |
| `Connecting...` / `Connection successful. Detecting changes...` | Transport up | all |
| `Waiting to connect to server` | Inside the reconnect backoff window | all |
| `Disconnected from server` | Socket dropped; reconnect follows | all |
| `Checking` | A known local file had no stored hash and was re-read from disk before comparison | all |
| `Accepted` | A pending server change was applied and recorded in the state database; suppressed for no-op and filtered entries | all |
| `Skipped` | Superseded by a later entry for the same path in the same batch | all |
| `Downloading <path>` / `Downloaded` | Remote content written locally | all |
| `Deleting <path>` | **A remote deletion applied to the local vault** | all, including `pull-only` |
| `Restoring <path>` | Locally missing file re-downloaded | `mirror-remote` |
| `Removing local-only file` / `Removing local-only folder` | Local-only content deleted | `mirror-remote` |
| `Reverting <path>` | Local modification overwritten by the remote copy | `mirror-remote` |
| `Renaming conflicted file` | A local *file* occupies a path the remote holds as a *folder*; the local file is renamed to `<name> (Conflicted copy).<ext>` to make room | all, independent of strategy |
| `Conflicted copy stored` | Local version written beside the original, remote version at the original path | `conflict` strategy |
| `Merging conflicted file` / `Merge successful` / `Merge failed. <error>` | In-place reconciliation | `merge` strategy for Markdown; config JSON in all modes |
| `Rejected server change` | Change could not be applied and was skipped | all |
| `Uploading` / `Uploading file` / `Upload complete` | Local content sent | `bidirectional` |
| `Deleting remote file` / `Deleting remote folder` | **A local deletion applied to the remote vault** | `bidirectional` |
| `Push: <path> (updated\|deleted)` | Server push received after the initial sync | continuous |
| `Ignoring remote file name with illegal characters` | Remote path unrepresentable locally | all |
| `Fully synced` | Reconciliation converged; a one-shot run stops here | all |
| `Received signal to shut down...` | `SIGINT`/`SIGTERM` handled | all |
| `Warning: btime native module failed to load.` | macOS/Windows only; creation times are not preserved | `sync-setup`, `sync` |

`Deleting` in a `pull-only` run is the line that surprises operators. Every one of them must be explained from the remote side before the run is accepted.

## On-disk layout

Client state, outside the vault:

```
~/.obsidian-headless/                     # macOS, Windows   (mode 0700)
${XDG_CONFIG_HOME:-~/.config}/obsidian-headless/   # Linux
  auth_token                              # account token    (mode 0600)
  sync/<vault-id>/config.json             # per-vault config (mode 0600)
  sync/<vault-id>/state.db                # sync state database
  sync/<vault-id>/sync.log                # append-only run log
  publish/<vault-id>/                     # publish state, out of scope
```

In the vault:

```
<vault-root>/<config-dir>/.sync.lock      # lock directory, never synced
```

`config.json` holds the derived `encryptionKey` and `encryptionSalt` in cleartext. Never copy, print, or commit it; use `sync-status --json` when a configuration needs to be recorded.

Keys written by `sync-setup`: `vaultId`, `vaultName`, `vaultPath`, `host`, `encryptionVersion`, `encryptionKey`, `encryptionSalt`, `conflictStrategy`, `deviceName`, `configDir`. Keys written only by `sync-config`: `syncMode` (absent means bidirectional), `ignoreFolders`, `allowTypes`, `allowSpecialFiles`. This asymmetry is why [recovery.md](recovery.md) captures the effective configuration before any re-pair.

## Boundary

This file documents what the commands do. It grants nothing. Network access, pairing, configuration changes, sync runs, unlinking, and daemon lifecycle are separate authorizations, and an unauthorized one is reported as not performed rather than attempted.

See [daemon.md](daemon.md) for continuous operation and [recovery.md](recovery.md) for incidents.
