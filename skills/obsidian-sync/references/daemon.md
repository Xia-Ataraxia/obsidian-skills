# Continuous sync under a supervisor

`ob sync --continuous` is a long-lived writer with a vault as its output. The supervisor owns process lifetime; `ob` owns sync policy. Keeping those two apart is what makes a restart safe: nothing about "the daemon is misbehaving" justifies changing the mode, the pairing, or the conflict strategy.

Read [commands.md](commands.md) first for the flag surface and the run-output vocabulary. This file covers everything that only matters once the process outlives the terminal.

## Preconditions

Continuous mode is the last step of the workflow in [`../SKILL.md`](../SKILL.md), never the first. Do not start one until all of these hold.

- [ ] Two consecutive one-shot runs finished with `Fully synced` and were compared against the Phase 0 baseline, not against expectations.
- [ ] `ob sync-status --path "$OBSIDIAN_VAULT_PATH"` reports the intended vault ID, the resolved root character for character, and the mode the task actually authorized.
- [ ] Exactly one writer will touch the root: no desktop app, no second `ob sync`, no file-sync client, no backup job writing into the vault.
- [ ] A named restore point exists and its coverage of uncommitted content is stated.
- [ ] The token reaches the process through `OBSIDIAN_AUTH_TOKEN` or the client's token file. No passphrase appears anywhere in the definition.
- [ ] Running the daemon was authorized as its own effect, separately from pairing and from the mode it will run in.

`ob sync-setup` cannot be part of a supervisor definition: its passphrase prompt needs a TTY, and `--json` or a non-interactive shell turns that into `Password not provided.`. Pair interactively, verify, then supervise.

## Inspect before you touch

A replica that is already syncing has a definition somebody wrote for a reason. Read it before changing anything: process name, executable path, exact arguments, working directory, environment, restart policy, log destinations, and boot integration.

Use the supervisor that the host already runs. Do not introduce a second one, and do not replace an existing definition with an example. If the observed definition disagrees with this file, the observed definition wins until its change is authorized.

The same rule covers a separate Git backup job. It is a different mechanism with a different owner; read its schedule, repository, branch, and include/exclude rules without replacing them, and never fold it into sync work.

## Definition shape

Whatever supervisor is in use, the definition needs the same five properties. This `systemd` user unit is an illustration to adapt, not a target to install:

```ini
[Unit]
Description=Obsidian headless sync (example-replica-01)

[Service]
Type=simple
WorkingDirectory=/srv/vaults/example-vault
ExecStart=/usr/local/bin/ob sync --path /srv/vaults/example-vault --continuous
# The file below holds OBSIDIAN_AUTH_TOKEN and is mode 0600, outside any repository.
EnvironmentFile=%h/.config/example-replica-01.env
Restart=on-failure
RestartSec=60
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=default.target
```

What each property is doing:

- **Absolute `--path`, resolved on this host.** Never copied from another machine. Without it the daemon silently targets its working directory.
- **Absolute binary path.** A service manager's `PATH` is not the operator's `PATH`. A bare `ob` can resolve to a different install, to a version-manager shim that is not on the service's `PATH` at all, or to nothing.
- **Token from a file outside the repository**, owner-readable only. A token inlined in a committed unit file is a leaked credential.
- **`SIGTERM` as the stop signal, with a stop timeout** long enough for an in-flight transfer to finish - see [Stopping](#stopping).
- **A restart delay, and no unbounded restart burst.** Restart pacing belongs in the supervisor. Ordering the unit against network availability does not: the client already reconnects on its own with exponential backoff, so a start before the network is up is not a failure.

Do not add flags the build does not have. Run the gate in [commands.md](commands.md#version-gate) against the exact binary the definition names.

## Starting

```bash
ob sync --path "$OBSIDIAN_VAULT_PATH" --continuous
```

The run prints `Starting sync:` and the configuration block first. Read it once, under supervision, before walking away - it is the last cheap chance to catch a wrong mode.

After start, `ob` keeps working from three triggers: a filesystem watcher on the root, pushes from the server, and an internal tick roughly every 30 seconds. `Fully synced` in continuous mode means the current batch converged; the process stays up and waits.

## Stopping

`SIGINT` and `SIGTERM` are handled. The client prints `Received signal to shut down...`, disconnects, closes the state database, stops the watcher, and releases the lock directory.

Send `SIGTERM` and let it exit. Do not follow it with `SIGKILL` on a short fuse:

- A hard kill can interrupt a file write mid-transfer, leaving the vault in a state that is neither the baseline nor the target.
- A hard kill skips the lock release. `<vault-root>/<config-dir>/.sync.lock` survives until it goes stale after 5 seconds, then the next run reclaims it automatically. Never delete it by hand - a lock that is not stale means a live writer you have not found yet.
- A hard kill also skips closing the state database.

After a stop, confirm the process is actually gone before starting anything else against the same root. `Another sync instance is already running for this vault.` (exit 1) on the next start means the old one is still alive.

## Restarting

A restart is a lifetime operation. Its scope is exactly one registered process, keeping its definition, environment, working directory, and boot integration as they are.

Restart-only work must not:

- reload a stale definition file that no longer matches the live process,
- rewrite the boot-time process list,
- change the sync mode, conflict strategy, device name, or pairing,
- re-run `sync-setup`,
- or delete `.sync.lock`.

Any mode change, unlink, pairing, or definition change is a different authorization, and it drops back to the one-shot gate: stop the daemon, make the change, run one bounded one-shot sync, compare against the baseline, and only then resume continuous operation.

## Log growth

`ob sync` mirrors every console line into `<client-config-dir>/sync/<vault-id>/sync.log`, prefixed with an ISO-8601 UTC timestamp. The file is opened **once, in append mode, at process start** and is never rotated or capped by the client. Under continuous operation it grows for as long as the process lives.

That single long-lived file descriptor determines which rotation strategies work:

| Strategy | Result |
|---|---|
| Copy the file, then truncate it in place (`copytruncate`) | Works. Appends continue at the new end. |
| Rename or move the file | **Does not work.** The descriptor follows the inode, so the daemon keeps writing into the moved file and the original path stays empty until the next restart. |
| Delete the file | **Does not work** and loses the history. The descriptor stays open; disk space is not reclaimed until the process exits. |
| Stop the daemon, archive the file, restart | Works, and is the only option that also gives a clean file boundary. |

The supervisor usually captures the same stream a second time through its own stdout/stderr files. Size both, and remember that neither is redacted: `sync.log` records the vault name, vault ID, absolute root, and device name. It never records the token, encryption key, or salt. Redact the identity fields before sharing a log; do not paste raw logs into an evidence report.

Never treat `sync.log` as disposable during an incident. `ob sync-unlink` deletes the whole per-vault directory including this file - copy it out first.

## Health evidence

Four different things get called "healthy". Report them separately and never let one stand in for another.

| Claim | Evidence that supports it | What it does not prove |
|---|---|---|
| The process is alive | Supervisor state and a stable restart count | Nothing about connectivity. `ob sync` does **not** exit when the server is unreachable; it stays up in a reconnect loop. |
| Transport is up | A recent `Connection successful. Detecting changes...` with no later `Disconnected from server` or `Waiting to connect to server` | Nothing about whether files moved |
| Reconciliation converged | A recent `Fully synced`, with its timestamp | Nothing about direction or correctness |
| The vault holds what it should | File count, `git status`, a diff against the named restore point, and a representative file opened and read | Nothing about the other end |

A recent timestamp on `Fully synced` is the single most useful liveness signal, because it is the only one that requires the transport, the state database, and the filesystem to all be working.

Round-trip is a fifth claim and needs its own authority. Proving that local edits leave this machine requires a named note, a specific reversible change, and readback on both machines. A `pull-only` run proves nothing about the upload direction, and promoting the mode just to complete a test is not a test - it is an unauthorized mode change. Without that authority, report the upload direction as unverified.

A remote Git backup is also its own claim. A local commit, a green scheduler, or a successful sync says nothing about what the backup destination holds; only reading the expected revision and content back from that destination does.

One diagnosis trap worth naming: on macOS, a non-interactive SSH shell may not have Full Disk Access, so files that exist can list as absent. Confirm a suspected deletion through a session that can actually read the root before reporting data loss.

## Crash-loop containment

Restart counts that keep climbing are not a transient. Each restart replays whatever the last one did, and if the cause was destructive, it replays that too.

Stop the process first. Then read the **earliest** relevant error, not the newest one - the newest is usually the fifth echo of the first.

Classify by exit code before deciding anything:

| Exit | Class | Restarting helps? |
|---|---|---|
| 3 | Identity - `No sync configuration found for <path>`, `Vault "<name>" not found.` | **No.** The path or the remote ID is wrong. |
| 2 | Credentials or encryption - no token, login failure, missing key | **No.** Needs an interactive login or a configuration repair. |
| 1 | Everything else - lock held, subscription expired, remote vault gone, runtime or native-module failure | **No, not before diagnosis.** Each of these has a distinct cause and a distinct fix. |

Exits 2 and 3 are terminal for an unattended process. A supervisor configured to restart on them produces a loop that cannot succeed, and it fills the log with copies of one error.

Two failures that look identical from the supervisor and are not:

- `Another sync instance is already running for this vault.` - a second writer exists, or a previous process is still shutting down. Find it. Do not delete the lock.
- `The connected remote vault no longer exists.` or `Your subscription to Obsidian Sync has expired` - the client stopped on purpose. These are account- or identity-level facts; no restart policy changes them.

Anything that looks like content loss - a large or unexplained deletion set, `Removing local-only file` in a mode that was supposed to be `pull-only`, `Merge failed.` on notes that matter - stops being a daemon problem. Stop every sync client touching the root and go to [recovery.md](recovery.md) before changing configuration.

## Checklist

- [ ] The daemon was authorized as its own effect, after two clean one-shot runs.
- [ ] The live definition was inspected and preserved; nothing was replaced by an example.
- [ ] The binary path and `--path` were resolved on this host, and the version gate passed against that exact binary.
- [ ] The token is supplied from outside any repository; no passphrase appears in the definition.
- [ ] Stop is `SIGTERM` with a timeout that lets an in-flight transfer finish.
- [ ] `sync.log` and the supervisor's own capture both have a size plan, using copy-truncate or a stop-archive-restart cycle.
- [ ] Liveness, transport, convergence, and vault content were reported as four separate claims.
- [ ] Round-trip and remote-backup claims were either evidenced end to end or reported as unverified.
- [ ] Restart counts were read before any restart, and exits 2 and 3 were treated as terminal.
