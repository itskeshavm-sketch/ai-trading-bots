# AI Trading Bots (live + paper)

An AI trader for **Zerodha (NSE stocks)** and **Binance (crypto + memecoins)** —
real orders when you arm it, paper trading by default. Bring **any**
OpenAI-compatible AI provider: OpenAI, OpenRouter, Groq, Together, DeepSeek,
Mistral, xAI, Cerebras, NVIDIA NIM, Ollama, LM Studio, OpenCode Zen, or your own
gateway. You pick the model.

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

## Install — one line

**PowerShell (no git needed):**
```powershell
irm https://raw.githubusercontent.com/itskeshavm-sketch/ai-trading-bots/main/install.ps1 | iex
```

**CMD:**
```
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
```

**Already cloned it?**
```
cd ai-trading-bots
setup.bat                      REM or: powershell -ExecutionPolicy Bypass -File setup.ps1
```

The installer creates a virtualenv, installs the dependencies, then asks which
AI provider you want. Nothing else to do.

## Pick your AI provider

The setup wizard asks three things and writes them to `.env`:

1. **Base URL** — the provider's OpenAI-compatible endpoint
2. **API key** — typed hidden, never printed
3. **Model** — it fetches that provider's model list and shows it; pick by
   number or type an id

```
Base URL [https://api.openai.com/v1]:
API key (hidden):
Fetching model list from https://api.openai.com/v1/models ...
OK - 87 model(s) available.
Filter by text (Enter = show all):
  [  1] gpt-4o
  [  2] gpt-4o-mini
  ...
Pick a model (number, or type the model id): 2
Testing gpt-4o-mini ...
  OK   model answered: 'pong'
```

Change it any time with `python setup_provider.py`. Check what is set with
`python setup_provider.py --check`.

Ready-made base URLs:

| Provider | Base URL |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Together | `https://api.together.xyz/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Mistral | `https://api.mistral.ai/v1` |
| xAI | `https://api.x.ai/v1` |
| Cerebras | `https://api.cerebras.ai/v1` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` |
| Ollama (local) | `http://localhost:11434/v1` |
| LM Studio (local) | `http://localhost:1234/v1` |
| OpenCode Zen | `https://opencode.ai/zen/v1` |

Providers that reject `reasoning` or `response_format` are handled
automatically — the bot retries with fewer optional fields and tells you what
it dropped.

## Broker keys (only for live — skip for paper)

`python setup_keys.py` covers every broker key with hidden typing and masked
display. Or paste them into `.env` by hand:
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
call .venv\Scripts\activate.bat
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

**Starting amount:** each bot defaults to 500 → 1000 (Rs. or USDT). Give it
more (or less) with `--cash` and `--target` — the AI goal, terminal header,
dashboard and live order caps all scale automatically:
```
python main.py --ai --loop --sleep 0 --max-steps 1000000 --market meme --cash 5000 --target 10000
```
The goal doesn't have to be 2× — any custom goal works, e.g. start 10000,
reach 15000:
```
python main.py --ai --loop --sleep 0 --max-steps 1000000 --market nse --cash 10000 --target 15000
```
Omit `--target` and it defaults to double your `--cash`.
Amounts apply on a fresh start and are saved in the state file, so restarts
keep them. To change amounts on a running account, add `--reset` (wipes it
back to the new starting cash — old trades are gone, so be sure).

## How it decides

Each step fetches live prices + RSI/SMA, the AI returns BUY/SELL/HOLD as JSON,
the loop executes. AI is only woken when a price moved ≥0.05% (else every
10th step), so flat markets cost nothing. Ctrl+C stops; state saves every step.

## Live rails (always on with `--live`)

- Per-order caps: Rs.500 (NSE/meme), 10 USDT (crypto) at default size, scaling
  to 50% of starting cash for bigger accounts — see `config.py`.
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

`main.py` loop (`--live` for real orders) · `brain.py` provider-agnostic AI client ·
`config.py` settings · `brokers.py` Kite + Binance routing · `kite_token.py` daily Zerodha token ·
`data.py` NSE feed · `crypto.py` Binance feed · `paper.py` ledger ·
`dashboard_server.py` + `dashboard1/2.html` · `test_live.py` (`python test_live.py`)

Setup helpers:
- `setup_provider.py` — **AI provider wizard**: base URL + key + model list (`--check`, `--list-models`)
- `setup.ps1` / `setup.bat` — venv + dependencies + provider wizard
- `install.ps1` — one-line installer (PowerShell)
- `setup_keys.py` — broker key setup (hidden typing, masked values)
- `envfile.py` — tiny `.env` reader/writer
