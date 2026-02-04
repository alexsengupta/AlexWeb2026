"""
Enrich a Scopus CSV with author information fetched from the CrossRef API.

Usage:
  python3 enrich_authors.py <input.csv> [output.csv]
  python3 enrich_authors.py scopus_subsurface_MHW.csv
  python3 enrich_authors.py scopus_all_MHW.csv scopus_all_MHW_enriched.csv
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error

CACHE_FILE = "author_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def fetch_authors_from_crossref(doi):
    """Fetch author list from CrossRef API for a given DOI."""
    url = f"https://api.crossref.org/works/{urllib.request.quote(doi, safe='')}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "PaperBrowser/1.0 (mailto:a.sengupta@unsw.edu.au)"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            authors = data.get("message", {}).get("author", [])
            names = []
            for a in authors:
                given = a.get("given", "")
                family = a.get("family", "")
                if family:
                    names.append(f"{family}, {given}".strip(", "))
            return "; ".join(names)
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
        print(f"  Failed for DOI {doi}: {e}")
        return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 enrich_authors.py <input.csv> [output.csv]")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else input_csv.replace(".csv", "_enriched.csv")

    cache = load_cache()

    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} papers from {input_csv}")
    print(f"Cache has {len(cache)} entries")

    new_fieldnames = fieldnames + ["authors"] if "authors" not in fieldnames else fieldnames
    total = len(rows)
    fetched = 0

    for i, row in enumerate(rows):
        doi = row.get("prism:doi", "").strip()
        title = row.get("dc:title", "")[:60]

        if doi in cache:
            row["authors"] = cache[doi]
            continue

        if not doi:
            row["authors"] = ""
            continue

        fetched += 1
        print(f"[{i+1}/{total}] Fetching: {title}...")
        authors = fetch_authors_from_crossref(doi)
        row["authors"] = authors
        cache[doi] = authors

        # Save cache every 20 fetches
        if fetched % 20 == 0:
            save_cache(cache)
            print(f"  Cache saved ({len(cache)} entries)")

        # Polite rate limiting
        time.sleep(0.3)

    save_cache(cache)

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with_authors = sum(1 for r in rows if r.get("authors"))
    print(f"\nDone! {with_authors}/{total} papers have author data.")
    print(f"Output: {output_csv}")

if __name__ == "__main__":
    main()
