# Moonshot Stocks

A Python stock screener that automatically finds multi-bagger candidates - stocks priced $5-40 with potential to grow 5x-10x.

## Features

- Fetches 6,800+ US stocks automatically (S&P 500 + NASDAQ/NYSE)
- Filters by price ($5-40), market cap ($100M-$15B), and volume (>200K)
- Scores stocks using a 6-factor system (100 points total):
  - **Growth** (25 pts): Revenue growth, earnings growth
  - **Value** (20 pts): P/S, PEG, P/B ratios
  - **Quality** (20 pts): Margins, ROE, debt levels
  - **Momentum** (10 pts): 52-week position, beta
  - **Sentiment** (10 pts): Insider/institutional ownership
  - **Sector** (15 pts): Priority sectors (Tech, Healthcare, Aerospace)
- Outputs ranked candidates to CSV and Markdown reports

## Quick Start

```bash
# Install dependencies
pip install yfinance pandas numpy requests tqdm

# Run the screener
python main.py

# Check results
cat output/multibagger_report.md
```

## Output

- `output/multibagger_results.csv` - Full data for all screened stocks
- `output/multibagger_report.md` - Top 25 candidates with score breakdowns

## Runtime

Full scan takes ~50 minutes (6,800 stocks with rate limiting).
