"""Paper portfolio - zero dependencies.

Mirrors the ledger semantics of the original ai-trading-bots paper.py, but with
no broker, no API keys and no real-money path. Simulation only.

State file (JSON):
  {"cash_start": 500.0, "cash": 412.5, "target": 1000.0,
   "positions": {"ITC": {"qty": 4.5, "avg_price": 220.0}},
   "trades": [["BUY", "ITC", 4.5, 220.0], ...]}
"""

import argparse
import json
import os
import sys


class PaperPortfolio:
    def __init__(self, cash_start=500.0, target=None):
        self.cash_start = float(cash_start)
        self.target = float(target) if target else self.cash_start * 2
        self.cash = self.cash_start
        self.positions = {}
        self.trades = []

    # ---------- persistence ----------
    def to_dict(self):
        return {
            "cash_start": self.cash_start,
            "target": self.target,
            "cash": self.cash,
            "positions": self.positions,
            "trades": self.trades,
        }

    @classmethod
    def from_dict(cls, d):
        pf = cls(d.get("cash_start", 500.0), d.get("target"))
        pf.cash = d.get("cash", pf.cash_start)
        pf.positions = d.get("positions", {})
        pf.trades = d.get("trades", [])
        return pf

    def save(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    # ---------- trading (simulated) ----------
    def buy(self, symbol, price, amount, max_per_order=None):
        amount = float(amount)
        if max_per_order is not None:
            amount = min(amount, float(max_per_order))
        amount = min(amount, self.cash)
        if amount < 1 or price <= 0:
            return 0.0
        qty = amount / price
        self.cash -= qty * price
        pos = self.positions.get(symbol, {"qty": 0.0, "avg_price": 0.0})
        total = pos["qty"] + qty
        pos["avg_price"] = (pos["qty"] * pos["avg_price"] + qty * price) / total
        pos["qty"] = total
        self.positions[symbol] = pos
        self.trades.append(["BUY", symbol, round(qty, 8), round(price, 8)])
        return qty

    def sell(self, symbol, price, qty=None):
        pos = self.positions.get(symbol)
        if not pos or pos["qty"] <= 0:
            return 0.0
        qty = pos["qty"] if qty is None else min(float(qty), pos["qty"])
        self.cash += qty * price
        pos["qty"] -= qty
        self.trades.append(["SELL", symbol, round(qty, 8), round(price, 8)])
        if pos["qty"] < 1e-9:
            del self.positions[symbol]
        return qty

    # ---------- reporting ----------
    def value(self, prices):
        total = self.cash
        for symbol, pos in self.positions.items():
            total += pos["qty"] * prices.get(symbol, pos["avg_price"])
        return total

    def summary(self, prices=None):
        prices = prices or {}
        total = self.value(prices)
        start = self.cash_start
        pnl = total - start
        pnl_pct = (pnl / start * 100.0) if start else 0.0
        lines = [
            f"Starting cash : {start:.2f}",
            f"Cash now      : {self.cash:.2f}",
        ]
        for symbol, pos in sorted(self.positions.items()):
            cur = prices.get(symbol, pos["avg_price"])
            pos_pnl_pct = ((cur - pos["avg_price"]) / pos["avg_price"] * 100.0) if pos["avg_price"] else 0.0
            lines.append(
                f"  {symbol}: qty {pos['qty']:.6g} @ avg {pos['avg_price']:.2f} -> {cur:.2f} ({pos_pnl_pct:+.2f}%)"
            )
        lines.append(f"Total value   : {total:.2f} ({pnl:+.2f} / {pnl_pct:+.2f}%)")
        lines.append(f"Target        : {self.target:.2f} ({'reached' if total >= self.target else 'not reached'})")
        lines.append(f"Trades        : {len(self.trades)}")
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Paper portfolio ledger (simulation only).")
    ap.add_argument("--state", required=True, help="portfolio state JSON file")
    ap.add_argument("--cash", type=float, default=None, help="starting cash for a new portfolio")
    ap.add_argument("--target", type=float, default=None, help="profit target")
    ap.add_argument("--add", action="append", default=[],
                    help='trade to apply: "BUY ITC 220 100" or "SELL ITC 225"')
    ap.add_argument("--prices", default=None, help="prices .json/.csv for marking positions to market")
    ap.add_argument("--reset", action="store_true", help="wipe state and start fresh")
    args = ap.parse_args()

    if args.reset and os.path.exists(args.state):
        os.remove(args.state)

    pf = PaperPortfolio.load(args.state)
    if not os.path.exists(args.state):
        pf = PaperPortfolio(args.cash if args.cash else 500.0, args.target)

    for raw in args.add:
        parts = raw.split()
        if len(parts) < 3:
            print(f"Skipping malformed trade '{raw}' (expected: BUY SYMBOL PRICE [AMOUNT])", flush=True)
            continue
        side, symbol = parts[0].upper(), parts[1].upper()
        try:
            price = float(parts[2])
        except ValueError:
            print(f"Skipping malformed trade '{raw}' (bad price)", flush=True)
            continue
        if side == "BUY":
            amount = float(parts[3]) if len(parts) > 3 else min(pf.cash, 100.0)
            qty = pf.buy(symbol, price, amount)
            print(f"BUY  {symbol} {qty:.6g} @ {price:.2f} (Rs.{amount:.2f})")
        elif side == "SELL":
            qty = pf.sell(symbol, price)
            print(f"SELL {symbol} {qty:.6g} @ {price:.2f}")
        else:
            print(f"Skipping unknown side '{side}' in '{raw}'")

    pf.save(args.state)

    prices = {}
    if args.prices:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from screen import load_prices
        series = load_prices(args.prices)
        prices = {symbol: closes[-1] for symbol, closes in series.items()}

    print()
    print(pf.summary(prices))
    print(f"\nState written to {args.state}")
    print("Simulation only - no real orders were placed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
