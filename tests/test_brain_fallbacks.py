"""Offline test of brain.py's provider-fallback logic (no network, no API key).

Run: python tests\test_brain_fallbacks.py
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# brain.py does `from openai import OpenAI` at import time. If the package is not
# installed, stub it so this test still runs.
try:
    import openai  # noqa: F401
except ImportError:
    stub = types.ModuleType("openai")
    stub.OpenAI = object
    sys.modules["openai"] = stub

import brain  # noqa: E402


class FakeMessage:
    def __init__(self, content, reasoning=""):
        self.content = content
        self.reasoning_content = reasoning


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(FakeMessage(content))]


class PickyClient:
    """Rejects optional fields the way real providers do, then accepts."""

    def __init__(self, reject=(), content='{"decisions": []}'):
        self.reject = set(reject)
        self.content = content
        self.calls = []
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(sorted(kwargs.keys()))
        if "extra_body" in kwargs and "extra_body" in self.reject:
            raise RuntimeError("400 unknown parameter: extra_body")
        if "response_format" in kwargs and "response_format" in self.reject:
            raise RuntimeError("400 response_format is not supported")
        if "max_tokens" in kwargs and "max_tokens" in self.reject:
            raise RuntimeError("400 unsupported parameter: max_tokens")
        return FakeResponse(self.content)


def check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}  {name}{(' -> ' + detail) if detail and not condition else ''}")
    return condition


results = []

# 1. plain provider
client = PickyClient()
resp = brain._chat(client, [{"role": "user", "content": "hi"}], verbose=False)
results.append(check("plain provider works", resp is not None))
results.append(check("plain provider called once", len(client.calls) == 1, str(client.calls)))

# 2. provider that rejects extra_body (reasoning)
client = PickyClient(reject={"extra_body"})
brain.config.AI_REASONING_EFFORT = "max"
resp = brain._chat(client, [{"role": "user", "content": "hi"}], verbose=False)
results.append(check("reasoning field dropped on rejection", resp is not None))
results.append(check("fell back instead of crashing", len(client.calls) >= 2, str(client.calls)))
results.append(check("final call had no extra_body",
                     all("extra_body" not in c for c in client.calls[1:]), str(client.calls)))

# 3. provider that only accepts max_completion_tokens
client = PickyClient(reject={"max_tokens"})
resp = brain._chat(client, [{"role": "user", "content": "hi"}], verbose=False)
results.append(check("max_completion_tokens fallback", resp is not None))
results.append(check("swap used max_completion_tokens",
                     any("max_completion_tokens" in c for c in client.calls), str(client.calls)))

# 4. provider that rejects response_format
brain.config.AI_REASONING_EFFORT = ""
brain.config.AI_JSON_MODE = True
client = PickyClient(reject={"response_format"})
resp = brain._chat(client, [{"role": "user", "content": "hi"}], verbose=False)
results.append(check("json mode dropped on rejection", resp is not None))
results.append(check("final call had no response_format",
                     all("response_format" not in c for c in client.calls[1:]), str(client.calls)))
brain.config.AI_JSON_MODE = False

# 5. ai_decide parses a normal answer
snapshots = [{"symbol": "ITC", "price": 220.0, "rsi14": 30.0, "sma20": 215.0}]
client = PickyClient(content='{"decisions":[{"symbol":"ITC","action":"BUY","rupees":100,"reason":"test"}]}')
out = brain.ai_decide(client, snapshots, "cash 500", verbose=False)
results.append(check("ai_decide parsed decisions", out["decisions"][0]["action"] == "BUY", str(out)))

# 6. ai_decide survives a code-fenced answer
client = PickyClient(content='```json\n{"decisions":[{"symbol":"ITC","action":"HOLD","rupees":0,"reason":"x"}]}\n```')
out = brain.ai_decide(client, snapshots, "cash 500", verbose=False)
results.append(check("code-fenced JSON handled", out["decisions"][0]["action"] == "HOLD", str(out)))

# 7. ai_decide falls back to rules on garbage
client = PickyClient(content="I think we should buy something, maybe?")
out = brain.ai_decide(client, snapshots, "cash 500", verbose=False)
results.append(check("garbage answer falls back to rules",
                     out.get("decisions") and out["decisions"][0]["symbol"] == "ITC", str(out)))

# 8. offline fallback when the provider is completely down
class DeadClient:
    chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **k: (_ for _ in ()).throw(RuntimeError("connection refused"))))
brain.AI_RETRIES = 1
out = brain.ai_decide(DeadClient(), snapshots, "cash 500", verbose=False)
results.append(check("provider down -> HOLD everything",
                     out.get("_offline") is True and all(d["action"] == "HOLD" for d in out["decisions"]), str(out)))
brain.AI_RETRIES = 3

# 9. each retry drops only what the provider actually rejected
brain.config.AI_REASONING_EFFORT = "max"
brain.config.AI_JSON_MODE = True
client = PickyClient(reject={"extra_body", "response_format"})
resp = brain._chat(client, [{"role": "user", "content": "hi"}], verbose=False)
shapes = [tuple(c) for c in client.calls]
results.append(check("no duplicate call shapes", len(shapes) == len(set(shapes)), str(shapes)))
results.append(check("at most 3 calls needed", len(shapes) <= 3, str(len(shapes))))
results.append(check("last call carries neither rejected field",
                     "extra_body" not in shapes[-1] and "response_format" not in shapes[-1], str(shapes[-1])))
brain.config.AI_JSON_MODE = False
brain.config.AI_REASONING_EFFORT = ""

print()
print(f"{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
