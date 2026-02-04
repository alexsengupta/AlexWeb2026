#!/bin/bash
# Process Scopus CSVs: enrich with authors and classify into themes.
#
# Usage:
#   export OPENAI_API_KEY="your-key-here"
#   bash process_csvs.sh
#
# Expects these input files in the current directory:
#   scopus_subsurface_MHW.csv
#   scopus_all_MHW.csv
#
# Produces:
#   scopus_subsurface_MHW_enriched.csv  (with authors)
#   scopus_all_MHW_enriched.csv         (with authors)
#   scopus_subsurface_MHW_themes.csv    (with authors + themes)
#   scopus_all_MHW_themes.csv           (with authors + themes)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable not set."
    echo "  export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

# --- Step 1: Enrich with author data ---
for csv in scopus_subsurface_MHW.csv scopus_all_MHW.csv; do
    if [ ! -f "$csv" ]; then
        echo "Warning: $csv not found, skipping."
        continue
    fi
    enriched="${csv%.csv}_enriched.csv"
    echo ""
    echo "=== Enriching $csv with author data ==="
    python3 enrich_authors.py "$csv" "$enriched"
done

# --- Step 2: Classify themes ---
for csv in scopus_subsurface_MHW_enriched.csv scopus_all_MHW_enriched.csv; do
    if [ ! -f "$csv" ]; then
        echo "Warning: $csv not found, skipping."
        continue
    fi
    themed="${csv/_enriched/_themes}"
    echo ""
    echo "=== Classifying themes for $csv ==="
    python3 classify_themes.py "$csv" "$themed"
done

echo ""
echo "=== All done! ==="
echo "Output files:"
ls -lh scopus_*_themes.csv 2>/dev/null || echo "  (no themed CSVs found)"
