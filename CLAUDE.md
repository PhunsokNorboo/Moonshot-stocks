# Moonshot Stocks - Project Context

> This file keeps Claude informed about the project state. Point Claude here if conversation compacts.

## Project Overview

**Moonshot Stocks** is a Python stock screener that automatically finds multi-bagger candidates (stocks that could 5x-10x).

- **GitHub:** https://github.com/PhunsokNorboo/Moonshot-stocks
- **Location:** `/Users/phunsoknorboo/Stocks automatic/`
- **Main file:** `main.py`
- **Output:** `output/multibagger_results.csv` and `output/multibagger_report.md`

## Current Version: v2.0 (Enhanced Analysis Suite)

### What It Does
1. Fetches 6,800+ US stocks from NASDAQ/NYSE + S&P 500
2. Filters: Price $5-40, Market Cap $100M-$15B, Volume >200K, US only
3. Enriches with technical indicators, insider data, earnings data
4. Scores on 7 factors (115 points max)
5. Outputs ranked candidates to CSV and Markdown

### Scoring System (115 points)
| Factor | Points | What It Measures |
|--------|--------|------------------|
| Growth | 25 | Revenue growth, earnings growth, forward P/E |
| Value | 20 | P/S, PEG, P/B ratios, analyst upside |
| Quality | 20 | Margins, ROE, debt levels |
| Momentum | 10 | 52-week position, beta |
| Sentiment | 10 | Insider/institutional ownership |
| Sector | 15 | Priority sectors (Tech, Healthcare, Aerospace) |
| Technical | 10 | RSI, MACD, SMA, volume trends |
| Insider Bonus | 5 | Recent insider buying activity |

### Technical Indicators Added in v2
- **RSI (14-day):** Overbought (>70) / Oversold (<30)
- **MACD:** Bullish/Bearish signal
- **50-day SMA:** Price above/below moving average
- **Volume ratio:** Current vs average volume

### Priority Sectors (bonus scoring)
- Technology, Healthcare, Industrials, Communication Services, Energy
- Priority industries: Aerospace, AI, Quantum, Semiconductors, Biotech, Clean Energy, Fintech, Robotics, Cloud

## Latest Run Results (Jan 30, 2026)

**Runtime:** 61 minutes (v2 with enrichment)

### Top 5 Candidates
| Rank | Ticker | Price | Score | Sector |
|------|--------|-------|-------|--------|
| 1 | ZVRA | $8.86 | 81/115 | Healthcare - Biotechnology |
| 2 | RGR | $37.05 | 80/115 | Industrials - Aerospace & Defense |
| 3 | CRMD | $8.02 | 79/115 | Healthcare - Biotechnology |
| 4 | ISSC | $19.05 | 78/115 | Industrials - Aerospace & Defense |
| 5 | INVA | $19.75 | 77/115 | Healthcare - Biotechnology |

### Oversold Opportunities (RSI < 30)
| Ticker | RSI | Score | Notes |
|--------|-----|-------|-------|
| MDXG | 12.7 | 75 | CMS Medicare reimbursement cuts crashed it |
| SLDE | 29 | 74 | Insurance sector |
| NAGE | 30 | 76 | Biotech |

### Key Finding: MDXG
- Score: 75 (high quality company)
- RSI: 12.7 (extreme oversold)
- **Why it crashed:** CMS changed Medicare reimbursement rules on Jan 1, 2026. Fixed cap of $125.38/sq cm for skin substitutes instead of ASP+6%. Analysts cut targets but still rate it Buy with ~$10 target (vs $5.14 current = 94% upside potential).

## Version History

### v1.0 (Initial)
- Basic 6-factor scoring (100 points)
- Fetches stocks, filters, scores, outputs
- Runtime: ~50 minutes

### v2.0 (Current)
- Added technical indicators (RSI, MACD, SMA, volume)
- Added insider transaction tracking
- Added earnings data (next date, beat/miss history)
- New scoring: Technical (10 pts) + Insider Bonus (5 pts)
- Enhanced reports with special sections
- Runtime: ~70-80 minutes

## What Worked / Didn't Work

### Worked Well
- Technical indicators differentiate stocks (1-7 point variation)
- Oversold list is actionable (found MDXG opportunity)
- Core screening finds quality small/mid-caps

### Needs Improvement
- Insider data came back empty (yfinance limitation)
- Earnings data found no upcoming earnings (timing issue)
- Consider alternative APIs: Finnhub, SEC EDGAR, Alpha Vantage

## Future Ideas Discussed

1. **Speed & Caching** - Cache stock data so reruns take 2 mins instead of 70
2. **Automation** - Schedule daily scans, email/SMS alerts
3. **UI/Dashboard** - Web interface to view and filter results
4. **Better Data Sources** - Finnhub for insider data, SEC EDGAR for filings

## How to Run

```bash
# Install dependencies
pip install yfinance pandas numpy requests tqdm

# Run the screener
cd "/Users/phunsoknorboo/Stocks automatic"
python main.py

# Check results
cat output/multibagger_report.md
```

## File Structure

```
/Users/phunsoknorboo/Stocks automatic/
├── main.py                      # Main screener (v2.0)
├── README.md                    # Project documentation
├── CLAUDE.md                    # This file - project context
├── MULTIBAGGER_PROJECT_SPEC.md  # Original specification
└── output/
    ├── multibagger_results.csv  # Full data (378KB, 1214 stocks)
    └── multibagger_report.md    # Top 25 + special sections
```

## Commands for Claude

If conversation compacted, run these to get current state:
```bash
# Check latest results
head -100 "/Users/phunsoknorboo/Stocks automatic/output/multibagger_report.md"

# See top stocks from last run
grep "Score:" /path/to/last/output | head -15

# Check git status
git -C "/Users/phunsoknorboo/Stocks automatic" log --oneline -5
```

---
*Last updated: Jan 30, 2026 after v2.0 run*
