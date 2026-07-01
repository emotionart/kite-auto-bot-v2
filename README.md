# Kite Auto Trading Bot v2 (Fresh Build)

Fully automatic BUY/SELL on Zerodha Kite for NIFTY + BANKNIFTY futures.
Strategy: VWAP + EMA(9/21) + RSI + MACD triple confirmation.

## ⚠️ One unavoidable reality

Zerodha requires a fresh interactive login **once every day** (SEBI security rule —
tokens expire daily). There is no legitimate way around this. This bot makes it a
**single tap**: every morning it Telegram-messages you a login link. Click it once,
log in normally on Zerodha's real page, and the bot trades fully automatically for
the rest of the day — no more manual clicks needed until the token expires again
the next day.

Anything that claims to "fully" auto-login by scraping your password + TOTP violates
Zerodha's Terms of Service and breaks the moment Zerodha changes their login page —
that's part of what broke the old bot.

## Setup

1. **Install dependencies** (for local testing only — Railway does this automatically):
   ```
   pip install -r requirements.txt
   ```

2. **Set these environment variables** (Railway → your project → Variables):
   ```
   KITE_API_KEY=your_kite_api_key
   KITE_API_SECRET=your_kite_api_secret
   TELEGRAM_TOKEN=your_telegram_bot_token
   CHAT_ID=your_telegram_chat_id
   MAX_DAILY_LOSS=5000
   MAX_TRADES_PER_DAY=5
   LOTS_PER_TRADE=1
   ```
   Never put these values directly in the code.

3. **Set your Kite Connect app's Redirect URL** (on developers.kite.trade) to:
   ```
   https://<your-railway-domain>/callback
   ```

4. **Deploy to Railway** — push this folder to a GitHub repo, connect it to Railway,
   Railway reads the `Procfile` and runs `python bot.py` automatically.

5. Every trading morning, tap the login link the bot sends you on Telegram (or visit
   `https://<your-railway-domain>/login`). The bot then runs the strategy automatically:
   scans every 5 minutes, places BUY/SELL orders with stop-loss when all 4 indicators
   agree, respects max daily loss and max trades, and auto-squares-off at 15:15.

## Telegram commands
- `/status` — is the bot logged in and trading?
- `/pnl` — today's P&L and trade count
- `/login` — resend the login link

## Files
- `bot.py` — main entry point (web server + trading loop + Telegram listener)
- `config.py` — all settings, reads only from environment variables
- `instruments.py` — dynamically resolves current-month futures (no more expired-contract bugs)
- `signals.py` — the VWAP/EMA/RSI/MACD strategy
- `executor.py` — order placement, stop-loss, square-off, P&L tracking

## Safety notes
- Paper-trade first if you haven't tested this exact strategy live before.
- Register a static IP with your Kite Connect app if required by SEBI rules for your account type.
- Never commit `.env` or real secrets to GitHub — `.gitignore` already excludes `.env`.
