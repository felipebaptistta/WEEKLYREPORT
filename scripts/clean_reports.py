"""
clean_reports.py
----------------
Cleans the markdown files in reports_clean/ produced by convert_reports.py.

Reads each .md file from reports_clean/, applies a cleaning pipeline, and
saves the result in reports_final/ without modifying the source files.

Cleaning steps (in order):
  1. Remove form feed characters (\f / \x0c) inserted at PDF page boundaries
  2. Remove known repeating footer/header lines:
       - info@HigbyBarrett.com
       - "Higby Barrett | Weekly Insights | <date>" page headers
  3. Remove isolated page numbers (standalone digits on their own line,
     "Page N of M", "- N -", "N / M")
  4. Normalize whitespace (collapse multiple spaces; limit blank lines to two)

Paragraph order, section headings, and all numeric data are preserved.

Usage:
    python scripts/clean_reports.py

Output:
    reports_final/<same filename>.md   — cleaned copy of each source file
    logs/clean_reports.log             — run log with per-file details
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
CLEAN_DIR    = PROJECT_ROOT / "reports_clean"
FINAL_DIR    = PROJECT_ROOT / "reports_final"
LOG_DIR      = PROJECT_ROOT / "logs"

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "clean_reports.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── Cleaning functions ────────────────────────────────────────────────────────

def remove_form_feeds(text: str) -> str:
    """
    Remove form feed characters (\f, \x0c) that PDF converters insert at
    every page boundary. These show up as blank lines or invisible separators
    that add no content value.
    """
    return text.replace('\f', '').replace('\x0c', '')


def remove_known_footers(text: str) -> str:
    """
    Remove lines matching known repeating footer and page-header patterns:
      - 'info@HigbyBarrett.com'  — email footer printed on every page
      - 'Higby Barrett | Weekly Insights | <date>'  — page header printed
        at the top of every page by the PDF layout engine

    The document-level title line ('Weekly Insights | <date>') that appears
    only once at the top is intentionally left in place.
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Email footer
        if re.match(r'(?i)info@higbybarrett\.com\s*$', stripped):
            continue
        # Page header: "Higby Barrett | Weekly Insights | <any date>"
        # This form uses a pipe before "Higby Barrett" and appears on every page.
        if re.match(r'(?i)higby\s*barrett\s*\|.*weekly\s*insights', stripped):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def remove_page_numbers(text: str) -> str:
    """
    Remove common page number patterns that PDF converters insert between
    content blocks:
      'Page 1 of 10', 'Page 1', '- 1 -', '1 / 10', or a bare digit on its own line.

    Note: the bare-digit pattern removes any line that contains only a number.
    Numbers that appear as part of paragraph text or table rows are not affected
    because they share the line with other characters.
    """
    patterns = [
        r'(?i)page\s+\d+\s+of\s+\d+',   # Page 1 of 10
        r'(?i)^\s*page\s+\d+\s*$',       # Page 1  (alone on a line)
        r'^\s*-\s*\d+\s*-\s*$',          # - 1 -
        r'^\s*\d+\s*/\s*\d+\s*$',        # 1 / 10
        r'^\s*\d+\s*$',                  # lone line with only a number
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace throughout the document:
      - Collapse multiple consecutive spaces/tabs within a line into one space
      - Strip trailing spaces from every line
      - Reduce runs of more than two consecutive blank lines to exactly two
    """
    # Collapse multiple spaces/tabs within a line
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove trailing spaces
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)
    # Limit consecutive blank lines to two
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_text(text: str) -> tuple[str, list[str]]:
    """
    Apply the full cleaning pipeline to a document string.

    Returns:
        A tuple of (cleaned_text, ops) where ops is a list of short strings
        describing each cleaning step that actually changed the text.
    """
    ops = []

    result = remove_form_feeds(text)
    if result != text:
        ops.append("form feeds removed")
    text = result

    result = remove_known_footers(text)
    if result != text:
        ops.append("email/page-header footers removed")
    text = result

    result = remove_page_numbers(text)
    if result != text:
        ops.append("isolated page numbers removed")
    text = result

    result = normalize_whitespace(text)
    if result != text:
        ops.append("whitespace normalized")
    text = result

    return text, ops


# ── Main logic ────────────────────────────────────────────────────────────────

def main():
    """
    Read all .md files from reports_clean/, clean each one, and save the
    result in reports_final/ under the same filename.
    """

    log.info("=" * 60)
    log.info(f"Starting clean_reports.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Source folder : {CLEAN_DIR}")
    log.info(f"Output folder : {FINAL_DIR}")

    FINAL_DIR.mkdir(exist_ok=True)

    md_files = sorted(CLEAN_DIR.glob("*.md"))

    if not md_files:
        log.info("No .md files found in reports_clean/. Run convert_reports.py first.")
        return

    log.info(f"Found {len(md_files)} file(s) to clean")

    cleaned  = 0
    no_change = 0
    failed   = 0

    for md_file in md_files:
        output_path = FINAL_DIR / md_file.name
        try:
            original = md_file.read_text(encoding="utf-8")
            cleaned_text, ops = clean_text(original)

            output_path.write_text(cleaned_text, encoding="utf-8")

            if ops:
                log.info(f"Cleaned : {md_file.name}  [{', '.join(ops)}]")
                cleaned += 1
            else:
                log.info(f"No changes: {md_file.name}")
                no_change += 1

        except Exception as e:
            log.error(f"Failed: {md_file.name}: {e}")
            failed += 1

    log.info("-" * 60)
    log.info(f"Done. Cleaned: {cleaned} | Unchanged: {no_change} | Failed: {failed}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
