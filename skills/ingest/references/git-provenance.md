# Git provenance

This is a recipe for an explicitly authorized vault transaction, not authorization to run git. One ingest, including multiple Raw/Entity/Concept outputs, is exactly one commit. No index.md/log.md. Sync carries content; git carries history. Track attachments without LFS; ignore only workspace/cache, trash and sync-lock artifacts according to live policy. Never create/delete a remote without concrete-effect approval. A published baseline on origin/main is required before live ingest. After `inbox delete` (5-C), `ingest.py --apply-state <state> --record-deletions <inbox-delete-result.json>` commits only those deletions as `inbox: delete {n} ingested originals` (trailer `Ingest-Source: <published ingest SHA>`), using the written-restart comparison: base equals the recorded input bytes, local is absent.

## Runtime

`scripts/vaultgit.py` (stdlib only) implements this recipe behind the explicit `--git` flag of `scripts/ingest.py`: `--request R --state S --apply --git [--title T]` or `--apply-state S --git`. Without `--git` no git command runs. The vault must be the repository top level with an `origin` remote and `main` branch. The repository lock is `.git/ingest.lock` (exclusive create, removed on exit). Session state `S` (outside the vault) records `writing`/`written`/`committed-local`/`published` and the commit SHA. The result returns the exact owned paths and SHA. Rerunning `--apply-state S --git` resumes from the recorded state. Commit title defaults to the first Raw name; `Ingest-Source` is the first member's source identity, or its Raw path when no identity is known.

## Preconditions and fixed order

Hold the repository writer lock; coordinate non-overlapping pilot runs across hosts. The vault repo sets `core.autocrlf false` locally (every host clone): byte guards compare blobs with disk bytes, so any line-ending conversion is refused. No unrelated staged entries. `git rev-list origin/main..HEAD` must be empty: unpublished commits block reset and must be published first, without recreating them. Never use hard reset or force push.

Fixed order: `git fetch` → `git reset --mixed origin/main` → write files → `git add -- <exact owned paths>` → `git commit -m "ingest: {title}"` → `git push`.

Every git call runs with `--literal-pathspecs`: an owned path is an exact filename, never a glob or pathspec magic. A note literally named `Raw/*.md` stages only itself; unrelated dirty files whose names the glob would match stay unstaged and byte-unchanged.

Immediately after fetch and before reset/write, compare fetched-base existence AND bytes with local existence AND bytes for every owned create/update/delete path. Create requires absent/absent. Update/delete requires the approved preimage to match both. Base-present/local-absent indicates possible Sync delay; base-absent/local-present indicates possible resurrection. Either mismatch, or a human dirty owned path, stops the transaction: no checkout/reset/replay to settle content. Unrelated dirty unstaged files remain untouched. Retain exact preimages/postimages outside notes.

After add, compare the staged path set to the owned set and each `git show :<path>` blob to intended postimage bytes. Deleted paths must be exact staged deletions. Reject unrelated staged entries or byte drift before committing.

Commit subject: `ingest: {title}`. Add trailers `Ingest-Source: <stable identity or canonical address hash>` and `Ingest-Paths: <hash of sorted exact owned paths>`. A title is not an identifier.

## Failure and restart

On non-fast-forward push, re-fetch once, inspect conflict, stop/report and retain local SHA as committed-local. Retry publication of that SHA; never reset, replay or force-push. A crash after writes uses [re-ingest's restart table](reingest.md), not the pre-write guard literally: fetched base must match recorded preimages, local files must match owned postimages. Before the restart's `reset --mixed`, every owned path already staged must hold the intended postimage blob in the index (stage 0, regular file); otherwise the restart refuses and leaves the index, disk, HEAD and remote untouched. Disk equality alone is not enough: a human may have staged other bytes and then restored the file, and the reset would discard that staged work. A staged entry equal to the postimage resumes normally. Staged-byte checks after add still apply. Push success before manifest update is reconciled by `git merge-base --is-ancestor <sha> origin/main`.

Recovery restores backed-up preimages only where current bytes still match owned postimages; never overwrite later human/Sync edits or use blanket checkout/revert. Report partial writes and exact paths. Sync activation and remote publication remain separate approved effects.
