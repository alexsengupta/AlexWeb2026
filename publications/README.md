# Publications Page Workflow

This directory contains the frontend and data pipeline for the "Paper Browser" (`publications.html`).

## Overview

The `publications.html` file is a standalone HTML page that uses React (loaded via CDN) to render a dynamic list of academic papers.
Instead of a database, it relies on a static file structure:
1.  **`pdf-summarizer/summaries/manifest.json`**: A list of all available processed papers.
2.  **`pdf-summarizer/summaries/*.md`**: Individual Markdown files containing metadata and summaries for each paper.

## Updating the Publications List

To add new papers or update existing summaries, follow this process using the Python tools in the `pdf-summarizer` directory.

### 1. Add PDF Files
Ensure your new PDF files are located in the input directory expected by the summarizer script (typically `pdf-summarizer/pdfs` or similar).

### 2. Generate Summaries
Run the summarizer script to process the PDFs and generate Markdown files.
*Note: This script likely requires an API key (e.g., OpenAI) if it uses AI for summarization.*

```bash
python pdf-summarizer/pdf_summarizer.py
```

### 3. Update the Manifest
After generating new Markdown files, you must update the `manifest.json` file so the webpage knows they exist.

```bash
python pdf-summarizer/create_manifest.py
```

### 4. Test Locally
Because the page uses `fetch()` to load local JSON and MD files, browsers may block these requests if you open the HTML file directly (due to CORS policies). It is recommended to run a local server:

```bash
# Run from the deploy/publications directory
python3 -m http.server 8000
```
Then visit: `http://localhost:8000/publications.html`

## Troubleshooting

*   **"Manifest file not found"**: Ensure you have run `create_manifest.py`.
*   **"Failed to load [filename]"**: Check that the `.md` file exists in `pdf-summarizer/summaries/` and matches the entry in `manifest.json`.