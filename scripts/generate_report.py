"""
generate_report.py
------------------
Orchestrates the full report generation pipeline for a given mode and date.

In placeholder mode (no LLM connected yet):
  - Runs select_reports.py to pick the right historical references
  - Runs build_prompt.py to assemble the full prompt
  - Saves the prompt to output/<mode>_prompt.txt for review or manual use

When an LLM is connected (see LLM INTEGRATION section below):
  - Does all of the above, then calls the LLM
  - Saves the generated report to output/<date>_<mode>_report.md
  - Saves the raw LLM response to logs/ for debugging

Supported modes:
    post_wasde  — WASDE was released this week
    pre_wasde   — WASDE is due next week
    weekly      — standard mid-cycle report

Usage:
    python scripts/generate_report.py --mode post_wasde
    python scripts/generate_report.py --mode pre_wasde
    python scripts/generate_report.py --mode weekly
    python scripts/generate_report.py --mode post_wasde --date 2026-03-12
    python scripts/generate_report.py --mode post_wasde --date 2026-03-12 --data-dir weekly_data/2026-03-12
    python scripts/generate_report.py --mode post_wasde --n 3

Arguments:
    --mode      Report type: post_wasde | pre_wasde | weekly  (required)
    --date      Report date YYYY-MM-DD (default: today)
    --data-dir  Folder with this week's data files
                (default: weekly_data/<date>/ if it exists, else weekly_data/)
    --n         Number of historical reference reports to select (default: 3)
"""

import argparse
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"
PROMPTS_DIR  = PROJECT_ROOT / "prompts"
OUTPUT_DIR   = PROJECT_ROOT / "output"
LOG_DIR      = PROJECT_ROOT / "logs"

VALID_MODES = ("post_wasde", "pre_wasde", "weekly")

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "generate_report.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Pipeline steps ────────────────────────────────────────────────────────────

def run_select(mode: str, n: int) -> bool:
    """
    Run select_reports.py --mode <mode> --n <n> to update selected_reports.txt.
    Returns True on success, False on failure.
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "select_reports.py"), "--mode", mode, "--n", str(n)]
    log.info(f"Running: {' '.join(cmd[1:])}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        log.error("select_reports.py failed.")
        return False
    return True


def run_build_prompt(mode: str, report_date: str, data_dir: str | None) -> Path | None:
    """
    Run build_prompt.py --mode <mode> --date <date> [--data-dir <dir>].
    Returns the path to the generated prompt file, or None on failure.
    """
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "build_prompt.py"),
        "--mode", mode,
        "--date", report_date,
    ]
    if data_dir:
        cmd += ["--data-dir", data_dir]

    log.info(f"Running: {' '.join(cmd[1:])}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        log.error("build_prompt.py failed.")
        return None

    prompt_file = PROMPTS_DIR / f"prompt_{report_date}_{mode}.txt"
    if not prompt_file.exists():
        log.error(f"Expected prompt file not found: {prompt_file}")
        return None
    return prompt_file


# ── LLM INTEGRATION ───────────────────────────────────────────────────────────
#
# The LLM is not connected yet. When you are ready, implement call_llm() below.
#
# Option A — Local model via Ollama (recommended first):
#
#   import requests
#
#   def call_llm(prompt: str) -> str:
#       response = requests.post(
#           "http://localhost:11434/api/generate",
#           json={"model": "llama3", "prompt": prompt, "stream": False},
#       )
#       return response.json()["response"]
#
# Option B — Anthropic Claude API:
#
#   import anthropic
#
#   def call_llm(prompt: str) -> str:
#       client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
#       message = client.messages.create(
#           model="claude-opus-4-6",
#           max_tokens=8096,
#           messages=[{"role": "user", "content": prompt}],
#       )
#       return message.content[0].text
#
# Option C — OpenAI-compatible API:
#
#   from openai import OpenAI
#
#   def call_llm(prompt: str) -> str:
#       client = OpenAI()                # reads OPENAI_API_KEY from env
#       response = client.chat.completions.create(
#           model="gpt-4o",
#           messages=[{"role": "user", "content": prompt}],
#       )
#       return response.choices[0].message.content
#
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> str | None:
    """
    Placeholder — LLM not yet connected.
    Returns None so the caller knows to skip report generation.
    Replace this body with a real LLM call when ready.
    """
    return None


# ── Output ────────────────────────────────────────────────────────────────────

def save_prompt_to_output(prompt_file: Path, mode: str) -> Path:
    """
    Copy the assembled prompt to output/<mode>_prompt.txt.
    This is the deliverable when no LLM is connected.
    """
    dest = OUTPUT_DIR / f"{mode}_prompt.txt"
    dest.write_text(prompt_file.read_text(encoding="utf-8"), encoding="utf-8")
    log.info(f"Prompt saved to output: {dest.name}")
    return dest


def save_report(content: str, report_date: str, mode: str) -> Path:
    """
    Save the LLM-generated report to output/<date>_<mode>_report.md.
    Also saves the raw response to logs/ for debugging.
    """
    report_file = OUTPUT_DIR / f"{report_date}_{mode}_report.md"
    report_file.write_text(content, encoding="utf-8")
    log.info(f"Report saved: {report_file.name}")

    raw_log = LOG_DIR / f"{report_date}_{mode}_llm_response.txt"
    raw_log.write_text(content, encoding="utf-8")
    log.info(f"Raw response logged: {raw_log.name}")

    return report_file


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a weekly commodity market report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/generate_report.py --mode post_wasde\n"
            "  python scripts/generate_report.py --mode pre_wasde --date 2026-03-05\n"
            "  python scripts/generate_report.py --mode weekly --data-dir weekly_data/2026-03-11\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        required=True,
        help="Report type: post_wasde | pre_wasde | weekly",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=str(date.today()),
        help="Report date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help=(
            "Folder with this week's data files. "
            "Defaults to weekly_data/<date>/ if it exists, otherwise weekly_data/."
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="Number of historical reference reports to select (default: 3)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    mode        = args.mode
    report_date = args.date
    data_dir    = args.data_dir
    n           = args.n

    log.info("=" * 60)
    log.info(f"Starting generate_report.py — {report_date} — mode: {mode}")

    # Step 1: Select historical reference reports for this mode
    log.info("Step 1/3 — Selecting reference reports...")
    if not run_select(mode, n):
        log.error("Aborting: could not select reference reports.")
        sys.exit(1)

    # Step 2: Assemble the prompt
    log.info("Step 2/3 — Building prompt...")
    prompt_file = run_build_prompt(mode, report_date, data_dir)
    if not prompt_file:
        log.error("Aborting: could not build prompt.")
        sys.exit(1)

    prompt = prompt_file.read_text(encoding="utf-8")
    log.info(f"Prompt size: {len(prompt):,} chars")

    # Step 3: Call LLM (or save prompt if not connected)
    log.info("Step 3/3 — Generating report...")
    report_text = call_llm(prompt)

    if report_text is None:
        # LLM not connected — save the prompt to output/ for manual use
        output_path = save_prompt_to_output(prompt_file, mode)
        log.info("-" * 60)
        log.info("LLM not connected. Prompt saved as the deliverable.")
        log.info(f"Output: {output_path}")
        log.info("")
        log.info("To generate a report, either:")
        log.info("  1. Implement call_llm() in this file and run again, OR")
        log.info(f"  2. Paste the contents of {output_path} into any LLM manually.")
        log.info("=" * 60)
    else:
        # LLM returned a result — save the report
        report_path = save_report(report_text, report_date, mode)
        log.info("-" * 60)
        log.info(f"Report draft saved: {report_path}")
        log.info("=" * 60)


if __name__ == "__main__":
    main()
