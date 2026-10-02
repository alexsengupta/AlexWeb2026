# BEES course maps

An interactive map of a major's structure: core courses, prescribed electives,
degree requirements, suggested pathways, prerequisites and offering terms.
Everything the map shows comes from a few Excel files in this folder, so it can
be kept up to date without touching any code.

Open `course_map.html` through a web server (see "Viewing it" below).

## What is in this folder

| File | What it is | Who edits it |
|---|---|---|
| `course_map.html` | The web page. Reads the Excel files when it loads. | Nobody, normally |
| `lib/xlsx.full.min.js` | Library that lets the page read Excel files. | Nobody |
| `programs.xlsx` | Which program workbooks to show, and site-wide text. | Program admin |
| `CLIME1_bsc.xlsx`, `CLIMB1_advsci.xlsx`, `CLIMB2_minor.xlsx` | One workbook per program: its structure and pathways. | Program admin |
| `handbook.xlsx` | Course titles, terms, prerequisites etc., scraped from the UNSW Handbook. | The scraper; hand corrections go in its `Overrides` sheet |
| `scrape_handbook.py` | Refreshes `handbook.xlsx` from the Handbook. | Run once or twice a year |
| `requirements.txt` | The Python packages the scraper needs. | Nobody |
| `BEES_course_maps_guide.pdf` | The full guide for whoever maintains this (start there). Source in `guide/`. | Update when the workflow changes |

## Editing a program (the common case)

Open the program's workbook in Excel. It has four sheets. In each, row 1 is a
note, row 2 is the header, and the data starts on row 3. Do not rename sheets
or headers.

**Program** – two columns, Setting and Value. Name, degree, program and plan
codes, structure year, subtitle, handbook link, and an optional honours note.
Any row whose Setting is `Note` is shown as a paragraph under the map; add as
many as you like.

**Stages** – one row per stage: the stage number, its label, core UoC and the
elective UoC students must choose from that stage's pool. Put `HONOURS` in the
Note column to render a stage as a text box instead of tiles.

**Structure** – one row per requirement:

| Column | Meaning |
|---|---|
| Stage | Which stage row it belongs to |
| Type | `Core` (everyone does it), `Elective` (one option in that stage's pool) or `Degree` (a degree requirement outside the major, shown in grey) |
| Course | The course code. For a co-badged course write both codes in one cell: `CLIM2001 / PHYS2801` |
| Alternative 1–3 | Other courses that can be taken instead ("or"). Leave blank if none |
| Display label | Only for Degree rows with no course code, e.g. an employability placeholder |
| Link | Optional web link shown in the side panel |
| Note | Optional text shown in the side panel |

To add a course: add a row. To remove one: delete its row. Order within a
stage is the order shown.

**Streams** – one row per suggested pathway: name, colour (a hex code such as
`#2471a3`), a one-line description, then the courses in that pathway across the
row in the `Course 1`, `Course 2` … columns. Which stage a course appears in is
worked out from its code (a 2xxx course is Stage 2). Streams should only list
electives; the `Check` button on the page will tell you if one lists a core
course or a course that is not on the map. Leave the sheet empty (headers only)
for a program with no pathways, such as a minor.

Save the file, reload the page. That is the whole update.

## Adding a new program or major

1. Copy an existing program workbook and rename it, e.g. `GEOSA1_bsc.xlsx`.
2. Edit its four sheets as above.
3. Add a row for it in `programs.xlsx` (sheet `Programs`): the file name, the
   Major it belongs to, the short label for its button, and `yes` in Show.
   Programs with the same Major share a page and appear as buttons; each
   different Major becomes an entry in a drop-down at the top of the page
   (the drop-down only appears once there is more than one Major).
4. Run the scraper (below) so the new course codes get handbook details.

A minor or any program without stages: set `Layout` to `pool` in the Program
sheet, give it a single Stages row (e.g. Stage `Minor`, Elective UoC 24) and
list its courses as `Elective` rows in Structure.

## Refreshing handbook details

`handbook.xlsx` holds course titles, offering terms, prerequisites, exclusions
and handbook links. The scraper rewrites it from the live UNSW Handbook.

**First time only:** install the Python packages it needs. Open a terminal in
this folder (Python 3.9 or newer must already be installed) and run

```
pip install -r requirements.txt
```

If `pip` is not found, try `pip3` or `python3 -m pip`. On a machine where you
do not want to change the system Python, make a virtual environment first:

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Each refresh:** from a terminal in this folder, on a machine with normal
internet access,

```
python scrape_handbook.py                # latest handbook year
python scrape_handbook.py --year 2027    # a specific year
python scrape_handbook.py --dry-run      # just list the codes, no fetching
```

It collects every course code mentioned in the program workbooks, fetches each
one, and reports courses it could not find. Do not edit the `Courses` or `Info`
sheets by hand: they are overwritten on every run.

**Corrections go in the `Overrides` sheet.** Any non-blank cell there replaces
the scraped value for that course, and rows for courses the Handbook does not
have yet (a new course, a code that has changed) are added to the map. The
Overrides sheet is never touched by the scraper, so fixes survive. This is how
BEES1042, which is new from 2028, has a place on the map before the Handbook
lists it.

## Checking your work

The `Check` button in the page header lists problems in the input files:
course codes with no handbook entry, missing titles or terms, streams that
mention a course not on the map, stage UoC totals that do not add up, and so
on. A red count means something will be missing or wrong on the map; amber is
worth a look. Aim for zero.

## Viewing it

Browsers will not let a page read files from your disk directly, so the page
must be served over HTTP. On the website this happens automatically. To
preview locally, open a terminal in this folder and run

```
python -m http.server
```

then open <http://localhost:8000/course_map.html>.

## For students

Click any course for its details, prerequisites (green outline: prerequisites
that are on the map; blue: courses it leads to), exclusions and a handbook
link. Click a pathway to highlight the electives that suit it. `Print` gives a
one-page landscape summary of the program on screen. The address bar remembers
the program and pathway, so a link like `course_map.html#CLIME1_bsc` opens
straight to the BSc.

## Notes on the data (September 2026)

* The map shows the 2028 structure agreed with the BEES education team in
  September 2026, with course details from the 2026 Handbook. Re-run the scraper
  when the 2027 and 2028 Handbooks are live; nothing else changes.
* From 2028 UNSW moves from trimesters to semesters. The term badges come from
  the Handbook, so they will change to semesters automatically after a scrape of
  the 2028 Handbook.
* Faculty core: the BSc shows SCIF1000; the Advanced Science workbook shows
  SCIF1001 because SCIF1002 (as suggested by Scott Mooney) does not exist in the
  2027 Handbook. Confirm which is right and edit the Structure sheet.
* Employability (WIL/RIL) courses are shown as a placeholder tile linking to the
  Faculty of Science WIL page rather than a list of courses, because that list
  is the Faculty's and changes.
