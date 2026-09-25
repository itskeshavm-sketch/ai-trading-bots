# AI Paper-Trading Bots (Rs.500 → Rs.1000 simulation)

Three tiny bots that **simulate** trading with Rs.500 paper money and let an AI
(OpenCode Zen) decide BUY / SELL / HOLD. Nothing here trades real money.

> **No API keys are included in this repo — not even fake ones.**
> `.env.example` is a blank template. You add your own key in 2 minutes
> (step 2 below). Your key and your bot state never leave your PC:
> `.gitignore` blocks `.env`, `portfolio*.json` and `last_prices*.json`.

| Bot | Market | Symbols | State file |
|-----|--------|---------|------------|
| NSE stocks | Yahoo Finance (free, 15-min delay) | ITC.NS, YESBANK.NS, IDEA.NS | `portfolio.json` |
| Crypto | Binance public feed (free, 24/7) | BTC, ETH, SOL (USDT) | `portfolio_crypto.json` |
| Memecoins | Binance public feed, priced in Rs. | DOGE, SHIB, PEPE | `portfolio_meme.json` |

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Add YOUR OpenCode Zen key (2 min, all in CMD)

1. Go to **https://opencode.ai/auth** → sign in → **Zen → API keys** → create a key.
2. In the OpenCode web console set a **monthly limit ($5 suggested)** so a
   `--sleep 0` loop can't burn money.
3. In CMD, inside the project folder, copy the template and open it:
   ```
   copy .env.example .env
   notepad .env
   ```
   Replace `sk-your-zen-key-here` with your key, save, close.
4. Back in CMD, check the key loads (prints `key: OK`):
   ```
   python -c "from dotenv import load_dotenv; load_dotenv(); from brain import get_client; print('key:', 'OK' if get_client() else 'MISSING')"
   ```
5. The bots use model `space-bunny-free` (works with $0 balance).
   `muse-spark` needs Zen credits. Reasoning effort is `max`
   (see `config.py` → `ZEN_REASONING_EFFORT`).
6. **No broker keys needed** — this repo is simulation only.
   Live trading would need Zerodha/Binance keys later (not implemented yet).

## 3. Run everything (one block — paste into CMD)

Change the `cd` line to wherever you downloaded this, then paste the whole block:

```
cd C:\Users\Dell\Downloads\stocks
start "nse bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market nse
start "crypto bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market crypto
start "meme bot" python main.py --ai --loop --sleep 0 --max-steps 1000000 --market meme
start "dashboard" python dashboard_server.py
timeout /t 4
start http://localhost:8000/dashboard2.html
```

Then also open http://localhost:8000/dashboard2.html in your browser if it
didn't open itself. Three bot windows trade live, the Board shows totals,
goal rings, allocation pies and P&L bars. Close any window to stop that piece.

Single bot / free test (no AI, no key spent):

```bash
python main.py --market meme --max-steps 1
python main.py --ai --loop --sleep 0 --max-steps 1000000 --market meme
```

The AI only calls Zen when a price moved ≥0.05% (or every 10th step), so
flat markets cost nothing. Ctrl+C stops; the portfolio file saves every step.

## 4. dashboards

- http://localhost:8000/dashboard2.html — **Board** (plain, default)
- http://localhost:8000/dashboard1.html — **Neon Trader** (dark)

`GET /api/status?market=meme` returns the same data as JSON for your own
front-ends. Run with `python dashboard_server.py`.

## 5. Safety notes

- `.env` (your key) and `portfolio*.json` / `last_prices*.json` (your live
  state) are in `.gitignore` and **never committed**. Only `.env.example`
  (placeholder) ships with the repo.
- Yahoo data is ~15 min delayed; NSE trades 9:15–15:30 IST; crypto is 24/7.
- Paper profits ≠ real profits. Micro-moves on Rs.500 are paise; real
  brokerage (~Rs.40–60/round-trip) would eat them.

## Files

`main.py` loop · `brain.py` Zen client · `data.py` NSE feed ·
`crypto.py` Binance feed · `paper.py` ledger · `config.py` settings ·
`dashboard_server.py` + `dashboard1/2.html` visual status
