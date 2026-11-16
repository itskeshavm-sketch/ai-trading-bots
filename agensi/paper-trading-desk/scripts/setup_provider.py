"""Interactive AI provider setup - works with ANY OpenAI-compatible endpoint.

    python setup_provider.py

Asks for:
  1. base URL   (OpenAI, OpenRouter, Groq, Together, DeepSeek, Mistral, xAI,
                  Cerebras, NVIDIA NIM, LM Studio, Ollama, vLLM, OpenCode Zen,
                  your own gateway - anything that speaks /v1/chat/completions)
  2. API key    (typed hidden, never printed)
  3. model      (your provider's model list is fetched and shown; pick by
                  number or type an id)

Then writes AI_BASE_URL / AI_API_KEY / AI_MODEL into .env and verifies the
model answers.

Stdlib only - runs before you install anything.

Non-interactive:
    python setup_provider.py --base-url https://api.openai.com/v1 \
        --api-key sk-... --model gpt-4o-mini
    python setup_provider.py --list-models --base-url ... --api-key ...
    python setup_provider.py --check
"""
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

from envfile import load_env, save_env, mask

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

ENV_KEYS = ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL",
            "AI_REASONING_EFFORT", "AI_MAX_TOKENS", "AI_JSON_MODE")


# ----------------------------------------------------------------- http helpers
def _request(url, key=None, payload=None, timeout=25):
    headers = {"Accept": "application/json", "User-Agent": "ai-trading-bots-setup"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        return exc.code, body
    except Exception as exc:
        return 0, str(exc)


def parse_models(payload):
    """Pull model ids out of the many shapes providers use."""
    ids = []
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = payload.get("data")
        if not isinstance(raw, list):
            raw = payload.get("models")
        if not isinstance(raw, list):
            raw = []
    else:
        raw = []

    for item in raw:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict):
            for field in ("id", "name", "model", "slug"):
                value = item.get(field)
                if isinstance(value, str) and value:
                    ids.append(value)
                    break
    seen, unique = set(), []
    for model_id in ids:
        if model_id not in seen:
            seen.add(model_id)
            unique.append(model_id)
    return unique


def fetch_models(base_url, key):
    """Try <base>/models, then <base>/v1/models. Returns (models, base_url_used, error)."""
    base = (base_url or "").rstrip("/")
    candidates = [base]
    if not base.endswith("/v1") and "/v1" not in base:
        candidates.append(base + "/v1")

    last_error = None
    for candidate in candidates:
        status, body = _request(candidate + "/models", key)
        if status == 200:
            try:
                models = parse_models(json.loads(body))
            except Exception as exc:
                last_error = f"could not parse model list: {exc}"
                continue
            if models:
                return models, candidate, None
            last_error = "provider returned an empty model list"
            continue
        if status == 401:
            last_error = "401 unauthorized - check the API key"
            continue
        if status == 404:
            last_error = f"404 at {candidate}/models"
            continue
        last_error = f"HTTP {status}: {body[:180]}"
    return [], base, last_error


def test_model(base_url, key, model, timeout=45):
    """One tiny chat call to prove the trio works. Returns (ok, detail)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
    }
    status, body = _request(base_url.rstrip("/") + "/chat/completions", key, payload, timeout=timeout)
    if status == 200:
        try:
            data = json.loads(body)
            reply = data["choices"][0]["message"].get("content") or ""
            return True, f"model answered: {str(reply).strip()[:60]!r}"
        except Exception as exc:
            return True, f"provider accepted the call (could not parse reply: {exc})"
    if status == 401:
        return False, "401 unauthorized - the API key is wrong"
    if status == 404:
        return False, f"404 - '{model}' not found on this provider (check the model id)"
    if status == 400:
        return False, f"400 - provider rejected the request: {body[:200]}"
    if status == 0:
        return False, f"network error: {body[:160]}"
    return False, f"HTTP {status}: {body[:200]}"


# ----------------------------------------------------------------- the wizard
def secret_prompt(prompt):
    """Hidden input when a console is attached, plain input otherwise."""
    try:
        if sys.stdin.isatty():
            return getpass.getpass(prompt)
    except Exception:
        pass
    return input(prompt + " (echoed, no console): ")


def choose_model(models, interactive=True):
    """Show the list, let the user filter, then pick. Returns a model id."""
    if not models:
        return None
    if not interactive:
        return models[0]

    print(f"\n{len(models)} model(s) available on this provider.")
    filtered = models

    while True:
        if len(filtered) > 25:
            hint = input("Filter by text (Enter = show all): ").strip()
            if hint:
                needle = hint.lower()
                filtered = [m for m in models if needle in m.lower()]
                if not filtered:
                    print("  no match, showing everything")
                    filtered = models
                else:
                    print(f"  {len(filtered)} match(es)")
            else:
                filtered = models

        shown = filtered[:60]
        for idx, model_id in enumerate(shown, 1):
            print(f"  [{idx:>3}] {model_id}")
        if len(filtered) > len(shown):
            print(f"  ... {len(filtered) - len(shown)} more (narrow it with a filter)")

        answer = input("Pick a model (number, or type the model id): ").strip()
        if not answer:
            continue
        if answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(shown):
                return shown[index - 1]
            print(f"  pick 1-{len(shown)}")
            continue
        if answer in filtered:
            return answer
        print("  not in the list - type it exactly if you want to force it")


def run_interactive(env_path=".env"):
    values = load_env(env_path)
    print("=" * 64)
    print("AI provider setup - any OpenAI-compatible endpoint")
    print("=" * 64)

    current_base = values.get("AI_BASE_URL") or DEFAULT_BASE_URL
    current_model = values.get("AI_MODEL") or DEFAULT_MODEL
    print(f"\nCurrent: base={current_base}  model={current_model}  key={mask(values.get('AI_API_KEY'))}")

    base_url = input(f"\nBase URL [{current_base}]: ").strip() or current_base
    base_url = base_url.rstrip("/")

    key = secret_prompt("API key (hidden, Enter = keep current): ").strip()
    if not key:
        key = values.get("AI_API_KEY", "")
    if not key:
        print("No API key given. Paste one, or press Ctrl+C to stop.")
        return None

    print(f"\nFetching model list from {base_url}/models ...")
    models, used_base, error = fetch_models(base_url, key)
    if models:
        print(f"OK - {len(models)} model(s) found.")
        base_url = used_base
    else:
        print(f"Could not list models ({error}).")
        print("You can still type a model id by hand - many gateways do not expose /models.")
        base_url = used_base

    model = choose_model(models) if models else None
    if not model:
        model = input(f"Model id [{current_model}]: ").strip() or current_model

    effort = values.get("AI_REASONING_EFFORT", "")
    effort_answer = input(
        f"Reasoning effort (Default/Low/Medium/High/Xhigh/Max) [{effort or 'Default'}]: "
    ).strip()
    if effort_answer:
        effort = "" if effort_answer.lower() == "default" else effort_answer

    tokens = values.get("AI_MAX_TOKENS", "4096")
    tokens_answer = input(f"Max tokens [{tokens}]: ").strip()
    if tokens_answer.isdigit():
        tokens = tokens_answer

    print(f"\nTesting {model} at {base_url} ...")
    ok, detail = test_model(base_url, key, model)
    print(("  OK  " if ok else "  FAIL ") + detail)
    if not ok:
        again = input("Save anyway? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print("Nothing saved.")
            return None

    values.update({
        "AI_BASE_URL": base_url,
        "AI_API_KEY": key,
        "AI_MODEL": model,
        "AI_REASONING_EFFORT": effort,
        "AI_MAX_TOKENS": str(tokens),
    })
    save_env(env_path, values)
    print(f"\nSaved to {env_path} (the key is never printed).")
    print(f"Provider: {base_url}  model: {model}")
    return values


def show_check(env_path=".env"):
    values = load_env(env_path)
    base = values.get("AI_BASE_URL", "(not set)")
    model = values.get("AI_MODEL", "(not set)")
    key = values.get("AI_API_KEY", "")
    print(f"Base URL : {base}")
    print(f"Model    : {model}")
    print(f"API key  : {mask(key)}")
    print(f"Reasoning: {values.get('AI_REASONING_EFFORT') or '(none sent)'}")
    print(f"Max tokens: {values.get('AI_MAX_TOKENS', '4096')}")
    if key:
        models, _, error = fetch_models(base, key)
        if models:
            print(f"Models   : {len(models)} available")
        else:
            print(f"Models   : could not list ({error})")
    return values


def main():
    ap = argparse.ArgumentParser(description="Configure any OpenAI-compatible AI provider.")
    ap.add_argument("--env-file", default=".env")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--no-test", action="store_true")
    args = ap.parse_args()

    if args.check:
        show_check(args.env_file)
        return 0

    values = load_env(args.env_file)

    if args.base_url or args.api_key or args.model:
        # non-interactive path
        base = (args.base_url or values.get("AI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        key = args.api_key or values.get("AI_API_KEY", "")
        model = args.model or values.get("AI_MODEL") or DEFAULT_MODEL
        if not key:
            print("No API key given.", file=sys.stderr)
            return 1
        if args.list_models:
            models, used_base, error = fetch_models(base, key)
            if not models:
                print(f"Could not list models ({error})", file=sys.stderr)
                return 1
            for model_id in models:
                print(model_id)
            return 0
        values.update({"AI_BASE_URL": base, "AI_API_KEY": key, "AI_MODEL": model})
        save_env(args.env_file, values)
        print(f"Saved {args.env_file}: {base} / {model}")
        if not args.no_test:
            ok, detail = test_model(base, key, model)
            print(("  OK   " if ok else "  FAIL ") + detail)
            if not ok:
                return 2
        return 0

    result = run_interactive(args.env_file)
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
