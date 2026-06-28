#!/usr/bin/env python3
"""Daily IDX + Japan + crypto OHLCV scraper.

Pulls daily bars from Yahoo Finance and appends/upserts one CSV per ticker
under ./data. Re-running is safe: rows are keyed by Date, so corrected or
late-arriving values overwrite the same day instead of duplicating.
"""
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

# --- EDIT THIS: tickers to track ---------------------------------------
# .JK = IDX (Indonesia), .T = Tokyo (Japan): trading days only.
# Crypto pairs trade 24/7, so they keep weekend/holiday squares green with
# real data instead of fake commits.
TICKERS = [
    # IDX (Indonesia)
    "BBCA.JK",  # Bank Central Asia
    "BBRI.JK",  # Bank Rakyat Indonesia
    "BMRI.JK",  # Bank Mandiri
    "TLKM.JK",  # Telkom Indonesia
    "ASII.JK",  # Astra International
    # Japan (Tokyo)
    "6356.T",   # Nippon Gear
    "7203.T",   # Toyota Motor
    "6758.T",   # Sony Group
    # Crypto (weekend coverage, real data)
    "BTC-USD",
    "ETH-USD",
]
# -----------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOOKBACK = "5d"       # pull last few days so gaps/corrections get filled
MAX_RETRIES = 3
WANTED_COLS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def fetch(ticker):
    """Download recent daily bars with simple retry/backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = yf.download(
                ticker,
                period=LOOKBACK,
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if df is not None and not df.empty:
                return df
        except Exception as e:  # noqa: BLE001 - log and retry anything
            print(f"  ! {ticker} attempt {attempt} failed: {e}")
        time.sleep(2 * attempt)
    return None


def upsert(ticker, df):
    """Merge new rows into the per-ticker CSV, keyed by Date."""
    # yfinance sometimes returns MultiIndex columns for a single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    cols = [c for c in WANTED_COLS if c in df.columns]
    df = df[cols].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "Date"

    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if os.path.exists(path):
        old = pd.read_csv(path, index_col="Date", parse_dates=True)
        combined = pd.concat([old, df])
        combined = combined[~combined.index.duplicated(keep="last")]
    else:
        combined = df
    combined = combined.sort_index()
    combined.to_csv(path)
    return len(combined)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    print(f"[{stamp}] scraping {len(TICKERS)} tickers")

    ok = 0
    for t in TICKERS:
        df = fetch(t)
        if df is None:
            print(f"  - {t}: no data")
            continue
        rows = upsert(t, df)
        print(f"  + {t}: {rows} rows total")
        ok += 1

    print(f"done: {ok}/{len(TICKERS)} ok")
    # Non-zero exit only if everything failed, so cron logs a real failure
    # but a partial success (e.g. one delisted ticker) still commits.
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
