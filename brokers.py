"""Live brokers. Paper trading is the default; nothing here runs without --live
plus LIVE_TRADING=I_UNDERSTAND in .env (dead-man switch)."""

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import requests


class LiveRefused(Exception):
    """Raised when a live order is blocked (no consent, no keys, over cap, too small)."""


def live_consent():
    return os.getenv("LIVE_TRADING", "") == "I_UNDERSTAND"


# ---------- Zerodha Kite (NSE) ----------

def nse_tradingsymbol(symbol):
    # "ITC.NS" -> ("NSE", "ITC")
    return "NSE", symbol.replace(".NS", "").upper()


class KiteBroker:
    """Delivery (CNC) market orders on NSE via Kite Connect."""

    def __init__(self):
        from kiteconnect import KiteConnect
        key = os.getenv("KITE_API_KEY", "")
        secret = os.getenv("KITE_API_SECRET", "")
        token = os.getenv("KITE_ACCESS_TOKEN", "")
        missing = [n for n, v in (("KITE_API_KEY", key), ("KITE_API_SECRET", secret),
                                  ("KITE_ACCESS_TOKEN", token)) if not v]
        if missing:
            raise LiveRefused(f"Kite keys missing in .env: {', '.join(missing)}. See README live section.")
        self.kite = KiteConnect(api_key=key)
        self.kite.set_access_token(token)

    def market_order(self, symbol, side, qty, price=None):
        exchange, tsym = nse_tradingsymbol(symbol)
        q = int(qty)  # NSE delivery needs whole shares
        if q < 1:
            raise LiveRefused(f"{symbol}: qty {qty:.3f} < 1 whole share, skipped.")
        try:
            oid = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR, exchange=exchange,
                tradingsymbol=tsym, transaction_type=side.upper(),
                quantity=q, order_type=self.kite.ORDER_TYPE_MARKET,
                product=self.kite.PRODUCT_CNC)
        except Exception as e:
            raise LiveRefused(f"Kite rejected {side} {symbol} x{q}: {str(e)[:150]}")
        # Kite returns only an order id; ledger records at signal price (approx).
        return {"order_id": oid, "qty": float(q), "price": None}


# ---------- Binance spot (crypto + memecoins) ----------

BINANCE_LIVE = "https://api.binance.com"
BINANCE_TEST = "https://testnet.binance.vision"


class BinanceBroker:
    """Spot market orders. BINANCE_TESTNET=1 routes to the free testnet."""

    def __init__(self):
        key = os.getenv("BINANCE_API_KEY", "")
        secret = os.getenv("BINANCE_API_SECRET", "")
        if not key or not secret:
            raise LiveRefused("BINANCE_API_KEY / BINANCE_API_SECRET missing in .env. See README live section.")
        self.key = key
        self.secret = secret.encode()
        self.base = BINANCE_TEST if os.getenv("BINANCE_TESTNET", "0") == "1" else BINANCE_LIVE
        self._lots = {}
        try:
            self._signed("GET", "/api/v3/account", {})
        except Exception as e:
            raise LiveRefused(f"Binance key check failed: {str(e)[:150]}")

    def _signed(self, method, path, params):
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        q = urlencode(params)
        sig = hmac.new(self.secret, q.encode(), hashlib.sha256).hexdigest()
        r = requests.request(method, self.base + path, params={**params, "signature": sig},
                             headers={"X-MBX-APIKEY": self.key}, timeout=15)
        r.raise_for_status()
        return r.json()

    def _filters(self, symbol):
        if symbol in self._lots:
            return self._lots[symbol]
        info = requests.get(self.base + "/api/v3/exchangeInfo",
                            params={"symbol": symbol}, timeout=15).json()
        fs = {x["filterType"]: x for x in info["symbols"][0]["filters"]}
        step = float(fs["LOT_SIZE"]["stepSize"])
        min_notional = 5.0
        if "NOTIONAL" in fs:
            min_notional = float(fs["NOTIONAL"].get("minNotional", 5.0))
        elif "MIN_NOTIONAL" in fs:
            min_notional = float(fs["MIN_NOTIONAL"].get("minNotional", 5.0))
        self._lots[symbol] = (step, min_notional)
        return self._lots[symbol]

    @staticmethod
    def _floor(qty, step):
        return (qty // step) * step

    def market_order(self, symbol, side, qty, price):
        step, min_notional = self._filters(symbol)
        q = self._floor(qty, step)
        if q * price < min_notional:
            raise LiveRefused(f"{symbol}: ~{q * price:.2f} USDT under min notional {min_notional}.")
        try:
            od = self._signed("POST", "/api/v3/order", {
                "symbol": symbol, "side": side.upper(), "type": "MARKET", "quantity": q})
        except Exception as e:
            raise LiveRefused(f"Binance rejected {side} {symbol}: {str(e)[:150]}")
        fills = od.get("fills", [])
        if fills:
            eq = sum(float(f["qty"]) for f in fills)
            ep = sum(float(f["qty"]) * float(f["price"]) for f in fills) / eq
            return {"order_id": od.get("orderId"), "qty": eq, "price": ep}
        return {"order_id": od.get("orderId"), "qty": float(od.get("executedQty", q)), "price": price}


def get_broker(market):
    if not live_consent():
        raise LiveRefused("Live mode needs LIVE_TRADING=I_UNDERSTAND in .env (dead-man switch).")
    if market == "nse":
        return KiteBroker()
    return BinanceBroker()  # crypto + meme both run on Binance spot
