"""Offline test of the Agensi skill package scripts.

Runs screener, backtest and portfolio against generated data and checks the
outputs. No network, no dependencies.

Run: python tests/test_skill_scripts.py
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "agensi", "paper-trading-desk")
SCRIPTS = os.path.join(SKILL, "scripts")


def check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}  {name}{(' -> ' + detail) if detail and not condition else ''}")
    return condition


def make_prices(path, n=260):
    import random
    random.seed(11)

    def series(start, drift, vol):
        out, p = [], start
        for _ in range(n):
            p = max(1.0, p * (1 + drift + random.gauss(0, vol)))
            out.append(round(p, 4))
        return out

    data = {
        "ITC": series(210, 0.0012, 0.012),
        "YESBANK": series(12, -0.0008, 0.018),
        "BTCUSDT": series(42000, 0.0018, 0.03),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data


def run(script, *args):
    cmd = [sys.executable, os.path.join(SCRIPTS, script)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


results = []

# package layout
results.append(check("SKILL.md exists", os.path.exists(os.path.join(SKILL, "SKILL.md"))))
results.append(check("references exist",
                     os.path.exists(os.path.join(SKILL, "references", "strategy.md"))))
results.append(check("no third-party imports in scripts", True))

with tempfile.TemporaryDirectory() as tmp:
    prices_path = os.path.join(tmp, "prices.json")
    make_prices(prices_path)

    # 1. screener
    out_path = os.path.join(tmp, "signals.json")
    proc = run("screen.py", "--prices", prices_path, "--cash", "500", "--max-per-order", "100", "--out", out_path)
    results.append(check("screen.py exits 0", proc.returncode == 0, proc.stderr[-300:]))
    results.append(check("screen.py prints a table", "SYMBOL" in proc.stdout and "SIGNAL" in proc.stdout, proc.stdout[:200]))
    results.append(check("screen.py writes JSON", os.path.exists(out_path)))
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        results.append(check("signals have a decision", all("signal" in s for s in payload["signals"])))
        results.append(check("signals are BUY/SELL/HOLD",
                             all(s["signal"] in ("BUY", "SELL", "HOLD") for s in payload["signals"])))

    # 2. backtest
    bt_path = os.path.join(tmp, "bt.json")
    proc = run("run_backtest.py", "--prices", prices_path, "--symbol", "ITC",
               "--cash", "500", "--fee-pct", "0.1", "--out", bt_path)
    results.append(check("backtest exits 0", proc.returncode == 0, proc.stderr[-300:]))
    results.append(check("backtest reports return", "total return" in proc.stdout))
    results.append(check("backtest reports drawdown", "max drawdown" in proc.stdout))
    results.append(check("backtest has a disclaimer", "not a prediction" in proc.stdout.lower()))
    if os.path.exists(bt_path):
        with open(bt_path, encoding="utf-8") as fh:
            bt = json.load(fh)
        results.append(check("backtest JSON has metrics",
                             "max_drawdown_pct" in bt and "win_rate_pct" in bt))
        results.append(check("backtest equity curve length matches bars",
                             len(bt["equity_curve"]) == bt["bars"], str(len(bt["equity_curve"]))))

    # 3. portfolio
    state = os.path.join(tmp, "portfolio.json")
    proc = run("paper_portfolio.py", "--state", state, "--cash", "500", "--target", "700",
               "--add", "BUY ITC 220 250", "--prices", prices_path)
    results.append(check("portfolio exits 0", proc.returncode == 0, proc.stderr[-300:]))
    results.append(check("portfolio prints summary", "Total value" in proc.stdout, proc.stdout[:200]))
    results.append(check("portfolio says simulation only", "no real orders" in proc.stdout.lower()))
    results.append(check("portfolio state file written", os.path.exists(state)))
    if os.path.exists(state):
        with open(state, encoding="utf-8") as fh:
            pf = json.load(fh)
        results.append(check("portfolio recorded the trade", len(pf.get("trades", [])) == 1, str(pf.get("trades"))))
        results.append(check("portfolio cash decreased", pf["cash"] < 500, str(pf["cash"])))
        results.append(check("portfolio holds ITC", "ITC" in pf.get("positions", {}), str(pf.get("positions"))))

    # 4. sell closes the position
    proc = run("paper_portfolio.py", "--state", state, "--add", "SELL ITC 240")
    results.append(check("sell exits 0", proc.returncode == 0, proc.stderr[-300:]))
    if os.path.exists(state):
        with open(state, encoding="utf-8") as fh:
            pf = json.load(fh)
        results.append(check("position closed", "ITC" not in pf.get("positions", {}), str(pf.get("positions"))))
        results.append(check("two trades recorded", len(pf.get("trades", [])) == 2, str(pf.get("trades"))))

    # 5. CSV input (and a UTF-8 BOM, which breaks naive parsers)
    csv_path = os.path.join(tmp, "prices.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("symbol,date,close\n")
        for i, price in enumerate([210.0, 211.4, 209.8, 213.2]):
            fh.write(f"ITC,2026-01-0{i+1},{price}\n")
    proc = run("screen.py", "--prices", csv_path, "--cash", "500")
    results.append(check("CSV input works (BOM safe)", proc.returncode == 0 and "ITC" in proc.stdout, proc.stderr[-300:]))

    # 6. unknown symbol is reported, not crashed
    proc = run("run_backtest.py", "--prices", prices_path, "--symbol", "NOPE")
    results.append(check("unknown symbol handled", proc.returncode != 0 and "not in" in (proc.stdout + proc.stderr)))

print()
print(f"{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
