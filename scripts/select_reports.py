"""
select_reports.py
-----------------
Selects a subset of historical reports from reports_clean/ to use as
style and narrative references when building the weekly prompt.

Selection strategy:
  1. Prefer the most recent reports (recency matters for tone and market context)
  2. Allow optional keyword filtering (e.g. select only reports mentioning "crude oil")
  3. Limit total number of selected reports to avoid overloading the prompt

The selected report paths are saved to a simple text file:
    prompts/selected_reports.txt

That file is then read by build_prompt.py.

Usage:
    python scripts/select_reports.py
    python scripts/select_reports.py --max 5
    python scripts/select_reports.py --max 5 --keywords "crude oil" "natural gas"

Arguments (all optional):
    --max       Maximum number of reports to select (default: 5)
    --keywords  One or more keywords; only reports containing all keywords are included
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT  = Path(__file__).parent.parent
CLEAN_DIR     = PROJECT_ROOT / "reports_clean"
PROMPTS_DIR   = PROJECT_ROOT / "prompts"
LOG_DIR       = PROJECT_ROOT / "logs"
SELECTION_FILE = PROMPTS_DIR / "selected_reports.txt"

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "select_reports.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── Selection functions ───────────────────────────────────────────────────────

def get_all_reports(clean_dir: Path) -> list[Path]:
    """
    Return all .md files in reports_clean/, sorted by modification time
    (most recently modified first). Modification time is used as a proxy
    for report date when file names do not contain dates.
    """
    files = list(clean_dir.glob("*.md"))
    # Sort by last modified time, most recent first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def filter_by_keywords(files: list[Path], keywords: list[str]) -> list[Path]:
    """
    Keep only files whose content contains ALL of the given keywords.
    The search is case-insensitive.

    Args:
        files:    List of markdown file paths to filter.
        keywords: List of keyword strings that must all appear in the file.

    Returns:
        Filtered list of file paths.
    """
    if not keywords:
        return files  # No filter applied

    matching = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8").lower()
            # Check that every keyword appears in the document
            if all(kw.lower() in content for kw in keywords):
                matching.append(f)
        except Exception as e:
            log.warning(f"Could not read {f.name} for keyword filtering: {e}")

    return matching


def select_reports(clean_dir: Path, max_reports: int, keywords: list[str]) -> list[Path]:
    """
    Full selection logic: get all reports, optionally filter, then take the top N.

    Args:
        clean_dir:   Folder containing cleaned .md files.
        max_reports: Maximum number of reports to select.
        keywords:    Keywords for content filtering (empty list = no filter).

    Returns:
        List of selected file paths (up to max_reports).
    """
    all_files = get_all_reports(clean_dir)
    log.info(f"Total reports available: {len(all_files)}")

    if keywords:
        all_files = filter_by_keywords(all_files, keywords)
        log.info(f"After keyword filter {keywords}: {len(all_files)} report(s) match")

    selected = all_files[:max_reports]
    return selected


def save_selection(selected: list[Path], output_file: Path) -> None:
    """
    Save the list of selected report paths to a plain text file.
    One absolute path per line.
    """
    output_file.parent.mkdir(exist_ok=True)
    lines = [str(f) for f in selected]
    output_file.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Saved selection to: {output_file}")


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Select historical reports for prompt building.")
    parser.add_argument(
        "--max", type=int, default=5,
        help="Maximum number of reports to select (default: 5)"
    )
    parser.add_argument(
        "--keywords", nargs="+", default=[],
        help="Only include reports containing all of these keywords"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log.info("=" * 60)
    log.info(f"Starting select_reports.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Max reports : {args.max}")
    log.info(f"Keywords    : {args.keywords if args.keywords else 'none'}")

    selected = select_reports(CLEAN_DIR, args.max, args.keywords)

    if not selected:
        log.warning("No reports were selected. Check that reports_clean/ is not empty.")
        return

    log.info(f"Selected {len(selected)} report(s):")
    for f in selected:
        log.info(f"  {f.name}")

    save_selection(selected, SELECTION_FILE)

    log.info("-" * 60)
    log.info("Done. Run build_prompt.py next.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
