"""Indicators - zero dependencies, pure stdlib.

Works on any list of closes (oldest -> newest).
Used by screen.py, run_backtest.py and paper_portfolio.py.
"""


def sma(values, period):
    """Simple moving average of the last `period` values. None if not enough data."""
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def rsi(values, period=14):
    """Wilder-style RSI on the last `period` changes. None if not enough data."""
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for prev, cur in zip(values[-(period + 1):], values[-period:]):
        delta = cur - prev
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def snapshot(closes):
    """Latest indicator values for one symbol."""
    return {
        "price": closes[-1],
        "prev_price": closes[-2] if len(closes) > 1 else closes[-1],
        "change_pct": ((closes[-1] - closes[-2]) / closes[-2] * 100.0) if len(closes) > 1 else 0.0,
        "sma20": sma(closes, 20),
        "sma50": sma(closes, 50),
        "rsi14": rsi(closes, 14),
        "bars": len(closes),
    }


def signal(snap, rsi_buy=35.0, rsi_sell=65.0):
    """Deterministic momentum signal.

    Rules (in order):
      1. BUY  - RSI14 at or below rsi_buy (oversold) AND the last bar closed UP
                (bounce off oversold).
      2. SELL - RSI14 at or above rsi_sell (overbought) AND the last bar closed
                DOWN (fade from overbought).
      3. HOLD - everything else, including oversold-but-still-falling and
                overbought-but-still-rising (no confirmation yet).

    SMA20/SMA50 are reported as context (trend filter) but do not block a
    signal on their own, so the strategy stays active in choppy markets.
    """
    price = snap["price"]
    prev = snap["prev_price"]
    sma20 = snap["sma20"]
    rsi14 = snap["rsi14"]
    if rsi14 is None:
        return {"action": "HOLD", "reason": "not enough bars for RSI14", "sma20": sma20, "rsi14": rsi14}

    up_bar = price > prev
    down_bar = price < prev
    oversold = rsi14 <= rsi_buy
    overbought = rsi14 >= rsi_sell
    trend = "uptrend" if (sma20 is not None and price > sma20) else (
        "downtrend" if sma20 is not None else "no trend data")

    if oversold and up_bar:
        action = "BUY"
        reason = f"RSI14 {rsi14:.1f} oversold and price bounced up {prev:.2f} -> {price:.2f} ({trend})"
    elif overbought and down_bar:
        action = "SELL"
        reason = f"RSI14 {rsi14:.1f} overbought and price fell {prev:.2f} -> {price:.2f} ({trend})"
    elif oversold:
        action = "HOLD"
        reason = f"RSI14 {rsi14:.1f} oversold but still falling - waiting for confirmation ({trend})"
    elif overbought:
        action = "HOLD"
        reason = f"RSI14 {rsi14:.1f} overbought but still rising - waiting for confirmation ({trend})"
    else:
        action = "HOLD"
        reason = f"RSI14 {rsi14:.1f} in neutral band, no momentum edge ({trend})"

    return {"action": action, "reason": reason, "sma20": sma20, "rsi14": rsi14}
