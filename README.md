# AI Trading Bots (live + paper)

AI (OpenCode Zen) trades for you — **real orders** on Zerodha (NSE stocks) and
Binance (crypto + memecoins) when you add your keys and pass `--live`.
**No keys set up? It just paper-trades** a virtual Rs.500 instead. Nothing
real happens unless you explicitly arm it.

> **No API keys are included here — not even fake ones.**
> `.env.example` is a blank template. Your keys and bot state never leave
> your PC (`.gitignore` blocks `.env`, `portfolio*.json`, `last_prices*.json`).

| Bot | Live venue | Symbols | Paper state |
|-----|-----------|---------|-------------|
| NSE stocks | Zerodha Kite (CNC delivery) | ITC, YESBANK, IDEA | `portfolio.json` |
| Crypto | Binance spot (BTC/ETH/SOL) | BTCUSDT, ETHUSDT, SOLUSDT | `portfolio_crypto.json` |
| Memecoins | Binance spot, tracked in Rs. | DOGE, SHIB, PEPE | `portfolio_meme.json` |

## Setup — everything in CMD, ~5 minutes

**1. Install:**
```
pip install -r requirements.txt
```

**2. AI key (required for both modes) — [opencode.ai/auth](https://opencode.ai/auth) → Zen → API keys, set a $5 monthly limit, then:**
```
copy .env.example .env
notepad .env
```
Replace `sk-your-zen-key-here`, save, close. Check it (prints `key: OK`):
```
python -c "from dotenv import load_dotenv; load_dotenv(); from brain import get_client; print('key:', 'OK' if get_client() else 'MISSING')"
```

**3. Broker keys (only for live — skip for paper):**
- *Binance (free):* API key with **spot trading only**, withdrawals off.
  Practice on the free testnet first: testnet keys + keep `BINANCE_TESTNET=1`.
- *Zerodha:* needs a paid Kite Connect app (~Rs.2000/month — skip unless you
  already have it). Paste key + secret in `.env`, then get a daily token:
  ```
  python kite_token.py
  ```
- *Arm it:* set `LIVE_TRADING=I_UNDERSTAND` in `.env`. Without this exact
  line, `--live` refuses to start. Remove it any time to disarm.

**4. Run — paste the whole block (change the `cd` line to your folder):**
```
cd C:\Users\Dell\Downloads\stocks
start "nse bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market nse
start "crypto bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market crypto
start "meme bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market meme
start "dashboard" python dashboard_server.py
timeout /t 4
start http://localhost:8000/dashboard2.html
```
This runs **paper** (safe default). For **live**, add `--live` and slow down,
e.g. `python main.py --ai --loop --sleep 60 --max-steps 1000000 --market meme --live`.
Then open http://localhost:8000/dashboard2.html — totals, goal rings,
allocation pies, P&L bars for every bot.

## How it decides

Each step fetches live prices + RSI/SMA, the AI returns BUY/SELL/HOLD as JSON,
the loop executes. AI is only woken when a price moved ≥0.05% (else every
10th step), so flat markets cost nothing. Ctrl+C stops; state saves every step.

## Live rails (always on with `--live`)

- Per-order caps: Rs.500 (NSE/meme), 10 USDT (crypto) — see `config.py`.
- NSE: whole shares only; Binance: lot-size + ~5 USDT min-notional enforced.
- Blocked orders print `LIVE SKIP` and never touch the ledger.
- Ledger mirrors real fills, so the dashboard works identically in both modes.
- Paper mode prints `[PAPER]`, live prints `[LIVE]` + order ids in the terminal.

## Honest warnings

- Real money can go to zero fast with Rs.500 AI scalping. Experimental
  software, not financial advice. Paper first, testnet second, tiny sizes third.
- Yahoo NSE data is ~15 min delayed; NSE trades 9:15–15:30 IST; crypto is 24/7.
- Paper profits ≠ real profits — real brokerage (~Rs.40–60/round-trip) eats
  micro-moves.

## Files

`main.py` loop (`--live` for real orders) · `brain.py` Zen client ·
`brokers.py` Kite + Binance routing · `kite_token.py` daily Zerodha token ·
`data.py` NSE feed · `crypto.py` Binance feed · `paper.py` ledger ·
`dashboard_server.py` + `dashboard1/2.html` · `test_live.py` (`python test_live.py`)
