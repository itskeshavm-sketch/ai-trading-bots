# Worked example

A full session: screen a watchlist, backtest one name, keep a paper portfolio.

## 1. The request

> "I'm looking at ITC, YESBANK, IDEA and BTC. Which are oversold? And paper trade
> me 500 rupees into the best one."

## 2. Get the data

```bash
python -c "
import yfinance as yf, json
syms=['ITC','YESBANK','IDEA','BTC-USD']
out={}
for s in syms:
    df=yf.download(s,period='6mo',auto_adjust=True)['Close'].dropna()
    out[s]=df.tolist()
json.dump(out, open('prices.json','w'))
"
```

## 3. Screen

```bash
python scripts/screen.py --prices prices.json --cash 500 --max-per-order 250
```

```
SYMBOL        PRICE    CHG%   RSI14     SMA20  SIGNAL  REASON
BTC-USD    63751.75  -1.96   63.6  59644.32    HOLD  RSI14 63.6 in neutral band, no momentum edge (uptrend)
IDEA          14.27   3.57   58.7     13.82    HOLD  RSI14 58.7 in neutral band, no momentum edge (uptrend)
ITC          329.98   1.32   45.6    321.91    HOLD  RSI14 45.6 in neutral band, no momentum edge (uptrend)
YESBANK        7.79   0.14   38.6      7.74    HOLD  RSI14 38.6 in neutral band, no momentum edge (uptrend)

0 BUY, 0 SELL, 4 HOLD  (virtual cash 500.00, per-order cap 250.00)
```

Every symbol is neutral. The honest answer is "no entry right now", not a
forced pick. A screener that always has a buy is a screener that is lying.

## 4. Backtest before trusting it

```bash
python scripts/run_backtest.py --prices prices.json --symbol ITC --cash 500 --fee-pct 0.1
```

```
=== Backtest: ITC ===
bars            : 260
start equity    : 500.00
end equity      : 515.11
total return    : +3.02%
max drawdown    : 1.22%
trades          : 1 (win rate 100.0%)
cost per side   : 0.1% of trade value
```

Read it as: one trade, +3%, 1.2% drawdown. One trade proves nothing about the
edge. Say that.

## 5. A day when there is a signal

```
SYMBOL        PRICE    CHG%   RSI14     SMA20  SIGNAL  REASON
YESBANK        7.79   1.84   33.1      7.95    BUY  RSI14 33.1 oversold and price bounced up 7.65 -> 7.79 (downtrend)
```

The note says downtrend - oversold bounces in a downtrend often fail. Worth
saying out loud when the trend context contradicts the signal.

## 6. Paper portfolio

```bash
python scripts/paper_portfolio.py --state portfolio.json --cash 500 --target 700 \
  --add "BUY YESBANK 7.79 250" --prices prices.json
```

```
BUY  YESBANK 32.08 @ 7.79 (Rs.250.00)

Starting cash : 500.00
Cash now      : 250.00
  YESBANK: qty 32.08 @ avg 7.79 -> 7.79 (+0.00%)
Total value   : 500.00 (+0.00 / +0.00%)
Target        : 700.00 (not reached)
Trades        : 1
```

The state file is plain JSON. Mark it to market later by passing `--prices`
again, or read it directly to build a chart.

## 7. The report

Give the user:

1. The signal table.
2. The backtest numbers with the fee assumption named.
3. The drawdown.
4. One line saying this is a simulation of a rule, not advice, and that a single
   backtest does not establish an edge.

If nothing qualified, say that plainly and stop. Do not invent a setup to fill
the space.
