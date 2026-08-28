#!/usr/bin/env python3
"""Append the 21 verified projection events to the events master.

Placement rule, following the brief: a study that states a projection year is
placed at that year; a study that states only a warming level or an emissions
scenario goes into a separate chapter past the dated ones, whose position on the
corridor carries no claim about timing. The chapter label says so.

Publication year and projection year are kept as separate columns and both are
shown on the card. Conflating them is the obvious way to mislead here: a 2016
paper projecting 2070 is not a 2070 event.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from projections import P

MASTER = "coral_reef_events_master_sourced.csv"
OUT    = "coral_reef_events_master_projected.csv"

NEW_COLS = ["is_projection", "proj_year", "proj_pub_year", "proj_scenario",
            "proj_quote", "proj_quote_note", "proj_undated",
            "abstract_agreement", "abstract_src"]

rows = list(csv.DictReader(open(MASTER, encoding="utf-8-sig")))
fields = list(rows[0].keys()) + NEW_COLS
for r in rows:
    for c in NEW_COLS:
        r[c] = ""

# Undated projections need a position, but must never display a year. They are
# given synthetic calendar slots after the last dated projection purely so the
# solver has a strict order to work with; proj_undated marks them so the app
# prints the scenario instead.
UNDATED_BASE, UNDATED_STEP = 2110, 2

und = 0
for p in P:
    if p["proj_year"]:
        year = p["proj_year"]
        chapter = "Projected: 2027–2100"
        disp = str(year)
        undated = ""
    else:
        year = UNDATED_BASE + UNDATED_STEP * und
        und += 1
        chapter = "Scenario, no date given"
        disp = p["scenario"]
        undated = "yes"

    rows.append({
        "event_id": p["id"],
        "display_date": disp,
        "end_range": "",
        "sort_year": f"{year}",
        "age_ma": "",
        "year_ce": f"{year}",
        "nonlinear_time_bin": chapter,
        "suggested_nonlinear_coordinate": "",
        "headline": p["headline"],
        "significance": p["significance"],
        "event_category": "Projection",
        "knowledge_frame": "Model projection",
        "regional_track": p["region"],
        "location": p["region"],
        "reef_system": p["region"],
        "why_it_matters": p["why"],
        "source_1_title": p["title"],
        "source_1_url": f"https://doi.org/{p['doi']}",
        "source_1_type": p["stype"],
        "source_2_title": "", "source_2_url": "", "source_2_type": "",
        "confidence": "High",
        "animation_priority": "Core",
        "editorial_notes": "Projection. Placed at its stated projection year; "
                           "see proj_* columns." if p["proj_year"] else
                           "Projection stated against a warming level or emissions "
                           "scenario, not a date. Corridor position implies no timing.",
        "category": p["category"],
        "category_group": p["group"],
        "evidence_type": p["evidence"],
        "is_projection": "yes",
        "proj_year": str(p["proj_year"]) if p["proj_year"] else "",
        "proj_pub_year": str(p["pub_year"]),
        "proj_scenario": p["scenario"],
        "proj_quote": p["quote"],
        "proj_quote_note": p["quote_note"] or "",
        "proj_undated": undated,
        "abstract_agreement": p["agreement"],
        "abstract_src": p["asrc"],
    })

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader(); w.writerows(rows)

print(f"Wrote {OUT}: {len(rows)} events ({len(P)} projections added)")
print(f"  dated projections   : {sum(1 for p in P if p['proj_year'])}")
print(f"  undated projections : {sum(1 for p in P if not p['proj_year'])}")
