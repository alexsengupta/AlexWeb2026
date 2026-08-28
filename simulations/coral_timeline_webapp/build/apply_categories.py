#!/usr/bin/env python3
"""
Add the controlled category vocabulary to the events master.

Reads coral_reef_events_master_clean.csv and category_map.json, and writes a new
CSV with three appended columns:

    category        the controlled category (7 values)
    category_group  its family (3 values)
    evidence_type   collapsed from knowledge_frame (8 values)

The original `event_category` and `knowledge_frame` are left untouched. That is
deliberate and follows the project's own update rule: append, never overwrite, so
any mapping decision can be revisited from the source values.

    python3 scripts/apply_categories.py \
        --events coral_reef_events_master_clean.csv \
        --map scripts/category_map.json \
        --out coral_reef_events_master_categorised.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="coral_reef_events_master_clean.csv")
    ap.add_argument("--map", default="scripts/category_map.json")
    ap.add_argument("--out", default="coral_reef_events_master_categorised.csv")
    args = ap.parse_args()

    cmap = json.loads(Path(args.map).read_text(encoding="utf-8"))
    cats = cmap["categories"]

    old2new = {}
    for c in cats:
        for src in c["from"]:
            if src in old2new:
                raise SystemExit(f"'{src}' is mapped by two categories; the map must partition")
            old2new[src] = c
    rules = [(re.compile(p, re.I), label) for p, label in cmap["evidence_rules"]]
    default = cmap["evidence_default"]

    def evidence_of(frame: str) -> str:
        for rx, label in rules:
            if rx.search(frame):
                return label
        return default

    with open(args.events, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    fields = list(rows[0].keys())

    unmapped = sorted({r["event_category"] for r in rows if r["event_category"] not in old2new})
    if unmapped:
        raise SystemExit("source categories with no mapping: " + ", ".join(unmapped))

    cat_n, fam_n, ev_n = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rows:
        c = old2new[r["event_category"]]
        r["category"] = c["name"]
        r["category_group"] = c["family"]
        r["evidence_type"] = evidence_of(r.get("knowledge_frame", ""))
        cat_n[c["name"]] += 1
        fam_n[c["family"]] += 1
        ev_n[r["evidence_type"]] += 1

    out_fields = fields + ["category", "category_group", "evidence_type"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    print(f"{n} events, all mapped. Wrote {args.out}")
    print(f"\n{'category':<34}{'n':>4}{'share':>8}")
    for c in cats:
        k = c["name"]
        print(f"{k:<34}{cat_n[k]:>4}{cat_n[k]/n*100:>7.1f}%")
    print(f"\n{'family':<34}{'n':>4}{'share':>8}")
    for k, v in fam_n.most_common():
        print(f"{k:<34}{v:>4}{v/n*100:>7.1f}%")
    print(f"\n{'evidence type':<34}{'n':>4}")
    for k, v in ev_n.most_common():
        print(f"{k:<34}{v:>4}")
    print(f"\nbalance: smallest {min(cat_n.values())}, largest {max(cat_n.values())}, "
          f"ratio {max(cat_n.values())/min(cat_n.values()):.1f}x")


if __name__ == "__main__":
    main()
