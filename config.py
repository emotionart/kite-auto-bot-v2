# config.py — ZERO hardcoded secrets. Sab Railway Variables se aayega.
import os

def _require(name):
    val = os.environ.get(name)
    if not val:
        print(f"[CONFIG WARNING] {name} not set in environment variables!")
    return val

# ================================================================
# KITE API — Railway Variables mein set karo
# ================================================================
KITE_API_KEY    = _require("KITE_API_KEY")
KITE_API_SECRET = _require("KITE_API_SECRET")

# ================================================================
# TELEGRAM
# ================================================================
TELEGRAM_TOKEN = _require("TELEGRAM_TOKEN")
CHAT_ID        = _require("CHAT_ID")

# ================================================================
# SERVER
# ================================================================
PORT         = int(os.environ.get("PORT", 8080))
RAILWAY_URL  = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
CALLBACK_URL = f"https://{RAILWAY_URL}/callback" if RAILWAY_URL else "http://localhost:8080/callback"

# ================================================================
# TRADING SETTINGS — apni risk appetite ke hisaab se badlo
# ================================================================
MAX_DAILY_LOSS     = float(os.environ.get("MAX_DAILY_LOSS", "5000"))
MAX_TRADES_PER_DAY = int(os.environ.get("MAX_TRADES_PER_DAY", "5"))
LOTS_PER_TRADE     = int(os.environ.get("LOTS_PER_TRADE", "1"))
TRADE_START_TIME   = os.environ.get("TRADE_START_TIME", "09:30")
TRADE_END_TIME     = os.environ.get("TRADE_END_TIME", "15:00")
SQUAREOFF_TIME     = os.environ.get("SQUAREOFF_TIME", "15:15")
SCAN_INTERVAL_SEC  = int(os.environ.get("SCAN_INTERVAL_SEC", "300"))  # 5 min

# ================================================================
# INDICATOR SETTINGS
# ================================================================
EMA_FAST    = 9
EMA_SLOW    = 21
RSI_PERIOD  = 14
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9
CANDLE_INTERVAL = "5minute"

# ================================================================
# INSTRUMENTS — symbols dynamically resolve honge (current month future)
# koi hardcoded expiry month nahi, isliye kabhi "expired contract" bug nahi aayega
# ================================================================
FUTURE_UNDERLYINGS = ["NIFTY", "BANKNIFTY"]  # NFO current-month futures
