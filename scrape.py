#!/usr/bin/env python3
"""Daily IDX + Japan + US + crypto OHLCV scraper.

Pulls daily bars from Yahoo Finance and upserts one CSV per ticker under ./data,
plus a manifest.json the dashboard uses to auto-discover tickers. Re-running is
safe: rows are keyed by Date, so corrections overwrite the same day.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

# --- EDIT THIS: tickers to track ---------------------------------------
TICKERS = [
    # IDX (Indonesia)
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK",
    "^JKSE",    # Jakarta Composite Index
    # Japan (Tokyo)
    "6356.T", "7203.T", "6758.T", "9984.T", "8306.T", "9432.T",
    "^N225",    # Nikkei 225
    # US / Global indices
    "^GSPC",    # S&P 500
    "^IXIC",    # Nasdaq Composite
    "^DJI",     # Dow Jones Industrial Average
    # Crypto (weekend coverage, real data)
    "BTC-USD", "ETH-USD",
]
# -----------------------------------------------------------------------

SPECIAL_GROUP = {
    "^JKSE": "IDX (Indonesia)",
    "^N225": "Japan (Tokyo)",
    "^GSPC": "US / Global",
    "^IXIC": "US / Global",
    "^DJI": "US / Global",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOOKBACK = "5d"
MAX_RETRIES = 3
WANTED_COLS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def group_of(sym):
    if sym in SPECIAL_GROUP:
        return SPECIAL_GROUP[sym]
    if sym.endswith(".JK"):
        return "IDX (Indonesia)"
    if sym.endswith(".T"):
        return "Japan (Tokyo)"
    if sym.endswith("-USD"):
        return "Crypto"
    return "Other"


def csv_name(sym):
    """Pages-safe filename: drop the ^ index prefix (no leading underscore)."""
    return sym.replace("^", "") + ".csv"


def fetch(ticker, period=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = yf.download(
                ticker, period=period or LOOKBACK, interval="1d",
                auto_adjust=False, progress=False, threads=False,
            )
            if df is not None and not df.empty:
                return df
        except Exception as e:  # noqa: BLE001
            print(f"  ! {ticker} attempt {attempt} failed: {e}")
        time.sleep(2 * attempt)
    return None


def upsert(ticker, df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = [c for c in WANTED_COLS if c in df.columns]
    df = df[cols].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "Date"
    path = os.path.join(DATA_DIR, csv_name(ticker))
    if os.path.exists(path):
        old = pd.read_csv(path, index_col="Date", parse_dates=True)
        combined = pd.concat([old, df])
        combined = combined[~combined.index.duplicated(keep="last")]
    else:
        combined = df
    combined = combined.sort_index()
    combined.to_csv(path)
    return len(combined)


def write_manifest(tickers):
    manifest = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tickers": [
            {"symbol": t, "group": group_of(t), "file": f"data/{csv_name(t)}"}
            for t in tickers
        ],
    }
    with open(os.path.join(DATA_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    print(f"[{stamp}] scraping {len(TICKERS)} tickers")
    ok, done = 0, []
    for t in TICKERS:
        df = fetch(t)
        if df is None:
            print(f"  - {t}: no data")
            continue
        rows = upsert(t, df)
        print(f"  + {t}: {rows} rows total")
        done.append(t)
        ok += 1
    write_manifest(done if done else TICKERS)
    print(f"done: {ok}/{len(TICKERS)} ok")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
