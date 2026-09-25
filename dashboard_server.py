"""Local dashboard server (stdlib only, no keys needed).

Run:
    python dashboard_server.py            # then open http://localhost:8000/dashboard2.html
    python dashboard_server.py --port 8080

Pages:
    /dashboard2.html  - Board (plain, default)
    /dashboard1.html  - Neon Trader (dark)

API:
    /api/status?market=nse|crypto|meme  -> live portfolio JSON
"""
import argparse
import json
import os
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

MARKETS = {
    "nse": {
        "state": "portfolio.json", "gate": "last_prices.json",
        "cash_start": 500.0, "target": 1000.0, "ccy": "Rs.",
        "label": "NSE Stocks (ITC, YESBANK, IDEA)",
    },
    "crypto": {
        "state": "portfolio_crypto.json", "gate": "last_prices_crypto.json",
        "cash_start": 500.0, "target": 1000.0, "ccy": "USDT",
        "label": "Crypto (BTC, ETH, SOL)",
    },
    "meme": {
        "state": "portfolio_meme.json", "gate": "last_prices_meme.json",
        "cash_start": 500.0, "target": 1000.0, "ccy": "Rs.",
        "label": "Memecoins (DOGE, SHIB, PEPE)",
    },
}


def get_status(market):
    cfg = MARKETS.get(market, MARKETS["nse"])
    state, last = {"cash": cfg["cash_start"], "positions": {}, "trades": []}, {}
    if os.path.exists(cfg["state"]):
        try:
            with open(cfg["state"]) as f:
                state = json.load(f)
        except Exception:
            pass
    if os.path.exists(cfg["gate"]):
        try:
            with open(cfg["gate"]) as f:
                last = json.load(f).get("prices", {})
        except Exception:
            pass
    positions = []
    invested = 0.0
    for sym, p in state.get("positions", {}).items():
        px = last.get(sym, p.get("avg_price", 0)) or 0
        val = p.get("qty", 0) * px
        invested += val
        avg = p.get("avg_price", 0) or 0
        pnl = ((px - avg) / avg * 100) if avg else 0.0
        positions.append({
            "symbol": sym, "qty": p.get("qty", 0), "avg": avg,
            "last": px, "value": val, "pnl_pct": pnl,
        })
    cash = state.get("cash", cfg["cash_start"])
    total = cash + invested
    trades = state.get("trades", [])
    return {
        "market": market, "label": cfg["label"], "ccy": cfg["ccy"],
        "cash_start": cfg["cash_start"], "target": cfg["target"],
        "cash": cash, "invested": invested, "total": total,
        "goal_pct": (total / cfg["target"] * 100) if cfg["target"] else 0,
        "pnl_vs_start": total - cfg["cash_start"],
        "positions": positions,
        "trades_total": len(trades),
        "recent_trades": trades[-10:][::-1],
        "updated": datetime.now().strftime("%H:%M:%S"),
    }


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/status":
            market = parse_qs(u.query).get("market", ["nse"])[0]
            body = json.dumps(get_status(market)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/":
            self.path = "/dashboard2.html"
        return super().do_GET()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dashboard live at http://localhost:{args.port}/dashboard2.html")
    print("Press Ctrl+C to stop.")
    srv.serve_forever()
