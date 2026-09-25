import os, json, time
from openai import OpenAI
import config

AI_RETRIES = 3

def get_client():
    key = os.getenv("OPENCODE_API_KEY", "")
    if not key or "your-zen" in key:
        return None
    return OpenAI(base_url=config.ZEN_BASE_URL, api_key=key)

PROMPT_NSE = """GOAL: Grow a real Rs.500 NSE trading account to Rs.1000 as fast as possible.
You are trading REAL money on the NSE. Every BUY/SELL you output executes as a live market order with real rupees. Losses are real and permanent. There is no reset, no practice mode.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","rupees":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional shares allowed. Keep reason <15 words.
"""

PROMPT_CRYPTO = """GOAL: Grow a real 500 USDT crypto trading account to 1000 USDT as fast as possible.
You are trading REAL money on Binance spot. Every BUY/SELL you output executes as a live market order with real USDT. Losses are real and permanent. There is no reset, no practice mode. Market runs 24/7, volatility is high.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","amount":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional amounts allowed. Amounts are in USDT. Keep reason <15 words.
"""

def get_prompt(market):
    if market == "crypto":
        return PROMPT_CRYPTO
    if market == "meme":
        return PROMPT_MEME
    return PROMPT_NSE

PROMPT_MEME = """GOAL: Grow a real Rs.500 memecoin trading account to Rs.1000 as fast as possible.
You are trading REAL money on crypto spot (DOGE, SHIB, PEPE). Every BUY/SELL you output executes as a live market order with real rupees. Losses are real and permanent. There is no reset, no practice mode. Market runs 24/7, memecoins are extremely volatile and can crash 30% in an hour.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots (prices in rupees) + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","amount":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional amounts allowed. Amounts are in rupees. Keep reason <15 words.
"""

PROMPT = PROMPT_NSE  # default

def ai_decide(client, snapshots, portfolio_text, verbose=True, market="nse"):
    # space-bunny-free works via Zen API with $0 balance.
    # Reasoning = your Max dropdown -> extra_body={"reasoning":{"effort":"max"}}
    # Needs large max_tokens because thinking consumes tokens.
    prompt = get_prompt(market)
    print(f"[STEP 3/5] Sending to {config.ZEN_MODEL} reasoning={config.ZEN_REASONING_EFFORT} ...")
    last_err = None
    for attempt in range(AI_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=config.ZEN_MODEL,
                messages=[{"role": "user", "content": prompt + f"\nSnapshots:\n{json.dumps(snapshots, indent=2)}\nPortfolio:\n{portfolio_text}"}],
                max_tokens=16000,
                extra_body={"reasoning": {"effort": config.ZEN_REASONING_EFFORT}},
            )
            break
        except Exception as e:
            last_err = e
            print(f"  ! Zen call failed (try {attempt+1}/{AI_RETRIES}): {str(e)[:150]}")
            time.sleep(5 * (attempt + 1))
    else:
        # network/Zen down (e.g. PC slept, DNS fail): HOLD everything, never crash
        print("  ! Zen unreachable after retries. Holding all positions this step.")
        return {"decisions": [
            {"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "ai offline, hold"}
            for s in snapshots
        ], "_reasoning": "", "_raw": "", "_offline": True}
    msg = resp.choices[0].message
    txt = (msg.content or "").strip()
    reasoning = getattr(msg, "reasoning_content", "") or ""
    def safe(t): return (t or "").replace("\u20b9", "Rs.").encode("cp1252", "replace").decode("cp1252")
    if verbose:
        print(f"\n--- AI THINKING ({config.ZEN_MODEL} @ {config.ZEN_REASONING_EFFORT}) ---")
        print(safe(reasoning) if reasoning else "(no reasoning returned)")
        print("--- END THINKING ---\n")
        print(f"[STEP 4/5] Raw answer: {safe(txt)[:1000]}")
    # strip code fences
    if txt.startswith("```"):
        txt = txt.strip("`").replace("json", "", 1).strip()
    start = txt.find("{")
    end = txt.rfind("}") + 1
    out = json.loads(txt[start:end])
    out["_reasoning"] = reasoning
    out["_raw"] = txt
    return out

def rule_decide(snapshots, portfolio, prices):
    """Fallback, no key needed. Simple RSI+SMA rule."""
    decisions = []
    for s in snapshots:
        price = s["price"]
        rsi = s.get("rsi14") or 50
        sma20 = s.get("sma20") or price
        pos = portfolio.positions.get(s["symbol"])
        if rsi < 35 and price > sma20 and not pos:
            decisions.append({"symbol": s["symbol"], "action": "BUY", "rupees": 150, "reason": "oversold bounce"})
        elif pos:
            avg = pos["avg_price"]
            if price < avg * 0.95 or price > avg * 1.10 or rsi > 70:
                decisions.append({"symbol": s["symbol"], "action": "SELL", "rupees": 0, "reason": "stop/take/overbought"})
            else:
                decisions.append({"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "holding"})
        else:
            decisions.append({"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "no signal"})
    return {"decisions": decisions}
