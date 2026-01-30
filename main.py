#!/usr/bin/env python3
"""
Moonshot Stock Finder v2.0 - Enhanced Analysis Suite

Automatically fetches thousands of US stocks, filters them based on multi-bagger
criteria, scores them using a 7-factor system with technical indicators,
insider transactions, and earnings data.
"""

import os
import time
import warnings
from datetime import datetime, timedelta
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
warnings.filterwarnings('ignore', category=UserWarning)

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
        print("   (S&P 500 stocks are included in NASDAQ listings)")
        return []


def fetch_nasdaq_traded_tickers():
    """Fetch all NASDAQ-traded tickers from official source."""
    print("   Fetching NASDAQ/NYSE listings from nasdaqtrader.com...")
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text), sep='|')

        if 'ETF' in df.columns:
            df = df[df['ETF'] == 'N']
        if 'Test Issue' in df.columns:
            df = df[df['Test Issue'] == 'N']

        if 'Symbol' in df.columns:
            tickers = df['Symbol'].dropna().tolist()
        elif 'NASDAQ Symbol' in df.columns:
            tickers = df['NASDAQ Symbol'].dropna().tolist()
        else:
            tickers = df.iloc[:, 1].dropna().tolist()

        tickers = [t for t in tickers if isinstance(t, str) and t.isalpha() and len(t) <= 5]
        return tickers
    except Exception as e:
        print(f"   ⚠️  Failed to fetch NASDAQ listings: {e}")
        return []


def build_stock_universe():
    """Build the complete stock universe from multiple sources."""
    print("\n📡 STEP 1: BUILDING STOCK UNIVERSE")

    all_tickers = set()

    sp500 = fetch_sp500_tickers()
    print(f"   ✓ S&P 500: {len(sp500)} tickers")
    all_tickers.update(sp500)

    nasdaq_traded = fetch_nasdaq_traded_tickers()
    print(f"   ✓ NASDAQ/NYSE: {len(nasdaq_traded)} tickers")
    all_tickers.update(nasdaq_traded)

    universe = sorted(list(all_tickers))
    print(f"   ✓ Total Universe: {len(universe)} unique tickers")

    return universe


# =============================================================================
# TECHNICAL INDICATORS
# =============================================================================

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)."""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
    except Exception:
        return None


def calculate_macd(prices):
    """Calculate MACD and signal line."""
    try:
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        macd_current = macd_line.iloc[-1]
        signal_current = signal_line.iloc[-1]

        # Bullish if MACD > Signal
        if pd.isna(macd_current) or pd.isna(signal_current):
            return None, None

        return macd_current, 'Bullish' if macd_current > signal_current else 'Bearish'
    except Exception:
        return None, None


def calculate_sma(prices, period):
    """Calculate Simple Moving Average."""
    try:
        sma = prices.rolling(window=period).mean()
        return sma.iloc[-1] if not pd.isna(sma.iloc[-1]) else None
    except Exception:
        return None


def get_technical_indicators(ticker):
    """Get technical indicators for a stock."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")

        if hist.empty or len(hist) < 50:
            return {}

        close = hist['Close']
        volume = hist['Volume']

        # RSI
        rsi = calculate_rsi(close)

        # MACD
        macd_value, macd_signal = calculate_macd(close)

        # Moving Averages
        sma20 = calculate_sma(close, 20)
        sma50 = calculate_sma(close, 50)
        current_price = close.iloc[-1]

        # Price vs SMA
        above_sma20 = current_price > sma20 if sma20 else None
        above_sma50 = current_price > sma50 if sma50 else None

        # Volume trend (current vs average)
        avg_volume = volume.mean()
        recent_volume = volume.iloc[-5:].mean()  # Last 5 days
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        return {
            'rsi_14': rsi,
            'macd_value': macd_value,
            'macd_signal': macd_signal,
            'sma_20': sma20,
            'sma_50': sma50,
            'above_sma20': above_sma20,
            'above_sma50': above_sma50,
            'volume_ratio': volume_ratio,
        }
    except Exception:
        return {}


# =============================================================================
# INSIDER TRANSACTIONS
# =============================================================================

def get_insider_data(ticker):
    """Get insider transaction data."""
    try:
        stock = yf.Ticker(ticker)

        # Get insider transactions
        try:
            insiders = stock.insider_transactions
        except Exception:
            insiders = None

        if insiders is None or insiders.empty:
            return {
                'insider_buys': 0,
                'insider_sells': 0,
                'insider_net_value': 0,
                'insider_sentiment': 'Neutral'
            }

        # Filter to last 90 days
        ninety_days_ago = datetime.now() - timedelta(days=90)

        if 'Start Date' in insiders.columns:
            insiders['Start Date'] = pd.to_datetime(insiders['Start Date'], errors='coerce')
            recent = insiders[insiders['Start Date'] >= ninety_days_ago]
        else:
            recent = insiders.head(20)  # Just use recent transactions

        # Count buys and sells
        buys = 0
        sells = 0
        net_value = 0

        if 'Transaction' in recent.columns:
            for _, row in recent.iterrows():
                trans = str(row.get('Transaction', '')).lower()
                value = safe_float(row.get('Value', 0)) or 0

                if 'buy' in trans or 'purchase' in trans:
                    buys += 1
                    net_value += value
                elif 'sell' in trans or 'sale' in trans:
                    sells += 1
                    net_value -= value

        # Determine sentiment
        if buys > sells:
            sentiment = 'Bullish'
        elif sells > buys:
            sentiment = 'Bearish'
        else:
            sentiment = 'Neutral'

        return {
            'insider_buys': buys,
            'insider_sells': sells,
            'insider_net_value': net_value,
            'insider_sentiment': sentiment
        }
    except Exception:
        return {
            'insider_buys': 0,
            'insider_sells': 0,
            'insider_net_value': 0,
            'insider_sentiment': 'Neutral'
        }


# =============================================================================
# EARNINGS DATA
# =============================================================================

def get_earnings_data(ticker):
    """Get earnings dates and surprise history."""
    try:
        stock = yf.Ticker(ticker)

        result = {
            'next_earnings': None,
            'days_to_earnings': None,
            'last_surprise_pct': None,
            'earnings_beat_rate': None
        }

        # Get calendar for next earnings
        try:
            calendar = stock.calendar
            if calendar is not None:
                if isinstance(calendar, dict):
                    if 'Earnings Date' in calendar:
                        earnings_dates = calendar['Earnings Date']
                        if earnings_dates:
                            next_date = earnings_dates[0] if isinstance(earnings_dates, list) else earnings_dates
                            if hasattr(next_date, 'date'):
                                result['next_earnings'] = next_date.strftime('%Y-%m-%d')
                                days = (next_date.date() - datetime.now().date()).days
                                result['days_to_earnings'] = days if days >= 0 else None
        except Exception:
            pass

        # Get earnings history for surprise data
        try:
            earnings_hist = stock.earnings_history
            if earnings_hist is not None and not earnings_hist.empty:
                # Calculate surprise percentages
                surprises = []
                for _, row in earnings_hist.iterrows():
                    actual = safe_float(row.get('epsActual'))
                    estimate = safe_float(row.get('epsEstimate'))
                    if actual is not None and estimate is not None and estimate != 0:
                        surprise = ((actual - estimate) / abs(estimate)) * 100
                        surprises.append(surprise)

                if surprises:
                    result['last_surprise_pct'] = surprises[0]  # Most recent
                    beats = sum(1 for s in surprises if s > 0)
                    result['earnings_beat_rate'] = beats / len(surprises) if surprises else None
        except Exception:
            pass

        return result
    except Exception:
        return {
            'next_earnings': None,
            'days_to_earnings': None,
            'last_surprise_pct': None,
            'earnings_beat_rate': None
        }


# =============================================================================
# STOCK DATA FETCHING AND FILTERING
# =============================================================================

def get_stock_info(ticker):
    """Fetch stock info from yfinance with error handling."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or 'currentPrice' not in info and 'regularMarketPrice' not in info:
            return None

        return info
    except Exception:
        return None


def passes_basic_filters(info):
    """Check if stock passes basic filter criteria."""
    try:
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price is None or not (MIN_PRICE <= price <= MAX_PRICE):
            return False

        market_cap = info.get('marketCap')
        if market_cap is None or not (MIN_MARKET_CAP <= market_cap <= MAX_MARKET_CAP):
            return False

        volume = info.get('averageVolume') or info.get('averageDailyVolume10Day')
        if volume is None or volume < MIN_VOLUME:
            return False

        country = info.get('country', '')
        if country and country not in ['United States', 'USA', 'US']:
            return False

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

        week_high = info.get('fiftyTwoWeekHigh') or price
        week_low = info.get('fiftyTwoWeekLow') or price

        if week_high > week_low:
            week_position = (price - week_low) / (week_high - week_low) * 100
        else:
            week_position = 50

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

        info = get_stock_info(ticker)
        if info is None:
            time.sleep(API_DELAY)
            continue

        if not passes_basic_filters(info):
            time.sleep(API_DELAY)
            continue

        stock_data = extract_stock_data(ticker, info)
        if stock_data:
            passed_stocks.append(stock_data)

        time.sleep(API_DELAY)

        if processed % 100 == 0:
            pbar.set_postfix({'passed': len(passed_stocks)})

    print(f"   ✅ Screening complete: {len(passed_stocks)} stocks passed")
    return passed_stocks


def enrich_stock_data(stocks):
    """Add technical indicators, insider data, and earnings to stocks."""
    print(f"\n📈 STEP 3: ENRICHING WITH TECHNICAL DATA")
    print(f"   Fetching technicals, insiders, and earnings for {len(stocks)} stocks...")

    for stock in tqdm(stocks, desc="   Enriching", unit="stock", ncols=80, leave=True):
        ticker = stock['ticker']

        # Get technical indicators
        technicals = get_technical_indicators(ticker)
        stock.update(technicals)

        # Get insider data
        insider = get_insider_data(ticker)
        stock.update(insider)

        # Get earnings data
        earnings = get_earnings_data(ticker)
        stock.update(earnings)

        time.sleep(API_DELAY)

    print(f"   ✅ Enrichment complete")
    return stocks


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

    earn_growth = safe_float(stock.get('earnings_growth'))
    if earn_growth is not None:
        if earn_growth > 0.50:
            score += 8
        elif earn_growth > 0.25:
            score += 6
        elif earn_growth > 0.10:
            score += 3

    trailing_pe = safe_float(stock.get('trailing_pe'))
    forward_pe = safe_float(stock.get('forward_pe'))
    if trailing_pe and forward_pe and forward_pe < trailing_pe:
        score += 5

    return min(score, 25)


def score_value(stock):
    """Score value factors (0-20 points)."""
    score = 0

    ps = safe_float(stock.get('price_to_sales'))
    if ps is not None:
        if ps < 3:
            score += 5
        elif ps < 6:
            score += 4
        elif ps < 10:
            score += 2

    peg = safe_float(stock.get('peg_ratio'))
    if peg is not None and peg > 0:
        if peg < 1:
            score += 5
        elif peg < 1.5:
            score += 4
        elif peg < 2:
            score += 2

    pb = safe_float(stock.get('price_to_book'))
    if pb is not None and pb > 0:
        if pb < 2:
            score += 5
        elif pb < 4:
            score += 3
        elif pb < 7:
            score += 1

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

    gm = safe_float(stock.get('gross_margin'))
    if gm is not None:
        if gm > 0.70:
            score += 5
        elif gm > 0.50:
            score += 4
        elif gm > 0.35:
            score += 2

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

    roe = safe_float(stock.get('return_on_equity'))
    if roe is not None:
        if roe > 0.20:
            score += 5
        elif roe > 0.15:
            score += 4
        elif roe > 0.10:
            score += 2

    de = safe_float(stock.get('debt_to_equity'))
    if de is not None and de >= 0:
        if de < 30:
            score += 5
        elif de < 70:
            score += 4
        elif de < 100:
            score += 2

    return min(score, 20)


def score_momentum(stock):
    """Score momentum factors (0-10 points)."""
    score = 0

    pos = safe_float(stock.get('week_52_position'))
    if pos is not None:
        if 30 <= pos <= 70:
            score += 4
        elif 20 <= pos <= 80:
            score += 2

    beta = safe_float(stock.get('beta'))
    if beta is not None:
        if 1.0 <= beta <= 1.8:
            score += 4
        elif 0.8 <= beta <= 2.5:
            score += 2

    rec = safe_float(stock.get('recommendation'))
    if rec is not None and rec <= 2.0:
        score += 2

    return min(score, 10)


def score_sentiment(stock):
    """Score sentiment factors (0-10 points)."""
    score = 0

    insider = safe_float(stock.get('insider_ownership'))
    if insider is not None:
        if insider > 0.15:
            score += 3
        elif insider > 0.08:
            score += 2

    inst = safe_float(stock.get('institutional_ownership'))
    if inst is not None:
        if 0.30 <= inst <= 0.65:
            score += 3
        elif 0.20 <= inst <= 0.80:
            score += 2

    short = safe_float(stock.get('short_percent'))
    if short is not None:
        if short < 0.05:
            score += 2
        elif short < 0.10:
            score += 1

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

    is_priority_sector = any(s.lower() in sector for s in PRIORITY_SECTORS)
    if is_priority_sector:
        score += 8
    else:
        score += 3

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


def score_technicals(stock):
    """Score technical indicators (0-10 points)."""
    score = 0

    # RSI - oversold bounce zone is good (30-50)
    rsi = safe_float(stock.get('rsi_14'))
    if rsi is not None:
        if 30 <= rsi <= 50:
            score += 3  # Oversold bounce zone
        elif 50 <= rsi <= 70:
            score += 2  # Neutral-bullish
        elif rsi < 30:
            score += 1  # Very oversold (risky but potential)

    # MACD signal
    macd_signal = stock.get('macd_signal')
    if macd_signal == 'Bullish':
        score += 3

    # Price above 50-day SMA
    if stock.get('above_sma50'):
        score += 2

    # Volume surge
    volume_ratio = safe_float(stock.get('volume_ratio'))
    if volume_ratio is not None and volume_ratio > 1.5:
        score += 2

    return min(score, 10)


def score_insider_activity(stock):
    """Score insider transaction activity (0-5 points bonus)."""
    score = 0

    buys = stock.get('insider_buys', 0) or 0
    sells = stock.get('insider_sells', 0) or 0

    # Net insider buying
    if buys > sells:
        score += 3
    elif buys > 0 and buys == sells:
        score += 1

    # Strong buying signal
    net_value = safe_float(stock.get('insider_net_value')) or 0
    if net_value > 1_000_000:  # Over $1M net buying
        score += 2
    elif net_value > 100_000:  # Over $100K net buying
        score += 1

    return min(score, 5)


def calculate_scores(stocks):
    """Calculate all scores for each stock."""
    print(f"\n📊 STEP 4: SCORING CANDIDATES")
    print(f"   Scoring {len(stocks)} stocks on 7 factors + bonuses...")

    for stock in tqdm(stocks, desc="   Scoring", unit="stock", ncols=80, leave=True):
        stock['growth_score'] = score_growth(stock)
        stock['value_score'] = score_value(stock)
        stock['quality_score'] = score_quality(stock)
        stock['momentum_score'] = score_momentum(stock)
        stock['sentiment_score'] = score_sentiment(stock)
        stock['sector_score'] = score_sector(stock)
        stock['technical_score'] = score_technicals(stock)
        stock['insider_bonus'] = score_insider_activity(stock)

        stock['total_score'] = (
            stock['growth_score'] +
            stock['value_score'] +
            stock['quality_score'] +
            stock['momentum_score'] +
            stock['sentiment_score'] +
            stock['sector_score'] +
            stock['technical_score'] +
            stock['insider_bonus']
        )

    stocks.sort(key=lambda x: x['total_score'], reverse=True)

    print(f"   ✅ Scoring complete")
    return stocks


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_top_stocks(stocks, n=15):
    """Print top N stocks to console with enhanced data."""
    print(f"\n🏆 TOP {n} MULTI-BAGGER CANDIDATES")
    print("=" * 70)

    for i, stock in enumerate(stocks[:n], 1):
        print(f"\n{i}. {stock['ticker']} - {stock['company_name']}")
        print(f"   💰 ${stock['current_price']:.2f} | Market Cap: ${stock['market_cap_billions']:.2f}B")
        print(f"   ⭐ Score: {stock['total_score']}/115 "
              f"(G:{stock['growth_score']} V:{stock['value_score']} "
              f"Q:{stock['quality_score']} M:{stock['momentum_score']} "
              f"S:{stock['sentiment_score']} Sec:{stock['sector_score']} "
              f"Tech:{stock['technical_score']} Ins:{stock['insider_bonus']})")

        # Technical line
        rsi = stock.get('rsi_14')
        macd = stock.get('macd_signal', 'N/A')
        above_sma = '✓' if stock.get('above_sma50') else '✗'
        rsi_str = f"{rsi:.0f}" if rsi else "N/A"
        print(f"   📊 RSI: {rsi_str} | MACD: {macd} | Above 50-SMA: {above_sma}")

        # Insider line
        buys = stock.get('insider_buys', 0)
        sells = stock.get('insider_sells', 0)
        net_val = stock.get('insider_net_value', 0)
        if buys > 0 or sells > 0:
            net_str = f"+${net_val/1e6:.1f}M" if net_val > 0 else f"-${abs(net_val)/1e6:.1f}M"
            print(f"   👔 Insiders: {buys} buys, {sells} sells ({net_str})")

        # Earnings line
        next_earn = stock.get('next_earnings')
        days = stock.get('days_to_earnings')
        surprise = stock.get('last_surprise_pct')
        if next_earn:
            days_str = f"({days}d)" if days else ""
            surprise_str = f" | Last: {'Beat' if surprise and surprise > 0 else 'Miss'} {abs(surprise):.0f}%" if surprise else ""
            print(f"   📅 Earnings: {next_earn} {days_str}{surprise_str}")

        print(f"   🏭 {stock['sector']} - {stock['industry']}")


def save_csv(stocks, filepath):
    """Save all stocks to CSV file."""
    df = pd.DataFrame(stocks)

    column_order = [
        'ticker', 'company_name', 'sector', 'industry', 'current_price',
        'market_cap_billions', 'total_score', 'growth_score', 'value_score',
        'quality_score', 'momentum_score', 'sentiment_score', 'sector_score',
        'technical_score', 'insider_bonus',
        'rsi_14', 'macd_signal', 'above_sma50', 'volume_ratio',
        'insider_buys', 'insider_sells', 'insider_net_value', 'insider_sentiment',
        'next_earnings', 'days_to_earnings', 'last_surprise_pct', 'earnings_beat_rate',
        'revenue_growth', 'earnings_growth', 'gross_margin', 'operating_margin',
        'trailing_pe', 'forward_pe', 'price_to_sales', 'price_to_book', 'peg_ratio',
        'return_on_equity', 'debt_to_equity', 'insider_ownership',
        'institutional_ownership', 'short_percent', 'target_price',
        'recommendation', 'num_analysts', 'beta', 'average_volume'
    ]

    columns = [c for c in column_order if c in df.columns]
    df = df[columns]

    df.to_csv(filepath, index=False)
    print(f"   - {filepath}")


def save_markdown_report(stocks, filepath):
    """Save markdown report with top candidates."""
    with open(filepath, 'w') as f:
        f.write("# 🚀 Moonshot Stock Finder Report v2.0\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Stocks Analyzed:** {len(stocks)} candidates passed screening\n\n")
        f.write("---\n\n")

        f.write("## 📊 Scoring System (115 points max)\n\n")
        f.write("| Factor | Weight | Description |\n")
        f.write("|--------|--------|-------------|\n")
        f.write("| Growth | 25 pts | Revenue growth, earnings growth, forward P/E |\n")
        f.write("| Value | 20 pts | P/S, PEG, P/B ratios, analyst upside |\n")
        f.write("| Quality | 20 pts | Margins, ROE, debt levels |\n")
        f.write("| Momentum | 10 pts | 52-week position, beta, analyst rating |\n")
        f.write("| Sentiment | 10 pts | Insider/institutional ownership, short interest |\n")
        f.write("| Sector | 15 pts | Priority sectors and industries |\n")
        f.write("| **Technical** | **10 pts** | RSI, MACD, SMA, volume (NEW) |\n")
        f.write("| **Insider Bonus** | **5 pts** | Recent insider buying activity (NEW) |\n\n")

        f.write("---\n\n")
        f.write("## 🏆 Top 25 Multi-Bagger Candidates\n\n")

        for i, stock in enumerate(stocks[:25], 1):
            f.write(f"### {i}. {stock['ticker']} - {stock['company_name']}\n\n")
            f.write(f"**Price:** ${stock['current_price']:.2f} | ")
            f.write(f"**Market Cap:** ${stock['market_cap_billions']:.2f}B\n\n")
            f.write(f"**Total Score:** {stock['total_score']}/115\n\n")
            f.write("| Factor | Score |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Growth | {stock['growth_score']}/25 |\n")
            f.write(f"| Value | {stock['value_score']}/20 |\n")
            f.write(f"| Quality | {stock['quality_score']}/20 |\n")
            f.write(f"| Momentum | {stock['momentum_score']}/10 |\n")
            f.write(f"| Sentiment | {stock['sentiment_score']}/10 |\n")
            f.write(f"| Sector | {stock['sector_score']}/15 |\n")
            f.write(f"| Technical | {stock['technical_score']}/10 |\n")
            f.write(f"| Insider Bonus | {stock['insider_bonus']}/5 |\n\n")

            f.write(f"**Sector:** {stock['sector']} | **Industry:** {stock['industry']}\n\n")

            # Technical indicators
            rsi = stock.get('rsi_14')
            macd = stock.get('macd_signal', 'N/A')
            f.write("**Technical Indicators:**\n")
            f.write(f"- RSI(14): {rsi:.1f}\n" if rsi else "- RSI(14): N/A\n")
            f.write(f"- MACD: {macd}\n")
            f.write(f"- Above 50-SMA: {'Yes' if stock.get('above_sma50') else 'No'}\n")

            # Insider activity
            buys = stock.get('insider_buys', 0)
            sells = stock.get('insider_sells', 0)
            if buys > 0 or sells > 0:
                f.write(f"- Insider Buys: {buys}, Sells: {sells}\n")

            # Earnings
            if stock.get('next_earnings'):
                f.write(f"- Next Earnings: {stock['next_earnings']}\n")

            # Key metrics
            f.write("\n**Key Metrics:**\n")
            if stock.get('revenue_growth') is not None:
                f.write(f"- Revenue Growth: {stock['revenue_growth']*100:.1f}%\n")
            if stock.get('gross_margin') is not None:
                f.write(f"- Gross Margin: {stock['gross_margin']*100:.1f}%\n")
            if stock.get('analyst_upside') is not None:
                f.write(f"- Analyst Upside: {stock['analyst_upside']:.1f}%\n")
            f.write("\n---\n\n")

        # Special sections
        f.write("## 👔 Stocks with Insider Buying\n\n")
        insider_buys = [s for s in stocks if s.get('insider_buys', 0) > s.get('insider_sells', 0)]
        if insider_buys:
            f.write("| Ticker | Company | Buys | Sells | Net Value |\n")
            f.write("|--------|---------|------|-------|----------|\n")
            for s in insider_buys[:15]:
                net_val = s.get('insider_net_value', 0)
                net_str = f"${net_val/1e6:.1f}M" if net_val else "N/A"
                f.write(f"| {s['ticker']} | {s['company_name'][:30]} | {s.get('insider_buys', 0)} | {s.get('insider_sells', 0)} | {net_str} |\n")
        else:
            f.write("No significant insider buying detected.\n")
        f.write("\n")

        f.write("## 📅 Upcoming Earnings (Next 14 Days)\n\n")
        upcoming = [s for s in stocks if s.get('days_to_earnings') is not None and 0 <= s.get('days_to_earnings', 999) <= 14]
        if upcoming:
            f.write("| Ticker | Company | Earnings Date | Days | Last Surprise |\n")
            f.write("|--------|---------|---------------|------|---------------|\n")
            for s in sorted(upcoming, key=lambda x: x.get('days_to_earnings', 999))[:15]:
                surprise = s.get('last_surprise_pct')
                surprise_str = f"{surprise:+.1f}%" if surprise else "N/A"
                f.write(f"| {s['ticker']} | {s['company_name'][:30]} | {s.get('next_earnings')} | {s.get('days_to_earnings')} | {surprise_str} |\n")
        else:
            f.write("No stocks with earnings in the next 14 days.\n")
        f.write("\n")

        f.write("## 📉 Technically Oversold (RSI < 40)\n\n")
        oversold = [s for s in stocks if s.get('rsi_14') and s.get('rsi_14') < 40]
        if oversold:
            f.write("| Ticker | Company | RSI | MACD | Score |\n")
            f.write("|--------|---------|-----|------|-------|\n")
            for s in sorted(oversold, key=lambda x: x.get('rsi_14', 100))[:15]:
                f.write(f"| {s['ticker']} | {s['company_name'][:30]} | {s.get('rsi_14', 0):.1f} | {s.get('macd_signal', 'N/A')} | {s['total_score']} |\n")
        else:
            f.write("No technically oversold stocks found.\n")
        f.write("\n")

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
    print("=" * 70)
    print("🚀 MOONSHOT STOCK FINDER v2.0 - Enhanced Analysis Suite")
    print("=" * 70)

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

    # Step 3: Enrich with technical data
    enriched_stocks = enrich_stock_data(passed_stocks)

    # Step 4: Score stocks
    scored_stocks = calculate_scores(enriched_stocks)

    # Step 5: Output results
    print_top_stocks(scored_stocks, n=15)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print("✅ COMPLETE! Files saved:")

    csv_path = os.path.join(OUTPUT_DIR, 'multibagger_results.csv')
    md_path = os.path.join(OUTPUT_DIR, 'multibagger_report.md')

    save_csv(scored_stocks, csv_path)
    save_markdown_report(scored_stocks, md_path)

    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed/60:.1f} minutes")
    print("=" * 70)


if __name__ == "__main__":
    main()
