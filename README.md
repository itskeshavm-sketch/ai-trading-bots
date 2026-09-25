# AI Paper-Trading Bots (Rs.500 → Rs.1000 simulation)

Three tiny bots that **simulate** trading with Rs.500 paper money and let an AI
(OpenCode Zen) decide BUY / SELL / HOLD. Paper mode is the default and costs
nothing. Section 6 adds optional **live** trading with real money.

> **No API keys are included in this repo — not even fake ones.**
> `.env.example` is a blank template. You add your own keys in minutes
> (steps 2 and 6 below). Your keys and your bot state never leave your PC:
> `.gitignore` blocks `.env`, `portfolio*.json` and `last_prices*.json`.

| Bot | Market | Symbols | Paper state |
|-----|--------|---------|-------------|
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
didn't open itself. Three bot windows trade paper money, the Board shows
totals, goal rings, allocation pies and P&L bars. Close any window to stop
that piece.

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

## 5. Safety notes (paper)

- `.env` (your keys) and `portfolio*.json` / `last_prices*.json` (your live
  state) are in `.gitignore` and **never committed**. Only `.env.example`
  (placeholder) ships with the repo.
- Yahoo data is ~15 min delayed; NSE trades 9:15–15:30 IST; crypto is 24/7.
- Paper profits ≠ real profits. Micro-moves on Rs.500 are paise; real
  brokerage (~Rs.40–60/round-trip) would eat them.

## 6. LIVE trading (real money — optional, off by default)

Without `--live` everything above is paper. With `--live`, the same AI
decisions execute as **real market orders**: NSE via **Zerodha Kite Connect**,
crypto + memecoins via **Binance spot**. The paper ledger mirrors real fills
so the dashboard keeps working.

**Costs and warnings first:**
- Zerodha Kite Connect API costs ~Rs.2000/month — more than this bot's whole
  account. Only use it if you already pay for it. (Free alternative Angel One
  SmartAPI is not implemented yet.)
- Binance spot API keys are free. Start on the free **testnet** before real money.
- Real money can go to zero fast with Rs.500-sized AI scalping. This is
  experimental software, not financial advice.

**6a. NSE live via Zerodha (only if you have Kite Connect):**

1. At developers.zerodha.com create an app → note API key + secret, set any
   redirect URL (e.g. `http://localhost:8000/`).
2. In CMD: `notepad .env`, fill `KITE_API_KEY=` and `KITE_API_SECRET=`.
3. Get a daily token (valid till ~7:30am next day, regenerate daily):
   ```
   python kite_token.py
   ```
   Open the printed URL, log in, paste the `request_token` back, then paste
   the printed access token into `.env` as `KITE_ACCESS_TOKEN=`.
4. Orders go as NSE delivery (CNC) market orders, whole shares only.

**6b. Crypto/meme live via Binance:**

1. On binance.com create an API key: enable **Spot trading only**,
   disable withdrawals, whitelist your IP if possible.
2. Practice first on the free testnet (testnet.binance.vision gives fake USDT):
   in `.env` set `BINANCE_API_KEY=`, `BINANCE_API_SECRET=` from the testnet
   site and keep `BINANCE_TESTNET=1`.
3. Only when testnet behaves, switch `.env` to real keys and set
   `BINANCE_TESTNET=0`. Binance rejects orders under ~5 USDT notional.

**6c. Arm it and run:**

1. In `.env` set `LIVE_TRADING=I_UNDERSTAND` (dead-man switch — without this
   exact line, `--live` refuses to start).
2. Run any bot with `--live` added, e.g.:
   ```
   python main.py --ai --loop --sleep 60 --max-steps 1000000 --market meme --live
   ```
   Use `--sleep 60` (not 0) for live — exchanges rate-limit and every order
   costs brokerage.
3. Rails that always apply: per-order caps (`LIVE_MAX_ORDER_RUPEES=500`,
   `LIVE_MAX_ORDER_USDT=10` in `config.py`), NSE whole-share flooring,
   Binance lot-size + min-notional checks, blocked orders print `LIVE SKIP`
   and never touch the ledger. Ctrl+C stops; remove the `LIVE_TRADING` line
   to disarm.

## Files

`main.py` loop · `brain.py` Zen client · `data.py` NSE feed ·
`crypto.py` Binance feed · `paper.py` ledger · `config.py` settings ·
`dashboard_server.py` + `dashboard1/2.html` visual status ·
`brokers.py` live routing (Kite + Binance) · `kite_token.py` daily token ·
`test_live.py` safety tests (`python test_live.py`)
