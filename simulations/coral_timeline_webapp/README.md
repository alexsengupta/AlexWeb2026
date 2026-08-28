# Coral Reef Timeline

A first-person walk through 175 events in the history of coral reefs, from 3.48 Ga stromatolites
to June 2026, and then past a marked boundary into 21 projections of what could come next. Time
runs along a curving reef crest; each event hangs above it on a card; clicking a card opens its
detail, sources and retrieved abstracts.

It reads at two levels. **Advanced** is the full text with citations and abstracts. **Basic** is
the same events in plain language for the general public and school students of about 11 to 14,
with journal references replaced by verified general-audience pages. Switch in the top bar, or
open `index.html#basic` to start there.

**To view it: open `index.html` in a browser.** Nothing else is required. It is a single
self-contained file with no server, no build step and no network requests.

---

## What is in this folder

```
index.html                     the whole app, ready to open or upload
coral_timeline_basic_text_REVIEW.xlsx
                               the plain-language text, side by side with the original,
                               for you to check and edit
build/                         everything needed to regenerate index.html
  corridor_template.html         the app itself, minus the data
  build_timeline_axis.py         step 1: solves where each event sits along the corridor
  build_corridor.py              step 5: inlines everything into the template
  apply_categories.py            adds the controlled category vocabulary
  apply_enrichment.py            merges retrieved abstracts, gated on verification
  apply_source_fixes.py          applies manual citation corrections
  projections.py                 the 21 projection studies, with their verified abstracts
  make_projection_rows.py        adds the projections to the events master
  apply_projection_enrichment.py merges their sources into the enrichment
  merge_basic_text.py            merges the plain-language text and further-reading links
  basic_text_corrections.py      the 18 fidelity corrections, written out in full
  audit_basic_text.py            checks reading level and that no number was invented
  make_review_workbook.py        builds the review spreadsheet
  apply_basic_review.py          reads your edits back out of it
  basic_links.json               the 55 verified further-reading pages and their topics
  category_map.json              the 7 categories, their families and their colours
  coral_manifest.json            each coral SVG's growth form, scale and detail class
  geological_timescale.json      ICS units, for the period readout
data/
  events_master.csv              the source of truth: 175 events, all fields
  events_enriched.json           retrieved abstracts + per-source verification status
  timeline_axis.json             solved corridor positions (regenerated, not hand-edited)
  timeline_axis_positions.csv    the same, as a spreadsheet
svg/                           16 coral growth-form silhouettes, used as CSS masks
```

---

## Rebuilding after a data change

Run from this folder. Step 1 only matters if you changed the events; step 4 only if you changed
the template, corals or categories.

```bash
# 1. after editing data/events_master.csv, re-solve the corridor positions
python3 build/build_timeline_axis.py --events data/events_master.csv --outdir .
cp data/derived/timeline_axis.json data/timeline_axis.json

# 2. after editing the review spreadsheet, read the plain-language text back in
python3 build/apply_basic_review.py \
    --master data/events_master.csv \
    --workbook coral_timeline_basic_text_REVIEW.xlsx \
    --out data/events_master.csv
#    then re-run step 1

# 3. after new source retrieval, rebuild the enrichment
python3 build/apply_enrichment.py \
    --events data/events_master.csv \
    --batches "enrich_batch_*.json" \
    --out data/events_enriched.json

# 4. rebuild the page
python3 build/build_corridor.py \
    --json data/timeline_axis.json \
    --template build/corridor_template.html \
    --coral-dir svg \
    --coral-manifest build/coral_manifest.json \
    --category-map build/category_map.json \
    --timescale build/geological_timescale.json \
    --enrichment data/events_enriched.json \
    --out index.html
```

Requires Python 3.10+ with `numpy` (the axis solver) and `openpyxl` (the spreadsheet scripts).

---

## The four things worth understanding

### 1. Distance along the corridor is not proportional to time

The walk spans 3.48 billion years. Laid out truthfully, every event after 1950 would sit inside
the last few centimetres and be unreadable. The corridor therefore stretches recent centuries and
compresses deep time, by a factor of about **700 million** between its slowest and fastest stretch.

Position is a layout output, not a formula on time. The solver blends a log-time warp with
event-density spacing, then runs an isotonic minimum-separation pass so no two cards are closer
than a readable gap while order is strictly preserved. About 45% of the spacing between cards is
set by legibility rather than by elapsed time.

Because of this, the app owes the reader an honest scale. The year posts beside the crest, the
local-scale readout in the panel, and the *Why the scale changes* page all exist for that reason.
If you change the look, keep them.

The track's own winding and rise carries **no data**. It is styling, kept small and regular so it
cannot be mistaken for a measurement.

### 2. Nothing unverified shows publication text

Every DOI was resolved and the title it returned compared against the title the spreadsheet
claims. A source is `verified` only if it resolved **and** the titles matched. Only verified
sources carry an abstract, and `build_corridor.py` refuses to build if that is violated.

That check exists because a wrong DOI would otherwise pull a wrong abstract into the timeline,
and the result would look completely convincing. In the first retrieval pass, 14 of 90 DOIs
resolved to entirely different papers, including one that pointed at a study of thigh foam rolling.

| | |
|---|---|
| Events | 175 |
| Events with at least one verified abstract | 119 |
| Verified sources | 170 |
| Sources that resolve but publish no abstract | 69 |
| Non-DOI sources (reports, legislation, archives) | 88 |
| Sources pointing at the wrong paper | 0 |
| Dead or withdrawn DOIs | 0 |
| Events with no source at all | 0 |

#### How abstracts are retrieved, and why that changed

The first 132 abstracts were rebuilt from OpenAlex's `abstract_inverted_index`, a word-to-positions
map that has to be reassembled into prose. That turned out not to be reproducible. Fetching the
same records twice and comparing:

| route | independent fetches identical | word agreement |
|---|---|---|
| OpenAlex inverted index | 0 of 5 | 92.6% |
| Publisher landing page | 3 of 3 | 100% |

Most of the 7% is dropped connectives, but not all of it. Storlazzi et al. 2018 came back once as
"**these studies** have not taken into account the additional hazard of wave-driven overwash" and
once as "**we** have not taken into account…", which inverts who is being criticised. One
reconstruction also appended the journal editor's summary as though it were the authors' abstract.

Abstracts are therefore now taken from a **contiguous-text source** — the publisher's own page, or
Crossref's JATS abstract — fetched **twice** with differently worded prompts, and shipped only
where the two agree exactly. Each abstract states in the panel where it came from and whether the
two fetches matched. OpenAlex is still used, but only for metadata verification, which was stable
across every duplicate fetch.

**The 132 abstracts carried over from the first pass have not yet been re-fetched this way.** They
are labelled *"rebuilt from an index, wording not re-checked"* in the panel so they are not
presented as equivalent. Re-fetching them is the top item in *Known gaps*.

### 3. The future is separated from the record, deliberately

21 projection studies sit past a boundary marked **THE PRESENT · everything beyond this point is
projected, not observed**. They are kept apart from the record in six ways, because a forecast that
reads as a measurement is the worst failure this app could have:

- a dashed card edge and a **Projected** flag, so the difference rides on shape, not just colour
- publication year and projection year shown **separately**. A 2016 paper about 2070 is not a 2070
  event, and the card says "by 2070 · study published 2016"
- the panel quotes the sentence the study itself uses, and names the **emissions scenario or
  warming level**. Without that, "reefs decline 99%" is meaningless: it is a statement about 2°C
- the geology readout stops naming epochs and reads **Projected**
- year posts past the present are styled apart from historical ones
- screen readers hear "Projection." before the event

12 studies state a year and sit at it, from 2030 to 2100. 9 state only a warming level or an
emissions pathway, and sit in a separate chapter, **Scenario, no date given**, where the app shows
no year at all and says plainly that position there implies nothing about timing. The synthetic
calendar slots those events use internally never reach the screen.

The set is not one-sided. It includes studies projecting that corals can persist or adapt
(Bay 2017, Matz 2018, Toth 2023, Bouttes 2025 under high mitigation, Bozec 2025 below 2°C)
alongside those projecting decline.

### 4. Basic mode is a restatement, not a different set of facts

The plain-language text says the same things in simpler words. It adds nothing. Checks run on it:

- **Numbers**: every numeric token in the plain text must already appear in that event's original.
  0 of 175 events failed.
- **Meaning**: three independent reviewers read all 175 rewrites against their originals looking
  only for drift — added claims, dropped qualifiers, hedges hardened into certainties, invented
  causation, projections written as history. They found 18 problems: none that would change what a
  reader believes, 5 that broadened or hardened a claim, 13 imprecise but not misleading. All 18
  corrections are applied, written out in full in `build/basic_text_corrections.py`.
- **Reading level**: Flesch-Kincaid grade fell from a median of 13.8 to 8.2. Events at or below
  grade 9 went from 14 of 175 to 113 of 175. Ages 11 to 14 is roughly grade 6 to 9.

In basic mode the journal citations, DOIs, abstracts, evidence type and confidence rating are
hidden. In their place, 129 of 175 events link to a general-audience page. Every one of the 55
pages was fetched and read before being accepted; 44 candidates were rejected for being dead,
blocked, paywalled, too technical or not actually about the topic. **46 events have no link at
all**, deliberately: no suitable page covers those subjects, and a weak link is worse than none.

Publishers used include NOAA, the Australian Institute of Marine Science, the Great Barrier Reef
Marine Park Authority, the Natural History Museum, Smithsonian Ocean, Britannica, National
Geographic Education, AIATSIS, UNESCO and the IUCN.

---

## Reviewing the plain-language text

`coral_timeline_basic_text_REVIEW.xlsx` puts the original beside the draft, one row per event.

- Edit the **blue** columns only. The grey ones are the advanced text, for reference.
- The **Drafter's note** column flags the 83 events where a judgement call was made. Those are the
  rows to read first if you are short of time.
- **Links used** lists all 55 pages and which events use each.
- **No link, and why** lists the 46 events with none, so you can add one if you know a good page.

Send the file back and run `build/apply_basic_review.py`; a blank cell is ignored rather than
allowed to wipe existing text.

---

## Data model, briefly

`data/events_master.csv` is the source of truth. Key columns:

- `event_id` — CR-001 to CR-154 for the record, PJ-001 to PJ-021 for the projections. Stable,
  never renumbered
- `display_date`, `end_range`, `age_ma`, `year_ce`, `sort_year` — geological time in Ma, historical
  time in calendar years, kept separate rather than forced into one scale
- `nonlinear_time_bin` — the 12 chapters the corridor is divided into
- `headline`, `significance`, `why_it_matters` — the advanced card and panel text
- `basic_headline`, `basic_significance`, `basic_why`, `basic_links` — the plain-language version
- `is_projection`, `proj_year`, `proj_pub_year`, `proj_scenario`, `proj_quote`, `proj_undated` —
  the projection fields. `proj_year` and `proj_pub_year` are separate on purpose
- `category`, `category_group` — the controlled 7-category vocabulary (see `category_map.json`)
- `event_category` — the original free-text category, **kept**, never overwritten
- `evidence_type` — 8 collapsed values; `knowledge_frame` keeps the original free text
- `source_1_*`, `source_2_*` — two citations per event with title, URL and type

Append new events with new IDs; never renumber. Keep the original columns when adding derived
ones, so any mapping decision can be revisited.

---

## Accessibility and browser notes

- A flat **List view** gives every event without motion, follows the basic/advanced switch, and is
  the automatic default when the browser reports `prefers-reduced-motion`.
- Full keyboard control: arrow keys step event to event, Home and End jump to the ends, PageUp and
  PageDown travel, Enter opens a card, Escape closes it.
- Cards are real buttons with labels; projections announce themselves as projections; abstract text
  is selectable.
- Category footer colours are measured against both light and dark ink and the better contrast is
  used; the worst band clears 4.76:1. The category name is always printed, so colour is never the
  only channel.
- Tested in Chromium and Safari. The scene uses CSS 3D transforms, not WebGL.

---

## Known gaps

- **The 132 first-pass abstracts need re-fetching** through the double-fetch publisher route
  described above. Until then they carry an honest label rather than a claim of fidelity. Expect a
  handful to change wording and a few to be dropped where the publisher page cannot be fetched.
- **No images.** The card layout has a hidden `imgslot` element ready for them; adding pictures is
  a CSS change plus an image column, not a rebuild. Reef photography is mostly copyrighted, so a
  rights field should go in the schema at the same time.
- **Date uncertainty is not encoded.** "c. 550–541 Ma" and "2 June 2026" currently look equally
  precise. The honest fix is a range bar whose width scales with the uncertainty.
- **Bleaching events have no quantitative data yet.** Peak degree heating weeks, alert level,
  spatial extent and mortality would come from NOAA Coral Reef Watch, AIMS and GCRMN, and suit
  structured fields rather than prose.
- **69 sources publish no abstract**, mostly pre-1990 papers. Those events show the citation alone,
  which is honest but thin.
- **The deep-time opening is sparse by design.** Only two events cover 3.48 Ga to 550 Ma, so the
  first stretch is deliberately empty. Whether that reads as vastness or as a bug is an editorial
  call; the chapter weighting to change it lives in `build_timeline_axis.py`.
- **Four projection abstracts came from Crossref rather than the publisher** because the publisher
  blocked the fetch. Crossref stores contiguous JATS text, so it is subject to the same
  double-fetch check and both fetches agreed, but it is a different source and is labelled as one.

---

## Provenance

Advanced abstracts were retrieved from OpenAlex and Crossref on 2026-08-12, and the projection
abstracts from publisher pages and Crossref on 2026-08-13. Each displayed abstract carries its
journal, year, retrieval date, retrieval source and agreement check in the panel, and links to the
paper. Nothing was written from a language model's own knowledge of the literature: where retrieval
returned nothing, the field is empty.
