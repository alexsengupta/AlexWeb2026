"""
Classify marine heatwave papers into thematic categories using OpenAI API.

Reads a Scopus CSV, sends each paper's title + abstract to GPT-4o-mini,
and writes an output CSV with a 'themes' column containing the assigned
theme numbers (e.g. "3,7,13").

Usage:
  export OPENAI_API_KEY="your-key-here"
  python3 classify_themes.py scopus_all_MHW.csv scopus_all_MHW_themed.csv

Supports resume: re-running skips papers already in the output file.
"""

import csv
import json
import os
import sys
import time
import requests

# -----------------------------
# CONFIG
# -----------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

CACHE_FILE = "theme_cache.json"

THEMES = {
    1: "Definition and detection of marine heatwaves: threshold-based definitions (percentiles, climatologies), event metrics (duration, intensity, cumulative heat stress), sensitivity to baseline choice and detrending, comparison of alternative MHW definitions.",
    2: "Surface marine heatwaves (SST-based): SST-derived MHWs as the dominant observational framework, satellite-based detection and biases, regional vs global SST MHW characteristics.",
    3: "Subsurface marine heatwaves: heatwave expression below the mixed layer, decoupling between surface and subsurface extremes, relevance for mesopelagic and benthic ecosystems, role of stratification and vertical heat storage.",
    4: "Physical drivers and mechanisms: atmospheric forcing (heat fluxes, winds), ocean dynamics (advection, upwelling suppression), role of stratification and mixed-layer depth, local vs remote forcing.",
    5: "Climate change influence on MHWs: long-term trends in frequency/duration/intensity, anthropogenic warming attribution, shifts in baseline conditions, emergence of 'new normal' thermal extremes.",
    6: "Extreme events and compound extremes: record-breaking or unprecedented MHWs, interaction with marine cold spells/hypoxia/acidification, compound climate extremes.",
    7: "Ecological and biological impacts: impacts on species distributions and mortality, thermal stress responses, trophic interactions, ecosystem-level consequences.",
    8: "Coral reef impacts and bleaching: coral bleaching linked to MHW metrics, thermal thresholds and recovery, regional reef vulnerability, repeated heat stress and resilience loss.",
    9: "Fisheries and socio-economic impacts: impacts on fisheries productivity, species redistribution affecting fisheries, economic consequences of MHWs, management implications.",
    10: "Regional case studies: Pacific, coastal systems and marginal seas, regional expressions of global-scale warming, event-focused analyses (e.g. specific years).",
    11: "Ecosystem vulnerability and resilience: differential vulnerability among ecosystems, acclimation and adaptation, legacy effects of past MHWs, recovery timescales.",
    12: "Modeling and predictability: representation of MHWs in climate models, model biases in extremes, seasonal to interannual predictability, event forecasting and early warning.",
    13: "Vertical heat content and thermal structure: heat storage in the upper ocean, role of thermal stratification, vertical coherence of MHWs, heatwave depth penetration.",
    14: "Impacts on biodiversity and species range shifts: poleward shifts, local extirpations, changes in community composition, links between MHWs and biogeography.",
    15: "Metrics, datasets, and methodological advances: new datasets and diagnostics, comparison of observational and reanalysis products, uncertainty quantification, best practices for MHW analysis.",
}


def build_prompt(title, abstract):
    theme_list = "\n".join(f"  {k}. {v}" for k, v in THEMES.items())

    text = abstract if abstract else "(no abstract available)"

    return f"""You are classifying marine heatwave research papers into thematic categories.

Given the paper title and abstract below, assign it to ONE or MORE of the following 15 themes. Only assign themes that are clearly relevant — do not over-assign.

THEMES:
{theme_list}

PAPER TITLE: {title}

PAPER ABSTRACT: {text}

Respond with ONLY a JSON array of the theme numbers that apply, e.g. [3, 7, 13]. No other text."""


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def classify_paper(title, abstract, cache):
    """Call OpenAI to classify a paper. Returns list of theme numbers."""
    cache_key = title[:100]  # use truncated title as cache key

    if cache_key in cache:
        return cache[cache_key]

    prompt = build_prompt(title, abstract)

    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 100,
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
            return []

        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()

        # Parse the JSON array from the response
        # Handle cases where the model wraps it in markdown code blocks
        text = text.replace("```json", "").replace("```", "").strip()
        themes = json.loads(text)

        # Validate: only keep numbers 1-15
        themes = sorted(set(int(t) for t in themes if 1 <= int(t) <= 15))

        cache[cache_key] = themes
        return themes

    except Exception as e:
        print(f"    Error classifying: {e}")
        return []


def main():
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("  export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python3 classify_themes.py <input.csv> [output.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace(".csv", "_themed.csv")

    # Read input CSV
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        input_fields = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} papers from {input_file}")

    # Check for existing output to resume from
    existing_eids = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row.get("eid", "")
                if eid:
                    existing_eids.add(eid)

    if existing_eids:
        print(f"Found existing {output_file} with {len(existing_eids)} rows – resuming.")
        mode = "a"
        write_header = False
    else:
        mode = "w"
        write_header = True

    output_fields = input_fields + ["themes"] if "themes" not in input_fields else input_fields
    cache = load_cache()
    print(f"Theme cache has {len(cache)} entries")

    total = len(rows)
    written = len(existing_eids)
    start_time = time.time()

    with open(output_file, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        if write_header:
            writer.writeheader()

        for idx, row in enumerate(rows, start=1):
            eid = row.get("eid", "")

            if eid in existing_eids:
                continue

            title = row.get("dc:title", "")
            abstract = row.get("abstract", "")

            elapsed = time.time() - start_time
            new_written = written - len(existing_eids) + 1
            rate = new_written / max(elapsed, 1)
            remaining = total - idx
            eta_min = (remaining / max(rate, 0.01)) / 60

            print(f"[{idx}/{total}] {title[:65]}...  (ETA: {eta_min:.0f} min)")

            themes = classify_paper(title, abstract, cache)
            row["themes"] = ",".join(str(t) for t in themes)

            writer.writerow(row)
            f.flush()

            written += 1

            # Save cache periodically
            if written % 50 == 0:
                save_cache(cache)
                print(f"  Cache saved ({len(cache)} entries)")

            time.sleep(0.3)  # polite rate limiting

    save_cache(cache)

    print(f"\nDone! {written} papers classified in {output_file}")
    print(f"Theme cache saved with {len(cache)} entries")

    # Print theme distribution summary
    print("\n--- Theme Distribution ---")
    theme_counts = {k: 0 for k in THEMES}
    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for t in row.get("themes", "").split(","):
                t = t.strip()
                if t and t.isdigit():
                    theme_counts[int(t)] = theme_counts.get(int(t), 0) + 1

    for k in sorted(theme_counts):
        name = THEMES[k].split(":")[0]
        print(f"  {k:2d}. {name}: {theme_counts[k]}")


if __name__ == "__main__":
    main()
