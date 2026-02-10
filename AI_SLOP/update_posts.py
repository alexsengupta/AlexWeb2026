#!/usr/bin/env python3
"""
Scan markdowns/ for new .md files and prepend them to posts.json.
New posts are added to the TOP of the array (newest additions first).

Run manually or via cron:
    python3 /path/to/AI_SLOP/update_posts.py

Extracts from each markdown:
  - title:       first # heading
  - description: first body paragraph (truncated to ~200 chars)
  - source:      journal/publication name from CITATION line
  - date:        publication date parsed from CITATION, else file mtime
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MARKDOWNS_DIR = SCRIPT_DIR / "markdowns"
POSTS_JSON = SCRIPT_DIR / "posts.json"


def extract_title(lines):
    """Get title from the first # heading, stripping markdown formatting."""
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            # Remove markdown italic/bold markers
            title = re.sub(r'\*+([^*]+)\*+', r'\1', title)
            return title
    return None


def extract_description(lines):
    """Get first body paragraph after the title as the description."""
    past_title = False
    paragraph_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip until we're past the title
        if not past_title:
            if stripped.startswith("# "):
                past_title = True
            continue

        # Skip ## headings (e.g. ## Summary)
        if stripped.startswith("## "):
            if paragraph_lines:
                break
            continue

        # Skip empty lines
        if not stripped:
            if paragraph_lines:
                break
            continue

        # Skip metadata lines at bottom
        if re.match(r'^(CITATION|DOI|LINK|TITLE):', stripped):
            break

        paragraph_lines.append(stripped)

    text = " ".join(paragraph_lines)
    # Truncate to ~200 chars at a word boundary
    if len(text) > 200:
        text = text[:200].rsplit(" ", 1)[0] + "\u2026"
    return text


def extract_source(lines):
    """Extract publication name from the CITATION line."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("CITATION:"):
            # Look for text between *...* (journal name in italics)
            match = re.search(r'\*+([^*]+)\*+', stripped)
            if match:
                source = match.group(1).strip()
                # Check for a non-year parenthetical after the journal, like "(Medium)"
                after = stripped[match.end():match.end() + 30]
                paren = re.search(r'\(([^)]+)\)', after)
                if paren and not re.match(r'^\d{4}$', paren.group(1)):
                    source += f" ({paren.group(1)})"
                return source
    return "Unknown"


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _find_date_in_text(text):
    """Try to find a date (day month year or month year) in text."""
    lower = text.lower()

    # Try "5 February 2026" or "6 November 2025"
    m = re.search(
        r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\s+(\d{4})', lower
    )
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"

    # Try "February 2026" or "November 2025"
    m = re.search(
        r'(january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\s+(\d{4})', lower
    )
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}-01"

    # Try bare year in parentheses like (2025)
    m = re.search(r'\((\d{4})\)', text)
    if m:
        return f"{m.group(1)}-01-01"

    return None


def extract_date(lines, filepath):
    """Parse publication date from CITATION line, then body text, then file mtime."""
    citation_date = None

    # Try the CITATION line first
    for line in lines:
        if line.strip().startswith("CITATION:"):
            citation_date = _find_date_in_text(line)
            break

    # If CITATION gave a precise date (has month), use it
    if citation_date and not citation_date.endswith("-01-01"):
        return citation_date

    # Scan body text (first few paragraphs often mention a more precise date)
    full_text = "".join(lines[:15])
    body_date = _find_date_in_text(full_text)
    if body_date and (not citation_date or not body_date.endswith("-01-01")):
        return body_date

    # Use the CITATION date if we got one (even if just a year)
    if citation_date:
        return citation_date

    # Fall back to file modification time
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def load_posts():
    """Load existing posts.json or return empty list."""
    if POSTS_JSON.exists():
        with open(POSTS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts(posts):
    """Write posts back to posts.json."""
    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    posts = load_posts()
    existing_slugs = {p["slug"] for p in posts}

    md_files = sorted(MARKDOWNS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)

    new_posts = []
    for md_path in md_files:
        slug = md_path.stem
        if slug in existing_slugs:
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        title = extract_title(lines)
        if not title:
            print(f"  Skipping {md_path.name}: no title found")
            continue

        description = extract_description(lines)
        source = extract_source(lines)
        date = extract_date(lines, md_path)

        entry = {
            "slug": slug,
            "title": title,
            "date": date,
            "description": description,
            "source": source,
        }
        new_posts.append(entry)
        print(f"  Added: {title}")

    if new_posts:
        # Prepend new posts (newest file first) to the top of the list
        posts = new_posts + posts
        save_posts(posts)
        print(f"\n{len(new_posts)} new post(s) added to posts.json")
    else:
        print("No new posts found.")


if __name__ == "__main__":
    main()
