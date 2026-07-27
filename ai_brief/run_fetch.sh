#!/usr/bin/env bash
#
# Cron wrapper for fetch_briefs.py.
#
# Handles the three things cron gets wrong by default: it does not inherit your
# shell environment, it does not activate virtualenvs, and it will happily start
# a second copy while the first is still running.
#
# Usage from crontab (see README.md):
#   30 6 * * * /var/www/Alex_web/ai_brief/run_fetch.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${AI_BRIEF_LOG:-$HERE/fetch.log}"
LOCK="$HERE/.fetch.lock"
VENV="${AI_BRIEF_VENV:-$HERE/venv}"

# Keep the log from growing without bound.
if [[ -f "$LOG" ]] && [[ "$(wc -l < "$LOG")" -gt 2000 ]]; then
  tail -n 1000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Refuse to start if a previous run is still going (flock is absent on macOS,
# in which case we simply proceed).
exec 9>"$LOCK"
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    echo "$(date '+%Y-%m-%d %H:%M:%S')  another run is in progress; exiting" >> "$LOG"
    exit 0
  fi
fi

if [[ -x "$VENV/bin/python" ]]; then
  PY="$VENV/bin/python"
else
  PY="$(command -v python3)"
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z')  $PY fetch_briefs.py $* ==="
  "$PY" "$HERE/fetch_briefs.py" "$@"
} >> "$LOG" 2>&1
