class PaperPortfolio:
    def __init__(self, cash_start):
        self.cash = cash_start
        self.positions = {}  # symbol -> {qty, avg_price}
        self.trades = []

    def to_dict(self):
        return {"cash": self.cash, "positions": self.positions, "trades": self.trades}

    @classmethod
    def from_dict(cls, d):
        pf = cls(d.get("cash", 500.0))
        pf.positions = d.get("positions", {})
        pf.trades = d.get("trades", [])
        return pf

    def buy(self, symbol, price, rupees):
        rupees = min(rupees, self.cash)
        if rupees < 1 or price <= 0:
            return 0
        qty = rupees / price  # fractional allowed for Rs.500 sim
        self.cash -= qty * price
        p = self.positions.get(symbol, {"qty": 0, "avg_price": 0})
        total_qty = p["qty"] + qty
        p["avg_price"] = (p["qty"] * p["avg_price"] + qty * price) / total_qty
        p["qty"] = total_qty
        self.positions[symbol] = p
        self.trades.append(("BUY", symbol, qty, price))
        return qty

    def sell(self, symbol, price, qty=None):
        p = self.positions.get(symbol)
        if not p or p["qty"] <= 0:
            return 0
        qty = p["qty"] if qty is None else min(qty, p["qty"])
        self.cash += qty * price
        p["qty"] -= qty
        self.trades.append(("SELL", symbol, qty, price))
        if p["qty"] < 1e-9:
            del self.positions[symbol]
        return qty

    def value(self, prices):
        v = self.cash
        for s, p in self.positions.items():
            v += p["qty"] * prices.get(s, p["avg_price"])
        return v

    def summary(self, prices):
        lines = [f"Cash: Rs.{self.cash:.2f}"]
        for s, p in self.positions.items():
            cur = prices.get(s, p["avg_price"])
            pnl = (cur - p["avg_price"]) / p["avg_price"] * 100
            lines.append(f"{s}: {p['qty']:.3f} @ avg {p['avg_price']:.2f} now {cur:.2f} ({pnl:+.1f}%)")
        lines.append(f"Total: Rs.{self.value(prices):.2f}")
        return "\n".join(lines)
