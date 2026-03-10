# CLAUDE.md — Persistent Instructions for Claude Code

This file contains standing instructions for Claude Code when working on the WEEKLYREPORT project.
Read this before making any changes to the codebase.

---

## Project Purpose

This is a **local pipeline for weekly commodity market report generation**.

The pipeline:
1. Ingests historical PDF/DOCX reports and converts them to clean markdown
2. Uses those reports as **style and narrative references only** — not as text to copy
3. Combines current weekly data with a writing prompt
4. Generates a new weekly report draft using an LLM

---

## Critical: How Historical Reports Should Be Used

**Historical reports are style references, not source material.**

- Do NOT copy sentences or paragraphs from historical reports into new reports
- DO use them to learn tone, structure, narrative flow, and analytical approach
- The generated report must reflect current weekly data, not past data
- Each report should feel freshly written, not templated

The distinction: a journalist reads past articles to understand the publication's voice,
then writes a new article based on today's facts. That is the intended use.

---

## Writing Style Requirements

Generated reports must be:

- **Analytical**: interpret data, identify trends, explain causes and effects
- **Narrative**: tell a coherent story across the week's events, not a bullet list
- **Professional**: suited for commodity traders, analysts, and institutional readers
- **Precise**: use correct commodity terminology, units, and market references
- **Concise**: no filler text, no repetition, no generic disclaimers

Avoid:
- Bullet-point summaries masquerading as analysis
- Vague language ("prices were mixed", "sentiment was uncertain")
- Copying phrases verbatim from historical reports
- Overlong introductions or conclusions

---

## Development Principles

Keep everything:

- **Simple**: prefer readable code over clever code
- **Local**: no cloud services, no external APIs until explicitly added
- **Debuggable**: log what each script does, use clear error messages
- **Incremental**: scripts can be run independently; each step saves its output

When adding new functionality:
- Add it to the appropriate existing script, not a new one, unless there is a clear reason
- Keep function names descriptive
- Add a docstring to every function
- Add inline comments where the logic is not obvious
- Do not add complexity that is not needed right now

---

## Folder Conventions

| Folder | Contents |
|---|---|
| `reports_raw/` | Original files only. Never modify files here. |
| `reports_clean/` | Auto-generated. Scripts write here; do not manually edit. |
| `weekly_data/` | Weekly inputs: prices, notes, CSV files. Named by date. |
| `prompts/` | Prompt templates and persistent writing instruction files. |
| `output/` | Generated report drafts. Named by date. |
| `logs/` | Log files from each script run. |

---

## Script Order

```
convert_reports.py  →  clean_reports.py  →  select_reports.py  →  build_prompt.py  →  generate_report.py
```

Scripts 1 and 2 run once per batch of new historical reports.
Scripts 3–5 run every week.

---

## LLM Integration (Not Yet Active)

`generate_report.py` is a placeholder. When LLM integration is added:
- Prefer local models (Ollama, llama.cpp) before adding cloud APIs
- Keep the API call isolated in one function so it is easy to swap providers
- Always save the raw LLM response to `logs/` before post-processing

---

## What NOT to Do

- Do not add a vector database until explicitly requested
- Do not add a web interface or server
- Do not add authentication or multi-user logic
- Do not refactor scripts that are working correctly
- Do not change the folder structure without updating README.md and this file
