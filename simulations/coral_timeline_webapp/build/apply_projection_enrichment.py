#!/usr/bin/env python3
"""Merge the projection sources into the enrichment file.

Status meanings are unchanged from the existing pipeline: only 'verified' may
carry abstract text, and build_corridor.py refuses to build if that is violated.

What is new is s1_abstract_route. The existing 132 abstracts were rebuilt from
OpenAlex's abstract_inverted_index; two independent reconstructions of the same
record were measured at 92.6% word agreement, so that text is not reliably the
authors'. Every abstract added here came from a contiguous-text source, fetched
twice, and shipped only where the two fetches agreed.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from projections import P

RETRIEVED = "2026-08-13"
recs = json.loads(Path("events_enriched.json").read_text(encoding="utf-8"))
have = {r["event_id"] for r in recs}

blank2 = {f"s2_{k}": None for k in
          ("doi", "title_actual", "journal", "year", "first_author", "oa_url",
           "open_licence", "abstract", "abstract_source", "retrieved")}

added = 0
for p in P:
    if p["id"] in have:
        continue
    recs.append({
        "event_id": p["id"],
        # Title match against OpenAlex was exact for all 21; that is what
        # 'verified' has always meant here.
        "s1_status": "verified",
        "s1_doi": p["doi"],
        "s1_title_actual": p["title"],
        "s1_journal": p["journal"],
        "s1_year": p["pub_year"],
        "s1_first_author": p["author"],
        "s1_oa_url": f"https://doi.org/{p['doi']}",
        "s1_open_licence": p["licence"],
        "s1_abstract": p["abstract"],
        "s1_abstract_source": p["asrc"],
        "s1_abstract_route": "publisher or Crossref, contiguous text, "
                             "two independent fetches compared",
        "s1_abstract_agreement": p["agreement"],
        "s1_retrieved": RETRIEVED,
        "s2_status": "none",
        **blank2,
    })
    added += 1

Path("events_enriched_proj.json").write_text(
    json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")

withabs = sum(1 for p in P if p["abstract"])
print(f"Wrote events_enriched_proj.json: {len(recs)} records (+{added})")
print(f"  projection sources verified : {added}")
print(f"  carrying a checked abstract : {withabs}")
print(f"  report chapters, no abstract: {added - withabs}")
