"""
build_prompt.py
---------------
Assembles the final prompt for the LLM, mode-aware.

Supported modes:
    post_wasde  — WASDE was released this week; report leads with balance sheet analysis
    pre_wasde   — WASDE is due next week; report frames the setup and risk scenarios
    weekly      — standard mid-cycle report; no major USDA report this week

The prompt is built from four components in this order:

  1. Style guide          — prompts/style_guide.md
                            Describes the publication's tone, structure, and conventions.

  2. Writing instructions — prompts/writing_instructions.txt
                            Standing rules for the LLM (do/don't).

  3. Style references     — the selected historical reports listed in
                            prompts/selected_reports.txt (produced by select_reports.py)
                            These show the LLM how a real report looks and reads.

  4. Weekly data          — all .txt, .csv, .md files found in --data-dir
                            The actual market data for this week's report.

  5. Task block           — mode-specific instructions telling the LLM exactly
                            what to write and what structure to follow.

The assembled prompt is saved to:
    prompts/prompt_<YYYY-MM-DD>_<mode>.txt

Usage:
    python scripts/build_prompt.py --mode post_wasde
    python scripts/build_prompt.py --mode pre_wasde
    python scripts/build_prompt.py --mode weekly
    python scripts/build_prompt.py --mode post_wasde --date 2026-03-12 --data-dir weekly_data/2026-03-12
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT      = Path(__file__).parent.parent
PROMPTS_DIR       = PROJECT_ROOT / "prompts"
LOG_DIR           = PROJECT_ROOT / "logs"
SELECTION_FILE    = PROMPTS_DIR / "selected_reports.txt"
STYLE_GUIDE_FILE  = PROMPTS_DIR / "style_guide.md"
INSTRUCTIONS_FILE = PROMPTS_DIR / "writing_instructions.txt"

VALID_MODES = ("post_wasde", "pre_wasde", "weekly")

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "build_prompt.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_style_guide() -> str:
    """
    Load prompts/style_guide.md, which describes the publication's tone,
    section structure, and analytical conventions.
    Returns empty string if the file does not exist.
    """
    if STYLE_GUIDE_FILE.exists():
        content = STYLE_GUIDE_FILE.read_text(encoding="utf-8").strip()
        log.info(f"Loaded style guide ({len(content):,} chars)")
        return content
    log.warning(f"{STYLE_GUIDE_FILE.name} not found — style guide will be omitted.")
    return ""


def load_writing_instructions() -> str:
    """
    Load prompts/writing_instructions.txt — standing do/don't rules for the LLM.
    Falls back to a minimal default if the file does not exist.
    """
    if INSTRUCTIONS_FILE.exists():
        content = INSTRUCTIONS_FILE.read_text(encoding="utf-8").strip()
        log.info(f"Loaded writing instructions ({len(content):,} chars)")
        return content
    log.warning(f"{INSTRUCTIONS_FILE.name} not found — using built-in default.")
    return (
        "You are an expert commodity market analyst writing a professional weekly report.\n"
        "Be analytical, narrative, and precise.\n"
        "Do not copy from the reference reports — use them only to understand tone and structure.\n"
        "Base the report entirely on the weekly data provided."
    )


def load_selected_reports() -> str:
    """
    Load the content of each report listed in prompts/selected_reports.txt.
    Each file path is absolute (written by select_reports.py).
    Returns empty string if the selection file is missing or empty.
    """
    if not SELECTION_FILE.exists():
        log.warning(
            f"{SELECTION_FILE.name} not found — no style references included. "
            "Run select_reports.py --mode <mode> first."
        )
        return ""

    paths = [p.strip() for p in SELECTION_FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
    if not paths:
        log.warning("selected_reports.txt is empty — no style references loaded.")
        return ""

    blocks = []
    for path_str in paths:
        p = Path(path_str)
        if not p.exists():
            log.warning(f"Reference report not found, skipping: {path_str}")
            continue
        content = p.read_text(encoding="utf-8").strip()
        blocks.append(
            f"--- REFERENCE REPORT: {p.name} ---\n"
            f"{content}\n"
            f"--- END REFERENCE REPORT ---"
        )
        log.info(f"Loaded reference: {p.name}")

    if not blocks:
        log.warning("No reference reports could be loaded.")
    return "\n\n".join(blocks)


def load_weekly_data(data_dir: Path) -> str:
    """
    Load all readable files (.txt, .csv, .md) from data_dir.
    Files are included verbatim, each labeled by filename.
    Returns empty string if the folder is empty or missing.
    """
    if not data_dir.exists():
        log.warning(f"Data directory not found: {data_dir}")
        return ""

    readable = {".txt", ".csv", ".md"}
    files = sorted(
        f for f in data_dir.iterdir()
        if f.is_file() and f.suffix.lower() in readable and not f.name.startswith(".")
    )

    if not files:
        log.warning(
            f"No data files found in {data_dir}. "
            "Add price files, CSV exports, or notes before building the prompt."
        )
        return ""

    blocks = []
    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        blocks.append(f"--- DATA FILE: {f.name} ---\n{content}\n--- END DATA FILE ---")
        log.info(f"Loaded data: {f.name}")

    return "\n\n".join(blocks)


# ── Mode-specific task blocks ─────────────────────────────────────────────────

def build_task_block(mode: str, report_date: str) -> str:
    """
    Return the closing TASK section for the prompt.
    This tells the LLM exactly what to write and how, based on the report mode.
    """
    preamble = (
        f"You are writing the HigbyBarrett Weekly Commodity Market Report "
        f"for the week of {report_date}.\n\n"
        "CRITICAL RULES — read before writing:\n"
        "- Do NOT copy any sentence, phrase, or number from the reference reports above.\n"
        "- The reference reports are provided so you can match tone, structure, and analytical "
        "approach — NOT to recycle their content.\n"
        "- Every piece of analysis must come from the weekly data provided above.\n"
        "- Use vague language only when genuine uncertainty exists; otherwise state the number "
        "and the direction.\n"
        "- Write in full analytical paragraphs. Bullet points only in the Watchlist section.\n"
    )

    if mode == "post_wasde":
        task = (
            "THIS IS A POST-WASDE REPORT.\n"
            "The USDA WASDE report was released this week. This is the primary event.\n\n"
            "Required structure:\n"
            "1. Executive Summary — one paragraph per commodity (corn, soybeans, wheat). "
            "Each paragraph must lead with what the WASDE showed vs. expectations, "
            "then state the market price reaction with exact figures.\n"
            "2. WASDE Balance Sheet Review — for each commodity: key USDA number changes, "
            "comparison to pre-report trade expectations, comparison to last year, "
            "and which direction the market moved in response.\n"
            "3. Post-WASDE Cash & Basis — how interior bids, river basis, and processor "
            "bids adjusted in the days following the release.\n"
            "4. Export & International Trade — weekly inspections, sales, and origin "
            "competition (Brazil FOB, Argentina FOB, Black Sea FOB vs. U.S. Gulf).\n"
            "5. Weather & Crop Conditions — U.S. and South America; use Crop Progress data.\n"
            "6. Macro & Policy — dollar, crude, interest rates, any policy developments.\n"
            "7. Synthesis & Outlook — base-case price ranges for each commodity. "
            "Name specific bullish AND bearish triggers. "
            "End with a one-paragraph verdict on market structure.\n"
            "8. Watchlist — bullet list of next week's key reports and what to watch for in each.\n"
        )

    elif mode == "pre_wasde":
        task = (
            "THIS IS A PRE-WASDE REPORT.\n"
            "The USDA WASDE report is due to be released next week. "
            "Markets are positioning ahead of it.\n\n"
            "Required structure:\n"
            "1. Executive Summary — one paragraph per commodity. "
            "Lead with the current price level and the dominant pre-WASDE narrative "
            "for each (what is the market pricing in, what is the risk).\n"
            "2. Commodity Deep Dives — for each of corn, soybeans, wheat:\n"
            "   - Current futures level, weekly move, carry structure (% of full carry)\n"
            "   - Funds/CFTC positioning direction and trend\n"
            "   - Cash & basis (river vs. processor split)\n"
            "   - Export flows (inspections, sales, key buyers)\n"
            "   - International competition (Brazil, Argentina, Black Sea FOB)\n"
            "   - So What? paragraph\n"
            "3. WASDE Setup — trade consensus expectations for each commodity. "
            "What are the key unknowns? What would a bullish surprise look like? "
            "What would a bearish surprise look like? Name specific numbers.\n"
            "4. Weather & Crop Conditions — U.S. and South America.\n"
            "5. Macro & Policy — dollar, crude, any policy risk ahead of WASDE.\n"
            "6. Synthesis & Outlook — current base-case price range AND "
            "WASDE risk scenarios (upside and downside) with specific trigger levels.\n"
            "7. Watchlist — WASDE as the top item; include what figure to watch "
            "in each commodity and what the market-moving threshold is.\n"
        )

    else:  # weekly
        task = (
            "THIS IS A STANDARD WEEKLY REPORT.\n"
            "No major USDA supply/demand report is due this week. "
            "The focus is on current market dynamics.\n\n"
            "Required structure:\n"
            "1. Executive Summary — one paragraph per commodity. "
            "Lead with the net price direction and the single most important driver.\n"
            "2. Commodity Deep Dives — for each of corn, soybeans, wheat:\n"
            "   - Current futures level, weekly move, carry structure (% of full carry)\n"
            "   - Funds/CFTC positioning direction and trend\n"
            "   - Cash & basis (river vs. processor split)\n"
            "   - Export flows (inspections, sales, key buyers)\n"
            "   - International competition (Brazil, Argentina, Black Sea FOB)\n"
            "   - So What? paragraph\n"
            "3. U.S. Cash Market & Basis — cross-commodity summary of basis conditions.\n"
            "4. International Trade Flows — Brazil, Argentina, China, Black Sea, EU.\n"
            "5. Weather & Crop Conditions — U.S. and South America.\n"
            "6. Macro & Policy — dollar, crude, any relevant policy developments.\n"
            "7. Synthesis & Outlook — base-case price ranges, bullish and bearish triggers, "
            "one-paragraph verdict.\n"
            "8. Watchlist — upcoming reports and events with specific things to watch for.\n"
        )

    return preamble + "\n" + task


# ── Prompt assembly ───────────────────────────────────────────────────────────

def assemble_prompt(
    style_guide: str,
    instructions: str,
    references: str,
    weekly_data: str,
    task_block: str,
    mode: str,
) -> str:
    """
    Combine all components into one prompt string, clearly labeled.
    Order: style guide → writing instructions → reference reports → weekly data → task.
    """
    sections = []

    # 1. Style guide
    if style_guide:
        sections.append("=== STYLE GUIDE ===\n" + style_guide)
    else:
        sections.append("=== STYLE GUIDE ===\n[Not available]")

    # 2. Writing instructions
    sections.append("=== WRITING INSTRUCTIONS ===\n" + instructions)

    # 3. Historical reference reports (style examples only)
    label = f"=== HISTORICAL REFERENCE REPORTS — {mode.upper()} (STYLE AND STRUCTURE ONLY) ==="
    if references:
        sections.append(
            label + "\n"
            "The following reports are provided as style references ONLY.\n"
            "Do NOT copy their text, data, or narrative. "
            "Use them to understand tone, paragraph structure, and analytical approach.\n\n"
            + references
        )
    else:
        sections.append(label + "\n[No reference reports selected. Run select_reports.py first.]")

    # 4. Weekly data (the actual input for this week's report)
    if weekly_data:
        sections.append("=== WEEKLY MARKET DATA (USE THIS TO WRITE THE REPORT) ===\n" + weekly_data)
    else:
        sections.append(
            "=== WEEKLY MARKET DATA ===\n"
            "[No data files found. Add files to the weekly data folder before building the prompt.]"
        )

    # 5. Task
    sections.append("=== TASK ===\n" + task_block)

    return "\n\n".join(sections)


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Build the LLM prompt for a weekly commodity report."
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="weekly",
        help="Report type: post_wasde | pre_wasde | weekly (default: weekly)",
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
            "Folder containing this week's data files. "
            "Defaults to weekly_data/<date>/ if it exists, otherwise weekly_data/."
        ),
    )
    return parser.parse_args()


def resolve_data_dir(data_dir_arg: str | None, report_date: str) -> Path:
    """
    Resolve the weekly data directory.
    Priority: --data-dir arg → weekly_data/<date>/ → weekly_data/
    """
    if data_dir_arg:
        return Path(data_dir_arg)
    dated = PROJECT_ROOT / "weekly_data" / report_date
    if dated.exists():
        return dated
    return PROJECT_ROOT / "weekly_data"


def main():
    args = parse_args()
    mode        = args.mode
    report_date = args.date
    data_dir    = resolve_data_dir(args.data_dir, report_date)

    log.info("=" * 60)
    log.info(f"Starting build_prompt.py — {report_date} — mode: {mode}")
    log.info(f"Data directory: {data_dir}")

    # Load components
    style_guide  = load_style_guide()
    instructions = load_writing_instructions()
    references   = load_selected_reports()
    weekly_data  = load_weekly_data(data_dir)
    task_block   = build_task_block(mode, report_date)

    # Assemble
    prompt = assemble_prompt(style_guide, instructions, references, weekly_data, task_block, mode)

    # Save
    PROMPTS_DIR.mkdir(exist_ok=True)
    output_file = PROMPTS_DIR / f"prompt_{report_date}_{mode}.txt"
    output_file.write_text(prompt, encoding="utf-8")

    log.info(f"Prompt saved : {output_file.name}")
    log.info(f"Prompt size  : {len(prompt):,} chars")
    log.info("-" * 60)
    log.info("Done. Run generate_report.py --mode next.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
