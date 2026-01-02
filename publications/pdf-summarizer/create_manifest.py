#!/usr/bin/env python3
"""
Create manifest.json file for publications.html viewer
This script scans the summaries folder and creates a JSON manifest
listing all markdown files for the web viewer to load.
"""

import json
from pathlib import Path

def create_manifest():
    """Create manifest.json with list of all summary files."""
    summaries_folder = Path('./summaries')

    if not summaries_folder.exists():
        print(f"❌ Summaries folder not found: {summaries_folder}")
        print("Please run the PDF summarizer first to generate summaries.")
        return

    # Find all markdown files
    md_files = list(summaries_folder.glob('*.md'))

    if not md_files:
        print(f"⚠️  No markdown files found in {summaries_folder}")
        print("Please run the PDF summarizer to generate summaries first.")
        return

    # Create manifest
    manifest = {
        "files": sorted([f.name for f in md_files]),
        "generated": str(Path.cwd()),
        "count": len(md_files)
    }

    # Save manifest
    manifest_path = summaries_folder / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ Created manifest with {len(md_files)} files")
    print(f"📄 Manifest saved to: {manifest_path}")
    print(f"\n📚 Files included:")
    for i, filename in enumerate(manifest['files'][:10], 1):
        print(f"   {i}. {filename}")
    if len(md_files) > 10:
        print(f"   ... and {len(md_files) - 10} more")

    print(f"\n🌐 To view publications:")
    print(f"   1. Start a local server:")
    print(f"      python3 -m http.server 8000")
    print(f"   2. Open in browser:")
    print(f"      http://localhost:8000/publications.html")

if __name__ == "__main__":
    create_manifest()
