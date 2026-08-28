#!/usr/bin/env python3
"""
Inline the solved timeline axis and the coral SVG set into the corridor template,
producing a single self-contained HTML file (no network, no build toolchain).

Run build_timeline_axis.py first; this consumes its JSON output.

    python3 scripts/build_corridor.py \
        --json data/derived/timeline_axis.json \
        --template scripts/corridor_template.html \
        --coral-dir SVG/optimised \
        --coral-manifest scripts/coral_manifest.json \
        --out timeline_corridor.html

To add a coral: drop the .svg in the coral folder, add an entry to the manifest,
re-run. Running the files through `svgo --precision=1` first roughly halves them;
Illustrator exports carry far more coordinate precision than a silhouette needs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DATA_PLACEHOLDER = "/*__TIMELINE_DATA__*/"
CORAL_PLACEHOLDER = "/*__CORAL_DATA__*/"
CATEGORY_PLACEHOLDER = "/*__CATEGORY_DATA__*/"
TIMESCALE_PLACEHOLDER = "/*__TIMESCALE_DATA__*/"

VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"([^"]+)"')
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
DECL_RE = re.compile(r"<\?xml.*?\?>", re.S)
DOCTYPE_RE = re.compile(r"<!DOCTYPE.*?>", re.S)
# The SVGs are used as CSS masks, so only geometry matters. Styling can go.
STYLE_RE = re.compile(r"<style.*?</style>", re.S)
PAINT_RE = re.compile(r'\s(?:fill|stroke|class|id|style)\s*=\s*"[^"]*"')
WS_RE = re.compile(r">\s+<")


def load_coral(svg_dir: Path, manifest_path: Path) -> list[dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out, missing, unlisted = [], [], []

    files = sorted(
        svg_dir.glob("*.svg"),
        key=lambda p: int(m.group()) if (m := re.search(r"\d+", p.stem)) else 0,
    )
    for path in files:
        key = path.stem
        meta = manifest.get(key)
        if meta is None:
            unlisted.append(key)
            continue

        svg = path.read_text(encoding="utf-8", errors="replace")
        box = VIEWBOX_RE.search(svg)
        if not box:
            missing.append(key)
            continue
        _, _, vw, vh = (float(v) for v in box.group(1).replace(",", " ").split())

        svg = DECL_RE.sub("", svg)
        svg = DOCTYPE_RE.sub("", svg)
        svg = COMMENT_RE.sub("", svg)
        svg = STYLE_RE.sub("", svg)
        # strip paint after removing <style>, but keep the root element's attributes
        head, sep, body = svg.partition(">")
        svg = head + sep + PAINT_RE.sub("", body)
        svg = WS_RE.sub("><", svg).strip()

        out.append({
            "n": meta["name"],
            "r": round(vw / vh, 4),          # width / height, sets the drawn box
            "s": meta.get("scale", 1.0),
            "d": meta.get("detail", "fine"),
            "svg": svg,
        })

    if unlisted:
        print(f"  NOTE: not in manifest, skipped: {', '.join(unlisted)}")
    if missing:
        print(f"  WARNING: no viewBox, skipped: {', '.join(missing)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/derived/timeline_axis.json")
    ap.add_argument("--template", default="scripts/corridor_template.html")
    ap.add_argument("--coral-dir", default="SVG/optimised")
    ap.add_argument("--coral-manifest", default="scripts/coral_manifest.json")
    ap.add_argument("--category-map", default="scripts/category_map.json")
    ap.add_argument("--timescale", default="build/geological_timescale.json",
                    help="ICS geological units, for the period readout")
    ap.add_argument("--enrichment", default="data/derived/events_enriched.json",
                    help="retrieved abstracts and per-source verification status")
    ap.add_argument("--out", default="timeline_corridor.html")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    template = Path(args.template).read_text(encoding="utf-8")

    for ph in (DATA_PLACEHOLDER, CORAL_PLACEHOLDER, CATEGORY_PLACEHOLDER, TIMESCALE_PLACEHOLDER):
        if ph not in template:
            raise SystemExit(f"template is missing the {ph} placeholder")

    # Merge the retrieval results. Only sources marked 'verified' carry text; the
    # rest contribute a status so the page can say plainly that a citation has not
    # been checked, rather than presenting it as if it had.
    enrich_path = Path(args.enrichment)
    if enrich_path.exists():
        enrich = {e["event_id"]: e for e in json.loads(enrich_path.read_text(encoding="utf-8"))}
        hit = 0
        for ev in data["events"]:
            ex = enrich.get(ev["id"])
            if not ex:
                continue
            hit += 1
            for k, v in ex.items():
                if k != "event_id":
                    ev[k] = v
        missing = len(data["events"]) - hit
        if missing:
            print(f"  NOTE: {missing} events had no enrichment record")
        leaked = [ev["id"] for ev in data["events"]
                  for n in ("1", "2")
                  if ev.get(f"s{n}_abstract") and ev.get(f"s{n}_status") != "verified"]
        if leaked:
            raise SystemExit("unverified sources carry abstracts: " + ", ".join(leaked))
    else:
        print(f"  NOTE: no enrichment file at {enrich_path}; building without abstracts")

    keep = {"id", "date", "yearsBP", "chapter", "lane", "x", "headline", "category",
            "region", "confidence", "priority", "significance", "why", "location",
            "end_range", "reef_system", "category_group", "category_source",
            "knowledge_frame", "evidence_type",
            "is_projection", "proj_year", "proj_pub_year", "proj_scenario",
            "proj_quote", "proj_quote_note", "proj_undated",
            "b_head", "b_sig", "b_why", "b_links",
            "source_title", "source_url", "source_type",
            "source2_title", "source2_url", "source2_type"}
    for n in ("1", "2"):
        keep |= {f"s{n}_status", f"s{n}_doi", f"s{n}_title_actual", f"s{n}_journal",
                 f"s{n}_year", f"s{n}_first_author", f"s{n}_oa_url", f"s{n}_open_licence",
                 f"s{n}_abstract", f"s{n}_abstract_source", f"s{n}_retrieved",
                 f"s{n}_abstract_route", f"s{n}_abstract_agreement"}
    data["events"] = [{k: v for k, v in e.items() if k in keep} for e in data["events"]]

    for ev in data["events"]:
        raw = ev.pop("b_links", "")
        if raw:
            try:
                ev["b_links"] = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{ev['id']}: basic_links is not valid JSON ({exc})")
    linked = sum(1 for e in data["events"] if e.get("b_links"))
    plain = sum(1 for e in data["events"] if e.get("b_head"))
    print(f"  plain-language text on {plain} events, "
          f"a further-reading link on {linked}")

    coral = load_coral(Path(args.coral_dir), Path(args.coral_manifest))
    if not coral:
        raise SystemExit("no coral SVGs loaded; check --coral-dir and --coral-manifest")

    def blob(obj) -> str:
        # "</" is escaped so an inlined string can never close the <script> element
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    # Categories and their colours come from the same map the CSV was built with,
    # so the legend and the cards can never drift from the data.
    cmap = json.loads(Path(args.category_map).read_text(encoding="utf-8"))
    cats = [{"name": c["name"], "colour": c["colour"], "family": c["family"]}
            for c in sorted(cmap["categories"], key=lambda c: c["slot"])]
    present = {e.get("category") for e in data["events"]}
    orphan = [c["name"] for c in cats if c["name"] not in present]
    if orphan:
        print(f"  NOTE: categories with no events: {', '.join(orphan)}")
    unknown = sorted(present - {c["name"] for c in cats})
    if unknown:
        raise SystemExit("events carry categories missing from the map: " + ", ".join(unknown))

    html = (template
            .replace(DATA_PLACEHOLDER, blob(data))
            .replace(CORAL_PLACEHOLDER, blob(coral))
            .replace(CATEGORY_PLACEHOLDER, blob(cats))
            .replace(TIMESCALE_PLACEHOLDER,
                     blob(json.loads(Path(args.timescale).read_text(encoding="utf-8")))))

    out = Path(args.out)
    out.write_text(html, encoding="utf-8")

    chunky = sum(1 for c in coral if c["d"] == "chunky")
    print(f"Wrote {out} ({out.stat().st_size / 1024:,.0f} KB)")
    ver = sum(1 for e in data["events"] if e.get("s1_abstract") or e.get("s2_abstract"))
    print(f"  {len(data['events'])} events ({ver} with a verified abstract), "
          f"{len(cats)} categories, {len(coral)} coral forms "
          f"({chunky} chunky / {len(coral) - chunky} fine)")


if __name__ == "__main__":
    main()
