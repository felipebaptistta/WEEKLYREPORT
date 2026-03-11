"""
build_style_corpus.py
---------------------
Assembles all cleaned historical reports from reports_final/ into a single
style reference file: prompts/style_corpus.md.

Each report is wrapped with clear markers and prepended with metadata so an
LLM can distinguish one report from another and understand its context.

Output files:
    prompts/style_corpus.md   — all reports combined, ordered by date
    logs/build_style_corpus.log

Usage:
    python scripts/build_style_corpus.py
"""

import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
FINAL_DIR    = PROJECT_ROOT / "reports_final"
PROMPTS_DIR  = PROJECT_ROOT / "prompts"
LOG_DIR      = PROJECT_ROOT / "logs"

CORPUS_FILE  = PROMPTS_DIR / "style_corpus.md"

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "build_style_corpus.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ── Date parsing ──────────────────────────────────────────────────────────────

# Maps month name tokens (including Portuguese "Fev") to month numbers.
MONTH_MAP = {
    "jan": 1,  "feb": 2,  "fev": 2,  "mar": 3,
    "apr": 4,  "may": 5,  "jun": 6,  "jul": 7,
    "aug": 8,  "sep": 9,  "oct": 10, "nov": 11, "dec": 12,
}

# Matches "Month DD, YYYY" or "Month D, YYYY" anywhere in a string.
# The comma after the day is optional (some filenames omit it).
DATE_PATTERN = re.compile(
    r'\b(Jan|Feb|Fev|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+'
    r'(\d{1,2}),?\s+(\d{4})\b',
    re.IGNORECASE
)


def parse_date_from_filename(filename: str) -> date | None:
    """
    Extract a date from a report filename using a month-name pattern.

    Handles English and Portuguese month abbreviations (e.g. 'Fev' for Feb).
    Returns a date object on success, or None if no date can be parsed.
    """
    match = DATE_PATTERN.search(filename)
    if not match:
        return None
    month_str, day_str, year_str = match.groups()
    month = MONTH_MAP.get(month_str.lower())
    if month is None:
        return None
    try:
        return date(int(year_str), month, int(day_str))
    except ValueError:
        return None


# ── Report block builder ──────────────────────────────────────────────────────

def build_report_block(md_file: Path, report_date: date | None) -> str:
    """
    Wrap the content of one report file in metadata and delimiters.

    Args:
        md_file:     Path to the cleaned .md file in reports_final/.
        report_date: Parsed date for this report, or None if parsing failed.

    Returns:
        A string block ready to be appended to the corpus file.
    """
    date_str = report_date.isoformat() if report_date else "UNKNOWN"
    content  = md_file.read_text(encoding="utf-8").strip()

    lines = [
        "=== REPORT START ===",
        f"DATE: {date_str}",
        f"REPORT_TYPE: HigbyBarrett Weekly Commodity Report",
        f"SOURCE_FILE: {md_file.name}",
        "",
        content,
        "",
        "=== REPORT END ===",
    ]
    return "\n".join(lines)


# ── Main logic ────────────────────────────────────────────────────────────────

def main():
    """Read all .md files from reports_final/, combine into style_corpus.md."""

    log.info("=" * 60)
    log.info(f"Starting build_style_corpus.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Source folder : {FINAL_DIR}")
    log.info(f"Output file   : {CORPUS_FILE}")

    PROMPTS_DIR.mkdir(exist_ok=True)

    md_files = sorted(FINAL_DIR.glob("*.md"))
    if not md_files:
        log.info("No .md files found in reports_final/. Run clean_reports.py first.")
        return

    log.info(f"Found {len(md_files)} file(s)")

    # Parse dates and flag any that failed
    dated = []
    unparsed = []
    for f in md_files:
        d = parse_date_from_filename(f.stem)
        if d is None:
            unparsed.append(f.name)
            log.warning(f"Could not parse date from: {f.name}")
        else:
            log.info(f"Parsed {d.isoformat()}  ←  {f.name}")
        dated.append((d, f))

    # Sort by date (files with no date go to the end)
    dated.sort(key=lambda x: (x[0] is None, x[0] or date.min))

    # Build corpus
    blocks = []
    for report_date, md_file in dated:
        try:
            block = build_report_block(md_file, report_date)
            blocks.append(block)
        except Exception as e:
            log.error(f"Failed to process {md_file.name}: {e}")

    header = (
        "# HigbyBarrett Weekly Report — Style Corpus\n"
        "#\n"
        "# This file contains historical weekly commodity market reports.\n"
        "# Use these reports as STYLE and NARRATIVE references only.\n"
        "# Do NOT copy text from these reports into new reports.\n"
        "# Each report is delimited by === REPORT START === / === REPORT END ===\n"
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"# Reports included: {len(blocks)}\n"
    )

    CORPUS_FILE.write_text(header + "\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")

    log.info("-" * 60)
    log.info(f"Corpus written: {CORPUS_FILE}  ({CORPUS_FILE.stat().st_size // 1024} KB)")
    if unparsed:
        log.warning(f"Files with unparsed dates ({len(unparsed)}): {unparsed}")
    else:
        log.info("All dates parsed successfully.")
    log.info(f"Done. Reports included: {len(blocks)} | Unparsed dates: {len(unparsed)}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
