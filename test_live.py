"""Safety tests for live-trading rails. No network, no keys, no real orders.
Run: python test_live.py
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import brokers
from brokers import BinanceBroker, LiveRefused, live_consent, nse_tradingsymbol


class TestLiveRails(unittest.TestCase):
    def test_no_consent_refuses(self):
        env = {k: v for k, v in os.environ.items() if k != "LIVE_TRADING"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(live_consent())
            with self.assertRaises(LiveRefused):
                brokers.get_broker("meme")

    def test_consent_ok_but_no_binance_keys(self):
        with patch.dict(os.environ, {"LIVE_TRADING": "I_UNDERSTAND",
                                     "BINANCE_API_KEY": "", "BINANCE_API_SECRET": ""}):
            with self.assertRaises(LiveRefused):
                BinanceBroker()

    def test_nse_symbol_map(self):
        self.assertEqual(nse_tradingsymbol("ITC.NS"), ("NSE", "ITC"))
        self.assertEqual(nse_tradingsymbol("YESBANK.NS"), ("NSE", "YESBANK"))

    def test_kite_whole_shares(self):
        fake = MagicMock()
        fake.VARIETY_REGULAR = "regular"
        fake.ORDER_TYPE_MARKET = "MARKET"
        fake.PRODUCT_CNC = "CNC"
        fake.place_order.return_value = "order123"
        sys.modules["kiteconnect"] = MagicMock(KiteConnect=MagicMock(return_value=fake))
        try:
            with patch.dict(os.environ, {"KITE_API_KEY": "k", "KITE_API_SECRET": "s",
                                          "KITE_ACCESS_TOKEN": "t"}):
                b = brokers.KiteBroker()
                r = b.market_order("ITC.NS", "BUY", 2.7)
                self.assertEqual(r["qty"], 2.0)
                self.assertEqual(r["order_id"], "order123")
                with self.assertRaises(LiveRefused):  # < 1 share blocked
                    b.market_order("ITC.NS", "BUY", 0.5)
        finally:
            del sys.modules["kiteconnect"]

    def test_binance_sign_lots_testnet(self):
        with patch("brokers.requests.request") as rq, patch("brokers.requests.get") as g:
            rq.return_value.json.return_value = {}  # account check
            g.return_value.json.return_value = {"symbols": [{"filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                {"filterType": "NOTIONAL", "minNotional": "5.0"}]}]}
            with patch.dict(os.environ, {"BINANCE_API_KEY": "k", "BINANCE_API_SECRET": "s",
                                          "BINANCE_TESTNET": "1"}):
                b = BinanceBroker()
                self.assertIn("testnet", b.base)
                rq.return_value.json.return_value = {
                    "orderId": 1, "fills": [{"qty": "0.060", "price": "100.0"}]}
                r = b.market_order("ETHUSDT", "BUY", 0.0609, 100.0)
                self.assertAlmostEqual(r["qty"], 0.060)  # floored to lot step
                self.assertAlmostEqual(r["price"], 100.0)
                with self.assertRaises(LiveRefused):  # under $5 notional
                    b.market_order("ETHUSDT", "BUY", 0.001, 100.0)
                _, kw = rq.call_args
                self.assertIn("signature", kw["params"])
                self.assertEqual(kw["headers"]["X-MBX-APIKEY"], "k")


if __name__ == "__main__":
    unittest.main(verbosity=2)
