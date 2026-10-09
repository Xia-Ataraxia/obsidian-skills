#!/usr/bin/env bash
# Refresh the qmd index in the background after a Markdown note inside a
# configured qmd collection is written or edited. Bursts of edits collapse
# into one run. Never blocks or fails the tool call.

PATH="$PATH:/opt/homebrew/bin:$HOME/.bun/bin"
CONFIG="${QMD_CONFIG:-$HOME/.config/qmd/index.yml}"
STATE="${TMPDIR:-/tmp}/secondbrain-qmd-reindex"
SETTLE=8        # seconds without a new edit before the run starts
STALE_MIN=60    # a running marker older than this is treated as dead

command -v qmd >/dev/null 2>&1 || exit 0
[ -f "$CONFIG" ] || exit 0

file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
case "$file" in *.md) ;; *) exit 0 ;; esac

inside=0
while IFS= read -r root; do
  case "$file" in "$root"/*) inside=1; break ;; esac
done < <(sed -n 's/^[[:space:]]*path:[[:space:]]*//p' "$CONFIG" | sed 's/^"\(.*\)"$/\1/')
[ "$inside" = 1 ] || exit 0

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }

touch "$STATE.request"
if [ -f "$STATE.running" ] && [ -z "$(find "$STATE.running" -mmin +"$STALE_MIN" 2>/dev/null)" ]; then
  exit 0
fi

(
  touch "$STATE.running"
  trap 'rm -f "$STATE.running"' EXIT
  seen=""
  while [ "$(mtime "$STATE.request")" != "$seen" ]; do
    seen=$(mtime "$STATE.request")
    sleep "$SETTLE"
  done
  {
    echo "=== $(date -u +%FT%TZ) qmd reindex ==="
    qmd update && qmd embed
    echo "=== exit $? ==="
  } >>"$STATE.log" 2>&1
) >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
