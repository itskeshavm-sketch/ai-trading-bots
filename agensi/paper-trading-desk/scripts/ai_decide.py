"""Optional LLM decision layer for the paper-trading desk - provider agnostic.

The desk works fully without this: the deterministic RSI/SMA rules in
`indicators.py` are the default. This module adds an AI that proposes
BUY/SELL/HOLD from the same snapshots, using ANY OpenAI-compatible endpoint
(OpenAI, OpenRouter, Groq, Together, DeepSeek, Mistral, xAI, Cerebras, NIM,
Ollama, LM Studio, OpenCode Zen, your own gateway).

Configuration lives in `.env` next to this file:
    AI_BASE_URL=https://api.openai.com/v1
    AI_API_KEY=sk-...
    AI_MODEL=gpt-4o-mini

Run `python setup_provider.py` to set those up interactively - it lists the
provider's models and lets you pick one.

Stdlib only. If the provider is unreachable, wrong, or returns something
unparsable, the deterministic rules take over. It never places an order.
"""

import json
import os
import re
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")


def load_env(path=ENV_PATH):
    values = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
    return values


def provider_config(path=ENV_PATH):
    env = load_env(path)
    base = (env.get("AI_BASE_URL") or os.getenv("AI_BASE_URL") or "").rstrip("/")
    key = env.get("AI_API_KEY") or os.getenv("AI_API_KEY") or ""
    model = env.get("AI_MODEL") or os.getenv("AI_MODEL") or ""
    return {"base_url": base, "api_key": key, "model": model,
            "max_tokens": int(env.get("AI_MAX_TOKENS") or 4096)}


def build_prompt(snapshots, portfolio_text, cash=500, target=1000, ccy="Rs."):
    return (
        f"GOAL: grow a virtual {ccy}{cash} paper-trading account to {ccy}{target}.\n"
        "This is a SIMULATION - no real money, no orders. Be disciplined but active.\n"
        "Given the snapshots and the current virtual portfolio, output ONLY JSON:\n"
        '{"decisions":[{"symbol":"...","action":"BUY|SELL|HOLD","amount":0,"reason":"under 15 words"}]}\n'
        "Rules: max 50% of cash per position; BUY when RSI<35 and price>SMA20; "
        "SELL on RSI>75 or -4% stop or +8% take; keep every position under the cap.\n"
        f"Snapshots:\n{json.dumps(snapshots, indent=2)}\n"
        f"Portfolio:\n{portfolio_text}"
    )


def _post_json(url, payload, key, timeout=90):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def call_provider(config, prompt):
    """One chat completion. Returns the assistant text, or raises."""
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config["max_tokens"],
    }
    data = _post_json(config["base_url"] + "/chat/completions", payload, config["api_key"])
    return (data["choices"][0]["message"].get("content") or "").strip()


def parse_decisions(text):
    """Pull the JSON object out of a model reply, fences and all."""
    if not text:
        raise ValueError("empty model reply")
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model reply")
    payload = json.loads(text[start:end])
    if not isinstance(payload.get("decisions"), list):
        raise ValueError("model reply has no decisions list")
    return payload["decisions"]


def ai_decide(snapshots, portfolio_text, cash=500, target=1000, ccy="Rs.", verbose=False):
    """Ask the configured provider. Falls back to the rules on any problem.

    Returns (decisions, meta) where meta says which path was used.
    """
    import sys
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import indicators  # noqa: E402  (same directory)

    config = provider_config()
    if not (config["base_url"] and config["api_key"] and config["model"]):
        return _rule_decisions(indicators, snapshots), {"source": "rules", "why": "no provider configured"}

    prompt = build_prompt(snapshots, portfolio_text, cash, target, ccy)
    try:
        text = call_provider(config, prompt)
        decisions = parse_decisions(text)
    except Exception as exc:
        if verbose:
            print(f"  ! provider failed ({str(exc)[:140]}) - using the rules instead")
        return _rule_decisions(indicators, snapshots), {"source": "rules", "why": str(exc)[:200]}

    known = {s["symbol"] for s in snapshots}
    clean = []
    for item in decisions:
        symbol = str(item.get("symbol", "")).upper()
        action = str(item.get("action", "HOLD")).upper()
        if symbol not in known or action not in ("BUY", "SELL", "HOLD"):
            continue
        try:
            amount = float(item.get("amount", item.get("rupees", 0)) or 0)
        except (TypeError, ValueError):
            amount = 0.0
        clean.append({"symbol": symbol, "action": action, "amount": amount,
                      "reason": str(item.get("reason", ""))[:80]})
    if not clean:
        return _rule_decisions(indicators, snapshots), {"source": "rules", "why": "no usable decisions"}
    return clean, {"source": "ai", "model": config["model"], "base_url": config["base_url"]}


def _rule_decisions(indicators, snapshots):
    """Deterministic fallback: the same rules the screener uses."""
    out = []
    for snap in snapshots:
        price = snap.get("price", 0)
        prev = snap.get("prev_price", price)
        sig = indicators.signal({
            "price": price,
            "prev_price": prev,
            "sma20": snap.get("sma20"),
            "rsi14": snap.get("rsi14"),
        })
        out.append({"symbol": snap["symbol"], "action": sig["action"], "amount": 0,
                    "reason": sig["reason"]})
    return out


if __name__ == "__main__":
    import sys
    print("This module is used by the agent. See SKILL.md for the workflow.")
    print("Current provider:", provider_config() or "(not configured)")
    sys.exit(0)
