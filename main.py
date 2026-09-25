import argparse, os, json, time
from dotenv import load_dotenv
load_dotenv()
import config
from data import fetch as fetch_nse, latest_snapshot
from crypto import fetch as fetch_crypto, fetch_rs as fetch_meme
from paper import PaperPortfolio
from brain import get_client, ai_decide, rule_decide

def mkt_cfg(market):
    if market == "crypto":
        return {
            "symbols": config.CRYPTO_SYMBOLS,
            "state": config.CRYPTO_STATE_FILE,
            "gate": "last_prices_crypto.json",
            "cash": config.CRYPTO_CASH_START,
            "target": config.CRYPTO_TARGET,
            "ccy": "USDT",
            "loop_interval": "1m",
            "fetcher": "crypto",
        }
    if market == "meme":
        return {
            "symbols": config.MEME_SYMBOLS,
            "state": config.MEME_STATE_FILE,
            "gate": config.MEME_GATE_FILE,
            "cash": config.MEME_CASH_START,
            "target": config.MEME_TARGET,
            "ccy": "Rs.",
            "loop_interval": "1m",
            "fetcher": "meme",
        }
    return {
        "symbols": config.SYMBOLS,
        "state": config.STATE_FILE,
        "gate": "last_prices.json",
        "cash": config.CASH_START,
        "target": config.TARGET,
        "ccy": "Rs.",
        "loop_interval": config.LOOP_INTERVAL,
        "fetcher": "nse",
    }

def load_pf(mkt, reset=False):
    if reset or not os.path.exists(mkt["state"]):
        return PaperPortfolio(mkt["cash"])
    try:
        with open(mkt["state"]) as f:
            return PaperPortfolio.from_dict(json.load(f))
    except Exception:
        return PaperPortfolio(mkt["cash"])

def save_pf(mkt, pf):
    with open(mkt["state"], "w") as f:
        json.dump(pf.to_dict(), f, indent=2)

def load_gate(mkt, reset=False):
    if reset or not os.path.exists(mkt["gate"]):
        return {}, 0
    try:
        with open(mkt["gate"]) as fh:
            d = json.load(fh)
            return d.get("prices", {}), d.get("steps", 0)
    except Exception:
        return {}, 0

def save_gate(mkt, prices, steps):
    with open(mkt["gate"], "w") as fh:
        json.dump({"prices": prices, "steps": steps}, fh)

def one_step(mkt, market, pf, use_ai, interval, period, step_no):
    ccy = mkt["ccy"]
    snapshots, prices = [], {}
    try:
        print(f"\n===== STEP {step_no} [{market}] GOAL: {ccy}500 -> {ccy}1000 =====")
        print(f"[STEP 1/5] Fetching {mkt['symbols']} ({interval}/{period}) ...")
        for sym in mkt["symbols"]:
            try:
                print(f"  > downloading {sym} ...")
                if mkt["fetcher"] == "crypto":
                    df = fetch_crypto(sym, interval)
                elif mkt["fetcher"] == "meme":
                    df = fetch_meme(sym, interval)
                else:
                    df = fetch_nse(sym, period, interval)
                s = latest_snapshot(sym, df)
                snapshots.append(s)
                prices[sym] = s["price"]
                def fmt(p):
                    return f"{p:.6f}" if p < 1 else f"{p:.2f}"
                print(f"  < {sym}: {ccy}{fmt(s['price'])} {s['change_pct']:+.2f}% RSI={s['rsi14']:.1f} SMA20={fmt(s['sma20'])}" if s['rsi14'] and s['sma20'] else f"  < {sym}: {ccy}{fmt(s['price'])}")
            except Exception as e:
                print(f"{sym} failed (skipped): {str(e)[:150]}")
        if not snapshots:
            print("No data at all this step. Keeping portfolio, will retry next step.")
            return pf.value({})
    except Exception as e:
        print(f"Step failed safely: {str(e)[:200]}. Portfolio untouched.")
        return pf.value({})

    total = pf.value(prices)
    # AI sees goal + current state, but NOT the auto-stop rule
    pf_text = pf.summary(prices).replace("Rs.", ccy) + f"\nTotal {ccy}{total:.2f} / Goal {ccy}1000"
    print(f"[STEP 2/5] Portfolio:\n{pf_text}")

    # CHANGE-GATE: skip AI call if nothing moved
    last, n = load_gate(mkt)
    n += 1
    moved = []
    for s in snapshots:
        old = last.get(s["symbol"])
        if old:
            chg = abs(s["price"] - old) / old * 100
            if chg >= config.PRICE_MOVE_PCT:
                moved.append(f"{s['symbol']} {chg:.2f}%")
    save_gate(mkt, prices, n)
    if use_ai and not moved and n % config.FORCE_AI_EVERY != 0 and last:
        print(f"[GATE] No price moved >= {config.PRICE_MOVE_PCT}% (step {n}). AI skipped, no Zen spent.")
        print(f"--- TOTAL: {ccy}{total:.2f} (Cash {ccy}{pf.cash:.2f}) ---")
        pct = min(100, total / mkt["target"] * 100)
        print(f"goal [{'#' * int(pct // 5)}{'-' * (20 - int(pct // 5))}] {pct:.1f}%  trades={len(pf.trades)}")
        save_pf(mkt, pf)
        return total
    if moved:
        print(f"[GATE] Moved: {', '.join(moved)}. Waking AI.")
    else:
        print(f"[GATE] Forced review (every {config.FORCE_AI_EVERY} steps). Waking AI.")

    if use_ai:
        client = get_client()
        if not client:
            print("No OPENCODE_API_KEY in .env.")
            return None
        print(f"[STEP 3/5] Asking {config.ZEN_MODEL} (reasoning={config.ZEN_REASONING_EFFORT}) ...")
        out = ai_decide(client, snapshots, pf_text, verbose=True, market=market)
        print(f"[STEP 4/5] AI decisions: {out['decisions']}")
    else:
        out = rule_decide(snapshots, pf, prices)
        print("RULE:", out)

    print("[STEP 5/5] Executing trades ...")
    for d in out["decisions"]:
        sym, act = d["symbol"], d["action"].upper()
        price = prices.get(sym)
        if not price:
            continue
        if act == "BUY":
            cap = total * config.MAX_POSITION_PCT
            amt = float(d.get("amount", d.get("rupees", 100)))
            q = pf.buy(sym, price, min(amt, cap))
            if q: print(f"BUY {sym} {q:.3f} @ {price:.2f} - {d.get('reason','')}")
        elif act == "SELL":
            amt = float(d.get("amount", d.get("rupees", 0)))
            qty = amt / price if amt > 0 else None
            q = pf.sell(sym, price, qty)
            if q: print(f"SELL {sym} {q:.3f} @ {price:.2f} - {d.get('reason','')}")
        else:
            print(f"HOLD {sym} - {d.get('reason','')}")

    total = pf.value(prices)
    print(f"--- TOTAL: {ccy}{total:.2f} (Cash {ccy}{pf.cash:.2f}) ---")
    pct = min(100, total / mkt["target"] * 100)
    print(f"goal [{'#' * int(pct // 5)}{'-' * (20 - int(pct // 5))}] {pct:.1f}%  trades={len(pf.trades)}")
    save_pf(mkt, pf)
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true")
    ap.add_argument("--loop", action="store_true", help="keep trading until target or ruin")
    ap.add_argument("--max-steps", type=int, default=200)
    ap.add_argument("--sleep", type=int, default=60, help="seconds between steps in loop")
    ap.add_argument("--reset", action="store_true", help="reset paper account")
    ap.add_argument("--market", choices=["nse", "crypto", "meme"], default="nse")
    args = ap.parse_args()

    mkt = mkt_cfg(args.market)
    pf = load_pf(mkt, reset=args.reset)
    if args.reset:
        save_pf(mkt, pf)
        save_gate(mkt, {}, 0)

    if not args.loop:
        one_step(mkt, args.market, pf, args.ai, config.INTERVAL, config.PERIOD, 1)
        return

    for i in range(1, args.max_steps + 1):
        try:
            total = one_step(mkt, args.market, pf, args.ai, mkt["loop_interval"], config.LOOP_PERIOD, i)
        except KeyboardInterrupt:
            print("\nStopped by you (Ctrl+C). Portfolio saved.")
            break
        except Exception as e:
            print(f"\nLoop guard caught: {str(e)[:200]}. Sleeping and continuing.")
            time.sleep(args.sleep)
            continue
        if total is None:
            print("Empty step. Sleeping and continuing (never dies overnight).")
            time.sleep(args.sleep)
            continue
        if total >= mkt["target"]:
            print(f"\n*** TARGET HIT: {total:.2f} >= {mkt['target']:.0f}. Stopping. ***")
            break
        if total <= config.RUIN:
            print(f"\n*** RUINED: {total:.2f}. Stopping. ***")
            break
        if i < args.max_steps:
            print(f"Sleeping {args.sleep}s ... (Ctrl+C to stop)")
            try:
                time.sleep(args.sleep)
            except KeyboardInterrupt:
                print("\nStopped by you (Ctrl+C). Portfolio saved.")
                break

if __name__ == "__main__":
    main()
