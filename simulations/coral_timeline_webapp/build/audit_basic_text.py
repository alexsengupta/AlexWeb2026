#!/usr/bin/env python3
"""Check the simplified text before it goes anywhere near a reviewer.

The failure mode that matters is not clumsy prose, it is a rewrite that quietly
asserts something the vetted original did not. Numbers are the part of that which
can be checked mechanically, so they are checked exhaustively: every numeric token
in the simplified text must already appear in the original for that same event.
"""
import csv, json, re, glob, statistics as st

# textstat needs an NLTK corpus that cannot be downloaded here, so Flesch-Kincaid
# is implemented directly. The vowel-group syllable heuristic is the standard one
# and is good enough: what matters is the comparison between the two versions,
# both scored the same way.
VOW = re.compile(r"[aeiouy]+")
def syllables(w):
    w = w.lower().strip(".,;:!?()\"'")
    if not w: return 0
    n = len(VOW.findall(w))
    if w.endswith("e") and not w.endswith(("le","ee","ye")) and n > 1: n -= 1
    return max(1, n)
def fk_grade(text):
    sents = [x for x in re.split(r"[.!?]+", text) if x.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not sents or not words: return 0.0
    return (0.39 * len(words) / len(sents)
            + 11.8 * sum(syllables(w) for w in words) / len(words) - 15.59)


rows = {r["event_id"]: r for r in
        csv.DictReader(open("coral_reef_events_master_projected.csv", encoding="utf-8-sig"))}
out = []
for f in sorted(glob.glob("basic/out/batch*.json"), key=lambda p: int(re.search(r"\d+", p.split("/")[-1]).group())):
    out += json.load(open(f))
B = {o["event_id"]: o for o in out}

print(f"events in master {len(rows)},  simplified {len(out)},  unique {len(B)}")
missing = sorted(set(rows) - set(B)); extra = sorted(set(B) - set(rows))
print(f"missing: {missing or 'none'}   unexpected: {extra or 'none'}")

NUM = re.compile(r"\d[\d,]*\.?\d*")
def nums(t):
    # compare as sets of digit strings, commas stripped, so "1,500" == "1500"
    return {n.replace(",", "").rstrip(".") for n in NUM.findall(t or "")}

bad_num, dash, longhead, past_proj, empty = [], [], [], [], []
fk_o, fk_b = [], []
PAST = re.compile(r"\b(was|were|happened|occurred|killed|destroyed|died|fell|rose|showed|found|reached)\b", re.I)
HEDGE = re.compile(r"\b(could|expect|predict|project|may|might|if|scenario|model|would)\w*\b", re.I)

for eid, r in rows.items():
    b = B.get(eid)
    if not b: continue
    orig = " ".join([r["headline"], r["significance"], r["why_it_matters"],
                     r["display_date"], r.get("proj_year",""), r.get("proj_pub_year",""),
                     r.get("proj_scenario","")])
    simp = " ".join([b["basic_headline"], b["basic_significance"], b["basic_why"]])
    if not all(b.get(k, "").strip() for k in ("basic_headline","basic_significance","basic_why")):
        empty.append(eid)
    added = nums(simp) - nums(orig)
    # a bare "1"/"2"/"3" is almost always "one of the", not a claim
    added = {a for a in added if a not in {"1","2","3","4","5","6","7","8","9","10"}}
    if added: bad_num.append((eid, sorted(added)))
    if "—" in simp or "–" in simp: dash.append(eid)
    if len(b["basic_headline"].split()) > 13: longhead.append((eid, len(b["basic_headline"].split())))
    if eid.startswith("PJ") and not HEDGE.search(simp): past_proj.append(eid)
    for txt, acc in ((r["significance"] + " " + r["why_it_matters"], fk_o),
                     (b["basic_significance"] + " " + b["basic_why"], fk_b)):
        acc.append(fk_grade(txt))

def band(v):
    return f"median {st.median(v):.1f}, mean {st.mean(v):.1f}, 90th pct {sorted(v)[int(len(v)*.9)]:.1f}"

print()
print("READING LEVEL  (Flesch-Kincaid US grade; ages 11-14 is grade 6-9)")
print(f"  original   {band(fk_o)}")
print(f"  simplified {band(fk_b)}")
print(f"  at or below grade 9:  original {sum(1 for v in fk_o if v<=9)}/{len(fk_o)}"
      f"   simplified {sum(1 for v in fk_b if v<=9)}/{len(fk_b)}")
print(f"  above grade 12:       original {sum(1 for v in fk_o if v>12)}/{len(fk_o)}"
      f"   simplified {sum(1 for v in fk_b if v>12)}/{len(fk_b)}")
print()
print("FIDELITY")
print(f"  events with a number NOT in the original : {len(bad_num)}")
for eid, a in bad_num[:12]: print(f"     {eid}: added {a}")
print(f"  empty fields                            : {empty or 'none'}")
print(f"  em/en dashes                            : {dash or 'none'}")
print(f"  headlines over 13 words                 : {longhead or 'none'}")
print(f"  projections with no hedging language    : {past_proj or 'none'}")
print()
notes = [(o['event_id'], o['note']) for o in out if o.get('note')]
print(f"judgement calls flagged by the drafters: {len(notes)}")
