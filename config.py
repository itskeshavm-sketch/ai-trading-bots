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

# Zen config - matches your screenshot
ZEN_BASE_URL = "https://opencode.ai/zen/v1"
ZEN_MODEL = "space-bunny-free"  # works via API with $0 balance. muse-spark-1.3-contributor-free is OpenCode-internal only (403 outside)
ZEN_MODEL_PAID = "muse-spark-1.3"  # use after you add credits
ZEN_REASONING_EFFORT = "max"  # Default/Low/Medium/High/Xhigh/Max in OpenCode UI
MAX_POSITION_PCT = 0.50  # 50% to push 500->1000 fast
STOP_LOSS_PCT = 0.05
TAKE_PROFIT_PCT = 0.10
# change-gate: only wake AI when a price actually moved
PRICE_MOVE_PCT = 0.05  # % move vs last check that counts as "changed"
FORCE_AI_EVERY = 10  # force AI review every Nth step even if flat (RSI/stops drift)

# live trading rails (only used with --live; paper is default)
LIVE_MAX_ORDER_RUPEES = 500.0  # max notional per live NSE/meme order
LIVE_MAX_ORDER_USDT = 10.0  # max notional per live crypto order
