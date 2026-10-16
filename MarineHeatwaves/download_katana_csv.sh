#!/bin/bash
# Runs on the Nectar VM (cron, 03:00 UTC on the 1st): copies the Scopus CSVs
# produced by the Katana PBS job (03:00 Sydney on the 1st) into the website.
set -e
echo "=== $(date -u) ==="

cd /home/ubuntu/AlexWeb2026/MarineHeatwaves || exit 1

scp z3045790@katana.restech.unsw.edu.au:'/home/z3045790/SCOPUS/*.csv' .

if [ -f "scopus_alex_sen_gupta_articles_with_abstracts.csv" ]; then
    mkdir -p /home/ubuntu/AlexWeb2026/assets/data
    mv scopus_alex_sen_gupta_articles_with_abstracts.csv /home/ubuntu/AlexWeb2026/assets/data/
    echo "Moved scopus_alex_sen_gupta_articles_with_abstracts.csv → assets/data/"
fi

echo "=== done $(date -u) ==="
