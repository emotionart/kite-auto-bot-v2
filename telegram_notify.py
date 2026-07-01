# telegram_notify.py — send-only notifications (bot is FULLY AUTOMATIC, no confirm needed)
import logging
import requests
from config import TELEGRAM_TOKEN, CHAT_ID

log = logging.getLogger(__name__)


def send(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        log.error(f"[TELEGRAM] Send error: {e}")


def get_updates(offset=None):
    if not TELEGRAM_TOKEN:
        return []
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"timeout": 5, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("result", [])
    except Exception:
        return []
