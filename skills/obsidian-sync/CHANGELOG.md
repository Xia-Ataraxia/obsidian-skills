# Changelog

## 0.2.1 — 2026-10-07

- 2026-10-07 — Collection release `0.2.1`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.2.0 — 2026-10-07

- 2026-10-07 — Collection release `0.2.0`: `metadata.version` follows the collection release identity so native plugin hosts see the upgrade. No behavior, reference or script change in this package.

## 0.1.0 — Unreleased

- This repository had no owner for headless Obsidian Sync, and the guidance that existed for it stopped at a command catalog → `obsidian-sync` becomes the self-contained owner of the `ob` client: binary identity and a fail-closed version gate, two-sided identity resolution before any command, a staged `pull-only` workflow whose acceptance is a baseline comparison rather than an exit code, conflict preservation, partial-network triage, secret handling, and an explicit composition boundary that never converts transport access into content authority.
- The two properties that actually cause data loss were undocumented and are now stated first in `SKILL.md`: download modes delete, because `pull-only` and `mirror-remote` both apply remote deletions locally; and pairing resets policy, because `ob sync-setup` writes a fresh configuration whose mode is bidirectional and whose conflict strategy is `merge`.
- An operator reading `--help` cannot tell which commands leave the machine, what a flag's effective default is, or what a run-output line means → [`references/commands.md`](references/commands.md) adds a runnable [version gate](references/commands.md#version-gate), a reach table splitting local-only commands from account/network commands, per-command entries with their exact error strings, mode semantics as a five-column effect table, conflict mechanics, the non-configurable sync scope filter, an exit-code table, the run-output vocabulary, and the on-disk layout.
- Continuous operation had no boundary between process lifetime and sync policy, so "restart the daemon" kept turning into a configuration change → [`references/daemon.md`](references/daemon.md) adds supervision preconditions, an annotated definition shape, graceful `SIGTERM` stop with its lock consequences, an explicit restart scope, log-growth mechanics with a rotation-strategy table, four separated health claims, and crash-loop containment keyed to exit codes.
- Incident response defaulted to re-pairing, which discards policy and can destroy the only run record → [`references/recovery.md`](references/recovery.md) adds containment, evidence preservation before any unlink, a classification table, three independent restores (client version, configuration, notes), a capture-repair-replay-verify procedure for exact configuration recovery, the remote-safety rule, staged re-admission, and an evidence receipt.
- Two claims in the existing `SKILL.md` were corrected against the installed build. Path matching is lexical, so `./` prefixes and trailing slashes normalize away and are safe, while letter case and symlinks are not - the earlier text listed all four as equally dangerous. And conflict strategy is not consulted during the initial reconciliation, so `--conflict-strategy conflict` does not protect first contact; only the Phase 0 restore point does.

### Grounded facts and sources

Read 2026-09-29 on the acting host, read-only. No account, network, or pairing operation was performed.

- Binary identity: `command -v ob` resolves to the global npm package `obsidian-headless`; `ob --version` reports `0.0.14`; `node --version` reports `v24.21.0`.
- Command surface, flags, and flag values: `ob --help` plus `ob <subcommand> --help` for `login`, `logout`, `sync-list-remote`, `sync-list-local`, `sync-create-remote`, `sync-setup`, `sync-config`, `sync-status`, `sync-unlink`, and `sync`. The `--configs` category list in this build includes `appearance-data`, which older third-party summaries omit.
- Command documentation, JSON-mode semantics, and the Node 22 requirement: the package's bundled `README.md`.
- Behavior that `--help` does not state - exit-code classes, exact error strings, lock timings, reconnect backoff, socket heartbeat, conflict-copy naming, the initial-reconciliation exception, the sync scope filter, the scope-change requeue, `--mode bidirectional` removing the stored key, and the log-stream open mode - was read from the bundled `cli.js` of that same installed build.
- Exit codes were confirmed by local probes against a freshly created empty directory that is not a configured vault: `sync-status`, `sync-config --mode pull-only`, `sync-unlink`, and `sync` each printed `No sync configuration found for <path>` and exited `3`, with `sync-config` and `sync` adding `Run 'ob sync-setup' first.`. Usage errors were confirmed the same way: a missing required option, an unknown option, and an unknown command each exited `1`.
- The version-gate script in `references/commands.md` was executed against this build and exited `0`, and a negative control confirmed it reports an absent flag rather than passing silently.
- The on-disk layout and file modes come from the path helpers in the bundled `cli.js` and from a permissions listing of the client's configuration root. No vault identifier, vault path, token, or note content was read or recorded.

### Provenance

- Requirements evidence came from four files of a local craft-skills checkout pinned at commit `836eb8778134d68f3ea675cd30ee5f9ae692f9e3`, opened read-only: `skills/obsidian/references/sync.md`, `sync-cli-commands.md`, `sync-daemon-operations.md`, and `sync-recovery.md`. They were used only to scope which failure modes an operator needs covered.
- No prose, table, checklist, command block, or example was copied from those files. That checkout publishes no root license or notice file, so nothing from it is redistributed here and no rights claim about it is made. Every rule in this package was re-derived from the installed build and re-authored independently.
- Three claims carried by that source material were contradicted by the installed build and are corrected here rather than repeated: the client configuration root is `~/.obsidian-headless` only on macOS and Windows, and follows `XDG_CONFIG_HOME` on Linux; `sync.log` is append-only with no rotation or size cap, not a rolling log; and `--file-types` governs attachments while `.md`, `.canvas`, and `.base` are always synced.
- All files in this package are original work for this repository, covered by its bundled [`LICENSE`](LICENSE). No upstream MIT notice applies, because no upstream-derived file is included.
- Every example is synthetic and public. No credentials, account identifiers, vault identifiers, workstation paths, private notes, or raw logs appear in any file.

### Limitations

- No account operation was performed: no `login`, `logout`, `sync-list-remote`, `sync-create-remote`, `sync-setup`, or `sync` run, one-shot or continuous. Everything about the network path - remote listing output shape, pairing behavior against a live vault, transfer behavior, and reconnection under a real outage - is documented from the installed build's own code and help text, not from an observed session.
- No daemon was started, no supervisor definition was created or restarted, and no rotation strategy was exercised on a live log. The definition shape in `references/daemon.md` is labelled as an illustration to adapt, not a configuration to install.
- No incident was reproduced and no recovery was rehearsed. The configuration capture-and-replay procedure in `references/recovery.md` is derived from the fields `sync-status --json` emits and the fields `sync-setup` writes; it has not been executed end to end against a paired vault.
- No round-trip, remote-backup readback, or multi-host behavior is claimed anywhere in this package.
- Scope note: this entry set records authored content only. No tests, gates, or formatters were run for this package, and no installation, deployment, or release was performed.
