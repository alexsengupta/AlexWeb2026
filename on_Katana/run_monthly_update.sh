#!/bin/bash
# Monthly Scopus refresh — called by cron.
# Re-runs the four Scopus download scripts so the website's CSVs stay current.

set -u

SCOPUS_DIR="$HOME/SCOPUS"
LOG_DIR="$SCOPUS_DIR/logs"
LOG_FILE="$LOG_DIR/cron_$(date +%Y%m%d_%H%M%S).log"
PYTHON="$SCOPUS_DIR/venv/bin/python"

mkdir -p "$LOG_DIR"

# Load API keys (ELSEVIER_API_KEY, OPENAI_API_KEY) from a file kept out of git.
ENV_FILE="$HOME/.scopus_env"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found — cannot run without API keys." >&2
    exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

cd "$SCOPUS_DIR" || exit 1

{
    echo "=== Monthly Scopus update started: $(date) ==="

    for script in \
        scopus_download_with_abstracts_MHW_all.py \
        scopus_download_with_abstracts_SMHW.py \
        scopus_download_with_abstracts_PolarMHW.py \
        scopus_download_with_abstracts.py
    do
        echo
        echo "--- Running $script ---"
        "$PYTHON" "$script"
        echo "--- $script exit code: $? ---"
    done

    echo
    echo "=== Finished: $(date) ==="

    # Keep the log directory tidy — drop logs older than 6 months
    find "$LOG_DIR" -name 'cron_*.log' -mtime +180 -delete
} >> "$LOG_FILE" 2>&1
