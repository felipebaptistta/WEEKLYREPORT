"""
convert_reports.py
------------------
Converts PDF and DOCX files from reports_raw/ into markdown (.md) files
saved in reports_clean/.

Uses the MarkItDown library, which handles both PDF and DOCX formats and
produces clean markdown output without needing format-specific parsers.

Usage:
    python scripts/convert_reports.py

What it does:
    - Scans reports_raw/ for any .pdf or .docx files
    - Skips files that have already been converted (checks reports_clean/)
    - Converts each new file to markdown
    - Saves the result as <original_filename>.md in reports_clean/
    - Logs progress and any errors to logs/conversion.log
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

# All paths are relative to the project root (the folder above scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR      = PROJECT_ROOT / "reports_raw"
CLEAN_DIR    = PROJECT_ROOT / "reports_clean"
LOG_DIR      = PROJECT_ROOT / "logs"

# Supported input formats
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "conversion.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),   # write to log file
        logging.StreamHandler(sys.stdout) # also print to terminal
    ]
)
log = logging.getLogger(__name__)


# ── Core functions ────────────────────────────────────────────────────────────

def find_raw_reports(raw_dir: Path) -> list[Path]:
    """Return a list of all PDF and DOCX files in the raw reports folder."""
    files = [
        f for f in raw_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)  # sort alphabetically for consistent ordering


def already_converted(raw_file: Path, clean_dir: Path) -> bool:
    """
    Check whether a raw file has already been converted.
    A converted file is expected at: clean_dir/<original_name>.md
    """
    expected_output = clean_dir / (raw_file.stem + ".md")
    return expected_output.exists()


def convert_file(raw_file: Path, clean_dir: Path) -> bool:
    """
    Convert a single PDF or DOCX file to markdown using MarkItDown.

    Args:
        raw_file:  Path to the source PDF or DOCX file.
        clean_dir: Directory where the .md output should be saved.

    Returns:
        True if conversion succeeded, False if it failed.
    """
    output_path = clean_dir / (raw_file.stem + ".md")

    try:
        # MarkItDown is the conversion library.
        # It is imported here (not at the top) so the script gives a clear error
        # if the library is not installed, rather than failing silently.
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(str(raw_file))

        # Write the markdown content to the output file
        output_path.write_text(result.text_content, encoding="utf-8")
        log.info(f"Converted: {raw_file.name} → {output_path.name}")
        return True

    except ImportError:
        log.error(
            "MarkItDown is not installed. Run: pip install markitdown"
        )
        return False

    except Exception as e:
        log.error(f"Failed to convert {raw_file.name}: {e}")
        return False


def main():
    """Main entry point: scan, filter, convert, report."""

    log.info("=" * 60)
    log.info(f"Starting convert_reports.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Source folder : {RAW_DIR}")
    log.info(f"Output folder : {CLEAN_DIR}")

    # Make sure the output folder exists
    CLEAN_DIR.mkdir(exist_ok=True)

    # Find all raw report files
    all_files = find_raw_reports(RAW_DIR)

    if not all_files:
        log.info("No PDF or DOCX files found in reports_raw/. Add your files and run again.")
        return

    log.info(f"Found {len(all_files)} file(s) in reports_raw/")

    # Track results
    converted = 0
    skipped   = 0
    failed    = 0

    for raw_file in all_files:
        if already_converted(raw_file, CLEAN_DIR):
            log.info(f"Skipping (already converted): {raw_file.name}")
            skipped += 1
            continue

        success = convert_file(raw_file, CLEAN_DIR)
        if success:
            converted += 1
        else:
            failed += 1

    # Summary
    log.info("-" * 60)
    log.info(f"Done. Converted: {converted} | Skipped: {skipped} | Failed: {failed}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
