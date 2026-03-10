"""
generate_report.py
------------------
Sends the assembled prompt to an LLM and saves the generated report draft.

This script is currently a PLACEHOLDER. The LLM integration is not active yet.
When you are ready to connect an LLM, see the section marked "LLM INTEGRATION"
below and follow the instructions there.

Current behaviour (placeholder mode):
    - Reads the most recent prompt from prompts/
    - Prints the prompt to the terminal so you can inspect it
    - Saves a placeholder output file to output/ as a reminder

Usage:
    python scripts/generate_report.py
    python scripts/generate_report.py --date 2026-03-10
    python scripts/generate_report.py --prompt prompts/prompt_2026-03-10.txt

Arguments (all optional):
    --date    Report date (YYYY-MM-DD). Determines which prompt file to load and
              how to name the output file. Defaults to today.
    --prompt  Explicit path to a prompt file (overrides --date).
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR  = PROJECT_ROOT / "prompts"
OUTPUT_DIR   = PROJECT_ROOT / "output"
LOG_DIR      = PROJECT_ROOT / "logs"

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "generate_report.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── Prompt loading ────────────────────────────────────────────────────────────

def find_prompt(report_date: str, explicit_path: str | None) -> Path | None:
    """
    Locate the prompt file to use.

    Priority:
      1. Explicit path provided via --prompt argument
      2. prompts/prompt_<date>.txt
      3. Most recently modified prompt file in prompts/

    Returns the Path if found, or None if no prompt file is available.
    """
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        else:
            log.error(f"Prompt file not found: {explicit_path}")
            return None

    # Try the date-based name first
    dated_file = PROMPTS_DIR / f"prompt_{report_date}.txt"
    if dated_file.exists():
        return dated_file

    # Fall back to the most recent prompt file
    all_prompts = sorted(PROMPTS_DIR.glob("prompt_*.txt"), key=lambda f: f.stat().st_mtime)
    if all_prompts:
        fallback = all_prompts[-1]
        log.warning(f"No prompt for {report_date}. Using most recent: {fallback.name}")
        return fallback

    log.error("No prompt files found in prompts/. Run build_prompt.py first.")
    return None


# ── LLM INTEGRATION ───────────────────────────────────────────────────────────
#
# This is where you will add LLM support when you are ready.
#
# Option A — Local model via Ollama (recommended for local-first setup):
#
#   import requests
#
#   def call_llm(prompt: str) -> str:
#       response = requests.post(
#           "http://localhost:11434/api/generate",
#           json={"model": "llama3", "prompt": prompt, "stream": False}
#       )
#       return response.json()["response"]
#
# Option B — OpenAI-compatible API:
#
#   from openai import OpenAI
#
#   def call_llm(prompt: str) -> str:
#       client = OpenAI()  # reads OPENAI_API_KEY from environment
#       response = client.chat.completions.create(
#           model="gpt-4o",
#           messages=[{"role": "user", "content": prompt}]
#       )
#       return response.choices[0].message.content
#
# Option C — Anthropic Claude API:
#
#   import anthropic
#
#   def call_llm(prompt: str) -> str:
#       client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment
#       message = client.messages.create(
#           model="claude-opus-4-6",
#           max_tokens=4096,
#           messages=[{"role": "user", "content": prompt}]
#       )
#       return message.content[0].text
#
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> str:
    """
    Placeholder function. Replace this with a real LLM call when ready.
    See the LLM INTEGRATION section above for examples.
    """
    # This is the placeholder — it does not call any model.
    return (
        "[PLACEHOLDER OUTPUT — LLM NOT YET CONNECTED]\n\n"
        "To generate a real report:\n"
        "1. Choose an LLM provider (Ollama, OpenAI, Anthropic)\n"
        "2. Replace the body of call_llm() in generate_report.py\n"
        "3. Run this script again\n\n"
        "Your prompt has been saved and is ready to send."
    )


def save_output(content: str, report_date: str) -> Path:
    """
    Save the generated report to output/<date>_report.md.
    Also saves the raw LLM response to logs/ for debugging.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / f"{report_date}_report.md"
    output_file.write_text(content, encoding="utf-8")
    log.info(f"Report saved to: {output_file}")

    # Also save raw response to logs for debugging
    raw_log = LOG_DIR / f"{report_date}_llm_response.txt"
    raw_log.write_text(content, encoding="utf-8")
    log.info(f"Raw response saved to: {raw_log.name}")

    return output_file


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Generate weekly report using LLM.")
    parser.add_argument(
        "--date", type=str, default=str(date.today()),
        help="Report date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "--prompt", type=str, default=None,
        help="Explicit path to a prompt file (overrides --date)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    report_date = args.date

    log.info("=" * 60)
    log.info(f"Starting generate_report.py — {report_date}")

    # Find the prompt file
    prompt_file = find_prompt(report_date, args.prompt)
    if not prompt_file:
        log.error("Cannot generate report without a prompt. Exiting.")
        sys.exit(1)

    log.info(f"Using prompt: {prompt_file.name}")
    prompt = prompt_file.read_text(encoding="utf-8")
    log.info(f"Prompt length: {len(prompt):,} characters")

    # Call the LLM (placeholder or real)
    log.info("Calling LLM...")
    report_text = call_llm(prompt)

    # Save the output
    output_file = save_output(report_text, report_date)

    log.info("-" * 60)
    log.info(f"Done. Report draft saved to: {output_file}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
