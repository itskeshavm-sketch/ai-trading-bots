# Strategy spec, sizing, costs and limits

## Indicators

All computed on daily closes, oldest to newest, using only the Python standard
library.

| Indicator | Definition |
|---|---|
| RSI14 | Wilder-style RSI over the last 14 changes. `100 - 100 / (1 + avg_gain / avg_loss)`. If there is no loss in the window, RSI is 100 (or 50 if there is no gain either). |
| SMA20 | Mean of the last 20 closes. |
| SMA50 | Mean of the last 50 closes. |

Minimum bars: **22** for RSI14 + SMA20. Under that, the signal is `HOLD` with
the reason "not enough bars for RSI14". SMA50 needs 50 bars and is reported as
blank until then.

## Signal rules

| # | Condition | Signal | Meaning |
|---|---|---|---|
| 1 | `RSI14 <= rsi_buy` (default 35) **and** last bar closed up | BUY | Bounce off oversold |
| 2 | `RSI14 >= rsi_sell` (default 65) **and** last bar closed down | SELL | Fade from overbought |
| 3 | oversold but last bar closed down | HOLD | No confirmation yet |
| 4 | overbought but last bar closed up | HOLD | No confirmation yet |
| 5 | RSI14 between the thresholds | HOLD | Neutral band |

The last-bar direction check is what keeps rule 1 from firing into a falling
knife and rule 2 from firing while momentum is still building.

SMA20 and SMA50 are reported as **context only**. They never block a signal.
That is deliberate: a hard trend filter cut the trade count by roughly 90% in
testing and made the desk look broken on sideways markets.

## Position sizing

- Virtual starting cash: `500` by default (`--cash`).
- Per-order cap: `50%` of cash, or `--max-per-order` to override.
- Buy size is `min(cap, cash)`. The ledger never spends cash it does not have.
- Fractional quantities are allowed - this is a simulation, and blocking
  fractional units would make a 500-rupee desk unable to buy anything.
- Target defaults to `2 x starting cash`; override with `--target`.

## Cost model

The backtest charges `--fee-pct` percent **per side** (default 0.1%) on the
trade value. Real-world Indian brokerage is roughly 0.1-0.3% per side for
delivery, and there is no STT on ordinary delivery buys, but F&O, intraday and
crypto carry extra charges. If the user is testing an intraday or options
strategy, raise the assumption and say you did.

**A backtest with no cost assumption is a lie.** Always state the number used.

## Metrics reported

| Metric | Meaning |
|---|---|
| total return % | (end equity - start equity) / start equity |
| max drawdown % | largest peak-to-trough decline of the equity curve |
| trades | number of closed round trips |
| win rate % | closed trades with positive return / closed trades |
| equity curve | one point per bar, for charting |

Always present the return **next to** the drawdown. A 12% return with a 25%
max drawdown is a worse trade than a 4% return with a 2% drawdown for most
retail-sized accounts.

## Known limitations - state these, do not hide them

1. **Daily bars only.** Intraday logic is not modelled.
2. **No slippage beyond the flat fee.** Real fills on thin NSE mid-caps or
   memecoins are worse than the assumption.
3. **Single rule, single symbol.** No cross-symbol ranking, no sector filter,
   no regime detection.
4. **Survivorship and lookahead.** History is taken as given. Results do not
   account for delisted names or for data that would not have been available
   at the time.
5. **Overfitting is the default failure mode.** Changing the RSI thresholds
   until the backtest looks good produces a curve that will not repeat. If the
   user asks for an "optimal" threshold set, say that you are fitting noise and
   suggest out-of-sample testing instead.
6. **Past simulation is not a prediction.** No claim about future returns may be
   made from this output.

## What this skill deliberately does not do

- It does not connect to brokers, read API keys, or place orders.
- It does not fetch prices on its own in a way that requires credentials.
- It does not produce "signals to follow" as advice; it produces what the rule
  would have said on paper.
