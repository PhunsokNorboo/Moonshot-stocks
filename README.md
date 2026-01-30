# Moonshot Stocks v2.0

A Python stock screener that automatically finds multi-bagger candidates - stocks priced $5-40 with potential to grow 5x-10x.

## Features

### Core Screening
- Fetches 6,800+ US stocks automatically (S&P 500 + NASDAQ/NYSE)
- Filters by price ($5-40), market cap ($100M-$15B), and volume (>200K)

### 7-Factor Scoring System (115 points max)

| Factor | Points | What It Measures |
|--------|--------|------------------|
| **Growth** | 25 | Revenue growth, earnings growth, forward P/E |
| **Value** | 20 | P/S, PEG, P/B ratios, analyst upside |
| **Quality** | 20 | Margins, ROE, debt levels |
| **Momentum** | 10 | 52-week position, beta |
| **Sentiment** | 10 | Insider/institutional ownership |
| **Sector** | 15 | Priority sectors (Tech, Healthcare, Aerospace) |
| **Technical** | 10 | RSI, MACD, SMA, volume trends |
| **Insider Bonus** | 5 | Recent insider buying activity |

### New in v2.0
- **Technical Indicators**: RSI(14), MACD, 20/50-day SMA, volume analysis
- **Insider Transactions**: Recent buys/sells, net value, sentiment
- **Earnings Data**: Next earnings date, days until, beat/miss history
- **Enhanced Reports**: Insider buying alerts, upcoming earnings, oversold stocks

## Quick Start

```bash
# Install dependencies
pip install yfinance pandas numpy requests tqdm

# Run the screener
python main.py

# Check results
cat output/multibagger_report.md
```

## Sample Output

```
1. ZVRA - Zevra Therapeutics
   💰 $8.86 | Market Cap: $0.50B
   ⭐ Score: 82/115 (G:17 V:12 Q:18 M:10 S:5 Sec:15 Tech:5 Ins:0)
   📊 RSI: 42 | MACD: Bullish | Above 50-SMA: ✓
   👔 Insiders: 2 buys, 0 sells (+$1.2M)
   📅 Earnings: Feb 15 (17d) | Last: Beat 12%
   🏭 Healthcare - Biotechnology
```

## Output Files

- `output/multibagger_results.csv` - Full data for all screened stocks
- `output/multibagger_report.md` - Top 25 candidates + special sections:
  - Stocks with insider buying
  - Upcoming earnings (next 14 days)
  - Technically oversold opportunities

## Runtime

- Full scan: ~70-80 minutes (6,800 stocks with technical enrichment)
- Basic scan (v1): ~50 minutes

## Priority Sectors

The screener gives bonus points to high-growth sectors:
- Technology
- Healthcare / Biotechnology
- Industrials / Aerospace & Defense
- Communication Services
- Energy / Clean Tech
