# weekly_data — Weekly Data Pack

This folder holds the market data used to write each week's report.
Create one subfolder per week, named by the report date (YYYY-MM-DD).
The pipeline reads all files from that subfolder automatically.

---

## Folder Structure

```
weekly_data/
└── 2026-03-12/              ← one folder per report (use the report date)
    ├── market_prices.md     ← CME front-month futures closes and weekly change
    ├── spreads.md           ← calendar spreads and % of full carry
    ├── exports.md           ← USDA export inspections and sales
    ├── basis.md             ← U.S. cash basis by region and market type
    ├── cftc.md              ← CFTC managed money positioning
    ├── weather.md           ← U.S. crop progress; South American conditions
    ├── wasde.md             ← WASDE key numbers (post_wasde mode only)
    └── notes.md             ← analyst observations and context
```

The folder name must match the `--date` you pass to `generate_report.py`.
All files are optional — include only what you have. Missing files are skipped.

---

## File Descriptions

### market_prices.md
CME front-month closing prices for corn, soybeans, and wheat.
Include: contract name, close price, week-over-week change, percent change.
Also include key international futures if available (Dalian, Euronext, B3 São Paulo).

Example:
```
Corn Dec '26:     $4.38/bu    -$0.07  (-1.6%)
Soybeans Nov '26: $10.21/bu   -$0.12  (-1.2%)
Wheat Dec '26:    $5.44/bu    +$0.03  (+0.6%)

Dalian Corn (Jan): ¥2,290/MT (~$7.90/bu)  +0.3%
Euronext Wheat (May): €202.50/MT (~$215)  -0.8%
```

### spreads.md
Calendar spreads and percent of full carry for each commodity.
Full carry assumes 7% annual interest + $0.05/bu/month storage/insurance.

Example:
```
Corn Dec/Mar:    +$0.17   (77% of full carry)
Soybeans Nov/Jan: +$0.19  (85% of full carry)
Wheat Dec/Mar:   +$0.18   (82% of full carry)
```
Also include any spread changes week-over-week and what they imply (widening carry
= market prefers to store; narrowing = market wants movement).

### exports.md
USDA weekly export inspections and export sales.
Include: weekly volume (MMT) per commodity, comparison to prior week and to last year,
top destination countries, cumulative year-to-date vs. USDA annual target.

### basis.md
U.S. cash basis conditions — cents over/under the nearby futures contract.
Separate river/Gulf export basis from inland processor basis for each commodity.
Include any notable regional splits (e.g. Illinois River vs. Iowa ethanol plant).

Example:
```
Corn:
  CIF Gulf (export):   -18¢ under Dec  (vs. -12¢ last week)
  Illinois River:      -30¢ under Dec
  Iowa ethanol plant:  +2¢ over Dec

Soybeans:
  CIF Gulf:            -35¢ under Nov
  Illinois crush plant: -20¢ under Nov
```

### cftc.md
CFTC Commitments of Traders — managed money (speculative) positioning.
Include: net position (long or short), week-over-week change, and direction trend.

Example:
```
Corn:     net short 92,000 contracts  (reduced by 14,000 on week)
Soybeans: net long  28,000 contracts  (added 6,000 on week)
Wheat:    net short 71,000 contracts  (roughly unchanged)
```

### weather.md
U.S. crop conditions and crop progress (from USDA Crop Progress report).
South American planting or harvest status and any weather risks.

Example:
```
U.S.:
  Corn planting: 8% complete (vs. 5% avg)
  Soybean planting: 4% complete (vs. 3% avg)
  Winter wheat condition: 47% good/excellent (vs. 52% last year)

South America:
  Brazil: soybean harvest 68% complete (ahead of pace); second-crop corn planting 92% done
  Argentina: recent rains improved corn crop in Buenos Aires province; harvest begins late April
```

### wasde.md  ← include this file only for post_wasde mode
Key USDA WASDE numbers released this week.
For each commodity include: the new USDA estimate, the change from the prior WASDE,
the pre-report trade expectation (if known), and the market reaction.

Example:
```
CORN (March WASDE):
  U.S. ending stocks: 1.540 bbu  (prior: 1.520 bbu; trade expected: 1.510 bbu)
  U.S. production:    unchanged at 15.143 bbu
  World ending stocks: 295.0 MMT  (prior: 293.4 MMT)
  Market reaction: Dec corn +3¢ on release; rally faded by close

SOYBEANS:
  U.S. ending stocks: 380 mbu  (prior: 380 mbu; trade expected: 375 mbu)
  Exports revised:    unchanged
  Market reaction: slightly bearish; Nov soybeans -4¢

WHEAT:
  U.S. ending stocks: 815 mbu  (prior: 798 mbu; trade expected: 800 mbu)
  World ending stocks: 258.7 MMT (bearish surprise vs. 257.9 expected)
  Market reaction: Dec wheat -6¢; fresh contract low
```

### notes.md
Free-text analyst observations — anything not captured in the structured files above.
Write in plain sentences. This is read directly by the LLM so clarity matters.

Include: fund activity notes, basis anomalies, logistics disruptions, policy news,
freight changes, currency movements, and anything you want the report to address.

---

## How to Create a Weekly Data Pack

```bash
# 1. Create the folder for your report date
mkdir weekly_data/2026-03-12

# 2. Add the data files (any combination; all are optional except what your mode needs)
#    For post_wasde: include wasde.md
#    For pre_wasde:  omit wasde.md
#    For weekly:     omit wasde.md

# 3. Run the pipeline
python scripts/generate_report.py --mode post_wasde --date 2026-03-12

# 4. The assembled prompt is saved to:
#    output/post_wasde_prompt.txt
#
#    Paste it into your LLM, or implement call_llm() in generate_report.py
```

---

## File Priority

The pipeline reads all files in the date subfolder alphabetically.
File names do not need to match these names exactly — any `.md` or `.txt` file
in the folder will be included. The names above are the recommended convention
so that the prompt reads in a logical order and the LLM can orient itself
(prices first, then spreads, then exports, basis, positioning, weather, wasde, notes).
