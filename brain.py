import os, json, time
from openai import OpenAI
import config

AI_RETRIES = 3


def get_client():
    """OpenAI-compatible client for whatever provider the user configured.

    Works with OpenAI, OpenRouter, Groq, Together, DeepSeek, Mistral, xAI,
    Cerebras, NVIDIA NIM, LM Studio, Ollama, vLLM, Gemini's compat layer,
    OpenCode Zen, or any gateway that speaks /v1/chat/completions.
    """
    key = config.AI_API_KEY
    if not key or "your-" in key or "your_" in key:
        return None
    try:
        return OpenAI(
            base_url=config.AI_BASE_URL,
            api_key=key,
            timeout=config.AI_TIMEOUT,
            max_retries=0,  # we do our own retries with clearer messages
        )
    except Exception as exc:  # bad base url etc.
        print(f"  ! Could not build AI client: {str(exc)[:200]}")
        return None


def provider_label():
    """Human readable 'provider/model' for logs."""
    base = (config.AI_BASE_URL or "").rstrip("/")
    host = base.split("/v")[0].split("//")[-1]
    return f"{host}/{config.AI_MODEL}"


PROMPT_NSE = """GOAL: Grow a real {CCY}{CASH} NSE trading account to {CCY}{TARGET} as fast as possible.
You are trading REAL money on the NSE. Every BUY/SELL you output executes as a live market order with real rupees. Losses are real and permanent. There is no reset, no practice mode.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","rupees":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional shares allowed. Keep reason <15 words.
"""

PROMPT_CRYPTO = """GOAL: Grow a real {CASH} USDT crypto trading account to {TARGET} USDT as fast as possible.
You are trading REAL money on Binance spot. Every BUY/SELL you output executes as a live market order with real USDT. Losses are real and permanent. There is no reset, no practice mode. Market runs 24/7, volatility is high.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","amount":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional amounts allowed. Amounts are in USDT. Keep reason <15 words.
"""

PROMPT_MEME = """GOAL: Grow a real {CCY}{CASH} memecoin trading account to {CCY}{TARGET} as fast as possible.
You are trading REAL money on crypto spot (DOGE, SHIB, PEPE). Every BUY/SELL you output executes as a live market order with real rupees. Losses are real and permanent. There is no reset, no practice mode. Market runs 24/7, memecoins are extremely volatile and can crash 30% in an hour.
You are an aggressive but disciplined trader. Prefer high-momentum setups, buy breakouts/oversold bounces, concentrate when confident.
Given live snapshots (prices in rupees) + your real portfolio, output ONLY JSON: {"decisions":[{"symbol":..., "action":"BUY|SELL|HOLD","amount":0,"reason":"..."}]}
Rules: max 50% per position, RSI>75 avoid chase, RSI<35 + price>SMA20 = strong buy, sell fast on -4% stop or +8% take or RSI>75. Fractional amounts allowed. Amounts are in rupees. Keep reason <15 words.
"""


def get_prompt(market, ccy="Rs.", cash=500, target=1000):
    if market == "crypto":
        p = PROMPT_CRYPTO
    elif market == "meme":
        p = PROMPT_MEME
    else:
        p = PROMPT_NSE
    amt = lambda v: f"{v:g}"
    return p.replace("{CCY}", ccy).replace("{CASH}", amt(cash)).replace("{TARGET}", amt(target))


PROMPT = PROMPT_NSE  # default


def _build_kwargs():
    """Base kwargs for a chat completion, before provider-specific fixes."""
    kwargs = {
        "model": config.AI_MODEL,
        "messages": [],
        "max_tokens": config.AI_MAX_TOKENS,
    }
    if config.AI_REASONING_EFFORT:
        # Only sent when the user explicitly asked for it. Many OpenAI-compatible
        # endpoints reject unknown body fields, so this stays opt-in.
        kwargs["extra_body"] = {"reasoning": {"effort": config.AI_REASONING_EFFORT}}
    if config.AI_JSON_MODE:
        kwargs["response_format"] = {"type": "json_object"}
    return kwargs


def _chat(client, messages, verbose=True):
    """Call the provider, degrading gracefully when it rejects optional fields.

    Every rejection is remembered, so each retry drops only what actually
    failed - no re-sending combinations the provider already refused.

    Handles providers that need max_completion_tokens instead of max_tokens,
    that have no JSON mode, or that reject a reasoning field.
    """
    blocked = set()
    last_err = None
    for attempt in range(6):
        kwargs = _build_kwargs()
        kwargs["messages"] = messages
        if "extra_body" in blocked:
            kwargs.pop("extra_body", None)
        if "response_format" in blocked:
            kwargs.pop("response_format", None)
        if "max_tokens" in blocked:
            kwargs.pop("max_tokens", None)
            kwargs["max_completion_tokens"] = config.AI_MAX_TOKENS

        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            fatal = ("401" in msg or "unauthorized" in msg or "invalid api key" in msg
                     or "insufficient" in msg or "balance" in msg)
            if fatal:
                if verbose:
                    print(f"  ! provider rejected the request: {str(exc)[:150]}")
                break

            if "max_token" in msg and "max_tokens" not in blocked:
                blocked.add("max_tokens")
                dropped = "max_tokens -> max_completion_tokens"
            elif ("response_format" in msg or "json_object" in msg) and "response_format" not in blocked:
                blocked.add("response_format")
                dropped = "response_format"
            elif ("extra_body" in msg or "reasoning" in msg) and "extra_body" not in blocked:
                blocked.add("extra_body")
                dropped = "reasoning/extra_body"
            else:
                if verbose:
                    print(f"  ! provider error: {str(exc)[:150]}")
                break

            if verbose:
                print(f"  ! provider rejected the call: {str(exc)[:120]}")
                print(f"    retrying without {dropped} ...")
    raise last_err


def ai_decide(client, snapshots, portfolio_text, verbose=True, market="nse",
              ccy="Rs.", cash_start=500, target=1000):
    prompt = get_prompt(market, ccy, cash_start, target)
    if verbose:
        effort = config.AI_REASONING_EFFORT or "none"
        print(f"[STEP 3/5] Asking {provider_label()} (reasoning={effort}) ...")
    messages = [{"role": "user",
                 "content": prompt + f"\nSnapshots:\n{json.dumps(snapshots, indent=2)}\nPortfolio:\n{portfolio_text}"}]

    last_err = None
    for attempt in range(AI_RETRIES):
        try:
            resp = _chat(client, messages, verbose=verbose)
            break
        except Exception as e:
            last_err = e
            print(f"  ! AI call failed (try {attempt+1}/{AI_RETRIES}): {str(e)[:200]}")
            time.sleep(5 * (attempt + 1))
    else:
        # Provider down (PC slept, DNS fail, bad key): HOLD everything, never crash
        print("  ! AI unreachable after retries. Holding all positions this step.")
        return {"decisions": [
            {"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "ai offline, hold"}
            for s in snapshots
        ], "_reasoning": "", "_raw": "", "_offline": True}

    msg = resp.choices[0].message
    txt = (msg.content or "").strip()
    reasoning = getattr(msg, "reasoning_content", "") or getattr(msg, "reasoning", "") or ""

    def safe(t):
        return (t or "").replace("\u20b9", "Rs.").encode("cp1252", "replace").decode("cp1252")

    if verbose:
        print(f"\n--- AI THINKING ({provider_label()}) ---")
        print(safe(reasoning) if reasoning else "(no reasoning returned)")
        print("--- END THINKING ---\n")
        print(f"[STEP 4/5] Raw answer: {safe(txt)[:1000]}")

    if txt.startswith("```"):
        txt = txt.strip("`").replace("json", "", 1).strip()
    start = txt.find("{")
    end = txt.rfind("}") + 1
    try:
        out = json.loads(txt[start:end])
    except Exception as exc:
        print(f"  ! Model did not return parsable JSON ({str(exc)[:120]}). Falling back to rules.")
        fallback = rule_decide(snapshots, None, None)
        fallback["_raw"] = txt
        return fallback
    out["_reasoning"] = reasoning
    out["_raw"] = txt
    return out


def rule_decide(snapshots, portfolio, prices):
    """Fallback, no key needed. Simple RSI+SMA rule."""
    stake = max(150, getattr(portfolio, "cash_start", 500) * 0.3)
    decisions = []
    for s in snapshots:
        price = s["price"]
        rsi = s.get("rsi14") or 50
        sma20 = s.get("sma20") or price
        pos = (portfolio.positions.get(s["symbol"]) if portfolio else None)
        if rsi < 35 and price > sma20 and not pos:
            decisions.append({"symbol": s["symbol"], "action": "BUY", "rupees": stake, "reason": "oversold bounce"})
        elif pos:
            avg = pos["avg_price"]
            if price < avg * 0.95 or price > avg * 1.10 or rsi > 70:
                decisions.append({"symbol": s["symbol"], "action": "SELL", "rupees": 0, "reason": "stop/take/overbought"})
            else:
                decisions.append({"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "holding"})
        else:
            decisions.append({"symbol": s["symbol"], "action": "HOLD", "rupees": 0, "reason": "no signal"})
    return {"decisions": decisions}
