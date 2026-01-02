#!/usr/bin/env python3
"""
PDF Academic Article Summarizer using Gemini API
Reads PDFs from a folder and generates accessible summaries in markdown format.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
import json
import google.generativeai as genai

# Configuration
DEFAULT_INPUT_FOLDER = "../../my_papers/pdfs"
DEFAULT_INPUT_FOLDER = "pdfs"
DEFAULT_OUTPUT_FOLDER = "./summaries"
PROGRESS_FILE = ".progress.json"

# Gemini model configuration
MODEL_NAME = "models/gemini-pro-latest"  # Gemini Pro model

# Prompt templates
SHORT_SUMMARY_PROMPT = """
Write a SHORT SUMMARY of this academic article in approximately 100 words.

Use an accessible, conversational style suitable for a general audience (not just academics).

Focus on:
- What the main research question or topic is
- The key finding or main point (include a concrete example if possible)
- Why it matters in the real world

If the paper mentions specific events, examples, or real-world cases, include one briefly.

Keep it concise and engaging.

IMPORTANT: Output ONLY the summary text. Do NOT include any preamble like "Here is a summary" or "Of course" or introductory phrases. Start directly with the summary content.
"""

DETAILED_SUMMARY_PROMPT = """
Write a DETAILED BRIEFING of this academic article in 800-1000 words.

Use an accessible, conversational style suitable for a general audience (not just academics).

Structure your briefing to cover:

1. **Background/Context**: What problem or question does this research address?
   - Include real-world context or motivating events if mentioned

2. **Main Research/Argument**: What did the researchers do or argue?
   - Describe the approach in concrete terms
   - Use analogies or examples to explain methods

3. **Key Findings**: What are the main results or conclusions?
   - IMPORTANT: Include specific examples, numbers, dates, or events from the paper
   - For example: "In 2023, the heatwave contributed to European heatwaves and severe rainfall"
   - Highlight concrete evidence or case studies mentioned

4. **Significance & Real-World Implications**: Why does this matter?
   - Connect findings to practical impacts on people, ecosystems, policy, etc.
   - Include specific examples of what might change or happen
   - For example: "Ocean temperatures influence weather on land" → "such events may become more common"

5. **Broader Takeaways**: What are the key lessons or warnings?
   - Highlight unexpected connections or paradoxes if mentioned
   - For example: "Human actions can have unexpected side effects - cleaner shipping fuel has health benefits but may contribute to ocean warming"
   - Include any "warning signs" or adaptation needs mentioned
   - Note any policy or practical implications

**Writing Guidelines:**
- Make it engaging and easy to understand
- Avoid jargon; explain technical terms when necessary
- Use concrete examples and specific details from the paper
- Include numbers, dates, locations, and real events when available
- Show connections between abstract findings and tangible impacts
- End with a clear conclusion that synthesizes the main message

CRITICAL: Output ONLY the briefing text. Do NOT include any preamble like "Here is a detailed briefing" or "Of course" or introductory phrases. Do NOT repeat the title. Start directly with the first section (Background/Context).
"""

METADATA_EXTRACTION_PROMPT = """
Extract the following metadata from this academic article. Respond ONLY with valid JSON format.

For the "keywords" field, select the MOST RELEVANT terms from this controlled vocabulary list only:

**Geographic/Regional:**
- Pacific
- Indian
- Southern Ocean
- Tropical Pacific
- Australia
- Antarctica

**Domain:**
- Atmosphere
- Ocean
- Sea ice
- Terrestrial
- Western Boundary Currents

**Methods/Tools:**
- Circulation
- Climate models
- Atmosphere models
- Ocean models
- Observation/Reanalysis
- Model–observation synthesis
- Lagrangian analysis
- ML/AI
- CMIP5
- CMIP3

**Phenomena:**
- Marine heatwaves
- subsurface MHWs
- ENSO
- Indian Ocean Dipole
- Southern Annular Mode
- Climate variability
- Climate Change
- Circulation change
- Stratification and mixing
- Rainfall

**Impacts/Biology:**
- Tuna
- Corals
- Topicalisation
- Ocean productivity
- Ocean Acidification
- Biological Impacts

Select 3-7 keywords from the above list that best describe the paper's focus.
Return as a comma-separated list.

JSON format:
{
  "title": "Full title of the paper",
  "authors": "Author names (Last, First; Last, First)",
  "year": "Publication year",
  "journal": "Journal name or conference",
  "keywords": "keyword1, keyword2, keyword3",
  "doi": "DOI if available, otherwise empty string"
}

If any field cannot be found, use "Not found" as the value.
Only return the JSON object, nothing else.
"""


class PDFSummarizer:
    def __init__(self, api_key: str, input_folder: str, output_folder: str):
        """Initialize the PDF summarizer with Gemini API."""
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.progress_file = Path(PROGRESS_FILE)

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(MODEL_NAME)

        # Load progress
        self.progress = self._load_progress()

        # Create output folder if it doesn't exist
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def _load_progress(self) -> Dict:
        """Load progress from file to track processed PDFs."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"processed": [], "failed": []}

    def _save_progress(self):
        """Save progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def _upload_pdf(self, pdf_path: Path):
        """Upload PDF to Gemini."""
        print(f"  Uploading PDF to Gemini...")
        uploaded_file = genai.upload_file(str(pdf_path))

        # Wait for file to be processed
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"File processing failed: {uploaded_file.state.name}")

        return uploaded_file

    def _generate_summary(self, uploaded_file, prompt: str) -> str:
        """Generate summary using Gemini."""
        response = self.model.generate_content([uploaded_file, prompt])
        return response.text

    def _extract_metadata(self, uploaded_file) -> Dict:
        """Extract metadata from the PDF."""
        try:
            response = self.model.generate_content([uploaded_file, METADATA_EXTRACTION_PROMPT])
            metadata_text = response.text.strip()

            # Try to parse JSON from response
            # Remove markdown code blocks if present
            if "```json" in metadata_text:
                metadata_text = metadata_text.split("```json")[1].split("```")[0].strip()
            elif "```" in metadata_text:
                metadata_text = metadata_text.split("```")[1].split("```")[0].strip()

            metadata = json.loads(metadata_text)
            return metadata
        except Exception as e:
            print(f"  ⚠️  Could not extract metadata: {str(e)}")
            return {
                "title": "Not found",
                "authors": "Not found",
                "year": "Not found",
                "journal": "Not found",
                "keywords": "Not found",
                "doi": ""
            }

    def _create_summary_filename(self, metadata: Dict, pdf_name: str) -> str:
        """Create consistent filename: FirstAuthor_etal_Year_TitleWords_Journal.md"""
        import re

        # Extract first author's last name
        authors = metadata.get("authors", "")
        if authors and authors != "Not found":
            # Format is typically "Last, First; Last2, First2"
            # Take first author's last name
            first_author = authors.split(";")[0].strip()
            # Get last name (before comma)
            if "," in first_author:
                author_part = first_author.split(",")[0].strip()
            else:
                # If no comma, take first word
                author_part = first_author.split()[0] if first_author.split() else "Unknown"
            # Clean and limit length
            author_part = re.sub(r'[^\w-]', '_', author_part)[:30]
        else:
            author_part = "Unknown"

        # Extract year
        year = metadata.get("year", "")
        if year and year != "Not found":
            year_part = str(year)
        else:
            year_part = "NoYear"

        # Extract title words (5-6 words, ~40 chars)
        title = metadata.get("title", "Unknown")
        if title != "Not found" and title != "Unknown":
            # Clean title: remove special chars, take first few words
            clean_title = re.sub(r'[^\w\s-]', '', title)
            words = clean_title.split()[:5]  # First 5 words
            title_part = "_".join(words)[:40]  # Max 40 chars
        else:
            # Fallback to PDF filename
            title_part = pdf_name[:30]

        # Extract journal name
        journal = metadata.get("journal", "")
        if journal and journal != "Not found":
            # Clean journal name
            clean_journal = re.sub(r'[^\w\s-]', '', journal)
            # Take first 3-4 words or limit to 40 chars
            journal_words = clean_journal.split()[:4]
            journal_part = "_".join(journal_words)[:40]
        else:
            journal_part = "NoJournal"

        # Construct filename: FirstAuthor_etal_Year_TitleWords_Journal.md
        filename = f"{author_part}_etal_{year_part}_{title_part}_{journal_part}.md"

        # Remove any remaining problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        return filename

    def _create_markdown(self, pdf_name: str, short_summary: str, detailed_summary: str,
                        metadata: Optional[Dict] = None) -> str:
        """Create formatted markdown output."""
        # Build the markdown content
        # Start with metadata if available
        if metadata:
            title = metadata.get("title", "Not found")
            markdown = f"""# {title}

## Article Information

**Title:** {metadata.get("title", "Not found")}
**Authors:** {metadata.get("authors", "Not found")}
**Year:** {metadata.get("year", "Not found")}
**Journal/Conference:** {metadata.get("journal", "Not found")}
**Keywords:** {metadata.get("keywords", "Not found")}
"""
            if metadata.get("doi"):
                markdown += f"**DOI:** {metadata.get('doi')}  \n"

            markdown += f"""
---

## Quick Summary (100 words)

{short_summary}

---

## Detailed Briefing (800-1000 words)

{detailed_summary}

---

*Generated by PDF Summarizer using Gemini API*
*Source: {pdf_name}*
"""
        else:
            markdown = f"""# {pdf_name}

## Quick Summary (100 words)

{short_summary}

---

## Detailed Briefing (800-1000 words)

{detailed_summary}

---

*Generated by PDF Summarizer using Gemini API*
*Source: {pdf_name}*
"""

        return markdown

    def process_pdf(self, pdf_path: Path) -> bool:
        """Process a single PDF file."""
        pdf_name = pdf_path.stem

        print(f"\n📄 Processing: {pdf_path.name}")

        try:
            # Upload PDF to Gemini
            uploaded_file = self._upload_pdf(pdf_path)

            # Extract metadata first to create proper filename
            print(f"  Extracting metadata...")
            metadata = self._extract_metadata(uploaded_file)

            # Create consistent filename from metadata
            summary_filename = self._create_summary_filename(metadata, pdf_name)
            output_file = self.output_folder / summary_filename

            # Check if summary already exists
            if output_file.exists():
                print(f"  ⏭️  Summary already exists: {summary_filename}")
                genai.delete_file(uploaded_file.name)
                return True

            # Small delay to avoid rate limiting
            time.sleep(1)

            # Generate short summary
            print(f"  Generating short summary...")
            short_summary = self._generate_summary(uploaded_file, SHORT_SUMMARY_PROMPT)

            # Small delay to avoid rate limiting
            time.sleep(1)

            # Generate detailed briefing
            print(f"  Generating detailed briefing...")
            detailed_summary = self._generate_summary(uploaded_file, DETAILED_SUMMARY_PROMPT)

            # Create markdown output
            markdown_content = self._create_markdown(
                pdf_path.name, short_summary, detailed_summary,
                metadata
            )

            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"  ✅ Saved summary to: {summary_filename}")

            # Update progress (for failure tracking)
            self.progress["processed"].append(str(pdf_path))
            self._save_progress()

            # Clean up uploaded file
            genai.delete_file(uploaded_file.name)

            return True

        except Exception as e:
            print(f"  ❌ Error processing {pdf_path.name}: {str(e)}")
            self.progress["failed"].append({"file": str(pdf_path), "error": str(e)})
            self._save_progress()
            return False

    def find_pdfs(self) -> List[Path]:
        """Find all PDF files in the input folder."""
        if not self.input_folder.exists():
            print(f"❌ Input folder not found: {self.input_folder}")
            print(f"Creating folder: {self.input_folder}")
            self.input_folder.mkdir(parents=True, exist_ok=True)
            return []

        pdfs = list(self.input_folder.glob("*.pdf"))
        return sorted(pdfs)

    def run(self):
        """Process all PDFs in the input folder."""
        print("🚀 PDF Academic Article Summarizer")
        print("=" * 50)
        print(f"Input folder: {self.input_folder.absolute()}")
        print(f"Output folder: {self.output_folder.absolute()}")
        print(f"Model: {MODEL_NAME}")
        print("=" * 50)

        # Find PDFs
        pdfs = self.find_pdfs()

        if not pdfs:
            print(f"\n⚠️  No PDF files found in {self.input_folder}")
            print(f"Please add PDF files to the folder and run again.")
            return

        print(f"\n📚 Found {len(pdfs)} PDF file(s)")

        # Process each PDF
        success_count = 0
        for pdf_path in pdfs:
            if self.process_pdf(pdf_path):
                success_count += 1
            # Rate limiting delay between files
            time.sleep(2)

        # Summary
        print("\n" + "=" * 50)
        print("✨ Processing Complete!")
        print(f"Successfully processed: {success_count}/{len(pdfs)}")
        if self.progress["failed"]:
            print(f"Failed: {len(self.progress['failed'])}")
            print("\nFailed files:")
            for failed in self.progress["failed"]:
                print(f"  - {Path(failed['file']).name}: {failed['error']}")
        print(f"\nSummaries saved to: {self.output_folder.absolute()}")
        print("=" * 50)


def main():
    """Main entry point."""
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  GEMINI_API_KEY=your-api-key-here")
        sys.exit(1)

    # Get folder paths from environment or use defaults
    input_folder = os.getenv("INPUT_FOLDER", DEFAULT_INPUT_FOLDER)
    output_folder = os.getenv("OUTPUT_FOLDER", DEFAULT_OUTPUT_FOLDER)

    # Create and run summarizer
    summarizer = PDFSummarizer(api_key, input_folder, output_folder)
    summarizer.run()


if __name__ == "__main__":
    main()
