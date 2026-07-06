import requests
import csv
import json
import os
import time

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = os.environ.get("ELSEVIER_API_KEY", "")
if not API_KEY:
    raise RuntimeError("ELSEVIER_API_KEY is not set in the environment.")

# Query targeting polar marine heatwaves (Arctic and Antarctic)
SCOPUS_QUERY = (
    'TITLE-ABS-KEY('
    '("marine heatwave*" OR "marine heat wave*" OR MHW) AND '
    '(Arctic OR Antarctic OR "Southern Ocean" OR "polar region*" OR "high latitude*" OR "sea ice")'
    ')'
)

SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
ABSTRACT_URL = "https://api.elsevier.com/content/abstract/eid/"

OUTPUT_FILE = "scopus_polar_MHW.csv"
SEARCH_CACHE = "scopus_polar_MHW_search_cache.json"
CACHE_MAX_AGE_DAYS = 3  # re-fetch from Scopus if cache is older than this

# --- OpenAI theme classification (optional) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
THEME_CACHE_FILE = "theme_cache_polar.json"

THEMES = {
    1: "Arctic focus: marine heatwaves in Arctic Ocean and adjacent seas (Barents, Chukchi, Beaufort, Kara, Laptev seas), Arctic-specific thermal extremes, warming trends in Arctic waters.",
    2: "Antarctic focus: marine heatwaves around Antarctica and sub-Antarctic regions, Southern Ocean warming extremes south of the Antarctic Circumpolar Current.",
    3: "Southern Ocean: marine heatwaves in the broader Southern Ocean domain, circumpolar dynamics, frontal zones, and inter-basin connections.",
    4: "Marginal ice zone (MIZ): heatwave dynamics at the sea-ice edge, ice-ocean feedbacks in the MIZ, role of open-water formation (polynyas, leads) in thermal extremes.",
    5: "Sea-ice feedbacks: interactions between marine heatwaves and sea-ice extent/thickness, ice-albedo feedbacks, delayed freeze-up or early melt driven by ocean heat.",
    6: "Definition and detection: threshold-based definitions (percentiles, climatologies) applied in polar contexts, event metrics (duration, intensity, cumulative heat stress), challenges of short baselines and non-stationarity in polar regions.",
    7: "Surface marine heatwaves (SST-based): SST-derived MHWs at high latitudes, satellite detection challenges (sea ice, cloud cover), regional characteristics of polar surface extremes.",
    8: "Subsurface marine heatwaves: heatwave expression below the mixed layer in polar seas, Atlantic Water and Pacific Water intrusions, relevance for benthic and under-ice ecosystems.",
    9: "Physical drivers and mechanisms: atmospheric forcing (heat fluxes, winds, cyclones), ocean dynamics (advection, boundary currents, upwelling), stratification and mixed-layer depth in polar settings.",
    10: "Climate change influence: long-term trends in polar MHW frequency/duration/intensity, Atlantification and Pacification of Arctic waters, anthropogenic attribution, 'new normal' thermal conditions.",
    11: "Compound and extreme events: co-occurrence of MHWs with low sea-ice, marine heatwave–cold-spell contrasts, hypoxia, acidification, unprecedented polar heat events.",
    12: "Ecological and biological impacts: impacts on polar species distributions and mortality, thermal stress on cold-adapted organisms, trophic cascades, ecosystem-level consequences.",
    13: "Fisheries and socio-economic impacts: effects on polar fisheries productivity, species redistribution affecting Arctic/Antarctic fisheries, management implications, Indigenous community impacts.",
    14: "Regional case studies: event-focused analyses of specific polar MHW episodes (e.g. specific years or regions), comparisons across Arctic basins or Antarctic sectors.",
    15: "Modelling and predictability: representation of polar MHWs in climate models, model biases at high latitudes, seasonal to interannual predictability, early-warning systems.",
    16: "Observations, datasets, and methods: in-situ measurements (Argo, moorings, ship-based), reanalysis products (ERA5, SOSE), remote sensing at high latitudes, uncertainty quantification, best practices for polar MHW analysis.",
}


# -----------------------------
# Helper: perform GET with retries
# -----------------------------
def get_with_retries(url, *, params=None, headers=None, max_retries=5, base_delay=2.0):
    """
    Perform a GET request with simple exponential backoff on transient errors.
    Retries on: 429, 500, 502, 503, 504.
    Returns (response or None).
    """
    if headers is None:
        headers = {}

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"Request exception on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt == max_retries - 1:
                return None
            delay = base_delay * (2 ** attempt)
            print(f"Waiting {delay:.1f}s before retry...")
            time.sleep(delay)
            continue

        status = resp.status_code
        print(f"HTTP status: {status} (attempt {attempt + 1}/{max_retries})")

        if status == 200:
            return resp

        if status in (429, 500, 502, 503, 504):
            if attempt == max_retries - 1:
                print("Giving up after max retries; last response snippet:")
                print(resp.text[:1000])
                return None
            delay = base_delay * (2 ** attempt)
            print(f"Transient error ({status}), retrying after {delay:.1f}s...")
            time.sleep(delay)
            continue

        print("Non-retryable error from Scopus. Response snippet:")
        print(resp.text[:1000])
        return None

    return None


# -----------------------------
# Fetch Scopus search results
# -----------------------------
def fetch_all_results():
    if os.path.exists(SEARCH_CACHE):
        age_days = (time.time() - os.path.getmtime(SEARCH_CACHE)) / 86400
        if age_days < CACHE_MAX_AGE_DAYS:
            with open(SEARCH_CACHE, "r", encoding="utf-8") as f:
                results = json.load(f)
            print(f"Loaded {len(results)} cached search results from {SEARCH_CACHE} ({age_days:.1f} days old)")
            return results
        else:
            print(f"Search cache is {age_days:.1f} days old (max {CACHE_MAX_AGE_DAYS}) – re-fetching from Scopus.")

    cursor = "*"
    results = []
    batch_idx = 0

    while True:
        print(f"\n=== Fetching batch {batch_idx} with cursor: {cursor} ===")

        params = {
            "query": SCOPUS_QUERY,
            "apiKey": API_KEY,
            "httpAccept": "application/json",
            "view": "STANDARD",
            "count": 200,
            "cursor": cursor,
        }

        response = get_with_retries(SEARCH_URL, params=params, max_retries=5)

        if response is None:
            print("Failed to get a valid response for this batch. Stopping search.")
            break

        try:
            data = response.json()
        except ValueError:
            print("Could not parse JSON. Response snippet:")
            print(response.text[:1000])
            break

        if "search-results" not in data:
            print("No 'search-results' in response. Raw JSON snippet:")
            print(str(data)[:1000])
            break

        sr = data["search-results"]

        total_results = sr.get("opensearch:totalResults")
        print(f"Total results reported by Scopus: {total_results}")

        entries = sr.get("entry", [])
        print(f"Entries in this batch: {len(entries)}")

        for i, e in enumerate(entries[:5]):
            title = e.get("dc:title", "(no title)")
            date = e.get("prism:coverDate", "(no date)")
            print(f"  {i+1}. {title} [{date}]")

        if not entries:
            print("No entries in this batch – stopping.")
            break

        results.extend(entries)

        cursor_obj = sr.get("cursor", {})
        next_cursor = cursor_obj.get("@next")

        if not next_cursor:
            print("No next cursor – reached end of results.")
            break

        cursor = next_cursor
        batch_idx += 1
        time.sleep(0.4)

    if results:
        with open(SEARCH_CACHE, "w", encoding="utf-8") as f:
            json.dump(results, f)
        print(f"\nCached {len(results)} search results to {SEARCH_CACHE}")

    return results


# -----------------------------
# Fetch abstract + authors for a given EID
# -----------------------------
def fetch_abstract_and_authors(eid):
    """Fetch abstract and author list from Scopus Abstract Retrieval API."""
    if not eid:
        return "", ""

    headers = {"Accept": "application/json"}
    params = {"apiKey": API_KEY}

    response = get_with_retries(ABSTRACT_URL + eid, params=params, headers=headers, max_retries=3)

    if response is None:
        return "", ""

    try:
        data = response.json()
    except ValueError:
        return "", ""

    abstract = ""
    authors_str = ""

    try:
        coredata = data["abstracts-retrieval-response"]["coredata"]
        abstract = coredata.get("dc:description", "") or ""
        abstract = abstract.replace("\n", " ").replace("\r", " ")
    except Exception:
        pass

    try:
        authors_data = data["abstracts-retrieval-response"].get("authors", {}).get("author", [])
        if authors_data is None:
            authors_data = []
        names = []
        for a in authors_data:
            pref = a.get("preferred-name", {})
            surname = pref.get("ce:surname", "") or a.get("ce:surname", "")
            given = pref.get("ce:given-name", "") or a.get("ce:given-name", "")
            if surname:
                names.append(f"{surname}, {given}".strip(", "))
        authors_str = "; ".join(names)
    except Exception:
        pass

    return abstract, authors_str


# -----------------------------
# Theme classification helpers
# -----------------------------
def load_theme_cache():
    if os.path.exists(THEME_CACHE_FILE):
        with open(THEME_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_theme_cache(cache):
    with open(THEME_CACHE_FILE, "w") as f:
        json.dump(cache, f)


def build_theme_prompt(title, abstract):
    theme_list = "\n".join(f"  {k}. {v}" for k, v in THEMES.items())
    text = abstract if abstract else "(no abstract available)"
    return f"""You are classifying polar marine heatwave research papers into thematic categories.

Given the paper title and abstract below, assign it to ONE or MORE of the following 16 themes. Only assign themes that are clearly relevant — do not over-assign.

THEMES:
{theme_list}

PAPER TITLE: {title}

PAPER ABSTRACT: {text}

Respond with ONLY a JSON array of the theme numbers that apply, e.g. [1, 9, 15]. No other text."""


def classify_paper_themes(title, abstract, cache):
    """Call OpenAI to classify a paper. Returns comma-separated theme string."""
    cache_key = title[:100]

    if cache_key in cache:
        return ",".join(str(t) for t in cache[cache_key])

    prompt = build_theme_prompt(title, abstract)

    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_completion_tokens": 100,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(OPENAI_URL, json=payload, headers=headers, timeout=30)

        if resp.status_code == 429:
            print("    Rate limited, waiting 30s...")
            time.sleep(30)
            resp = requests.post(OPENAI_URL, json=payload, headers=headers, timeout=30)

        if resp.status_code != 200:
            print(f"    OpenAI error {resp.status_code}: {resp.text[:200]}")
            return ""

        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        themes = json.loads(text)
        themes = sorted(set(int(t) for t in themes if 1 <= int(t) <= 16))

        cache[cache_key] = themes
        return ",".join(str(t) for t in themes)

    except Exception as e:
        print(f"    Error classifying: {e}")
        return ""


# -----------------------------
# Write CSV with resume support
# -----------------------------
def write_metadata_csv(results):
    fields = [
        "dc:title",
        "prism:publicationName",
        "prism:coverDate",
        "prism:volume",
        "prism:issueIdentifier",
        "prism:pageRange",
        "prism:doi",
        "subtype",
        "subtypeDescription",
        "citedby-count",
        "eid",
        "pubmed-id",
        "openaccess",
        "abstract",
        "authors",
        "themes",
    ]

    if not results:
        print("No results to write.")
        return

    existing_eids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row.get("eid", "")
                if eid:
                    existing_eids.add(eid)

    if existing_eids:
        print(f"Found existing {OUTPUT_FILE} with {len(existing_eids)} rows – resuming.")
        mode = "a"
        write_header = False
    else:
        mode = "w"
        write_header = True

    classify = bool(OPENAI_API_KEY)
    if classify:
        print("OpenAI API key found – will classify themes.")
        theme_cache = load_theme_cache()
        print(f"Theme cache has {len(theme_cache)} entries")
    else:
        print("No OPENAI_API_KEY set – skipping theme classification.")
        theme_cache = {}

    total = len(results)
    skipped = 0
    written = len(existing_eids)
    start_time = time.time()

    with open(OUTPUT_FILE, mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        if write_header:
            writer.writeheader()

        for idx, entry in enumerate(results, start=1):
            eid = entry.get("eid", "")

            if eid in existing_eids:
                skipped += 1
                continue

            title = entry.get("dc:title", "(no title)")
            elapsed = time.time() - start_time
            new_written = written - len(existing_eids) + 1
            rate = new_written / max(elapsed, 1)
            remaining = total - idx
            eta_min = (remaining / max(rate, 0.01)) / 60

            print(f"[{idx}/{total}] {title[:60]}...  (ETA: {eta_min:.0f} min)")

            row = {k: entry.get(k, "") for k in fields if k not in ("abstract", "authors", "themes")}
            abstract, authors = fetch_abstract_and_authors(eid)
            row["abstract"] = abstract
            row["authors"] = authors

            if classify:
                row["themes"] = classify_paper_themes(title, abstract, theme_cache)
            else:
                row["themes"] = ""

            writer.writerow(row)
            csvfile.flush()

            written += 1

            if classify and written % 50 == 0:
                save_theme_cache(theme_cache)
                print(f"  Theme cache saved ({len(theme_cache)} entries)")

            time.sleep(0.2)

    if classify:
        save_theme_cache(theme_cache)

    print(f"\nDone! {written} rows in {OUTPUT_FILE} ({skipped} skipped as already present).")


# -----------------------------
# Main
# -----------------------------
def main():
    print("Searching Scopus for polar marine heatwave literature (Arctic & Antarctic)...")
    results = fetch_all_results()
    print(f"\nTotal entries collected: {len(results)}")

    if not results:
        print(
            "\nNo entries collected. Possible reasons:\n"
            "  - Scopus service still intermittently unavailable (503/5xx).\n"
            "  - API key / access restrictions.\n"
            "  - Or the query is too specific (you can test with a broader MHW query)."
        )
    else:
        print("\nFetching abstracts and writing CSV...")
        write_metadata_csv(results)
        print(f"\nOutput saved to: {OUTPUT_FILE}")
        print(f"(To re-run the search from scratch, delete {SEARCH_CACHE})")


if __name__ == "__main__":
    main()
