"""
select_reports.py
-----------------
Classifies historical reports from reports_final/ as post_wasde, pre_wasde,
or weekly, and selects the most relevant ones for use as style references.

Classification is date-driven using a known WASDE release calendar:
  - post_wasde: report published 1–7 days after a WASDE release
  - pre_wasde:  report published 0–9 days before a WASDE release
  - weekly:     everything else

Update WASDE_DATES at the top of this file when new months are added.

Selection priority (within the requested mode):
  1. Full commodity coverage (corn + soybeans + wheat) ranked first
  2. Most recent reports first within the same coverage tier

Outputs:
    prompts/selected_reports.txt  — file paths, one per line (read by build_prompt.py)
    prompts/selected_reports.md   — human-readable selection summary
    logs/select_reports.log

Usage:
    python scripts/select_reports.py --mode weekly     [--n 3]
    python scripts/select_reports.py --mode post_wasde [--n 3]
    python scripts/select_reports.py --mode pre_wasde  [--n 3]
    python scripts/select_reports.py --test-all        (classify + select all three modes)
"""

import argparse
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

OUTPUT_TXT = PROMPTS_DIR / "selected_reports.txt"
OUTPUT_MD  = PROMPTS_DIR / "selected_reports.md"

# ── WASDE release calendar ────────────────────────────────────────────────────
# WASDE is published monthly, typically between the 9th and 14th.
# Add new entries here as the archive grows.

WASDE_DATES = [
    date(2025,  9, 12),
    date(2025, 10,  9),   # scheduled; delayed by government shutdown (~Oct 16)
    date(2025, 11, 14),   # resumed after shutdown
    date(2025, 12,  9),
    date(2026,  1, 10),
    date(2026,  2, 11),
    date(2026,  3, 11),
]

PRE_WINDOW  = 9   # days before WASDE → pre_wasde
POST_WINDOW = 7   # days after  WASDE → post_wasde

# ── Commodity coverage ────────────────────────────────────────────────────────

COMMODITY_PATTERNS = [
    re.compile(r'\bcorn\b',    re.I),
    re.compile(r'\bsoybean\b', re.I),
    re.compile(r'\bwheat\b',   re.I),
]

# ── Date parsing ──────────────────────────────────────────────────────────────

MONTH_MAP = {
    "jan": 1,  "feb": 2,  "fev": 2,  "mar": 3,
    "apr": 4,  "may": 5,  "jun": 6,  "jul": 7,
    "aug": 8,  "sep": 9,  "oct": 10, "nov": 11, "dec": 12,
}

DATE_PATTERN = re.compile(
    r'\b(Jan|Feb|Fev|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+'
    r'(\d{1,2}),?\s+(\d{4})\b',
    re.IGNORECASE
)


def parse_date_from_filename(filename: str) -> date | None:
    """
    Extract a date from a report filename using a month-name pattern.
    Handles English and Portuguese abbreviations (Fev = February).
    Returns None if no date can be parsed.
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


# ── Classification ────────────────────────────────────────────────────────────

def classify(report_date: date) -> str:
    """
    Classify a report as 'post_wasde', 'pre_wasde', or 'weekly' based on
    proximity to the nearest entry in WASDE_DATES.

    Same day as WASDE is treated as pre_wasde — the report is published
    before the market has fully digested the release.
    """
    for wd in WASDE_DATES:
        days_after  = (report_date - wd).days
        days_before = (wd - report_date).days

        if 1 <= days_after <= POST_WINDOW:
            return "post_wasde"
        if 0 <= days_before <= PRE_WINDOW:
            return "pre_wasde"

    return "weekly"


# ── Scoring ───────────────────────────────────────────────────────────────────

def commodity_coverage(text: str) -> int:
    """
    Return the count of major commodities (corn, soybeans, wheat) mentioned.
    Maximum is 3. Used as a ranking tiebreaker.
    """
    return sum(1 for p in COMMODITY_PATTERNS if p.search(text))


# ── Report loading ────────────────────────────────────────────────────────────

def load_reports() -> list[dict]:
    """
    Read all .md files from reports_final/, parse their dates, classify them,
    and return a list sorted by date descending (most recent first).

    Each dict has keys: date, file, classification, coverage, content.
    """
    reports = []
    for md_file in sorted(FINAL_DIR.glob("*.md")):
        report_date = parse_date_from_filename(md_file.stem)
        content     = md_file.read_text(encoding="utf-8")
        cls         = classify(report_date) if report_date else "weekly"
        cov         = commodity_coverage(content)

        reports.append({
            "date":           report_date,
            "file":           md_file,
            "classification": cls,
            "coverage":       cov,
            "content":        content,
        })

    # Most recent first; no-date reports go last
    reports.sort(
        key=lambda r: (r["date"] is None, r["date"] or date.min),
        reverse=True,
    )
    return reports


# ── Selection ─────────────────────────────────────────────────────────────────

def select(reports: list[dict], mode: str, n: int) -> list[dict]:
    """
    Return up to n reports matching mode, ranked by:
      1. Full commodity coverage (3 = corn + soybeans + wheat) descending
      2. Most recent date descending
    """
    filtered = [r for r in reports if r["classification"] == mode]
    # Stable sort: coverage descending, then date already descending from load
    filtered.sort(key=lambda r: r["coverage"], reverse=True)
    return filtered[:n]


# ── Output writers ────────────────────────────────────────────────────────────

def write_txt(selected: list[dict]) -> None:
    """
    Write prompts/selected_reports.txt — one absolute file path per line.
    This file is consumed by build_prompt.py.
    """
    lines = [str(r["file"]) for r in selected]
    OUTPUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_md(mode_selections: dict[str, list[dict]], all_reports: list[dict]) -> None:
    """
    Write prompts/selected_reports.md — a human-readable summary showing
    the full classification of the archive and selected reports per mode.
    The selected report content is included so the file can be read directly
    as a style reference without touching the corpus.
    """
    lines = [
        "# Selected Reports — Style Reference",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Classification Summary",
        "",
    ]

    for mode in ("post_wasde", "pre_wasde", "weekly"):
        c = sum(1 for r in all_reports if r["classification"] == mode)
        lines.append(f"- {mode}: {c} report(s)")

    lines += ["", "## Full Archive Classification (chronological)", ""]
    for r in sorted(all_reports, key=lambda x: (x["date"] or date.min)):
        d   = r["date"].isoformat() if r["date"] else "UNKNOWN"
        lines.append(f"- {d}  [{r['classification']:12s}]  {r['file'].name}")

    for mode, selected in mode_selections.items():
        n = len(selected)
        lines += ["", f"## Selected for: {mode}  (top {n})", ""]
        if not selected:
            lines.append("_(no reports available for this mode)_")
            continue
        for r in selected:
            d = r["date"].isoformat() if r["date"] else "UNKNOWN"
            lines.append(f"- {d}  {r['file'].name}")
        lines.append("")
        for r in selected:
            d = r["date"].isoformat() if r["date"] else "UNKNOWN"
            lines += [
                "=== REPORT START ===",
                f"DATE: {d}",
                f"REPORT_TYPE: {mode}",
                f"SOURCE_FILE: {r['file'].name}",
                "",
                r["content"].strip(),
                "",
                "=== REPORT END ===",
                "",
            ]

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Parse args, classify all reports, select, and write outputs."""

    parser = argparse.ArgumentParser(description="Select style reference reports.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mode",
        choices=["post_wasde", "pre_wasde", "weekly"],
        help="Select reports for this report type.",
    )
    group.add_argument(
        "--test-all",
        action="store_true",
        help="Classify all reports and select top-N for every mode. "
             "Writes selected_reports.md only; does not update selected_reports.txt.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="Number of reports to select per mode (default: 3).",
    )
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    PROMPTS_DIR.mkdir(exist_ok=True)

    log_file = LOG_DIR / "select_reports.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger(__name__)

    log.info("=" * 60)
    log.info(f"Starting select_reports.py — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load and classify
    all_reports = load_reports()
    log.info(f"Loaded {len(all_reports)} report(s) from {FINAL_DIR.name}/")

    counts = {}
    for mode in ("post_wasde", "pre_wasde", "weekly"):
        counts[mode] = sum(1 for r in all_reports if r["classification"] == mode)
        log.info(f"  {mode:12s}: {counts[mode]} report(s)")

    # Select
    modes_to_run = ["post_wasde", "pre_wasde", "weekly"] if args.test_all else [args.mode]
    mode_selections: dict[str, list[dict]] = {}

    for mode in modes_to_run:
        selected = select(all_reports, mode, args.n)
        mode_selections[mode] = selected
        log.info(f"Selected for '{mode}' (top {args.n}):")
        for r in selected:
            d = r["date"].isoformat() if r["date"] else "UNKNOWN"
            log.info(f"  {d}  {r['file'].name}")
        if not selected:
            log.warning(f"  No reports classified as '{mode}'.")

    # Write outputs
    write_md(mode_selections, all_reports)
    log.info(f"Wrote: {OUTPUT_MD.name}")

    if not args.test_all:
        write_txt(mode_selections[args.mode])
        log.info(f"Wrote: {OUTPUT_TXT.name}  ({len(mode_selections[args.mode])} path(s))")
    else:
        log.info("--test-all: skipping selected_reports.txt (not a pipeline run)")

    log.info("-" * 60)
    log.info("Done.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
