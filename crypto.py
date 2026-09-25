"""Free crypto prices via Binance public API. No key needed."""
import time, requests
import pandas as pd
from data import add_indicators

BASE = "https://api.binance.com/api/v3/klines"
_CACHE = {}
TTL = 10  # seconds
_RATE_CACHE = {"rate": 90.0, "ts": 0}
RATE_TTL = 600  # refetch USDT->INR every 10 min

def get_usdtinr():
    """Live USDT->INR rate for Rs. accounting. Falls back to 90."""
    now = time.time()
    if now - _RATE_CACHE["ts"] < RATE_TTL:
        return _RATE_CACHE["rate"]
    for url in ("https://open.er-api.com/v6/latest/USD",
                "https://api.exchangerate.host/latest?base=USD&symbols=INR"):
        try:
            r = requests.get(url, timeout=10).json()
            rate = r.get("rates", {}).get("INR") or r.get("result", {}).get("INR")
            if rate:
                _RATE_CACHE.update(rate=float(rate), ts=now)
                return float(rate)
        except Exception:
            continue
    return _RATE_CACHE["rate"]

def fetch(symbol, interval="1m", limit=100):
    """symbol like BTCUSDT. Returns df with Close/Volume + indicators."""
    key = f"{symbol}:{interval}"
    now = time.time()
    if key in _CACHE and now - _CACHE[key][0] < TTL:
        return _CACHE[key][1]
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(BASE, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
            r.raise_for_status()
            raw = r.json()
            if not raw or len(raw) < 2:
                raise ValueError(f"no klines for {symbol}")
            df = pd.DataFrame(raw, columns=[
                "ot", "Open", "High", "Low", "Close", "Volume",
                "ct", "qa", "nt", "taker_b", "taker_q", "x"])[["Close", "Volume"]].astype(float)
            df = add_indicators(df)
            _CACHE[key] = (now, df)
            return df
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    if key in _CACHE:
        return _CACHE[key][1]
    raise ValueError(f"{symbol} failed: {last_err}")

def fetch_rs(symbol, interval="1m", limit=100):
    """Same as fetch() but prices converted to Rs. for Rs. accounting."""
    df = fetch(symbol, interval, limit).copy()
    rate = get_usdtinr()
    df["Close"] = df["Close"] * rate
    df["Volume"] = df["Volume"] / rate  # keep notionals comparable
    df = add_indicators(df[["Close", "Volume"]])  # recompute SMA/RSI in Rs.
    return df
