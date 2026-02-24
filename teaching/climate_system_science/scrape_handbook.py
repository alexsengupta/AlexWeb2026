"""
UNSW Handbook Scraper - 2026 Climate Science Courses
======================================================
Scrapes course information from the UNSW Student Handbook (2026) for all
courses listed in the Climate Science program PowerPoint.

HOW IT WORKS
------------
The UNSW Handbook is a Next.js server-side-rendered app (Courseloop platform).
All course data is embedded directly in the page HTML inside a
<script id="__NEXT_DATA__"> JSON block — no separate API call is needed.
This script fetches each course page, extracts that JSON block, and parses
the correct fields (confirmed by live browser inspection of the real site).

The enrolment_rules text is also sent to the Gemini API for structured
prerequisite parsing (set GEMINI_API_KEY env var to enable).

Usage:
    python scrape_handbook.py

Output:
    - courses_handbook_2026.csv   (spreadsheet-friendly)
    - courses_handbook_2026.json  (full structured detail)

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import glob
import json
import csv
import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# Course codes — auto-discovered from *_structure.md files in the same folder.
# To add a course: put its code anywhere in bsc_structure.md or
# advsci_structure.md (e.g. as a bullet line) and re-run the scraper.
# ─────────────────────────────────────────────────────────────────────────────
def _codes_from_markdowns(directory: str = ".") -> list[str]:
    codes: set[str] = set()
    pattern = os.path.join(directory, "*_structure.md")
    md_files = glob.glob(pattern)
    if not md_files:
        raise FileNotFoundError(
            f"No *_structure.md files found in {os.path.abspath(directory)}.\n"
            "Expected files like bsc_structure.md and advsci_structure.md."
        )
    for path in md_files:
        text = open(path, encoding="utf-8").read()
        # Strip comments (everything after # on a bullet line)
        text = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
        found = re.findall(r"\b[A-Z]{4}\d{4}\b", text)
        codes.update(found)
        print(f"  {os.path.basename(path)}: {len(found)} code mentions, "
              f"{len(set(found))} unique")
    return sorted(codes)


here = os.path.dirname(os.path.abspath(__file__))
print("Discovering course codes from *_structure.md …")
COURSE_CODES = _codes_from_markdowns(here)
print(f"  → {len(COURSE_CODES)} courses to scrape: {', '.join(COURSE_CODES)}\n")

YEAR = 2026

# ─────────────────────────────────────────────────────────────────────────────
# Gemini API (structured prerequisite parsing)
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def parse_prereqs_gemini(session: requests.Session, text: str) -> dict:
    """
    Use the Gemini API to parse complex prerequisite text into structured JSON.

    Returns a dict with:
      all_codes  – every unique course code mentioned
      groups     – OR-groups; each group is an AND-list of codes
                   (satisfying ANY one group fulfils the requirement)
      raw        – the original text
      error      – only present if the API call failed

    Falls back to a simple regex extraction if the API key is absent or
    the call fails.
    """
    regex_codes = sorted(set(re.findall(r"\b[A-Z]{4}\d{4}\b", text or "")))
    base = {"all_codes": regex_codes, "groups": [], "raw": text or ""}

    if not text or not GEMINI_API_KEY:
        return base

    prompt = (
        "Parse this university course prerequisite text and extract all course "
        "codes (format: 4 uppercase letters + 4 digits, e.g. MATH2011).\n"
        "Return ONLY valid JSON — no markdown, no code fences — in exactly this shape:\n"
        '{"all_codes":["MATH2011",...],"groups":[["MATH2011","MATH2111"],...] }\n'
        "Rules:\n"
        "  all_codes = every unique course code found in the text\n"
        "  groups    = outer list = alternatives (OR); inner list = must all be done (AND)\n"
        "  If the structure is ambiguous, list each course code as its own group.\n\n"
        f"Prerequisite text:\n{text}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }
    try:
        resp = session.post(
            GEMINI_URL, json=payload, params={"key": GEMINI_API_KEY}, timeout=30
        )
        resp.raise_for_status()
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences if the model wrapped the JSON anyway
        raw_text = re.sub(r"```[a-z]*\s*|\s*```", "", raw_text).strip()
        parsed = json.loads(raw_text)
        # Ensure expected keys exist
        if "all_codes" not in parsed:
            parsed["all_codes"] = regex_codes
        if "groups" not in parsed:
            parsed["groups"] = []
        parsed["raw"] = text
        return parsed
    except Exception as exc:
        return {**base, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_level(course_code: str) -> str:
    """UG vs PG: leading digit ≥ 5 → postgraduate (UNSW convention)."""
    m = re.search(r"\d", course_code)
    return "postgraduate" if m and int(m.group()) >= 5 else "undergraduate"


def handbook_url(course_code: str, year: int = YEAR) -> str:
    return f"https://www.handbook.unsw.edu.au/{get_level(course_code)}/courses/{year}/{course_code}"


def strip_html(html: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(separator=" ").strip()


def safe_str(obj, *keys, default="") -> str:
    """Safely traverse nested dicts/lists and return a string value."""
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, list):
            obj = obj[0] if obj else None
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
    return str(obj).strip() if obj is not None else default


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch — parses __NEXT_DATA__ embedded in the server-rendered HTML
# ─────────────────────────────────────────────────────────────────────────────

def fetch_course(session: requests.Session, course_code: str) -> dict:
    """
    Fetch one course page and extract structured data from __NEXT_DATA__.

    Field paths confirmed by live browser inspection of the Courseloop/Next.js
    app at handbook.unsw.edu.au (February 2026):

        pc.cl_code                              → course code
        pc.title                                → course title
        pc.credit_points                        → units of credit
        pc.description                          → overview text (HTML)
        pc.school_detail[0].name                → school
        pc.school_detail[0].parent.value        → faculty
        pc.study_level[0].label                 → study level
        pc.offering_detail.offering_terms       → offering terms (e.g. "Term 2")
        pc.admin_location.value                 → campus (e.g. "Sydney")
        pc.academic_calendar_type.value         → academic calendar
        pc.exclusion[n].associated_ai_cl_id.value → excluded course codes
        pc.enrolment_rules[n].description       → enrolment rule text (NOT requisite_description)
        pc.hb_delivery_variations[0].delivery_mode.value   → delivery mode
        pc.hb_delivery_variations[0].contact_hours         → contact hours
        pc.hb_delivery_variations[0].delivery_collaborators.label → format
    """
    url = handbook_url(course_code)
    result_base = {"course_code": course_code, "url": url}

    try:
        resp = session.get(url, timeout=20)
    except requests.RequestException as e:
        return {**result_base, "error": f"request failed: {e}"}

    # The server returns HTTP 404 for courses not in the handbook this year,
    # but we also handle a 200 page with pageType=ErrorPage gracefully.
    if resp.status_code == 404:
        return {**result_base, "error": "not in 2026 handbook (404)"}
    if resp.status_code != 200:
        return {**result_base, "error": f"HTTP {resp.status_code}"}

    # Extract __NEXT_DATA__ JSON block
    soup = BeautifulSoup(resp.text, "lxml")
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if not next_data_tag:
        return {**result_base, "error": "no __NEXT_DATA__ found in page"}

    try:
        next_data = json.loads(next_data_tag.string)
    except json.JSONDecodeError as e:
        return {**result_base, "error": f"JSON parse error: {e}"}

    page_props = next_data.get("props", {}).get("pageProps", {})

    # Check for error page (course exists in URL routing but not in handbook)
    if page_props.get("pageType") == "ErrorPage":
        return {**result_base, "error": "not in 2026 handbook (ErrorPage)"}

    pc = page_props.get("pageContent", {})
    if not pc or not pc.get("cl_code"):
        return {**result_base, "error": "pageContent missing or empty"}

    # ── Parse fields ──────────────────────────────────────────────────────────

    # Exclusions: list of dicts with associated_ai_cl_id.value = course code
    exclusions = ", ".join(
        e.get("associated_ai_cl_id", {}).get("value", "")
        for e in (pc.get("exclusion") or [])
        if e.get("associated_ai_cl_id", {}).get("value")
    )

    # Enrolment rules: the correct field name is "description" (not "requisite_description")
    # Confirmed by live browser inspection of __NEXT_DATA__ on the UNSW handbook.
    enrolment_rules = "; ".join(
        strip_html(r.get("description", ""))
        for r in (pc.get("enrolment_rules") or [])
        if r.get("description")
    )

    # Delivery: first variation
    dv = (pc.get("hb_delivery_variations") or [{}])[0]

    # Offering terms and campus from offering_detail (pre-aggregated by server)
    od = pc.get("offering_detail") or {}

    return {
        "course_code":      pc.get("cl_code", course_code),
        "title":            pc.get("title", ""),
        "units_of_credit":  pc.get("credit_points", ""),
        "faculty":          safe_str(pc.get("school_detail"), "parent", "value"),
        "school":           safe_str(pc.get("school_detail"), "name"),
        "study_level":      safe_str(pc.get("study_level"), "label"),
        "offering_terms":   od.get("offering_terms", ""),
        "campus":           safe_str(pc.get("admin_location"), "value"),
        "academic_calendar": safe_str(pc.get("academic_calendar_type"), "value"),
        "overview":         strip_html(pc.get("description", "")),
        "enrolment_rules":  enrolment_rules,
        "exclusions":       exclusions,
        "delivery_mode":    safe_str(dv.get("delivery_mode"), "value"),
        "delivery_format":  safe_str(dv.get("delivery_collaborators"), "label"),
        "contact_hours":    dv.get("contact_hours", ""),
        "url":              url,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────

def scrape_all(course_codes: list[str], delay: float = 1.5) -> list[dict]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": "https://www.handbook.unsw.edu.au/",
    })

    gemini_enabled = bool(GEMINI_API_KEY)
    if gemini_enabled:
        print(f"Gemini API key found — prerequisite text will be parsed structurally.\n")
    else:
        print("No GEMINI_API_KEY set — falling back to regex code extraction.\n")

    results = []
    total = len(course_codes)

    for i, code in enumerate(course_codes, 1):
        print(f"[{i:02d}/{total}] {code}  →  {handbook_url(code)}")
        result = fetch_course(session, code)

        if "error" in result:
            print(f"  ✗ {result['error']}")
            result["prereq_parsed"] = {"all_codes": [], "groups": [], "raw": ""}
        else:
            print(f"  ✓ {result['title']}  |  {result['units_of_credit']} UoC"
                  f"  |  {result['offering_terms']}  |  {result['campus']}")

            # Parse prerequisites structurally
            enrolment_text = result.get("enrolment_rules", "")
            if enrolment_text:
                parsed = parse_prereqs_gemini(session, enrolment_text)
                if "error" in parsed:
                    print(f"  ⚠ Gemini parse failed: {parsed['error']}")
                else:
                    print(f"  → prereqs: {parsed.get('all_codes', [])}")
                result["prereq_parsed"] = parsed
            else:
                result["prereq_parsed"] = {"all_codes": [], "groups": [], "raw": ""}

        results.append(result)

        if i < total:
            time.sleep(delay)

    return results


def save_results(results: list[dict], base_name: str = "courses_handbook_2026"):
    # JSON — prereq_parsed stored as a nested object
    with open(f"{base_name}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved → {base_name}.json")

    # CSV — prereq_parsed serialised as a JSON string in the cell
    fieldnames = [
        "course_code", "title", "units_of_credit", "faculty", "school",
        "study_level", "offering_terms", "campus", "academic_calendar",
        "overview", "enrolment_rules", "exclusions",
        "delivery_mode", "delivery_format", "contact_hours",
        "prereq_parsed",
        "url", "error",
    ]
    with open(f"{base_name}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            # Serialise the nested prereq_parsed dict to a JSON string for CSV
            row_out = dict(row)
            if isinstance(row_out.get("prereq_parsed"), dict):
                row_out["prereq_parsed"] = json.dumps(row_out["prereq_parsed"])
            writer.writerow(row_out)
    print(f"Saved → {base_name}.csv")


if __name__ == "__main__":
    print(f"UNSW Handbook Scraper — {YEAR}")
    print(f"Courses to fetch: {len(COURSE_CODES)}\n")

    results = scrape_all(COURSE_CODES, delay=1.5)

    ok  = sum(1 for r in results if "error" not in r)
    bad = sum(1 for r in results if "error" in r)
    print(f"\n{'─'*55}")
    print(f"Done: {ok} succeeded, {bad} not found / failed.")
    if bad:
        print("Not retrieved:")
        for r in results:
            if "error" in r:
                print(f"  {r['course_code']:12s}  {r['error']}")

    save_results(results)
