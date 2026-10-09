#!/usr/bin/env bash
# Refresh the qmd index in the background. Bursts of calls collapse into one
# run. Never blocks or fails the caller. Works from any agent runtime.
#
#   qmd-reindex.sh            reindex now (manual or end of ingest)
#   qmd-reindex.sh FILE       reindex only if FILE is a note in a qmd collection
#   <hook JSON> | qmd-reindex.sh   same, FILE read from tool_input.file_path

PATH="$PATH:/opt/homebrew/bin:$HOME/.bun/bin"
CONFIG="${QMD_CONFIG:-$HOME/.config/qmd/index.yml}"
STATE="${TMPDIR:-/tmp}/secondbrain-qmd-reindex"
SETTLE=8        # seconds without a new edit before the run starts
STALE_MIN=60    # a running marker older than this is treated as dead

command -v qmd >/dev/null 2>&1 || exit 0
[ -f "$CONFIG" ] || exit 0

file="${1:-}"
if [ -z "$file" ] && [ ! -t 0 ]; then
  file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
fi

if [ -n "$file" ]; then
  case "$file" in *.md) ;; *) exit 0 ;; esac
  inside=0
  while IFS= read -r root; do
    case "$file" in "$root"/*) inside=1; break ;; esac
  done < <(sed -n 's/^[[:space:]]*path:[[:space:]]*//p' "$CONFIG" | sed 's/^"\(.*\)"$/\1/')
  [ "$inside" = 1 ] || exit 0
fi

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }

touch "$STATE.request"
if [ -f "$STATE.running" ] && [ -z "$(find "$STATE.running" -mmin +"$STALE_MIN" 2>/dev/null)" ]; then
  exit 0
fi

(
  touch "$STATE.running"
  trap 'rm -f "$STATE.running"' EXIT
  seen=""
  prev=""
  while [ "$(mtime "$STATE.request")" != "$seen" ]; do
    seen=$(mtime "$STATE.request")
    sleep "$SETTLE"
  done
  {
    echo "=== $(date -u +%FT%TZ) qmd reindex ==="
    qmd update && while :; do
      qmd embed
      left=$(qmd status | sed -n 's/^ *Pending: *\([0-9]*\) need embedding.*/\1/p')
      [ -n "$left" ] && [ "$left" != 0 ] && [ "$left" != "$prev" ] || break
      prev=$left
    done
    echo "=== exit $? ==="
  } >>"$STATE.log" 2>&1
) >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
