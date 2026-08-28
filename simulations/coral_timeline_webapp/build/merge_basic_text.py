#!/usr/bin/env python3
"""Merge the plain-language text and the verified educational links into the master.

Two modes ship in one file. Advanced is the existing text with its citations and
abstracts; basic is this text, for readers around 11 to 14, with no journal
references at all. The basic text is a restatement of the vetted advanced text and
adds no facts to it. Three independent reviewers checked every rewrite against its
original for meaning drift; their 18 corrections are in basic/fixes.py.

Links are only attached where a verified general-audience page genuinely covers
that event's subject. 46 of 175 events carry no link, which is the intended
outcome: a wrong link is worse than no link.
"""
import csv, json, glob, re
from pathlib import Path

out = []
for f in sorted(glob.glob("basic/out/batch*.json"),
                key=lambda p: int(re.search(r"\d+", p.split("/")[-1]).group())):
    out += json.load(open(f))
B = {o["event_id"]: o for o in out}
LK = json.loads(Path("basic/links.json").read_text())

rows = list(csv.DictReader(open("coral_reef_events_master_projected.csv", encoding="utf-8-sig")))
NEW = ["basic_headline", "basic_significance", "basic_why", "basic_links"]
fields = list(rows[0].keys()) + NEW

nlink = 0
for r in rows:
    b = B[r["event_id"]]
    r["basic_headline"]     = b["basic_headline"]
    r["basic_significance"] = b["basic_significance"]
    r["basic_why"]          = b["basic_why"]
    links = []
    for tid in LK["events"].get(r["event_id"], []):
        t = LK["topics"][tid]
        for l in t["links"]:
            links.append({"t": l["title"], "u": l["url"], "p": l["publisher"], "s": t["label"]})
    # two links is plenty for a child; more reads as a reading list
    links = links[:2]
    if links: nlink += 1
    r["basic_links"] = json.dumps(links, ensure_ascii=False) if links else ""

with open("coral_reef_events_master_basic.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)

print(f"Wrote coral_reef_events_master_basic.csv: {len(rows)} events")
print(f"  with plain-language text : {sum(1 for r in rows if r['basic_headline'])}")
print(f"  with a 'find out more' link : {nlink}")
print(f"  with no link, by design     : {len(rows)-nlink}")
