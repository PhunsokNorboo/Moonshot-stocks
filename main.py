#!/usr/bin/env python3
"""
Multi-Bagger Stock Finder v2.0

Automatically fetches thousands of US stocks, filters them based on multi-bagger
criteria, scores them using a 6-factor system, and outputs top candidates.
"""

import os
import time
import warnings
from datetime import datetime
from io import StringIO

import numpy as np
import pandas as pd
import requests
import urllib3
import yfinance as yf
from tqdm import tqdm

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Filter criteria
MIN_PRICE = 5
MAX_PRICE = 40
MIN_MARKET_CAP = 100_000_000      # $100M
MAX_MARKET_CAP = 15_000_000_000   # $15B
MIN_VOLUME = 200_000

# Rate limiting
API_DELAY = 0.25  # seconds between API calls

# Priority sectors for bonus scoring
PRIORITY_SECTORS = [
    'Technology',
    'Healthcare',
    'Industrials',
    'Communication Services',
    'Energy',
]

# Priority industries for extra bonus scoring (keywords)
PRIORITY_INDUSTRIES = [
    'aerospace', 'space', 'defense',
    'artificial intelligence', 'machine learning', 'ai ',
    'quantum', 'computing',
    'semiconductor', 'chip',
    'cybersecurity', 'security software',
    'biotechnology', 'genomics', 'biotech',
    'solar', 'wind', 'nuclear', 'clean energy', 'renewable',
    'fintech', 'financial technology', 'payments',
    'robotics', 'automation',
    'cloud', 'data center', 'infrastructure',
]

# Output directory
OUTPUT_DIR = 'output'


# =============================================================================
# STOCK UNIVERSE FETCHING
# =============================================================================

def fetch_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia."""
    print("   Fetching S&P 500 from Wikipedia...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()

        tables = pd.read_html(StringIO(response.text))
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
        return tickers
    except Exception as e:
        print(f"   ⚠️  Failed to fetch S&P 500: {e}")
        # The NASDAQ trader file already includes most S&P 500 stocks
        print("   (S&P 500 stocks are included in NASDAQ listings)")
        return []


def fetch_nasdaq_traded_tickers():
    """Fetch all NASDAQ-traded tickers from official source."""
    print("   Fetching NASDAQ/NYSE listings from nasdaqtrader.com...")
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()

        # Parse the pipe-delimited file
        df = pd.read_csv(StringIO(response.text), sep='|')

        # Filter for common stocks (not ETFs, warrants, etc.)
        # Column 'ETF' = 'N' means it's not an ETF
        # Column 'Test Issue' = 'N' means it's not a test
        if 'ETF' in df.columns:
            df = df[df['ETF'] == 'N']
        if 'Test Issue' in df.columns:
            df = df[df['Test Issue'] == 'N']

        # Get tickers from Symbol column
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].dropna().tolist()
        elif 'NASDAQ Symbol' in df.columns:
            tickers = df['NASDAQ Symbol'].dropna().tolist()
        else:
            tickers = df.iloc[:, 1].dropna().tolist()

        # Clean tickers - remove any with special characters (warrants, units, etc.)
        tickers = [t for t in tickers if isinstance(t, str) and t.isalpha() and len(t) <= 5]

        return tickers
    except Exception as e:
        print(f"   ⚠️  Failed to fetch NASDAQ listings: {e}")
        return []


def build_stock_universe():
    """Build the complete stock universe from multiple sources."""
    print("\n📡 STEP 1: BUILDING STOCK UNIVERSE")

    all_tickers = set()

    # Fetch from multiple sources
    sp500 = fetch_sp500_tickers()
    print(f"   ✓ S&P 500: {len(sp500)} tickers")
    all_tickers.update(sp500)

    nasdaq_traded = fetch_nasdaq_traded_tickers()
    print(f"   ✓ NASDAQ/NYSE: {len(nasdaq_traded)} tickers")
    all_tickers.update(nasdaq_traded)

    # Convert to sorted list
    universe = sorted(list(all_tickers))
    print(f"   ✓ Total Universe: {len(universe)} unique tickers")

    return universe


# =============================================================================
# STOCK DATA FETCHING AND FILTERING
# =============================================================================

def get_stock_info(ticker):
    """Fetch stock info from yfinance with error handling."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Basic validation - must have price and market cap
        if not info or 'currentPrice' not in info and 'regularMarketPrice' not in info:
            return None

        return info
    except Exception:
        return None


def passes_basic_filters(info):
    """Check if stock passes basic filter criteria."""
    try:
        # Get price
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price is None or not (MIN_PRICE <= price <= MAX_PRICE):
            return False

        # Get market cap
        market_cap = info.get('marketCap')
        if market_cap is None or not (MIN_MARKET_CAP <= market_cap <= MAX_MARKET_CAP):
            return False

        # Get volume
        volume = info.get('averageVolume') or info.get('averageDailyVolume10Day')
        if volume is None or volume < MIN_VOLUME:
            return False

        # Check country (US only)
        country = info.get('country', '')
        if country and country not in ['United States', 'USA', 'US']:
            return False

        # Check exchange
        exchange = info.get('exchange', '')
        valid_exchanges = ['NYQ', 'NMS', 'NGM', 'NCM', 'NYSE', 'NASDAQ', 'AMEX', 'ASE', 'PCX']
        if exchange and not any(ex in exchange.upper() for ex in valid_exchanges):
            return False

        return True
    except Exception:
        return False


def extract_stock_data(ticker, info):
    """Extract relevant data from stock info."""
    try:
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        market_cap = info.get('marketCap') or 0

        # 52-week data
        week_high = info.get('fiftyTwoWeekHigh') or price
        week_low = info.get('fiftyTwoWeekLow') or price

        # Calculate 52-week position (0-100%)
        if week_high > week_low:
            week_position = (price - week_low) / (week_high - week_low) * 100
        else:
            week_position = 50

        # Analyst upside
        target_price = info.get('targetMeanPrice')
        if target_price and price > 0:
            analyst_upside = (target_price - price) / price * 100
        else:
            analyst_upside = None

        return {
            'ticker': ticker,
            'company_name': info.get('shortName') or info.get('longName') or ticker,
            'sector': info.get('sector') or 'Unknown',
            'industry': info.get('industry') or 'Unknown',
            'current_price': price,
            'market_cap': market_cap,
            'market_cap_billions': market_cap / 1_000_000_000,
            'average_volume': info.get('averageVolume') or 0,

            # Growth metrics
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),

            # Value metrics
            'price_to_sales': info.get('priceToSalesTrailing12Months'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'analyst_upside': analyst_upside,
            'target_price': target_price,

            # Quality metrics
            'gross_margin': info.get('grossMargins'),
            'operating_margin': info.get('operatingMargins'),
            'return_on_equity': info.get('returnOnEquity'),
            'debt_to_equity': info.get('debtToEquity'),

            # Momentum metrics
            'week_52_high': week_high,
            'week_52_low': week_low,
            'week_52_position': week_position,
            'beta': info.get('beta'),
            'recommendation': info.get('recommendationMean'),

            # Sentiment metrics
            'insider_ownership': info.get('heldPercentInsiders'),
            'institutional_ownership': info.get('heldPercentInstitutions'),
            'short_percent': info.get('shortPercentOfFloat'),
            'num_analysts': info.get('numberOfAnalystOpinions'),
        }
    except Exception:
        return None


def screen_stocks(universe):
    """Screen all stocks in the universe and collect data."""
    print(f"\n🔍 STEP 2: SCREENING STOCKS")
    print(f"   Criteria: Price ${MIN_PRICE}-${MAX_PRICE}, Market Cap ${MIN_MARKET_CAP/1e6:.0f}M-${MAX_MARKET_CAP/1e9:.0f}B, US only")

    passed_stocks = []
    processed = 0

    pbar = tqdm(universe, desc="   Screening", unit="stock", ncols=80, leave=True)
    for ticker in pbar:
        processed += 1

        # Fetch stock info
        info = get_stock_info(ticker)
        if info is None:
            time.sleep(API_DELAY)
            continue

        # Apply filters
        if not passes_basic_filters(info):
            time.sleep(API_DELAY)
            continue

        # Extract data
        stock_data = extract_stock_data(ticker, info)
        if stock_data:
            passed_stocks.append(stock_data)

        time.sleep(API_DELAY)

        # Update progress bar suffix
        if processed % 100 == 0:
            pbar.set_postfix({'passed': len(passed_stocks)})

    print(f"   ✅ Screening complete: {len(passed_stocks)} stocks passed")
    return passed_stocks


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def safe_float(value):
    """Safely convert a value to float, returning None if not possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def score_growth(stock):
    """Score growth factors (0-25 points)."""
    score = 0

    # Revenue Growth (0-12 points)
    rev_growth = safe_float(stock.get('revenue_growth'))
    if rev_growth is not None:
        if rev_growth > 0.50:
            score += 12
        elif rev_growth > 0.30:
            score += 9
        elif rev_growth > 0.15:
            score += 6
        elif rev_growth > 0:
            score += 3

    # Earnings Growth (0-8 points)
    earn_growth = safe_float(stock.get('earnings_growth'))
    if earn_growth is not None:
        if earn_growth > 0.50:
            score += 8
        elif earn_growth > 0.25:
            score += 6
        elif earn_growth > 0.10:
            score += 3

    # Forward P/E < Trailing P/E (0-5 points)
    trailing_pe = safe_float(stock.get('trailing_pe'))
    forward_pe = safe_float(stock.get('forward_pe'))
    if trailing_pe and forward_pe and forward_pe < trailing_pe:
        score += 5

    return min(score, 25)


def score_value(stock):
    """Score value factors (0-20 points)."""
    score = 0

    # Price/Sales Ratio (0-5 points)
    ps = safe_float(stock.get('price_to_sales'))
    if ps is not None:
        if ps < 3:
            score += 5
        elif ps < 6:
            score += 4
        elif ps < 10:
            score += 2

    # PEG Ratio (0-5 points)
    peg = safe_float(stock.get('peg_ratio'))
    if peg is not None and peg > 0:
        if peg < 1:
            score += 5
        elif peg < 1.5:
            score += 4
        elif peg < 2:
            score += 2

    # Price/Book Ratio (0-5 points)
    pb = safe_float(stock.get('price_to_book'))
    if pb is not None and pb > 0:
        if pb < 2:
            score += 5
        elif pb < 4:
            score += 3
        elif pb < 7:
            score += 1

    # Analyst Upside (0-5 points)
    upside = safe_float(stock.get('analyst_upside'))
    if upside is not None:
        if upside > 50:
            score += 5
        elif upside > 30:
            score += 4
        elif upside > 15:
            score += 2

    return min(score, 20)


def score_quality(stock):
    """Score quality factors (0-20 points)."""
    score = 0

    # Gross Margin (0-5 points)
    gm = safe_float(stock.get('gross_margin'))
    if gm is not None:
        if gm > 0.70:
            score += 5
        elif gm > 0.50:
            score += 4
        elif gm > 0.35:
            score += 2

    # Operating Margin (0-5 points)
    om = safe_float(stock.get('operating_margin'))
    if om is not None:
        if om > 0.25:
            score += 5
        elif om > 0.15:
            score += 4
        elif om > 0.05:
            score += 2
        elif om > 0:
            score += 1

    # Return on Equity (0-5 points)
    roe = safe_float(stock.get('return_on_equity'))
    if roe is not None:
        if roe > 0.20:
            score += 5
        elif roe > 0.15:
            score += 4
        elif roe > 0.10:
            score += 2

    # Debt/Equity Ratio (0-5 points) - lower is better
    de = safe_float(stock.get('debt_to_equity'))
    if de is not None and de >= 0:
        if de < 30:  # yfinance returns as percentage (30 = 0.3)
            score += 5
        elif de < 70:
            score += 4
        elif de < 100:
            score += 2

    return min(score, 20)


def score_momentum(stock):
    """Score momentum factors (0-10 points)."""
    score = 0

    # 52-Week Position (0-4 points) - middle range preferred
    pos = safe_float(stock.get('week_52_position'))
    if pos is not None:
        if 30 <= pos <= 70:
            score += 4
        elif 20 <= pos <= 80:
            score += 2

    # Beta (0-4 points) - moderate volatility preferred
    beta = safe_float(stock.get('beta'))
    if beta is not None:
        if 1.0 <= beta <= 1.8:
            score += 4
        elif 0.8 <= beta <= 2.5:
            score += 2

    # Analyst Recommendation (0-2 points)
    rec = safe_float(stock.get('recommendation'))
    if rec is not None and rec <= 2.0:
        score += 2

    return min(score, 10)


def score_sentiment(stock):
    """Score sentiment factors (0-10 points)."""
    score = 0

    # Insider Ownership (0-3 points)
    insider = safe_float(stock.get('insider_ownership'))
    if insider is not None:
        if insider > 0.15:
            score += 3
        elif insider > 0.08:
            score += 2

    # Institutional Ownership (0-3 points) - sweet spot 30-65%
    inst = safe_float(stock.get('institutional_ownership'))
    if inst is not None:
        if 0.30 <= inst <= 0.65:
            score += 3
        elif 0.20 <= inst <= 0.80:
            score += 2

    # Short Interest (0-2 points) - lower is better
    short = safe_float(stock.get('short_percent'))
    if short is not None:
        if short < 0.05:
            score += 2
        elif short < 0.10:
            score += 1

    # Analyst Coverage (0-2 points) - moderate coverage preferred
    analysts = safe_float(stock.get('num_analysts'))
    if analysts is not None:
        if 3 <= analysts <= 15:
            score += 2

    return min(score, 10)


def score_sector(stock):
    """Score sector factors (0-15 points)."""
    score = 0

    sector = stock.get('sector', '').lower()
    industry = stock.get('industry', '').lower()

    # Priority Sector (0-8 points)
    is_priority_sector = any(s.lower() in sector for s in PRIORITY_SECTORS)
    if is_priority_sector:
        score += 8
    else:
        score += 3

    # Priority Industry (0-7 points)
    industry_match = False
    for keyword in PRIORITY_INDUSTRIES:
        if keyword in industry or keyword in sector:
            industry_match = True
            break

    if industry_match:
        score += 7
    elif any(kw in industry for kw in ['software', 'tech', 'medical', 'pharma', 'electric']):
        score += 4
    else:
        score += 1

    return min(score, 15)


def calculate_scores(stocks):
    """Calculate all scores for each stock."""
    print(f"\n📊 STEP 3: SCORING CANDIDATES")
    print(f"   Scoring {len(stocks)} stocks...")

    for stock in tqdm(stocks, desc="   Scoring", unit="stock", ncols=80, leave=True):
        stock['growth_score'] = score_growth(stock)
        stock['value_score'] = score_value(stock)
        stock['quality_score'] = score_quality(stock)
        stock['momentum_score'] = score_momentum(stock)
        stock['sentiment_score'] = score_sentiment(stock)
        stock['sector_score'] = score_sector(stock)

        stock['total_score'] = (
            stock['growth_score'] +
            stock['value_score'] +
            stock['quality_score'] +
            stock['momentum_score'] +
            stock['sentiment_score'] +
            stock['sector_score']
        )

    # Sort by total score descending
    stocks.sort(key=lambda x: x['total_score'], reverse=True)

    print(f"   ✅ Scoring complete")
    return stocks


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_top_stocks(stocks, n=15):
    """Print top N stocks to console."""
    print(f"\n🏆 TOP {n} MULTI-BAGGER CANDIDATES")
    print("=" * 60)

    for i, stock in enumerate(stocks[:n], 1):
        print(f"\n{i}. {stock['ticker']} - {stock['company_name']}")
        print(f"   💰 ${stock['current_price']:.2f} | Market Cap: ${stock['market_cap_billions']:.2f}B")
        print(f"   ⭐ Score: {stock['total_score']}/100 "
              f"(G:{stock['growth_score']} V:{stock['value_score']} "
              f"Q:{stock['quality_score']} M:{stock['momentum_score']} "
              f"S:{stock['sentiment_score']} Sec:{stock['sector_score']})")
        print(f"   🏭 {stock['sector']} - {stock['industry']}")


def save_csv(stocks, filepath):
    """Save all stocks to CSV file."""
    df = pd.DataFrame(stocks)

    # Reorder columns
    column_order = [
        'ticker', 'company_name', 'sector', 'industry', 'current_price',
        'market_cap_billions', 'total_score', 'growth_score', 'value_score',
        'quality_score', 'momentum_score', 'sentiment_score', 'sector_score',
        'revenue_growth', 'earnings_growth', 'gross_margin', 'operating_margin',
        'trailing_pe', 'forward_pe', 'price_to_sales', 'price_to_book', 'peg_ratio',
        'return_on_equity', 'debt_to_equity', 'insider_ownership',
        'institutional_ownership', 'short_percent', 'target_price',
        'recommendation', 'num_analysts', 'beta', 'average_volume'
    ]

    # Only include columns that exist
    columns = [c for c in column_order if c in df.columns]
    df = df[columns]

    df.to_csv(filepath, index=False)
    print(f"   - {filepath}")


def save_markdown_report(stocks, filepath):
    """Save markdown report with top candidates."""
    with open(filepath, 'w') as f:
        f.write("# 🚀 Multi-Bagger Stock Finder Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Stocks Analyzed:** {len(stocks)} candidates passed screening\n\n")
        f.write("---\n\n")

        f.write("## 📊 Scoring System\n\n")
        f.write("| Factor | Weight | Description |\n")
        f.write("|--------|--------|-------------|\n")
        f.write("| Growth | 25 pts | Revenue growth, earnings growth, forward P/E |\n")
        f.write("| Value | 20 pts | P/S, PEG, P/B ratios, analyst upside |\n")
        f.write("| Quality | 20 pts | Margins, ROE, debt levels |\n")
        f.write("| Momentum | 10 pts | 52-week position, beta, analyst rating |\n")
        f.write("| Sentiment | 10 pts | Insider/institutional ownership, short interest |\n")
        f.write("| Sector | 15 pts | Priority sectors and industries |\n\n")

        f.write("---\n\n")
        f.write("## 🏆 Top 25 Multi-Bagger Candidates\n\n")

        for i, stock in enumerate(stocks[:25], 1):
            f.write(f"### {i}. {stock['ticker']} - {stock['company_name']}\n\n")
            f.write(f"**Price:** ${stock['current_price']:.2f} | ")
            f.write(f"**Market Cap:** ${stock['market_cap_billions']:.2f}B\n\n")
            f.write(f"**Total Score:** {stock['total_score']}/100\n\n")
            f.write("| Factor | Score |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Growth | {stock['growth_score']}/25 |\n")
            f.write(f"| Value | {stock['value_score']}/20 |\n")
            f.write(f"| Quality | {stock['quality_score']}/20 |\n")
            f.write(f"| Momentum | {stock['momentum_score']}/10 |\n")
            f.write(f"| Sentiment | {stock['sentiment_score']}/10 |\n")
            f.write(f"| Sector | {stock['sector_score']}/15 |\n\n")
            f.write(f"**Sector:** {stock['sector']} | **Industry:** {stock['industry']}\n\n")

            # Key metrics
            f.write("**Key Metrics:**\n")
            if stock.get('revenue_growth') is not None:
                f.write(f"- Revenue Growth: {stock['revenue_growth']*100:.1f}%\n")
            if stock.get('gross_margin') is not None:
                f.write(f"- Gross Margin: {stock['gross_margin']*100:.1f}%\n")
            if stock.get('analyst_upside') is not None:
                f.write(f"- Analyst Upside: {stock['analyst_upside']:.1f}%\n")
            f.write("\n---\n\n")

        f.write("## 📈 Sector Distribution\n\n")
        sector_counts = {}
        for stock in stocks:
            sector = stock.get('sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        f.write("| Sector | Count |\n")
        f.write("|--------|-------|\n")
        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"| {sector} | {count} |\n")

    print(f"   - {filepath}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 MULTI-BAGGER STOCK FINDER v2.0")
    print("=" * 60)

    start_time = time.time()

    # Step 1: Build stock universe
    universe = build_stock_universe()

    if len(universe) == 0:
        print("❌ Failed to fetch stock universe. Exiting.")
        return

    # Step 2: Screen stocks
    passed_stocks = screen_stocks(universe)

    if len(passed_stocks) == 0:
        print("❌ No stocks passed screening criteria. Exiting.")
        return

    # Step 3: Score stocks
    scored_stocks = calculate_scores(passed_stocks)

    # Step 4: Output results
    print_top_stocks(scored_stocks, n=15)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("✅ COMPLETE! Files saved:")

    # Save outputs
    csv_path = os.path.join(OUTPUT_DIR, 'multibagger_results.csv')
    md_path = os.path.join(OUTPUT_DIR, 'multibagger_report.md')

    save_csv(scored_stocks, csv_path)
    save_markdown_report(scored_stocks, md_path)

    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed/60:.1f} minutes")
    print("=" * 60)


if __name__ == "__main__":
    main()
