#!/usr/bin/env python3
"""Apply the fidelity reviewers' corrections to the simplified text.

Three independent reviewers checked all 175 rewrites against the vetted original,
looking only for meaning drift. They found 18 problems: 0 that would change what a
reader believes, 5 that broadened or hardened a claim, 13 imprecise but not
misleading. Each fix below is written out in full rather than applied by pattern,
so the change is reviewable and cannot silently hit the wrong event.

field: h = basic_headline, s = basic_significance, w = basic_why
"""
FIXES = [
 # ---- broadened or hardened claims (medium) --------------------------------
 ("CR-051","h","Darwin works out how reefs form as islands sink",
             "Darwin comes up with a theory that reefs form as islands sink"),
 ("CR-053","h","Dana publishes the first big worldwide study of corals",
             "Dana publishes the first big organised study of corals from a worldwide expedition"),
 ("CR-064","h","First crown of thorns outbreaks recorded on the Great Barrier Reef",
             "First crown of thorns outbreaks of modern times recorded on the Great Barrier Reef"),
 ("CR-071","h","Mass bleaching first entered the scientific record",
             "Modern mass bleaching entered the scientific record"),
 ("CR-118","s","Some of that survival was passed down from parent corals, and some came from the corals getting used to the heat.",
             "That survival was linked to two things: traits passed down from parent corals, and the corals getting used to the heat."),
 # ---- imprecise (low) ------------------------------------------------------
 ("CR-044","s","Local systems such as rahui and tabu set seasonal rules for using those grounds.",
             "Communities owned fishing grounds, closed them at times and set seasonal rules, through customary systems such as rahui and tabu."),
 ("CR-047","w","It ties together sailing, the study of nature and later colonial use of these places.",
             "It ties together sailing, the study of nature and the way colonists later exploited these places."),
 ("CR-056","s","He said the banks grow as material settles from the open water and other parts dissolve away",
             "He argued reefs can build up on underwater banks, as material settles out of the open water and other parts dissolve away"),
 ("CR-058","w","even though the hole did not settle the debate",
             "even though the hole did not settle the debate for certain"),
 ("CR-061","w","It was the strongest direct test of Darwin's idea that the volcanoes slowly sank.",
             "It was the strongest direct test yet, and it backed up Darwin's idea that the volcanoes slowly sank."),
 ("CR-070","h","A new idea said some disturbance keeps reefs rich in species",
             "A new idea said some disturbance can keep reefs rich in species"),
 ("CR-078","h","A disease killed off the Caribbean's main grazing urchin",
             "A disease killed huge numbers of the Caribbean's main grazing urchin"),
 ("CR-101","h","Record heat causes widespread bleaching across the Caribbean",
             "Record heat and widespread bleaching across the Caribbean"),
 ("CR-106","s","CO2 seeps naturally out of the sea floor",
             "CO2 leaks naturally into the sea"),
 ("CR-124","w","It moves attention towards helpful local organisations and people caring for their own reefs.",
             "It moves attention towards organisations that make success possible, and towards people caring for their own reefs."),
 ("PJ-018","h","Corals could hold enough genetic variety to adapt over 100 to 250 years",
             "Corals across one region could hold enough genetic variety to adapt over 100 to 250 years"),
]
# Two rewrites needed replacing outright rather than patching a phrase.
REPLACE = {
 ("CR-121","s"): "Scientists tagged coral colonies and followed them through the heatwave. "
                 "The colonies differed in how they resisted the heat and how they recovered. "
                 "The tiny algae living inside the corals, and local disturbance, shaped those different paths.",
 ("CR-154","s"): "The update keeps the same figures as before. About 84.4% of the world's reef area "
                 "was exposed, and at least 83 countries and territories were affected.",
}

if __name__ == "__main__":
    import json, glob, re
    KEY = {"h":"basic_headline","s":"basic_significance","w":"basic_why"}
    files = sorted(glob.glob("basic/out/batch*.json"),
                   key=lambda p: int(re.search(r"\d+", p.split("/")[-1]).group()))
    data = {f: json.load(open(f)) for f in files}
    idx = {o["event_id"]: (f, o) for f, arr in data.items() for o in arr}

    done, miss = 0, []
    for eid, fld, old, new in FIXES:
        _, o = idx[eid]; k = KEY[fld]
        if old in o[k]:
            o[k] = o[k].replace(old, new); done += 1
        else:
            miss.append(f"{eid}.{fld}")
    for (eid, fld), new in REPLACE.items():
        _, o = idx[eid]; o[KEY[fld]] = new; done += 1

    for f, arr in data.items():
        json.dump(arr, open(f, "w"), ensure_ascii=False, indent=1)
    print(f"applied {done} of {len(FIXES)+len(REPLACE)} corrections")
    print(f"phrases that did not match: {miss or 'none'}")
