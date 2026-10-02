# Climate Science Course Map

A React-based interactive course planner for UNSW's BSc and AdvSci in Climate Science programs. Visualise course sequences, prerequisites, and stream electives at a glance.

---

## Quick Start

### 1. Scrape the UNSW Handbook

First, generate course data by scraping the UNSW handbook:

```bash
python scrape_handbook.py
```

This creates `courses_handbook_2026.json` (or `.csv`), containing course codes, titles, prerequisites, offerings, and other metadata. The scraper **auto-discovers course codes** from the markdown files in your folder (`*_structure.md`), so you don't need to manually list them.

### 2. Run a Local Server

The app requires an HTTP server to fetch markdown files and course data at runtime:

```bash
python -m http.server
```

Then open your browser to **`http://localhost:8000`** and load `clim_course_map.html`.

> **Why HTTP server?** Browsers block file:// URLs from fetching other files for security reasons. A local server lets the app load markdown files dynamically.

### 3. Load Your Data

- If the scraper ran successfully and `courses_handbook_2026.json` exists in the same folder, the app loads automatically.
- If not, click **❓ Help** in the app header, or use the "Choose file" button on the splash screen to manually select a `.json` or `.csv` file.

---

## Setting Up Program Markdown Files

Course structure is defined in **per-program markdown files**. The app looks for files matching `*_structure.md`:

### File Naming
- `bsc_structure.md` — Bachelor of Science in Climate Science
- `advsci_structure.md` — Advanced Science (Climate)

Each file defines:
- **Program ID** and subtitle
- **Stages** (Year 1, 2, 3, Honours)
- **Core courses** (compulsory, same for all students)
- **Streams** (specialisations: Meteorology, Modelling, Civil, GIS, Government)
- **Electives per stream** (students pick from stream-specific options)

### Markdown Syntax

#### Program Header
```markdown
# Bachelor of Science in Climate Science

**Internal ID:** `bsc`
**Subtitle:** 3-year specialised degree with meteorology, modelling, civil, GIS, or government focus
```

#### Stage Section (Core Courses)
```markdown
## Stage 1 Core — Fundamentals (18 UoC)

- MATH1131
- MATH1231 | MATH1241  # Alt-group: student picks one
- PHYS1121 | PHYS1131 | PHYS1141  # 3-way alt-group
- CHEM1011 | CHEM1031
- BEES1011
- GEOS1701
```

#### Stream Electives Section
```markdown
## Stream Electives

### Stream: Meteorology

**Color:** `#ff6b6b`

**Stage 1 electives:**
- MATH1X41 (higher maths track)
- PHYS1X31 (higher physics)

**Stage 2 electives:**
- CLIM2001 / PHYS2801  # Co-badged: same enrolment, two codes
- MSCI2001
```

#### Special Notation

| Syntax | Meaning | Example |
|--------|---------|---------|
| `-` prefix | Single required course | `- CLIM1001` |
| `\|` separator | Alt-group (pick ONE) | `- MATH1131 \| MATH1141` |
| `/` separator | Co-badged (same enrolment, two codes) | `- CLIM2001 / PHYS2801` |
| Multiple bullets | All required | Two bullets = two courses |

#### Honours Stage
```markdown
## Stage 4 Core — Honours

> HONOURS

This notation creates a non-interactive honours info box. No tiles are rendered for this stage.
```

### Color Codes

Stream colours should be hex codes:
```markdown
**Color:** `#16a085`
```

These appear as:
- Stream button colours in the header
- Multi-colour stripes on shared electives
- Badge accents in the side panel

---

## File Structure

```
clim_course_map.html           Main app (React 18, Babel CDN, no build)
bsc_structure.md                BSc program definition
advsci_structure.md             AdvSci program definition
courses_handbook_2026.json      Scraped course metadata (or .csv)
scrape_handbook.py              Handbook scraper
README.md                       This file
```

---

## Using the App

### Navigation

**Program Selector** (header) — Switch between BSc and AdvSci. Resets selection and stream filter.

**Stream Filter** (header) — Click "All" to see all streams, or click a stream name to focus on that specialisation.
  - Tiles from the active stream appear normal
  - Other streams' tiles are dimmed (still visible but low contrast)

**Help** (header) — Opens a modal explaining features

### Course Interaction

**Hover** — See course code, title, and offering terms in a tooltip

**Click** — Open the side panel with:
  - Full course details (faculty, school, campus, delivery mode)
  - Prerequisites and prerequisite chain (if any)
  - Courses this one unlocks
  - Exclusions
  - Link to UNSW Handbook entry

**Deselect** — Press `Esc` or click the background

### Visual Cues

**Discipline Colours** (legend, bottom of header):
- Course tiles get a subtle background tint matching their discipline (MATH=blue, BEES=green, etc.)
- Darker when selected or highlighted

**Stage Information** (colour bar above each stage):
- Core UoC count (fixed per stage)
- Elective UoC count (range across streams, or exact when one stream is active)

**Prerequisites (green)** — Highlighted when a course is selected

**Unlocks (blue)** — Courses that require the selected course as a prerequisite

---

## Customising the Course Map

### Adding a New Program

1. Create a new markdown file, e.g. `myprogram_structure.md`
2. Follow the markdown syntax above (program ID, stages, streams, electives)
3. The app auto-discovers it on next page load

### Updating Course Data

Edit the relevant `*_structure.md` file (course codes, alt-groups, streams):

```bash
# Refresh browser (no Python step needed)
```

Or run the scraper again to update metadata (titles, prerequisites, offerings):

```bash
python scrape_handbook.py
python -m http.server  # Restart server if needed
```

### Changing Colours

Update hex codes in the `**Color:**` field for each stream:

```markdown
**Color:** `#ff6b6b`
```

Reload the page to see changes.

### Adjusting UoC Assumptions

By default, all courses are assumed to be **6 UoC**. To change this, edit the `StageRow` component in `clim_course_map.html`:

```javascript
const coreUoC = coreGroups.length * 6;  // Change 6 to your UoC value
```

---

## Troubleshooting

### "Could not load program structure"

- Ensure `bsc_structure.md` and `advsci_structure.md` exist in the same folder as the HTML
- Make sure you're using `python -m http.server` (not opening via `file://`)
- Check browser console (F12) for error details

### "No data — tiles show codes only"

- `courses_handbook_2026.json` or `.csv` not found
- Run `python scrape_handbook.py` again
- Or manually load a file via the splash screen

### Tiles not appearing for a course code

- Check that the code format is exactly `XXXX1234` (4 letters, 4 digits)
- Verify it's in `*_structure.md` using proper syntax (with `-` bullet prefix)
- Run scraper to ensure the code is in the course database

### Alt-group or co-badged not rendering correctly

- Verify separator: `|` for alt-groups, `/` for co-badged
- No spaces before/after separators (e.g. `MATH1131|MATH1141`, not `MATH1131 | MATH1141`)
- For co-badged, only the 3 predefined pairs are supported:
  - `CLIM2001 / PHYS2801`
  - `CLIM3001 / CLIM6001`
  - `MSCI3001 / MSCI5004`

---

## Technical Details

### Stack

- **React 18** — via CDN (no build step)
- **Babel** — client-side JSX transpilation
- **PapaParse** — CSV parsing
- **Markdown parsing** — custom state-machine parser in JS

### Data Flow

1. **Startup:** Load `*.md` files, parse to in-memory program objects
2. **Load courses:** Fetch `courses_handbook_2026.json` (or `.csv`), index by code
3. **User interaction:** Click tiles → update selected course → recompute prereqs/dependents → highlight related courses
4. **Stream filter:** Filter elective visibility based on active stream; adjust elective UoC range

### Client-Side vs Server-Side

- **No backend server required** — static files only
- **All processing in browser** — faster, private data stays local
- **HTTP server needed for file fetching** — not for computation

---

## Contributing

To extend or modify:

- **Add discipline colours:** Edit `DISC_COLORS` in the HTML
- **Add streams:** Just add a `### Stream:` section in markdown; app auto-discovers
- **Change stage count:** Add new `## Stage N` sections in markdown
- **Modify tile appearance:** Edit `tileVisuals()` or component styles

---

## License

For educational use at UNSW Climate Science.

---

## Questions?

Click **❓ Help** in the app for an interactive guide, or edit the markdown files and reload to see changes immediately (no scraping required for structure updates).
