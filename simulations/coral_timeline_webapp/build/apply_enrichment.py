#!/usr/bin/env python3
"""
Merge the retrieval results into a per-event enrichment file.

Each of an event's two sources gets an explicit status. Only 'verified' sources
carry retrieved text; a source whose DOI resolved to a different paper, or did
not resolve at all, carries none. That gate is the point of this script: without
it, a wrong DOI would silently pull a wrong abstract into the timeline, and the
result would look entirely convincing.

    python3 scripts/apply_enrichment.py \
        --events coral_reef_events_master_categorised.csv \
        --batches "enrich_batch_*.json" \
        --out data/derived/events_enriched.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
from pathlib import Path

RETRIEVED = "2026-08-12"
CC = ("creativecommons", "cc-by", "cc0", "publicdomain")


def status_of(rec: dict | None) -> str:
    if rec is None:
        return "not-checked"
    if not rec.get("resolves"):
        return "dead"
    note = (rec.get("notes") or "").lower()
    if "tombstone" in note or "deleted" in note:
        return "tombstone"
    if rec.get("title_match") == "MISMATCH":
        return "wrong-paper"
    if len((rec.get("abstract") or "").strip()) >= 200:
        return "verified"
    return "no-abstract"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="coral_reef_events_master_categorised.csv")
    ap.add_argument("--batches", default="enrich_batch_*.json")
    ap.add_argument("--out", default="data/derived/events_enriched.json")
    args = ap.parse_args()

    import csv
    recs = {}
    for f in sorted(glob.glob(args.batches)):
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            recs[r["doi"].strip()] = r

    with open(args.events, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    out, tally = [], collections.Counter()
    for r in rows:
        e = {"event_id": r["event_id"]}
        for n in ("1", "2"):
            url = r[f"source_{n}_url"].strip()
            pre = f"s{n}_"
            if not url:
                e[pre + "status"] = "none"
                continue
            if "doi.org" not in url:
                e[pre + "status"] = "non-doi"
                tally["non-doi"] += 1
                continue
            doi = url.split("doi.org/")[-1].strip()
            rec = recs.get(doi)
            st = status_of(rec)
            e[pre + "status"] = st
            e[pre + "doi"] = doi
            tally[st] += 1
            if st != "verified":
                # a failed source contributes nothing but its status
                continue
            lic = (rec.get("licence") or "").lower()
            e.update({
                pre + "title_actual": rec.get("title_actual", ""),
                pre + "journal": rec.get("journal", ""),
                pre + "year": rec.get("year", ""),
                pre + "first_author": rec.get("first_author", ""),
                pre + "oa_url": rec.get("oa_url", "") or "",
                pre + "open_licence": any(k in lic for k in CC),
                pre + "abstract": rec["abstract"].strip(),
                pre + "abstract_source": rec.get("abstract_source", ""),
                pre + "abstract_chars": len(rec["abstract"].strip()),
                pre + "retrieved": RETRIEVED,
            })
        out.append(e)

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    ev_ok = sum(1 for e in out if e.get("s1_status") == "verified" or e.get("s2_status") == "verified")
    ev_bad = sum(1 for e in out if "wrong-paper" in (e.get("s1_status"), e.get("s2_status")))
    print(f"Wrote {dest}")
    print(f"  {len(out)} events | {ev_ok} with at least one verified source "
          f"| {ev_bad} citing a wrong paper")
    for k, v in tally.most_common():
        print(f"    {k:<14} {v:>4} sources")


if __name__ == "__main__":
    main()
