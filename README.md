# WEEKLYREPORT — Local Weekly Commodity Report Pipeline

A simple, local Python pipeline for generating weekly commodity market reports.
Historical reports are used as style and narrative references, not copied text.

---

## Project Purpose

This pipeline automates the generation of weekly commodity market reports by:

1. Converting historical PDF/DOCX reports into clean markdown text
2. Selecting relevant historical reports as style references
3. Combining current weekly data, analyst notes, and writing instructions into a prompt
4. Passing that prompt to an LLM to generate a new weekly report draft

Everything runs locally. No cloud infrastructure required.

---

## Folder Structure

```
WEEKLYREPORT/
├── reports_raw/        # Drop your original PDF and DOCX files here
├── reports_clean/      # Converted and cleaned markdown files (auto-generated)
├── weekly_data/        # Weekly commodity data: prices, notes, CSV exports
├── prompts/            # Prompt templates and persistent writing instructions
├── scripts/            # All Python pipeline scripts
├── output/             # Generated report drafts (auto-generated)
├── logs/               # Log files from each script run (auto-generated)
├── README.md           # This file
├── CLAUDE.md           # Persistent instructions for Claude Code
└── requirements.txt    # Python dependencies
```

---

## Expected Workflow

Run the scripts in this order each week:

```
Step 1 — Convert raw reports (only needed once per report)
  python scripts/convert_reports.py

Step 2 — Clean the converted text
  python scripts/clean_reports.py

Step 3 — Select relevant historical reports for reference
  python scripts/select_reports.py

Step 4 — Build the prompt for the LLM
  python scripts/build_prompt.py

Step 5 — Generate the new report draft
  python scripts/generate_report.py
```

Steps 1 and 2 only need to run again when you add new historical reports.
Steps 3–5 run every week.

---

## How to Add Your Historical Reports

1. Copy your PDF and DOCX files into the `reports_raw/` folder.
2. Run `python scripts/convert_reports.py` to convert them to markdown.
3. Run `python scripts/clean_reports.py` to normalize the text.
4. The cleaned files will appear in `reports_clean/` and are ready to use.

You only need to do this once per report. The pipeline will remember them.

---

## What Each Script Does

| Script | Purpose |
|---|---|
| `convert_reports.py` | Converts PDF and DOCX files from `reports_raw/` to markdown in `reports_clean/` |
| `clean_reports.py` | Normalizes whitespace, removes repeated headers/footers, preserves paragraph order |
| `select_reports.py` | Selects the most recent and relevant historical reports to use as style references |
| `build_prompt.py` | Combines writing instructions + selected reports + weekly data + analyst notes into a single prompt file |
| `generate_report.py` | Sends the prompt to an LLM and saves the generated draft to `output/` |

---

## Weekly Data Files

Each week, add your data files to the `weekly_data/` folder. These can be:
- CSV price exports
- Plain text market summaries
- Analyst notes (`.txt` files)

Name them clearly, for example: `2026-03-10_prices.csv`, `2026-03-10_notes.txt`

---

## First-Time Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

That's it. No database, no server, no cloud account needed.

---

## Requirements

- Python 3.9 or later
- Dependencies listed in `requirements.txt`
