import csv, requests, time, os

API_KEY   = os.environ.get("ELSEVIER_API_KEY", "")
if not API_KEY:
    raise RuntimeError("ELSEVIER_API_KEY is not set in the environment.")
AUTHOR_ID = "57242726600"
HEADERS   = {"Accept": "application/json", "X-ELS-APIKey": API_KEY}

SEARCH_URL   = "https://api.elsevier.com/content/search/scopus"
ABSTRACT_URL = "https://api.elsevier.com/content/abstract/eid/"

FIELDS = ",".join([
    "dc:title","prism:publicationName","prism:coverDate","prism:volume",
    "prism:issueIdentifier","prism:pageRange","prism:doi","subtype",
    "subtypeDescription","citedby-count","eid","pubmed-id","openaccess"
])

params = {
    "query": f"AU-ID({AUTHOR_ID})",
    "field": FIELDS,
    "count": "200",
    "cursor": "*"
}

rows, seen = [], set()
page = 0

print("Fetching list of papers...")
while True:
    r = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=60)
    r.raise_for_status()
    sr = r.json()["search-results"]
    entries = sr.get("entry", [])
    if not entries:
        break
    page += 1
    print(f"Page {page}: {len(entries)} results")

    for e in entries:
        eid = e.get("eid")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        rows.append({
            "eid": eid,
            "title": e.get("dc:title"),
            "journal": e.get("prism:publicationName"),
            "date": e.get("prism:coverDate"),
            "volume": e.get("prism:volume"),
            "issue": e.get("prism:issueIdentifier"),
            "pages": e.get("prism:pageRange"),
            "doi": e.get("prism:doi"),
            "subtype": e.get("subtype"),
            "subtype_desc": e.get("subtypeDescription"),
            "citedby": e.get("citedby-count"),
            "pmid": e.get("pubmed-id"),
            "open_access": e.get("openaccess"),
            "abstract": None,
            "authors": None
        })

    nxt = (sr.get("cursor") or {}).get("next")
    if not nxt:
        break
    params["cursor"] = nxt
    time.sleep(0.2)

print(f"Retrieved {len(rows)} papers; now fetching abstracts + authors...\n")

for i, row in enumerate(rows, 1):
    eid = row["eid"]
    try:
        url = f"{ABSTRACT_URL}{eid}?view=FULL"
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 200:
            data = r.json()
            resp = data.get("abstracts-retrieval-response", {})
            abstract = resp.get("coredata", {}).get("dc:description")
            row["abstract"] = abstract
            title = row.get("title", eid)
            print(f"[{i}/{len(rows)}] {title[:70]}")

            # Extract authors
            authors_data = resp.get("authors", {})
            if authors_data:
                authors_data = authors_data.get("author", []) or []
            else:
                authors_data = []
            names = []
            for a in authors_data:
                pref = a.get("preferred-name", {})
                surname = pref.get("ce:surname", "") or a.get("ce:surname", "")
                given = pref.get("ce:given-name", "") or a.get("ce:given-name", "")
                if surname:
                    names.append(f"{surname}, {given}".strip(", "))
            row["authors"] = "; ".join(names)
        else:
            print(f"[{i}/{len(rows)}] {eid} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"[{i}/{len(rows)}] {eid} failed: {e}")
    time.sleep(0.5)  # polite delay

outfile = "scopus_alex_sen_gupta_articles_with_abstracts.csv"
with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"\nWrote {len(rows)} records with abstracts to {outfile}")
