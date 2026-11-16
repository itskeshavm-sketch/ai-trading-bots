import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv is optional - .env is still parsed by envfile.py
    pass


def env(*names, default=""):
    """First non-empty value among the given env var names."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def env_int(*names, default=0):
    try:
        return int(env(*names, default=str(default)) or default)
    except (TypeError, ValueError):
        return default


def env_bool(*names, default=False):
    raw = env(*names, default="1" if default else "0").lower()
    return raw in ("1", "true", "yes", "y", "on")


# ---------------------------------------------------------------- AI provider
# Any OpenAI-compatible endpoint works: OpenAI, OpenRouter, Groq, Together,
# DeepSeek, Mistral, xAI, Cerebras, NVIDIA NIM, LM Studio, Ollama, vLLM,
# Gemini's OpenAI-compat layer, OpenCode Zen, or your own gateway.
# setup_provider.py writes these into .env after you pick a model.
AI_BASE_URL = env("AI_BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE",
                  default="https://api.openai.com/v1")
AI_API_KEY = env("AI_API_KEY", "OPENAI_API_KEY", "OPENCODE_API_KEY")
AI_MODEL = env("AI_MODEL", "OPENAI_MODEL", default="gpt-4o-mini")
# Empty = do not send a reasoning-effort field at all (most providers reject it).
AI_REASONING_EFFORT = env("AI_REASONING_EFFORT", "ZEN_REASONING_EFFORT", default="")
AI_MAX_TOKENS = env_int("AI_MAX_TOKENS", default=4096)
AI_TIMEOUT = env_int("AI_TIMEOUT", default=120)
# Ask the provider for strict JSON output. Off by default: plenty of compatible
# endpoints reject response_format.
AI_JSON_MODE = env_bool("AI_JSON_MODE", default=False)

# ---------------------------------------------------------------- trading
CASH_START = 500.0  # rupees, virtual
TARGET = 1000.0  # code stops here (AI only sees goal, not auto-stop)
RUIN = 1.0  # code stops here
STATE_FILE = "portfolio.json"
SYMBOLS = ["ITC.NS", "YESBANK.NS", "IDEA.NS"]  # cheap + liquid, fits Rs.500
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # free Binance feed, 24/7
CRYPTO_STATE_FILE = "portfolio_crypto.json"
CRYPTO_CASH_START = 500.0  # USDT paper
CRYPTO_TARGET = 1000.0
MEME_SYMBOLS = ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT"]  # wild side, same free feed
MEME_STATE_FILE = "portfolio_meme.json"
MEME_GATE_FILE = "last_prices_meme.json"
MEME_CASH_START = 500.0  # Rs. paper
MEME_TARGET = 1000.0
INTERVAL = "1d"
PERIOD = "3mo"
LOOP_INTERVAL = "1m"  # fastest free Yahoo, ~1min candles = near real speed
LOOP_PERIOD = "1d"
TICK_CACHE_TTL = 15  # seconds for loop mode

MAX_POSITION_PCT = 0.50  # 50% to push 500->1000 fast
STOP_LOSS_PCT = 0.05
TAKE_PROFIT_PCT = 0.10
# change-gate: only wake AI when a price actually moved
PRICE_MOVE_PCT = 0.05  # % move vs last check that counts as "changed"
FORCE_AI_EVERY = 10  # force AI review every Nth step even if flat (RSI/stops drift)

# live trading rails (only used with --live; paper is default)
LIVE_MAX_ORDER_RUPEES = 500.0  # max notional per live NSE/meme order
LIVE_MAX_ORDER_USDT = 10.0  # max notional per live crypto order
