import yfinance as yf
import pandas as pd
import time

_CACHE = {}  # symbol+interval -> (timestamp, df)
CACHE_TTL = 60  # seconds, avoids Yahoo ban even with --sleep 0
LOOP_CACHE_TTL = 15  # faster for 1m loop mode

def fetch(symbol, period="3mo", interval="1d"):
    key = f"{symbol}:{period}:{interval}"
    now = time.time()
    ttl = LOOP_CACHE_TTL if interval in ("1m", "5m") else CACHE_TTL
    if key in _CACHE and now - _CACHE[key][0] < ttl:
        return _CACHE[key][1]
    # batch-friendly: single symbol, 1 call per TTL max
    last_err = None
    for attempt_interval in ([interval] if interval == "1d" else [interval, "5m", "1d"]):
        for attempt in range(2):
            try:
                df = yf.download(symbol, period=period, interval=attempt_interval, progress=False, auto_adjust=True)
                if df is None or df.empty or len(df) < 2:
                    raise ValueError(f"no usable data for {symbol} ({period}/{attempt_interval})")
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna()
                if len(df) < 2:
                    raise ValueError(f"too few rows for {symbol}")
                # indicators
                df["SMA20"] = df["Close"].rolling(20).mean()
                df["SMA50"] = df["Close"].rolling(50).mean()
                delta = df["Close"].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = -delta.clip(upper=0).rolling(14).mean()
                df["RSI14"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
                _CACHE[key] = (now, df)
                return df
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
    # last resort: stale cache (even expired) so one bad symbol never kills a run
    if key in _CACHE:
        return _CACHE[key][1]
    raise ValueError(f"{symbol} failed after retries: {last_err}")

def add_indicators(df):
    """Shared by NSE + crypto fetchers."""
    df = df.dropna()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    df["RSI14"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
    return df

def latest_snapshot(symbol, df):
    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else row
    return {
        "symbol": symbol,
        "price": float(row["Close"]),
        "change_pct": float((row["Close"] - prev["Close"]) / prev["Close"] * 100),
        "sma20": float(row["SMA20"]) if pd.notna(row["SMA20"]) else None,
        "sma50": float(row["SMA50"]) if pd.notna(row["SMA50"]) else None,
        "rsi14": float(row["RSI14"]) if pd.notna(row["RSI14"]) else None,
        "volume": float(row["Volume"]),
    }
