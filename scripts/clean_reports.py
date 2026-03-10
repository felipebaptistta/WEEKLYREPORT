"""
clean_reports.py
----------------
Cleans the markdown files in reports_clean/ produced by convert_reports.py.

The goal is to normalize the text so it is easier to use as a reference:
  - Remove excessive blank lines
  - Normalize whitespace within paragraphs
  - Strip page headers and footers that repeat across pages (e.g. "Page 1 of 10")
  - Preserve paragraph order and structure
  - Save cleaned files in-place (overwrites the .md files in reports_clean/)

Usage:
    python scripts/clean_reports.py

What it does:
    - Reads every .md file in reports_clean/
    - Applies the cleaning pipeline to each file
    - Overwrites the file with the cleaned version
    - Logs changes to logs/clean_reports.log
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
CLEAN_DIR    = PROJECT_ROOT / "reports_clean"
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

def remove_page_numbers(text: str) -> str:
    """
    Remove common page number patterns such as:
      'Page 1 of 10', 'Page 1', '- 1 -', '1 / 10'
    These are frequently inserted by PDF converters between paragraphs.
    """
    patterns = [
        r'(?i)page\s+\d+\s+of\s+\d+',   # Page 1 of 10
        r'(?i)page\s+\d+',               # Page 1
        r'^\s*-\s*\d+\s*-\s*$',          # - 1 -
        r'^\s*\d+\s*/\s*\d+\s*$',        # 1 / 10
        r'^\s*\d+\s*$',                  # lone line with just a number
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    return text


def remove_repeated_lines(text: str, min_repeat: int = 3) -> str:
    """
    Remove lines that appear identically three or more times in the document.
    This catches repeating headers/footers (e.g. company name, report title)
    that PDF converters insert at the top or bottom of every page.

    Args:
        text:       The full document text.
        min_repeat: How many times a line must repeat before it is removed.
    """
    lines = text.splitlines()

    # Count how many times each non-empty line appears
    from collections import Counter
    line_counts = Counter(line.strip() for line in lines if line.strip())

    # Build a set of lines that appear too many times to be content
    repeated = {line for line, count in line_counts.items() if count >= min_repeat}

    # Keep lines that are not in the repeated set
    cleaned_lines = [
        line for line in lines
        if line.strip() not in repeated
    ]
    return "\n".join(cleaned_lines)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace within each paragraph:
      - Collapse multiple spaces within a line into one
      - Preserve intentional paragraph breaks (blank lines between blocks)
      - Limit consecutive blank lines to a maximum of two
    """
    # Collapse multiple spaces and tabs into a single space (within lines)
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove trailing spaces at the end of each line
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)

    # Collapse more than 2 consecutive blank lines into exactly 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def clean_text(text: str) -> str:
    """
    Apply the full cleaning pipeline to a document string.
    Steps are applied in this order to avoid interference between them.
    """
    text = remove_page_numbers(text)
    text = remove_repeated_lines(text)
    text = normalize_whitespace(text)
    return text


# ── Main logic ────────────────────────────────────────────────────────────────

def main():
    """Read all .md files in reports_clean/, clean them, and save in-place."""

    log.info("=" * 60)
    log.info(f"Starting clean_reports.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Target folder: {CLEAN_DIR}")

    md_files = sorted(CLEAN_DIR.glob("*.md"))

    if not md_files:
        log.info("No .md files found in reports_clean/. Run convert_reports.py first.")
        return

    log.info(f"Found {len(md_files)} file(s) to clean")

    cleaned = 0
    failed  = 0

    for md_file in md_files:
        try:
            original = md_file.read_text(encoding="utf-8")
            cleaned_text = clean_text(original)

            # Only write back if something actually changed
            if cleaned_text != original:
                md_file.write_text(cleaned_text, encoding="utf-8")
                log.info(f"Cleaned : {md_file.name}")
            else:
                log.info(f"No changes: {md_file.name}")

            cleaned += 1

        except Exception as e:
            log.error(f"Failed to clean {md_file.name}: {e}")
            failed += 1

    log.info("-" * 60)
    log.info(f"Done. Processed: {cleaned} | Failed: {failed}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
