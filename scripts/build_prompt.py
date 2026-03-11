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

        "════════════════════════════════════════════════════════\n"
        "CRITICAL RULES — READ THESE BEFORE WRITING A SINGLE WORD\n"
        "════════════════════════════════════════════════════════\n\n"

        "ANTI-COPYING RULES (absolute — no exceptions):\n"
        "- Do NOT copy any sentence, phrase, clause, or transition from any reference report.\n"
        "  Not even a partial sentence. Not even paraphrased with the same structure.\n"
        "- Do NOT reuse opening sentences. Every section and every paragraph must begin with\n"
        "  freshly written sentences that are specific to this week's data and events.\n"
        "- Do NOT reuse 'So What?' wording. The conclusion, framing, and commercial implication\n"
        "  of every 'So What?' paragraph must be written entirely from scratch.\n"
        "- Do NOT mirror any prior report paragraph-by-paragraph, even loosely.\n"
        "  Reading a reference and then reproducing its sequence of observations with new numbers\n"
        "  is exactly what is forbidden. The argument must grow from this week's data, not be\n"
        "  transplanted from a prior week.\n"
        "- Do NOT echo the prior week's conclusions or verdicts. If last week's report said the\n"
        "  market was 'rangebound with a bearish tilt', and this week that is still true, you must\n"
        "  say it differently and justify it with this week's specific evidence.\n"
        "- Do NOT recycle the same transitions mechanically. Words like 'Meanwhile', 'Against that\n"
        "  backdrop', 'On the cash side', and 'Looking ahead' are legitimate only when they arise\n"
        "  naturally from this week's argument — not as slot-fillers borrowed from a prior report.\n"
        "- Do NOT import any number, price, or data point from the reference reports.\n"
        "  Every figure cited must appear in the weekly data section below.\n\n"

        "FRESHNESS RULES:\n"
        "- Historical reports are references only. They demonstrate method, voice, and structure.\n"
        "  They do not dictate what to write this week. The weekly data does that.\n"
        "- The current week's facts must drive every section. If a data point is not in the\n"
        "  weekly data below, it does not belong in the report.\n"
        "- Repeated wording is unacceptable. Any sentence that could have been lifted verbatim\n"
        "  or near-verbatim from a prior report must be rewritten from scratch.\n"
        "- The output must sound like the same writer on a new week — same analytical voice,\n"
        "  same institutional register, same structural discipline — but with entirely fresh\n"
        "  language, fresh transitions, and analysis that belongs only to this week.\n"
        "  It should not sound like a paraphrase of last week.\n"
        "- Maintain continuity of thought — the reader should recognize the same analyst —\n"
        "  but never repeat sentence patterns, structural templates, or verbal formulas.\n"
        "- Every section transition must be freshly written for this report.\n"
        "- The Synthesis section must open with a sentence that could only have been written\n"
        "  this week — referencing a specific event, figure, or shift from the weekly data.\n"
        "- The Watchlist must name specific upcoming reports and specific thresholds to watch,\n"
        "  drawn entirely from the current market context.\n\n"

        "STYLE REQUIREMENTS (preserve these precisely):\n"
        "- Analytical and confident: every claim is backed by a specific figure or observable\n"
        "  market fact. Never hedge without a reason.\n"
        "- Narrative discipline: sections are connected paragraphs that build an argument.\n"
        "  Do NOT substitute bullet lists for analytical prose in any body section.\n"
        "- Institutional register: technical terms (basis, carry, FOB, MMT, bbu, WASDE,\n"
        "  managed money, % of full carry) are used without definition.\n"
        "- 'So What?' discipline: every major commodity section ends with a 'So What?'\n"
        "  paragraph that names a clear, direct implication for a commercial operator\n"
        "  (merchandiser, elevator, crusher, or end-user).\n"
        "- Precise: state price levels, percent changes, spread widths, and FOB comparisons\n"
        "  with exact values from the data. 'Prices fell' is not acceptable;\n"
        "  'December corn fell 2.5 percent to $4.21/bu' is.\n"
        "- Cause and effect: always explain why prices moved, not just that they moved.\n\n"

        "ROLE OF THE REFERENCE REPORTS:\n"
        "- They demonstrate the analytical framework, section depth, and institutional voice.\n"
        "- They do not tell you what to write this week. The weekly data does that.\n"
        "- Continuity with prior weeks comes from consistent analytical method and structure —\n"
        "  not from recycling sentences, transitions, or verdicts.\n"
        "- Preserve the analytical voice and structural discipline you see in the references,\n"
        "  but generate fresh language every time.\n"
        "- Treat the references as a craftsman studies a master's technique: absorb the method,\n"
        "  then produce entirely original work.\n\n"

        "════════════════════════════════════════════════════════\n\n"
    )

    # ── Shared deep-dive subsection templates ─────────────────────────────────

    # Subsections present in every deep dive (all modes)
    _dd_common = (
        "   Futures & Spreads — one paragraph of 6–10 sentences.\n"
        "     Open with a sentence that connects to the balance sheet or prior\n"
        "     subsection — do not open with the commodity name alone.\n"
        "     State the front-month close, the weekly move in cents and percent,\n"
        "     and the carry structure. Express every calendar spread as a dollar\n"
        "     width AND as a percent of full carry. Interpret what the spread level\n"
        "     signals about market preference for storage vs. movement. Explain\n"
        "     what the carry structure means for a commercial operator making\n"
        "     storage or movement decisions right now. Do not merely list numbers.\n\n"
        "   [PRODUCTS_CRUSH_PLACEHOLDER]\n"
        "   Funds & Positioning — one paragraph of 6–10 sentences.\n"
        "     Open with a transitional sentence referencing the prior subsection\n"
        "     (e.g. 'The positioning data reinforces that signal.' or 'The futures\n"
        "     curve alone does not explain the price behavior — the fund book does.').\n"
        "     State the managed money net position, the week-over-week change,\n"
        "     and the directional trend over the past four weeks. Explain what the\n"
        "     positioning extreme (if any) implies for price risk — specifically,\n"
        "     whether a crowded short or long creates squeeze risk or amplifies\n"
        "     downside. State the asymmetry: what kind of catalyst would be needed\n"
        "     to move this position, and what would happen to prices if it moved.\n\n"
        "   Cash & Basis — one paragraph of 6–10 sentences.\n"
        "     Open with a transitional sentence connecting to the futures or\n"
        "     positioning picture (e.g. 'The cash market provides a clearer read\n"
        "     on near-term demand.' or 'The futures signal finds confirmation in\n"
        "     the basis structure.').\n"
        "     Report Gulf CIF basis, Illinois/Ohio River basis, and relevant\n"
        "     processor or ethanol plant bids. Quote each as cents over/under the\n"
        "     nearby futures contract and note the week-over-week change. Explain\n"
        "     the divergence (if any) between export-channel basis and domestic\n"
        "     processor basis — these often move in opposite directions and carry\n"
        "     different signals. State what the basis behavior implies about the\n"
        "     strength and durability of demand in each channel.\n\n"
        "   Export Sales & Inspections — one paragraph of 6–10 sentences.\n"
        "     State weekly inspections in MMT, compare to the prior week and to the\n"
        "     same week last year. State cumulative YTD inspections vs. the USDA\n"
        "     annual export target (as a percent shipped with weeks remaining).\n"
        "     Calculate the weekly run rate required to close the YTD gap and state\n"
        "     whether the current pace achieves it. Name the top destination countries\n"
        "     and whether any large buyer is accelerating or slowing purchases.\n"
        "     Include the most recent weekly export sales figure, whether it was above\n"
        "     or below expectations, and what that implies for forward pipeline coverage.\n\n"
        "   Global Context — one paragraph of 6–10 sentences.\n"
        "     Compare U.S. Gulf FOB offers to Brazil Santos FOB, Argentina Up-River\n"
        "     FOB, and Black Sea FOB. State the exact price spread between U.S. and\n"
        "     the cheapest competitor origin. Explain which buyers are choosing which\n"
        "     origin and why (price, logistics, quality, relationship). Assess whether\n"
        "     the U.S. price gap to South America is widening or narrowing and what\n"
        "     that trajectory implies for U.S. export market share over the next\n"
        "     60–90 days. State specifically which markets remain open to U.S. origin\n"
        "     and why.\n\n"
        "   So What — one paragraph of 6–10 sentences.\n"
        "     This is the most important paragraph in the section. Provide direct,\n"
        "     actionable commercial guidance. Name at least two specific operator\n"
        "     types from: elevator operators, merchandisers, crush plant operators,\n"
        "     exporters, end-users (millers/feedlots/ethanol plants), hedgers.\n"
        "     For each operator type, state specifically what they should do or\n"
        "     watch for, with a threshold or timing reference grounded in this\n"
        "     week's data. Do not write a summary. Do not be generic.\n"
        "     A So What that could have appeared in last week's report has failed.\n"
    )

    # Subsection added at the top of each deep dive for post-WASDE only
    _dd_wasde_sub = (
        "   Post-WASDE Balance Sheet — one paragraph of 6–10 sentences.\n"
        "     This subsection appears ONLY in post-WASDE reports.\n"
        "     Open with the price reaction, not the USDA numbers — lead with what\n"
        "     the market did, then explain why.\n"
        "     State the new ending stocks estimate, the change from the prior WASDE,\n"
        "     the pre-report trade expectation, and whether the print was bullish or\n"
        "     bearish relative to that expectation. Explain the specific USDA\n"
        "     assumption changes (production, exports, crush, feed use) that drove\n"
        "     the revision. Integrate the balance sheet shift with the price behavior:\n"
        "     if the print was bearish but prices recovered, explain why; if it was\n"
        "     bullish but prices faded, explain why. State what the new balance sheet\n"
        "     level implies for the supply narrative going forward.\n\n"
    )

    # Products & Crush: soybeans only, placed between Futures & Spreads and Funds
    _products_crush = (
        "   Products & Crush — one paragraph of 6–10 sentences. [SOYBEANS ONLY — do not include for corn or wheat]\n"
        "     Open with a transitional sentence from Futures & Spreads (e.g. 'The\n"
        "     futures spread structure is consistent with what crush margins are\n"
        "     showing.' or 'The flat-price weakness masks a more constructive picture\n"
        "     inside the crush complex.').\n"
        "     Discuss current soybean crush margins and what is driving them (meal\n"
        "     demand, biodiesel policy, oil values). State NOPA crush data if\n"
        "     available and compare to expectations and prior year. Explain whether\n"
        "     domestic processing demand is providing a price floor that offsets\n"
        "     export headwinds, or whether crush economics are also under pressure.\n"
        "     State what crush-plant operators are doing in the origination market\n"
        "     as a result.\n\n"
    )

    def _deep_dive(commodity: str, wasde_mode: bool) -> str:
        """Build the deep-dive block for one commodity."""
        header = f"{commodity} Market Deep Dive\n\n"
        wasde_prefix = _dd_wasde_sub if wasde_mode else ""
        body = _dd_common.replace(
            "   [PRODUCTS_CRUSH_PLACEHOLDER]\n",
            _products_crush if commodity == "Soybean" else "",
        )
        return header + wasde_prefix + body

    # ── Shared section templates ───────────────────────────────────────────────

    _us_cash = (
        "5. US Cash Market & Basis\n\n"
        "   This section must contain exactly four subsections. Each is one paragraph\n"
        "   of 5–7 sentences. Open with a cross-commodity framing sentence that\n"
        "   connects this section to the deep dives above.\n\n"
        "   Corn — report Gulf CIF, river, and ethanol-plant basis as cents\n"
        "     over/under the nearby contract with week-over-week change. Explain\n"
        "     the direction and cause. State whether the movement is logistical\n"
        "     (temporary) or demand-driven (structural).\n\n"
        "   Soybeans — report Gulf CIF, river, and crush-plant basis with\n"
        "     week-over-week change. Explain the divergence (if any) between\n"
        "     export-channel and domestic-processor basis. State what that\n"
        "     divergence reveals about where demand is strongest.\n\n"
        "   Wheat — report SRW Gulf CIF, Ohio River, and flour-mill basis with\n"
        "     week-over-week change. State what the basis level implies about\n"
        "     U.S. wheat's export competitiveness relative to Black Sea and EU.\n\n"
        "   So What — one paragraph of 5–7 sentences synthesizing the\n"
        "     cross-commodity basis picture. Address merchandisers and elevator\n"
        "     operators specifically: which commodity's basis offers the best\n"
        "     current origination opportunity, and in which channel. Provide a\n"
        "     sequencing recommendation if basis strength differs by commodity.\n\n"
    )

    _intl_trade = (
        "6. International Cash & Trade Flows\n\n"
        "   One paragraph of 5–7 sentences per region. Each paragraph must open\n"
        "   with the commercial fact (FOB price, harvest pace, or policy change),\n"
        "   then explain the implication for U.S. origin competition.\n\n"
        "   Brazil — harvest pace vs. last year, current FOB offer levels with the\n"
        "     spread vs. U.S. Gulf, export program pace, currency effect.\n"
        "     State explicitly: is Brazilian competition widening, narrowing, or\n"
        "     stable vs. U.S. this week?\n\n"
        "   Argentina — crop conditions, current FOB offers, export tax policy,\n"
        "     currency. State how Argentine origin competes with U.S. in\n"
        "     specific destination markets.\n\n"
        "   China — import pace vs. prior year, buyer behavior (accelerating,\n"
        "     steady, slowing), state reserve activity if relevant. State whether\n"
        "     China is a supportive or neutral factor for U.S. export pace.\n\n"
        "   EU / Black Sea — FOB offers, export pace, any logistical or policy\n"
        "     developments. Focus on wheat competition to North Africa and Middle\n"
        "     East; corn competition to EU feed markets.\n\n"
        "   Other Regions — any other origin or destination that moved markets this\n"
        "     week (India, Ukraine, Mexico, Middle East import tenders).\n\n"
        "   So What — one paragraph of 5–7 sentences. Name the one or two origins\n"
        "     currently winning global market share and why. Address exporters\n"
        "     specifically: which markets remain viable for U.S. origin, what\n"
        "     price level or spread adjustment would restore competitiveness, and\n"
        "     what forward-booking strategy is appropriate given current spreads.\n\n"
    )

    _key_fundamentals_wasde = (
        "7. Key Fundamentals & Reports\n\n"
        "   Each subsection must be one paragraph. Do not use bullets inside paragraphs.\n\n"
        "   USDA WASDE [POST-WASDE REPORTS ONLY] — summarize the WASDE release at the\n"
        "     report level (not per-commodity; those details belong in the deep dives).\n"
        "     State the overall tone (bullish, bearish, neutral), which commodity\n"
        "     surprised most vs. expectations, and the aggregate market reaction.\n\n"
        "   Export Inspections — weekly total across all grains; compare to prior week\n"
        "     and prior year; highlight any single-commodity standout.\n\n"
        "   Export Sales — weekly net new sales; state whether the figure was above\n"
        "     or below pre-report expectations; name any large single-destination sales.\n\n"
        "   NOPA Soybean Crush — most recent monthly NOPA crush figure; compare to\n"
        "     expectations and to the same month last year; state what it implies for\n"
        "     the USDA crush forecast.\n\n"
        "   CFTC Positioning — cross-commodity summary of managed money positioning\n"
        "     changes this week; identify where the positioning risk is most acute.\n\n"
        "   So What — one paragraph of 5–7 sentences on what this week's government\n"
        "     data collectively signals. Address the demand pace vs. USDA's annual\n"
        "     target: are inspections and sales running ahead of, in line with, or\n"
        "     behind the pace required to meet the USDA forecast? State the\n"
        "     implication for the next WASDE revision risk (higher, lower, or\n"
        "     unchanged ending stocks). Name which operator type should act on this.\n\n"
    )

    _key_fundamentals_no_wasde = (
        "7. Key Fundamentals & Reports\n\n"
        "   Each subsection must be one paragraph. Do not use bullets inside paragraphs.\n\n"
        "   Export Inspections — weekly total across all grains; compare to prior week\n"
        "     and prior year; highlight any single-commodity standout.\n\n"
        "   Export Sales — weekly net new sales; state whether the figure was above\n"
        "     or below pre-report expectations; name any large single-destination sales.\n\n"
        "   NOPA Soybean Crush — most recent monthly NOPA crush figure; compare to\n"
        "     expectations and to the same month last year; state what it implies for\n"
        "     the USDA crush forecast.\n\n"
        "   CFTC Positioning — cross-commodity summary of managed money positioning\n"
        "     changes this week; identify where the positioning risk is most acute.\n\n"
        "   So What — one paragraph of 5–7 sentences on what this week's government\n"
        "     data collectively signals. Address the demand pace vs. USDA's annual\n"
        "     target: are inspections and sales running ahead of, in line with, or\n"
        "     behind the pace required to meet the USDA forecast? State the\n"
        "     implication for the next WASDE revision risk (higher, lower, or\n"
        "     unchanged ending stocks). Name which operator type should act on this.\n\n"
    )

    _intl_reports = (
        "8. International Reports\n\n"
        "   One paragraph of 4–6 sentences per region, covering official government\n"
        "   or trade-body crop estimates, export data, or policy announcements\n"
        "   released this week. For each region, state the specific figure, compare\n"
        "   it to USDA's current estimate, and explain the implication.\n\n"
        "   Brazil — CONAB, ABIOVE, ANEC, or Mato Grosso state ag data. State the\n"
        "     specific estimate and the gap vs. USDA. Explain the direction of\n"
        "     revision risk for the next WASDE.\n\n"
        "   Argentina — BCBA, Rosario Exchange, or government export data. Same\n"
        "     structure: specific figure, USDA gap, revision risk direction.\n\n"
        "   China — CNGOIC, customs data, or state reserve announcements. Focus on\n"
        "     what the data implies for import demand trajectory.\n\n"
        "   EU / Black Sea — EU Commission export licenses, IGC estimates, or\n"
        "     Russian/Ukrainian ag ministry data. Focus on what is new vs. prior week.\n\n"
        "   So What — one paragraph of 4–6 sentences on what the international data\n"
        "     changes about the global supply picture relative to the USDA balance\n"
        "     sheet. State the net revision risk direction (will world stocks likely\n"
        "     go higher or lower in the next WASDE?) and which commodity is most\n"
        "     exposed to revision.\n\n"
    )

    _weather = (
        "9. Weather & Crop Conditions\n\n"
        "   One paragraph of 5–7 sentences per region. For each region, state the\n"
        "   current condition data, compare it to prior week and prior year, and\n"
        "   explain the market implication. Do not stop at reporting the rating —\n"
        "   explain what it means for production potential and price.\n\n"
        "   United States — current winter wheat condition ratings (good/excellent\n"
        "     percent, poor/very poor percent, week-over-week change, year-over-year\n"
        "     comparison); soil moisture by state; planting progress where relevant;\n"
        "     7-14 day forecast. State specifically: what rating threshold, if\n"
        "     breached, would attract weather-premium buying?\n\n"
        "   Brazil — soybean harvest percent complete vs. last year and 5-year average;\n"
        "     quality reports from key producing states; safrinha corn planting percent\n"
        "     complete and condition; identify the next weather risk window and when\n"
        "     it opens.\n\n"
        "   Argentina — crop condition ratings for corn and soybeans with\n"
        "     week-over-week and year-over-year comparisons; recent rainfall or\n"
        "     dryness events with millimeter data; harvest progress; any revision to\n"
        "     yield estimates from consultancy or exchange sources.\n\n"
        "   Global — any other weather development with a market-moving implication\n"
        "     (Black Sea, EU winter wheat, Australia, India). If none, state that\n"
        "     no weather risk outside the Americas is market-relevant this week.\n\n"
        "   So What — one paragraph of 5–7 sentences. Rank the weather risks by\n"
        "     potential price impact. Name the specific region and threshold (e.g.\n"
        "     'Kansas good/excellent below 38 percent nationally by April 1') that\n"
        "     would produce a measurable price response. State what commercial\n"
        "     operators should be monitoring and at what frequency.\n\n"
    )

    _synthesis = (
        "10. Synthesis & Outlook\n\n"
        "    This section must contain the following paragraphs in this exact order.\n"
        "    Do not combine paragraphs. Do not add extra paragraphs.\n"
        "    Each paragraph must be 6–8 sentences except where noted.\n\n"
        "    Introduction — one paragraph of 6–8 sentences tying together the week's\n"
        "      dominant theme. REQUIRED: open with a sentence referencing a specific\n"
        "      data point or event from this week that no prior report could have\n"
        "      contained. Then state what that fact reveals about the structural\n"
        "      condition of the market — not just what happened, but what it means.\n"
        "      Connect the three commodities into a single overarching narrative.\n\n"
        "    Corn Outlook — one paragraph of 6–8 sentences. State the base-case price\n"
        "      range for the front month and the next major contract with specific\n"
        "      price levels. Define the upper and lower bounds with specific factors\n"
        "      (not just 'bullish/bearish'). Name the single most important variable\n"
        "      that will determine direction over the next two to three weeks and\n"
        "      explain why it is the deciding factor.\n\n"
        "    Soybean Outlook — one paragraph of 6–8 sentences. Same format.\n"
        "      Include the crush margin dynamic if it is relevant to the price range.\n\n"
        "    Wheat Outlook — one paragraph of 6–8 sentences. Same format.\n"
        "      Address both SRW and HRW if they are diverging structurally.\n\n"
        "    Bullish Triggers — one paragraph of 6–8 sentences naming at least three\n"
        "      specific, data-grounded events or thresholds that would push prices\n"
        "      materially higher. Each trigger must be specific and measurable —\n"
        "      not 'weather risk' but 'Kansas good/excellent below 38 percent\n"
        "      nationally by April 1 with Kansas topsoil adequate below 30 percent'.\n"
        "      Explain the mechanism: why each trigger would produce a price rally.\n\n"
        "    Bearish Triggers — one paragraph of 6–8 sentences naming at least three\n"
        "      specific, data-grounded events or thresholds that would push prices\n"
        "      lower. Same specificity requirement. Explain the mechanism for each.\n\n"
        "    Summary — one paragraph of 6–8 sentences delivering a clear, direct\n"
        "      verdict on market structure and bias (bullish, bearish, or neutral).\n"
        "      This paragraph must be derived entirely from this week's evidence.\n"
        "      End with a sentence that tells a commercial operator the most important\n"
        "      single action they should take based on this week's collective picture.\n\n"
        "    Watchlist — exactly five bullet points. Bullets are the ONLY list\n"
        "      permitted in the entire report. Each bullet must name:\n"
        "      (a) a specific report or event due next week,\n"
        "      (b) the specific figure or threshold to watch for,\n"
        "      (c) what a bullish vs. bearish outcome would look like in concrete terms.\n\n"
    )

    # ── Section enforcement header ─────────────────────────────────────────────

    _section_lock = (
        "════════════════════════════════════════════════════════\n"
        "REQUIRED REPORT STRUCTURE — ENFORCED\n"
        "════════════════════════════════════════════════════════\n\n"
        "The report must contain exactly these 10 sections in this exact order.\n"
        "You may NOT add, remove, rename, reorder, or combine any section.\n"
        "You may NOT invent subsections not listed below.\n"
        "You may NOT use bullet lists in any body paragraph outside the Watchlist.\n\n"
        "  1.  Executive Summary\n"
        "  2.  Corn Market Deep Dive\n"
        "  3.  Soybean Market Deep Dive\n"
        "  4.  Wheat Market Deep Dive\n"
        "  5.  US Cash Market & Basis\n"
        "  6.  International Cash & Trade Flows\n"
        "  7.  Key Fundamentals & Reports\n"
        "  8.  International Reports\n"
        "  9.  Weather & Crop Conditions\n"
        "  10. Synthesis & Outlook\n\n"
        "════════════════════════════════════════════════════════\n\n"
    )

    # ── Executive Summary (shared across all modes) ────────────────────────────

    _exec_summary = (
        "1. Executive Summary\n\n"
        "   This section must contain exactly five paragraphs of 5–7 sentences each.\n"
        "   Each paragraph must begin with its title in bold or capitalized inline\n"
        "   label, followed immediately by the paragraph text.\n"
        "   No additional paragraphs allowed.\n\n"
        "   Each paragraph must follow this five-element structure:\n"
        "     Sentence 1 — dominant market event or price reaction\n"
        "     Sentence 2 — key data point that drove it (exact figure, comparison)\n"
        "     Sentence 3 — structural interpretation of what the data means\n"
        "     Sentence 4 — positioning or behavioral context\n"
        "     Sentence 5 — forward implication or signal for the week ahead\n\n"
        "   Do NOT write Executive Summary paragraphs as bullet summaries.\n"
        "   Do NOT list three events and call it a paragraph.\n"
        "   Each paragraph is a mini-thesis, not a headline wire summary.\n\n"
        "   Corn — 5–7 sentences. Lead with the most important corn development.\n"
        "     In a post-WASDE week, lead with the WASDE surprise vs. expectations\n"
        "     and the price reaction. Include at least one exact price figure and\n"
        "     one percent-change figure.\n\n"
        "   Soybeans — 5–7 sentences. Same structure. Lead with the dominant soybean\n"
        "     development. In a post-WASDE week, lead with the WASDE surprise and\n"
        "     the November soybean price reaction. Name the key driver of the move.\n\n"
        "   Wheat — 5–7 sentences. Same structure. Lead with the dominant wheat\n"
        "     development. Note any new contract highs or lows. Include the basis\n"
        "     implication if it is the primary story.\n\n"
        "   Macro / Policy — 5–7 sentences. Cover the dollar index level and\n"
        "     week-over-week change, crude oil price and change, and any government\n"
        "     policy or trade development that affected grain prices. Explain the\n"
        "     channel through which macro conditions affected grain markets.\n\n"
        "   Weather — 5–7 sentences. Identify the single most market-relevant weather\n"
        "     situation globally. State its current status with specific data\n"
        "     (rating percent, topsoil moisture, harvest pace). State the price\n"
        "     implication and the threshold that would change the weather narrative.\n\n"
    )

    # ── Assemble mode-specific task ────────────────────────────────────────────

    if mode == "post_wasde":
        mode_header = (
            "THIS IS A POST-WASDE REPORT.\n"
            "The USDA WASDE report was released this week. It is the primary market event.\n"
            "Each commodity deep dive must include a 'Post-WASDE Balance Sheet' subsection\n"
            "as its first paragraph. The 'Key Fundamentals & Reports' section must include\n"
            "a 'USDA WASDE' subsection as its first paragraph.\n\n"
        )
        kf_block = _key_fundamentals_wasde
        wasde_mode = True

    elif mode == "pre_wasde":
        mode_header = (
            "THIS IS A PRE-WASDE REPORT.\n"
            "The USDA WASDE report is due to be released next week.\n"
            "Markets are positioning ahead of it.\n"
            "Do NOT include a 'Post-WASDE Balance Sheet' subsection in any deep dive.\n"
            "Do NOT include a 'USDA WASDE' subsection in Key Fundamentals & Reports.\n"
            "In the deep dives, replace 'Post-WASDE Balance Sheet' with a 'WASDE Setup'\n"
            "subsection that states: trade consensus expectations for this commodity,\n"
            "the key unknown, what a bullish surprise looks like, what a bearish surprise\n"
            "looks like, and which specific number the market will focus on.\n\n"
        )
        kf_block = _key_fundamentals_no_wasde
        wasde_mode = False

    else:  # weekly
        mode_header = (
            "THIS IS A STANDARD WEEKLY REPORT.\n"
            "No major USDA supply/demand report was released or is due this week.\n"
            "Do NOT include a 'Post-WASDE Balance Sheet' subsection in any deep dive.\n"
            "Do NOT include a 'USDA WASDE' subsection in Key Fundamentals & Reports.\n\n"
        )
        kf_block = _key_fundamentals_no_wasde
        wasde_mode = False

    corn_dd    = "2. " + _deep_dive("Corn",    wasde_mode)
    soybean_dd = "3. " + _deep_dive("Soybean", wasde_mode)
    wheat_dd   = "4. " + _deep_dive("Wheat",   wasde_mode)

    task = (
        mode_header
        + _section_lock
        + "SECTION DETAIL — write each section exactly as specified below.\n\n"
        + _exec_summary
        + corn_dd
        + soybean_dd
        + wheat_dd
        + _us_cash
        + _intl_trade
        + kf_block
        + _intl_reports
        + _weather
        + _synthesis
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
        ref_note = (
            "THESE REPORTS ARE STYLE REFERENCES ONLY.\n"
            "They are ordered by relevance: same-type reports (matching this report's mode)\n"
            "appear first, followed by recent reports for narrative continuity.\n\n"
            "Permitted use:\n"
            "  ✓ Observe the section sequence and depth of analysis\n"
            "  ✓ Absorb the analytical register and institutional voice\n"
            "  ✓ Note how 'So What?' paragraphs are structured as commercial implications\n"
            "  ✓ Understand how spreads, basis, and carry are explained together\n\n"
            "Prohibited use:\n"
            "  ✗ Do NOT copy sentences, transitions, openings, or closings\n"
            "  ✗ Do NOT mirror a reference report's paragraph sequence with new numbers\n"
            "  ✗ Do NOT use any number or data point from these reports\n"
            "  ✗ Do NOT reuse 'So What?' conclusions even in paraphrase\n\n"
        )
        sections.append(label + "\n" + ref_note + references)
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
