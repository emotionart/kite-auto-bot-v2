# bot.py — MAIN ENTRY POINT
# Fully automatic BUY/SELL once logged in. Run: python bot.py
#
# IMPORTANT REALITY CHECK:
# Zerodha requires a fresh interactive login once every day (SEBI security rule).
# There is NO legitimate way to bypass this — any bot that tries to auto-login
# with scraped username/password/TOTP violates Zerodha's Terms of Service and
# breaks constantly when Zerodha changes their login page. This bot instead
# sends you a Telegram message each morning with a one-tap login link.
# Click it once -> bot trades fully automatically the rest of the day.

import sys, io, os, time, logging, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import pandas as pd
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from kiteconnect import KiteConnect

import config
import telegram_notify as tg
from instruments import get_current_month_future
from signals import get_signal
from executor import OrderManager
import market_intel

# ================================================================
# LOGGING — logs/ folder must exist BEFORE FileHandler is created
# ================================================================
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ================================================================
# GLOBAL STATE
# ================================================================
kite = KiteConnect(api_key=config.KITE_API_KEY)
state = {
    "access_token": None,
    "logged_in_at": None,
    "order_mgr": None,
    "active_positions": {},   # symbol -> "BUY"/"SELL"
    "trading_thread_started": False,
}

# ================================================================
# HTTP SERVER — health check + Kite login/callback
# ================================================================
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silence default HTTP logs

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ("/", "/health"):
            status = "TRADING (logged in)" if state["access_token"] else "WAITING FOR LOGIN"
            pnl = state["order_mgr"].daily_pnl if state["order_mgr"] else 0
            trades = state["order_mgr"].trade_count if state["order_mgr"] else 0
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"""
                <html><body style="font-family:Arial;background:#0a0a0f;color:#fff;text-align:center;padding:50px">
                <h1 style="color:#00d4aa">Kite Auto Trading Bot</h1>
                <h2>Status: {status}</h2>
                <p>P&L: Rs.{pnl:.2f} | Trades: {trades}/{config.MAX_TRADES_PER_DAY}</p>
                {'<p><a href="/login" style="color:#00d4aa">Login to Zerodha</a></p>' if not state['access_token'] else ''}
                </body></html>
            """.encode())

        elif parsed.path == "/login":
            login_url = kite.login_url()
            self.send_response(302)
            self.send_header("Location", login_url)
            self.end_headers()

        elif parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            request_token = params.get("request_token", [None])[0]
            self.send_response(200)
            self.end_headers()
            if request_token:
                try:
                    session = kite.generate_session(request_token, api_secret=config.KITE_API_SECRET)
                    state["access_token"] = session["access_token"]
                    state["logged_in_at"] = datetime.now()
                    kite.set_access_token(state["access_token"])
                    state["order_mgr"] = OrderManager(kite)
                    self.wfile.write(b"<h2 style='font-family:Arial;color:green'>Login successful! Bot is now trading. You can close this tab.</h2>")
                    log.info("[AUTH] Login successful, access token set.")
                    tg.send("Login successful. Bot ab trading start karega.")
                    if not state["trading_thread_started"]:
                        threading.Thread(target=trading_loop, daemon=True).start()
                        state["trading_thread_started"] = True
                except Exception as e:
                    self.wfile.write(f"<h2 style='color:red'>Login failed: {e}</h2>".encode())
                    log.error(f"[AUTH] Login failed: {e}")
            else:
                self.wfile.write(b"<h2 style='color:red'>No request_token received.</h2>")
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    server = HTTPServer(("0.0.0.0", config.PORT), Handler)
    log.info(f"[SERVER] Listening on port {config.PORT}")
    server.serve_forever()


# ================================================================
# TELEGRAM COMMAND LISTENER
# ================================================================
def telegram_listener():
    log.info("[TG] Listener started")
    tg.send(
        "Kite Auto Bot online.\n\n"
        f"Login karne ke liye: {config.CALLBACK_URL.replace('/callback', '/login')}\n"
        "Commands: /status /pnl /report"
    )
    offset = None
    while True:
        try:
            updates = tg.get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                text = update.get("message", {}).get("text", "").strip().lower()
                if text == "/status":
                    status = "Trading (logged in)" if state["access_token"] else "Waiting for login"
                    tg.send(f"Status: {status}")
                elif text == "/pnl":
                    if state["order_mgr"]:
                        state["order_mgr"].update_pnl()
                        tg.send(f"P&L: Rs.{state['order_mgr'].daily_pnl:.2f} | Trades: {state['order_mgr'].trade_count}/{config.MAX_TRADES_PER_DAY}")
                    else:
                        tg.send("Bot abhi login nahi hua.")
                elif text == "/login":
                    tg.send(f"Login link: {config.CALLBACK_URL.replace('/callback', '/login')}")
                elif text == "/report":
                    if not state["access_token"]:
                        tg.send("Pehle /login karo, tabhi real data mil payega.")
                    else:
                        tg.send("Report ban rahi hai, thoda ruko...")
                        try:
                            oi_nifty = market_intel.get_oi_buildup(kite, "NIFTY")
                            oi_bn = market_intel.get_oi_buildup(kite, "BANKNIFTY")
                            movers = market_intel.get_top_movers(kite)
                            fii_dii = market_intel.get_fii_dii_data()
                            report = market_intel.format_report(oi_nifty, oi_bn, movers, fii_dii)
                            tg.send(report)
                        except Exception as e:
                            log.error(f"[REPORT ERROR] {e}")
                            tg.send(f"Report banane mein error: {e}")
        except Exception as e:
            log.error(f"[TG] Listener error: {e}")
        time.sleep(2)


# ================================================================
# TRADING LOOP
# ================================================================
def get_candles(token):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)
        data = kite.historical_data(token, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"), config.CANDLE_INTERVAL)
        df = pd.DataFrame(data)
        if df.empty:
            return None
        return df
    except Exception as e:
        log.error(f"[CANDLE ERROR] token={token}: {e}")
        return None


def trading_loop():
    log.info("=" * 55)
    log.info("TRADING LOOP STARTED")
    log.info(f"Underlyings: {config.FUTURE_UNDERLYINGS}")
    log.info(f"Max Loss: Rs.{config.MAX_DAILY_LOSS} | Max Trades: {config.MAX_TRADES_PER_DAY}")
    log.info("=" * 55)

    order_mgr = state["order_mgr"]

    while state["access_token"]:
        try:
            now = datetime.now().strftime("%H:%M")
            pnl = order_mgr.update_pnl()

            if pnl <= -config.MAX_DAILY_LOSS:
                log.warning(f"[STOP] Max daily loss hit! P&L: Rs.{pnl:.2f}")
                tg.send(f"MAX LOSS HIT! P&L: Rs.{pnl:.2f}. Squaring off all positions.")
                order_mgr.square_off_all("MIS")
                break

            if order_mgr.trade_count >= config.MAX_TRADES_PER_DAY:
                log.info(f"[STOP] Max trades ({config.MAX_TRADES_PER_DAY}) reached for today")
                tg.send(f"Max trades ({config.MAX_TRADES_PER_DAY}) done for today. Bot pausing.")
                time.sleep(300)
                continue

            if now >= config.SQUAREOFF_TIME:
                if state["active_positions"]:
                    log.info("[SQUAREOFF TIME] Closing all positions")
                    order_mgr.square_off_all("MIS")
                    state["active_positions"] = {}
                    tg.send("Square-off time. All positions closed for today.")
                time.sleep(60)
                continue

            if now < config.TRADE_START_TIME or now >= config.TRADE_END_TIME:
                time.sleep(60)
                continue

            for underlying in config.FUTURE_UNDERLYINGS:
                if underlying in state["active_positions"]:
                    continue

                contract = get_current_month_future(kite, underlying)
                if not contract:
                    log.warning(f"[SKIP] Could not resolve contract for {underlying}")
                    continue

                df = get_candles(contract["token"])
                if df is None or len(df) < 30:
                    continue

                signal, ind = get_signal(df)
                log.info(f"{underlying} [{contract['symbol']}] price={ind.get('price')} vwap={ind.get('vwap')} rsi={ind.get('rsi')} signal={signal}")

                if signal in ("BUY", "SELL"):
                    quantity = config.LOTS_PER_TRADE * contract["lot_size"]
                    prev = df.iloc[-2]
                    sl = round(prev["low"] * 0.998, 2) if signal == "BUY" else round(prev["high"] * 1.002, 2)

                    order_id = order_mgr.place_order(contract["symbol"], "NFO", signal, quantity, "MIS")
                    if order_id:
                        order_mgr.set_stop_loss(contract["symbol"], "NFO", signal, quantity, sl, "MIS")
                        state["active_positions"][underlying] = signal
                        tg.send(
                            f"<b>{signal} {contract['symbol']}</b>\n"
                            f"Qty: {quantity} | Entry: ~{ind.get('price')} | SL: {sl}\n"
                            f"RSI: {ind.get('rsi')} | VWAP: {ind.get('vwap')}"
                        )

            time.sleep(config.SCAN_INTERVAL_SEC)

        except Exception as e:
            log.error(f"[LOOP ERROR] {e}")
            tg.send(f"Bot error: {e}")
            time.sleep(30)

    log.info("[LOOP] Trading loop stopped (token cleared or day ended)")


# ================================================================
# START
# ================================================================
if __name__ == "__main__":
    threading.Thread(target=telegram_listener, daemon=True).start()
    run_server()
