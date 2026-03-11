# weekly_data — Weekly Data Pack

This folder holds the market data for the current week's report.
Create one subfolder per week, named by date.

---

## Folder Structure

```
weekly_data/
└── 2026-03-12/                    ← one folder per report week (YYYY-MM-DD)
    ├── prices.md                  ← CME futures prices and spreads
    ├── exports.md                 ← USDA export inspections and sales
    ├── wasde.md                   ← WASDE key numbers (post_wasde mode only)
    ├── weather.md                 ← weather and crop progress summary
    └── notes.txt                  ← analyst free-text observations
```

The folder name must match the `--date` argument you pass to `generate_report.py`.
If no subfolder exists for the date, the script falls back to reading files
directly from `weekly_data/`.

---

## File Descriptions

### prices.md
CME front-month futures prices and calendar spreads for corn, soybeans, and wheat.
Include: close price, week-over-week change, Dec/Mar or Nov/Jan spread, % of full carry.
Also include key international futures if relevant (Dalian, Euronext, B3).

Example content:
```
Corn Dec '26:    $4.38/bu   -$0.07 (-1.6%)   Dec/Mar spread: +$0.17 (77% full carry)
Soybeans Nov '26: $10.21/bu  -$0.12 (-1.2%)   Nov/Jan spread: +$0.19 (85% full carry)
Wheat Dec '26:   $5.44/bu   +$0.03 (+0.6%)   Dec/Mar spread: +$0.18 (82% full carry)
```

### exports.md
USDA weekly export inspections and export sales data.
Include: weekly volume per commodity, comparison to prior week, comparison to last year,
top destination countries, cumulative year-to-date vs. USDA target.

### wasde.md  (post_wasde mode)
Key USDA WASDE numbers released this week.
Include: U.S. ending stocks (bbu), world ending stocks (MMT), production, yield,
and any changes from the prior WASDE. Compare to pre-report trade expectations.

### weather.md
U.S. crop progress (% harvested or planted, % good/excellent ratings).
South American planting or harvest progress.
Key weather events or forecasts that affect near-term supply.

### notes.txt
Free-text analyst observations — anything that does not fit cleanly into
the structured files above. This is optional but valuable. Write in plain
sentences. Examples: notable fund activity, basis anomalies, policy news,
logistics disruptions.

---

## Quick-Start for a Post-WASDE Report

1. Create the folder:
   ```
   mkdir weekly_data/2026-03-12
   ```

2. Add your data files (prices.md, exports.md, wasde.md, weather.md, notes.txt).

3. Run the pipeline:
   ```
   python scripts/generate_report.py --mode post_wasde --date 2026-03-12
   ```

4. The assembled prompt is saved to:
   ```
   output/post_wasde_prompt.txt
   ```

5. Paste the prompt into your LLM of choice, or implement `call_llm()` in
   `scripts/generate_report.py` to automate the call.
