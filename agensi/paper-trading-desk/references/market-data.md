# Getting price data

The scripts never fetch data themselves. You supply closes; the scripts do the
rest. This keeps the skill dependency-free and works with whatever market data
the host agent already has access to.

## On Agensi

Agensi's MCP exposes stock, crypto and market data tools on Agensi's keys, so
the buyer does not need their own broker or data account. The user approves the
price per call.

Two shapes work with the scripts:

**Flat map**

```json
{ "ITC": [210.1, 211.4, 209.8], "YESBANK": [12.4, 12.9] }
```

**Rich map**

```json
{ "ITC": { "name": "ITC Ltd", "closes": [210.1, 211.4, 209.8] } }
```

Write the map to `prices.json`, then run `screen.py`.

## Locally (Claude Code, Cursor, Codex, any Python)

```bash
python -c "
import yfinance as yf, json
syms=['ITC','YESBANK','IDEA','TATAMOTORS']
out={}
for s in syms:
    df=yf.download(s,period='6mo',auto_adjust=True)['Close'].dropna()
    out[s]=df.tolist()
json.dump(out, open('prices.json','w'))
"
```

Crypto: `BTC-USD`, `ETH-USD`, `SOL-USD`. Indian indices: `^NSEI`, `^NSEBANK`.
Use the `.NS` suffix for NSE single stocks (`ITC.NS`) if the plain ticker
returns nothing.

## CSV input

`screen.py` and `run_backtest.py` also read CSV with a `symbol` and `close`
column. Extra columns are ignored.

```csv
symbol,date,close
ITC,2026-01-01,210.10
ITC,2026-01-02,211.40
ITC,2026-01-03,209.80
```

Rows are grouped per symbol in file order. If your export is newest-first,
reverse the series before use - the indicators assume oldest first.

## Minimum bars

- 22 bars: RSI14 + SMA20
- 50 bars: RSI14 + SMA20 + SMA50

Below 22 the screener reports `HOLD` with "not enough bars for RSI14". That is
a deliberate refusal to guess, not a bug.

## If data fails

Say the data is unavailable and which symbol failed. Never fabricate a price
series, never carry values forward from a previous symbol, and never substitute
a plausible-looking number. A wrong price silently produces a wrong signal,
which is worse than no signal.
