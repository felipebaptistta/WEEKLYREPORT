"""
build_prompt.py
---------------
Assembles the final prompt that will be sent to the LLM in generate_report.py.

The prompt is built by combining four components in this order:

  1. Writing instructions  — from prompts/writing_instructions.txt
                             Defines tone, structure, and what the LLM must do.

  2. Style references      — the selected historical reports listed in
                             prompts/selected_reports.txt (produced by select_reports.py)
                             These are inserted as examples for the LLM to mirror.

  3. Weekly data           — all files found in weekly_data/
                             Prices, CSV exports, market summaries for this week.

  4. Analyst notes         — from weekly_data/ files ending in _notes.txt
                             Optional free-text notes from the analyst.

The assembled prompt is saved to:
    prompts/prompt_<YYYY-MM-DD>.txt

Usage:
    python scripts/build_prompt.py
    python scripts/build_prompt.py --date 2026-03-10
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT       = Path(__file__).parent.parent
PROMPTS_DIR        = PROJECT_ROOT / "prompts"
WEEKLY_DATA_DIR    = PROJECT_ROOT / "weekly_data"
LOG_DIR            = PROJECT_ROOT / "logs"
SELECTION_FILE     = PROMPTS_DIR / "selected_reports.txt"
INSTRUCTIONS_FILE  = PROMPTS_DIR / "writing_instructions.txt"

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "build_prompt.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── Section builders ──────────────────────────────────────────────────────────

def load_writing_instructions() -> str:
    """
    Load the persistent writing instructions from prompts/writing_instructions.txt.
    If the file does not exist, return a default placeholder instruction block.
    """
    if INSTRUCTIONS_FILE.exists():
        content = INSTRUCTIONS_FILE.read_text(encoding="utf-8").strip()
        log.info(f"Loaded writing instructions from {INSTRUCTIONS_FILE.name}")
        return content
    else:
        log.warning(
            f"{INSTRUCTIONS_FILE.name} not found. Using default placeholder instructions. "
            f"Create {INSTRUCTIONS_FILE} to customize."
        )
        return (
            "You are an expert commodity market analyst. "
            "Write a professional weekly market report based on the data and context provided below. "
            "The report should be analytical, narrative, and precise. "
            "Do not copy from the reference reports — use them only to understand tone and structure."
        )


def load_selected_reports() -> str:
    """
    Load the content of the reports listed in prompts/selected_reports.txt.
    Each report is wrapped in a labeled block so the LLM can distinguish them.
    """
    if not SELECTION_FILE.exists():
        log.warning(
            f"{SELECTION_FILE.name} not found. No style references will be included. "
            "Run select_reports.py first."
        )
        return ""

    paths = SELECTION_FILE.read_text(encoding="utf-8").splitlines()
    paths = [p.strip() for p in paths if p.strip()]

    if not paths:
        log.warning("selected_reports.txt is empty. No style references loaded.")
        return ""

    blocks = []
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            log.warning(f"Reference report not found, skipping: {path_str}")
            continue
        content = path.read_text(encoding="utf-8").strip()
        blocks.append(
            f"--- REFERENCE REPORT: {path.name} ---\n{content}\n--- END REFERENCE REPORT ---"
        )
        log.info(f"Loaded reference report: {path.name}")

    return "\n\n".join(blocks)


def load_weekly_data() -> str:
    """
    Load all files from weekly_data/.
    Supported formats: .txt, .csv, .md
    Files are included as plain text, labeled by filename.
    """
    data_files = sorted(WEEKLY_DATA_DIR.glob("*"))
    # Only include readable text-like files
    readable_extensions = {".txt", ".csv", ".md"}
    data_files = [
        f for f in data_files
        if f.is_file() and f.suffix.lower() in readable_extensions
        and not f.name.startswith(".")
    ]

    if not data_files:
        log.warning(
            "No data files found in weekly_data/. "
            "Add your price files, CSV exports, or notes before building the prompt."
        )
        return ""

    blocks = []
    for f in data_files:
        content = f.read_text(encoding="utf-8").strip()
        blocks.append(f"--- DATA FILE: {f.name} ---\n{content}\n--- END DATA FILE ---")
        log.info(f"Loaded data file: {f.name}")

    return "\n\n".join(blocks)


def assemble_prompt(instructions: str, references: str, weekly_data: str) -> str:
    """
    Combine the three components into a single prompt string.
    Each section is clearly labeled so the LLM can parse the structure.
    """
    sections = []

    # Section 1: Writing instructions (always present)
    sections.append("=== WRITING INSTRUCTIONS ===\n" + instructions)

    # Section 2: Historical style references (may be empty if not yet available)
    if references:
        sections.append("=== HISTORICAL REFERENCE REPORTS (FOR STYLE ONLY) ===\n" + references)
    else:
        sections.append("=== HISTORICAL REFERENCE REPORTS ===\n[None provided]")

    # Section 3: Weekly data (the actual input for this week's report)
    if weekly_data:
        sections.append("=== WEEKLY MARKET DATA ===\n" + weekly_data)
    else:
        sections.append("=== WEEKLY MARKET DATA ===\n[No data files found in weekly_data/]")

    # Final instruction to close the prompt
    sections.append(
        "=== TASK ===\n"
        "Using the writing instructions and the style of the reference reports as a guide, "
        "write a new weekly commodity market report based on the data provided above. "
        "Do not copy text from the reference reports. "
        "The report must reflect only the current week's data."
    )

    return "\n\n".join(sections)


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Build the LLM prompt for the weekly report.")
    parser.add_argument(
        "--date", type=str, default=str(date.today()),
        help="Report date in YYYY-MM-DD format (default: today)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    report_date = args.date

    log.info("=" * 60)
    log.info(f"Starting build_prompt.py — {report_date}")

    # Load each component
    instructions = load_writing_instructions()
    references   = load_selected_reports()
    weekly_data  = load_weekly_data()

    # Assemble the full prompt
    prompt = assemble_prompt(instructions, references, weekly_data)

    # Save to prompts/ with the date in the filename
    output_file = PROMPTS_DIR / f"prompt_{report_date}.txt"
    PROMPTS_DIR.mkdir(exist_ok=True)
    output_file.write_text(prompt, encoding="utf-8")

    log.info(f"Prompt saved to: {output_file}")
    log.info(f"Prompt length  : {len(prompt):,} characters")
    log.info("-" * 60)
    log.info("Done. Run generate_report.py next.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
