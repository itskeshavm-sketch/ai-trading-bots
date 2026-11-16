"""Backtest one symbol with the same rules the screener uses.

  python run_backtest.py --prices prices.json --symbol ITC --cash 500 --fee-pct 0.1

Reports: total return, max drawdown, trade count, win rate, CAGR-free summary.
Pure stdlib. No network, no keys.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import signal, snapshot  # noqa: E402
from screen import load_prices  # noqa: E402


def backtest(closes, cash=500.0, fee_pct=0.1, rsi_buy=35.0, rsi_sell=65.0, max_per_order=None):
    cash = float(cash)
    cap = max_per_order if max_per_order is not None else cash * 0.5
    qty = 0.0
    entry = 0.0
    equity, trades, wins = [], [], 0
    start_equity = cash

    for i in range(len(closes)):
        window = closes[: i + 1]
        if len(window) < 22:
            equity.append(cash + qty * closes[i])
            continue
        snap = snapshot(window)
        sig = signal(snap, rsi_buy=rsi_buy, rsi_sell=rsi_sell)
        price = closes[i]
        fee = price * fee_pct / 100.0

        if sig["action"] == "BUY" and qty == 0 and cash >= cap:
            spend = min(cap, cash)
            qty = spend / (price + fee)
            entry = price
            cash -= spend
            trades.append({"side": "BUY", "price": price, "qty": qty})
        elif sig["action"] == "SELL" and qty > 0:
            cash += qty * (price - fee)
            pnl = (price - entry) / entry * 100.0
            if pnl > 0:
                wins += 1
            trades.append({"side": "SELL", "price": price, "qty": qty, "pnl_pct": round(pnl, 2)})
            qty = 0.0
            entry = 0.0
        equity.append(cash + qty * price)

    if qty > 0:
        last = closes[-1]
        cash += qty * last
        pnl = (last - entry) / entry * 100.0
        if pnl > 0:
            wins += 1
        trades.append({"side": "SELL", "price": last, "qty": qty, "pnl_pct": round(pnl, 2), "open_close": True})
        equity[-1] = cash
        qty = 0.0

    peak, max_dd = equity[0] if equity else start_equity, 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak - value) / peak * 100.0)

    total_return = ((cash - start_equity) / start_equity * 100.0) if start_equity else 0.0
    closed = [t for t in trades if t["side"] == "SELL"]
    return {
        "symbol": None,
        "bars": len(closes),
        "start_equity": round(start_equity, 2),
        "end_equity": round(cash, 2),
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "trades": len(closed),
        "win_rate_pct": round((wins / len(closed) * 100.0), 1) if closed else 0.0,
        "fee_pct_per_side": fee_pct,
        "trade_log": trades,
        "equity_curve": [round(v, 2) for v in equity],
    }


def main():
    ap = argparse.ArgumentParser(description="Backtest the paper-trading rules on one symbol.")
    ap.add_argument("--prices", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--cash", type=float, default=500.0)
    ap.add_argument("--fee-pct", type=float, default=0.1, help="cost per side, percent of trade value")
    ap.add_argument("--rsi-buy", type=float, default=35.0)
    ap.add_argument("--rsi-sell", type=float, default=65.0)
    ap.add_argument("--max-per-order", type=float, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    prices = load_prices(args.prices)
    if args.symbol not in prices:
        print(f"Symbol '{args.symbol}' not in {args.prices}. Available: {', '.join(sorted(prices))}", file=sys.stderr)
        return 1

    result = backtest(prices[args.symbol], cash=args.cash, fee_pct=args.fee_pct,
                      rsi_buy=args.rsi_buy, rsi_sell=args.rsi_sell, max_per_order=args.max_per_order)
    result["symbol"] = args.symbol

    print(f"=== Backtest: {args.symbol} ===")
    print(f"bars            : {result['bars']}")
    print(f"start equity    : {result['start_equity']:.2f}")
    print(f"end equity      : {result['end_equity']:.2f}")
    print(f"total return    : {result['total_return_pct']:+.2f}%")
    print(f"max drawdown    : {result['max_drawdown_pct']:.2f}%")
    print(f"trades          : {result['trades']} (win rate {result['win_rate_pct']:.1f}%)")
    print(f"cost per side   : {result['fee_pct_per_side']}% of trade value")
    print("\nDisclaimer: historical simulation, not a prediction. Paper only.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

