"""Screen symbols and emit trade signals.

Input (JSON or CSV) with price history per symbol:

  JSON  {"ITC": [210.1, 211.4, ...]}                        # closes, oldest -> newest
  JSON  {"ITC": {"name": "ITC", "closes": [210.1, ...]}}     # richer form
  CSV   symbol,date,close  (one row per bar, any order)

Output: human-readable table on stdout, machine-readable JSON with --out.

Example:
  python screen.py --prices prices.json --cash 500 --max-per-order 100 --out signals.json
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import snapshot, signal  # noqa: E402
from paper_portfolio import PaperPortfolio  # noqa: E402


def load_prices(path):
    """Return {symbol: [closes]} from a .json or .csv file."""
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8-sig") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict) and "symbols" in raw:
            raw = raw["symbols"]
        out = {}
        for symbol, value in raw.items():
            if isinstance(value, dict):
                closes = value.get("closes") or value.get("close") or []
            else:
                closes = value
            closes = [float(c) for c in closes if c is not None]
            if closes:
                out[symbol] = closes
        return out

    rows = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            clean = {(k or "").strip().lower(): v for k, v in row.items()}
            symbol = (clean.get("symbol") or clean.get("ticker") or "").strip()
            close = clean.get("close") or clean.get("price") or clean.get("adj close")
            if not symbol or close in (None, ""):
                continue
            rows.setdefault(symbol, []).append(float(close))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Screen symbols and emit BUY/SELL/HOLD signals.")
    ap.add_argument("--prices", required=True, help="prices .json or .csv")
    ap.add_argument("--cash", type=float, default=500.0, help="virtual cash for sizing")
    ap.add_argument("--max-per-order", type=float, default=None, help="cap per order (default: 50%% of cash)")
    ap.add_argument("--rsi-buy", type=float, default=35.0)
    ap.add_argument("--rsi-sell", type=float, default=65.0)
    ap.add_argument("--portfolio", default=None, help="optional portfolio .json to read open positions from")
    ap.add_argument("--out", default=None, help="write signals as JSON here")
    args = ap.parse_args()

    prices = load_prices(args.prices)
    if not prices:
        print("No usable price series found.", file=sys.stderr)
        return 1

    pf = PaperPortfolio.load(args.portfolio) if args.portfolio else PaperPortfolio(args.cash)
    cap = args.max_per_order if args.max_per_order is not None else pf.cash * 0.5

    rows = []
    for symbol in sorted(prices):
        closes = prices[symbol]
        snap = snapshot(closes)
        sig = signal(snap, rsi_buy=args.rsi_buy, rsi_sell=args.rsi_sell)
        held = symbol in pf.positions
        size = 0.0
        if sig["action"] == "BUY" and not held:
            size = min(cap, pf.cash)
        elif sig["action"] == "SELL" and held:
            size = pf.positions[symbol]["qty"]
        rows.append({
            "symbol": symbol,
            "price": round(snap["price"], 4),
            "change_pct": round(snap["change_pct"], 2),
            "rsi14": None if snap["rsi14"] is None else round(snap["rsi14"], 1),
            "sma20": None if snap["sma20"] is None else round(snap["sma20"], 4),
            "sma50": None if snap["sma50"] is None else round(snap["sma50"], 4),
            "bars": snap["bars"],
            "signal": sig["action"],
            "reason": sig["reason"],
            "held": held,
            "suggested_size": round(size, 4),
            "suggested_amount": round(size * snap["price"], 2),
        })

    width = max(len(r["symbol"]) for r in rows) + 2
    print(f"{'SYMBOL':<{width}}{'PRICE':>10}{'CHG%':>8}{'RSI14':>7}{'SMA20':>10}{'SIGNAL':>8}  REASON")
    for r in rows:
        rsi_txt = "-" if r["rsi14"] is None else f"{r['rsi14']:.1f}"
        sma_txt = "-" if r["sma20"] is None else f"{r['sma20']:.2f}"
        print(f"{r['symbol']:<{width}}{r['price']:>10.2f}{r['change_pct']:>8.2f}{rsi_txt:>7}{sma_txt:>10}"
              f"{r['signal']:>8}  {r['reason']}")

    buys = [r for r in rows if r["signal"] == "BUY"]
    sells = [r for r in rows if r["signal"] == "SELL"]
    print(f"\n{len(buys)} BUY, {len(sells)} SELL, {len(rows) - len(buys) - len(sells)} HOLD  "
          f"(virtual cash {pf.cash:.2f}, per-order cap {cap:.2f})")

    if args.out:
        payload = {"generated_from": os.path.basename(args.prices), "cash": pf.cash,
                   "per_order_cap": cap, "signals": rows}
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

