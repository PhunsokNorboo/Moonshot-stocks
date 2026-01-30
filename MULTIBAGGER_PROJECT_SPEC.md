# 🚀 Multi-Bagger Stock Finder - Project Specification

---
## 📋 INSTRUCTIONS FOR CLAUDE

**Please build a complete Python program based on this specification.**

Create a single `main.py` file that I can run with `python main.py`. The program should:
1. Automatically fetch thousands of US stocks from the internet
2. Filter them based on my criteria
3. Score and rank them
4. Output the top candidates to console and save to files

No need to ask clarifying questions - everything you need is in this document. Just build it!

---

## Project Goal

Build a Python program that **automatically finds stocks under $40 with potential to grow 5x-10x** (like Palantir did from ~$9 to $150+). 

**Key Requirement:** The program should NOT use a hand-picked list of stocks. Instead, it should **dynamically fetch the ENTIRE US stock universe (3,000+ stocks)** and filter/score them automatically to find hidden gems.

---

## What the Program Should Do

### Step 1: Fetch Stock Universe (Automatic)
Pull ALL US-traded stocks from multiple sources:

1. **S&P 500** - from Wikipedia table
2. **NASDAQ listings** - from `https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt`
3. **NYSE listings** - similar source or use yfinance screener
4. **Recent IPOs** - to catch new high-growth companies

**Target: 2,000-5,000 unique tickers to screen**

### Step 2: Filter Stocks (Multi-Stage)
Apply these filters to narrow down candidates:

| Filter | Criteria | Why |
|--------|----------|-----|
| **Price** | $5 - $40 | Our target range for multi-baggers |
| **Market Cap** | $100M - $15B | Small/mid caps have room to grow 10x |
| **Avg Volume** | > 200,000 shares/day | Need liquidity |
| **Country** | USA only | Focus on US markets |
| **Exchange** | NYSE, NASDAQ, AMEX | Major exchanges only |

### Step 3: Score Each Stock (0-100 points)
Use a **6-factor scoring system** based on academic research on multi-bagger characteristics:

| Factor | Weight | Max Points | What to Measure |
|--------|--------|------------|-----------------|
| **Growth** | 25% | 25 | Revenue growth, earnings growth, forward EPS vs trailing |
| **Value** | 20% | 20 | P/S ratio, PEG ratio, P/B ratio, analyst upside |
| **Quality** | 20% | 20 | Gross margin, operating margin, ROE, debt/equity |
| **Momentum** | 10% | 10 | 52-week position, price vs SMA50, beta |
| **Sentiment** | 10% | 10 | Insider ownership, institutional ownership, short interest |
| **Sector** | 15% | 15 | Bonus for high-growth sectors (see below) |

### Step 4: Prioritize High-Growth Sectors
Give bonus points to stocks in these emerging sectors:

**Priority Sectors:**
- Technology
- Healthcare  
- Industrials
- Communication Services
- Energy

**Priority Industries (extra bonus):**
- Space/Aerospace (like LUNR - my personal interest!)
- AI/Machine Learning
- Quantum Computing
- Semiconductors
- Cybersecurity
- Biotechnology/Genomics
- Clean Energy/Nuclear
- Fintech
- Robotics/Automation
- Cloud/Data Infrastructure

### Step 5: Output Results
Generate:
1. **Console output** - Top 15-20 ranked stocks with scores
2. **CSV file** - Full data for all stocks that passed screening
3. **Markdown report** - Summary with top 25 candidates and score breakdowns

---

## Scoring Details

### Growth Score (0-25 points)
```
Revenue Growth (YoY):
  > 50%  → 12 points
  > 30%  → 9 points
  > 15%  → 6 points
  > 0%   → 3 points

Earnings Growth (YoY):
  > 50%  → 8 points
  > 25%  → 6 points
  > 10%  → 3 points

Forward P/E < Trailing P/E (growth expected):
  Yes   → 5 points
```

### Value Score (0-20 points)
```
Price/Sales Ratio:
  < 3   → 5 points
  < 6   → 4 points
  < 10  → 2 points

PEG Ratio:
  < 1   → 5 points
  < 1.5 → 4 points
  < 2   → 2 points

Price/Book Ratio:
  < 2   → 5 points
  < 4   → 3 points
  < 7   → 1 point

Analyst Upside (target vs current price):
  > 50% → 5 points
  > 30% → 4 points
  > 15% → 2 points
```

### Quality Score (0-20 points)
```
Gross Margin:
  > 70% → 5 points
  > 50% → 4 points
  > 35% → 2 points

Operating Margin:
  > 25% → 5 points
  > 15% → 4 points
  > 5%  → 2 points
  > 0%  → 1 point

Return on Equity (ROE):
  > 20% → 5 points
  > 15% → 4 points
  > 10% → 2 points

Debt/Equity Ratio:
  < 0.3 → 5 points
  < 0.7 → 4 points
  < 1.0 → 2 points
```

### Momentum Score (0-10 points)
```
52-Week Position (where price is in range):
  30-70% (middle) → 4 points  # Research shows this outperforms!
  20-80%          → 2 points

Beta:
  1.0-1.8 → 4 points  # Moderate volatility preferred
  0.8-2.5 → 2 points

Analyst Recommendation (1=Strong Buy, 5=Sell):
  ≤ 2.0 → 2 points
```

### Sentiment Score (0-10 points)
```
Insider Ownership:
  > 15% → 3 points
  > 8%  → 2 points

Institutional Ownership:
  30-65% → 3 points  # Sweet spot
  20-80% → 2 points

Short Interest:
  < 5%  → 2 points
  < 10% → 1 point

Analyst Coverage:
  3-15 analysts → 2 points  # Not too obscure, not over-covered
```

### Sector Score (0-15 points)
```
Priority Sector (Tech, Healthcare, etc.):
  Yes → 8 points
  No  → 3 points

Priority Industry (Space, AI, Quantum, etc.):
  Direct match     → 7 points
  Related keywords → 4 points
  Other            → 1 point
```

---

## Technical Requirements

### Libraries to Use
```
yfinance          - Stock data (FREE, no API key needed)
pandas            - Data manipulation
numpy             - Calculations
requests          - Fetching stock lists
beautifulsoup4    - Parsing HTML if needed
tqdm              - Progress bars (optional)
```

### Data to Fetch for Each Stock (via yfinance)
```python
stock = yf.Ticker("LUNR")
info = stock.info

# Key fields to extract:
info['currentPrice']           # Current stock price
info['marketCap']              # Market capitalization
info['averageVolume']          # Average daily volume
info['sector']                 # Sector
info['industry']               # Industry
info['country']                # Country

# Valuation
info['trailingPE']             # P/E ratio
info['forwardPE']              # Forward P/E
info['priceToSalesTrailing12Months']  # P/S ratio
info['priceToBook']            # P/B ratio
info['pegRatio']               # PEG ratio

# Growth
info['revenueGrowth']          # Revenue growth (YoY)
info['earningsGrowth']         # Earnings growth (YoY)

# Profitability
info['grossMargins']           # Gross margin
info['operatingMargins']       # Operating margin
info['returnOnEquity']         # ROE

# Financial Health
info['debtToEquity']           # Debt/Equity ratio

# Ownership
info['heldPercentInsiders']    # Insider ownership %
info['heldPercentInstitutions'] # Institutional ownership %
info['shortPercentOfFloat']    # Short interest %

# Analyst Data
info['targetMeanPrice']        # Average analyst target
info['recommendationMean']     # Analyst rating (1-5)
info['numberOfAnalystOpinions'] # Number of analysts

# Technical
info['fiftyTwoWeekHigh']       # 52-week high
info['fiftyTwoWeekLow']        # 52-week low
info['beta']                   # Beta
```

---

## Expected Output

### Console Output Example:
```
============================================================
🚀 MULTI-BAGGER STOCK FINDER v2.0
============================================================

📡 STEP 1: BUILDING STOCK UNIVERSE
   ✓ S&P 500: 503 tickers
   ✓ NASDAQ: 2,847 tickers
   ✓ Total Universe: 3,215 unique tickers

🔍 STEP 2: SCREENING STOCKS
   Criteria: Price $5-$40, Market Cap $100M-$15B, US only
   Progress: 1000/3215 (47 passed)
   Progress: 2000/3215 (89 passed)
   Progress: 3215/3215 (142 passed)
   ✅ Screening complete: 142 stocks passed

📊 STEP 3: SCORING CANDIDATES
   Scoring 142 stocks...
   ✅ Scoring complete

🏆 TOP 15 MULTI-BAGGER CANDIDATES
============================================================

1. LUNR - Intuitive Machines Inc
   💰 $18.50 | Market Cap: $2.7B
   ⭐ Score: 78/100 (G:18 V:14 Q:12 M:8 S:7 Sec:15)
   🏭 Industrials - Aerospace & Defense

2. IONQ - IonQ Inc
   💰 $32.40 | Market Cap: $7.2B
   ⭐ Score: 74/100 (G:20 V:10 Q:8 M:7 S:6 Sec:15)
   🏭 Technology - Computer Hardware

... (continues for top 15)

============================================================
✅ COMPLETE! Files saved:
   - output/multibagger_results.csv
   - output/multibagger_report.md
============================================================
```

### CSV Output Columns:
```
ticker, company_name, sector, industry, current_price, market_cap_billions,
total_score, growth_score, value_score, quality_score, momentum_score, 
sentiment_score, sector_score, revenue_growth, earnings_growth, gross_margin,
operating_margin, pe_ratio, price_to_sales, price_to_book, peg_ratio,
return_on_equity, debt_to_equity, insider_ownership, institutional_ownership,
short_percent, analyst_target, recommendation, num_analysts, beta
```

---

## Important Notes

### Rate Limiting
- Add `time.sleep(0.25)` between API calls to avoid getting blocked
- yfinance is free but has rate limits

### Error Handling
- Many tickers will fail to fetch data - this is normal
- Skip failed tickers and continue
- Print progress every 100-200 stocks

### Caching (Optional but Recommended)
- Save the stock universe to a CSV so you don't have to re-fetch every run
- Cache is valid for 24 hours

### My Personal Interest
- I'm particularly interested in **space stocks like LUNR** (Intuitive Machines)
- LUNR is around $18-20 now and I believe it has massive potential
- Make sure space/aerospace stocks get proper sector scoring

---

## Success Criteria

The program is successful if it:

1. ✅ Automatically fetches 2,000+ US stocks (not a hand-picked list)
2. ✅ Filters down to ~100-200 candidates matching our criteria
3. ✅ Scores each stock on the 6-factor system
4. ✅ Ranks and outputs top candidates
5. ✅ Runs in under 30 minutes (with rate limiting)
6. ✅ Generates usable CSV and markdown reports

---

## How to Run

```bash
# Install dependencies
pip install yfinance pandas numpy requests tqdm

# Run the screener
python main.py

# Check outputs
cat output/multibagger_report.md
```

---

## File Structure to Create

```
main.py                      # <-- The main program (create this)
output/
  multibagger_results.csv    # <-- Generated by the program
  multibagger_report.md      # <-- Generated by the program
```

Just create `main.py` with all the logic. Keep it in ONE file for simplicity.

---

*Build the complete program now. Make sure it actually fetches real stock data from the internet and produces real results!*
