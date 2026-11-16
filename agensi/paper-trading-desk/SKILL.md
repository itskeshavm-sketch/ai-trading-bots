---
name: paper-trading-desk
description: Screen and backtest trading ideas without risking money. Use when the user asks to paper trade, backtest or simulate a strategy, scan stocks or crypto for RSI/SMA signals, check what a signal would have paid, build a virtual portfolio, track paper P&L, or asks "should I buy", "what would this have returned", "test my strategy on X", "which stocks are oversold", "simulate trading BTC/ETH/ITC/NIFTY". Works on NSE and Indian stocks plus crypto tickers. Simulation only - never places real orders.
---

# Paper Trading Desk

A deterministic paper-trading and backtesting desk for the agent. Prices go in, a
scored signal list and a simulated P&L come out. No broker, no API keys, no real
orders, no money at risk.

**Always simulation.** This skill never places, signs or routes a real order, and
it never asks for broker credentials. If the user wants live trading, say that
this skill is paper-only and point them at a broker's own API for that.

## When to use

- "Paper trade NIFTY / ITC / BTC" - run the screener, propose a virtual position
- "Backtest an RSI strategy on YESBANK" - run the backtest, report return and drawdown
- "Which of my watchlist stocks are oversold right now?" - screen and rank
- "I bought at 210, what would a 20/50 SMA cross have done?" - backtest the rule
- "Track my virtual portfolio" - read/write the paper portfolio JSON

## Workflow

### Step 1 - Get price history

You need recent closes per symbol, oldest first.

**On Agensi** use the built-in market data tools (stock, crypto and market data
tools are available on Agensi's keys - see `references/market-data.md` for exact
tool names and the expected output shape).

**Locally** (Claude Code, Cursor, Codex, anything with Python) you can pull data
yourself:

```bash
python -c "
import yfinance as yf, json
syms=['ITC','YESBANK','IDEA']
out={s: yf.download(s,period='6mo',auto_adjust=True)['Close'].dropna().tolist() for s in syms}
json.dump(out, open('prices.json','w'))
"
```

Crypto works the same way (`BTC-USD`, `ETH-USD`). If a market-data tool is
available, prefer it over `yfinance` - it is faster and needs no extra package.

### Step 2 - Screen for signals

```bash
python scripts/screen.py --prices prices.json --cash 500 --max-per-order 100
```

Prints one row per symbol: price, day change, RSI14, SMA20, the signal and a
plain-English reason. Add `--out signals.json` to keep the machine-readable copy.

Optional flags: `--rsi-buy` / `--rsi-sell` (default 35 / 65), `--portfolio` to
read open positions from a paper portfolio file.

### Step 3 - Backtest the rule

```bash
python scripts/run_backtest.py --prices prices.json --symbol ITC --cash 500 --fee-pct 0.1
```

Reports total return, max drawdown, trade count and win rate, with a cost
assumption of `--fee-pct` percent per side. Always quote the drawdown next to
the return - a strategy that made 12% while taking a 25% drawdown is not a
strategy anyone should act on.

### Step 4 - Keep a virtual portfolio

```bash
python scripts/paper_portfolio.py --state portfolio.json --add "BUY ITC 220 100"
python scripts/paper_portfolio.py --state portfolio.json --prices prices.json
```

Shows cash, open positions, unrealised P&L and progress toward a target. The
state file is plain JSON, so it can be read, edited and versioned.

### Step 5 - Report back

Give the user a short table (symbol, price, RSI, signal, suggested size), then
state plainly:

- what the rule says right now
- what the backtest says over the same window
- the costs assumed and the drawdown
- that this is a simulation and not advice

## Signal rules

| Condition | Signal |
|---|---|
| RSI14 <= 35 **and** last bar closed up | **BUY** - bounce off oversold |
| RSI14 >= 65 **and** last bar closed down | **SELL** - fade from overbought |
| everything else | **HOLD** |

SMA20 / SMA50 are reported as trend context but never block a signal. Full rule
spec, sizing rules and cost assumptions: `references/strategy.md`.

## Sizing rules (defaults)

- Virtual starting cash: 500 (any number, it is not real money)
- Per-order cap: 50% of cash, or `--max-per-order`
- Never suggest a position larger than the cap without saying so explicitly

## Hard rules

1. **Paper only.** Never place, sign or simulate routing a real order. Never
   ask for Zerodha / Binance / broker credentials or API keys.
2. **Never promise returns.** Report what the simulation produced, including
   drawdown and the loss-making periods. No "guaranteed", no "risk-free".
3. **State the assumptions.** Number of bars, fee assumption, that historical
   simulation is not a prediction.
4. **Flag thin data.** Fewer than 22 bars is not enough for RSI14 + SMA20 -
   say so instead of guessing.
5. **Do not invent prices.** If a market-data tool fails or returns nothing,
   say the data is unavailable. Never fabricate a price series.

## Optional: let an LLM propose the trades

The desk works fully without this - the deterministic rules above are the
default and never need a key. But if you want an AI to read the snapshots and
propose BUY/SELL/HOLD instead, point it at **any** OpenAI-compatible endpoint.

```bash
python scripts/setup_provider.py
```

It asks for the base URL, asks for the API key (hidden), fetches that
provider's model list, shows it, and writes the choice to `.env`:

```
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

Works with OpenAI, OpenRouter, Groq, Together, DeepSeek, Mistral, xAI,
Cerebras, NVIDIA NIM, Ollama, LM Studio, OpenCode Zen, or any gateway that
speaks `/v1/chat/completions`. Then:

```python
import sys; sys.path.insert(0, "scripts")
from ai_decide import ai_decide
decisions, meta = ai_decide(snapshots, portfolio_text, cash=500, target=1000)
# meta["source"] is "ai" or "rules"
```

If the provider is unreachable, the key is wrong, or the reply is not valid
JSON, `ai_decide` silently falls back to the deterministic rules and says so
in `meta["why"]`. It never places an order either way.

## Files

```
scripts/screen.py           # screener: symbols in, BUY/SELL/HOLD out
scripts/run_backtest.py     # backtest one symbol, equity curve + metrics
scripts/paper_portfolio.py  # virtual portfolio ledger (cash, positions, P&L)
scripts/indicators.py       # SMA / RSI / signal rules (pure stdlib)
scripts/setup_provider.py   # optional: pick any OpenAI-compatible provider
scripts/ai_decide.py        # optional: LLM proposals, falls back to the rules
scripts/envfile.py          # tiny .env reader/writer
references/strategy.md      # full rules, sizing, costs, limitations
references/market-data.md   # getting prices via MCP tools or yfinance
references/worked-example.md# a full worked session, start to finish
```

All scripts are pure Python 3 standard library. No pip install, no dependencies.
