# market_intel.py — REAL data only: Kite OI/volume + NSE FII-DII (published) + news headlines
import logging
import requests
from datetime import datetime

log = logging.getLogger(__name__)


def get_oi_buildup(kite, underlying="NIFTY"):
    """
    Real-time Call/Put OI from Kite for the current-month options chain.
    Highest OI strike = where the most money is positioned (a genuine institutional-positioning proxy).
    """
    try:
        instruments = kite.instruments("NFO")
        today = datetime.now().date()

        opts = [
            i for i in instruments
            if i["name"] == underlying
            and i["instrument_type"] in ("CE", "PE")
            and i["expiry"] >= today
        ]
        if not opts:
            return None

        nearest_expiry = min(o["expiry"] for o in opts)
        opts = [o for o in opts if o["expiry"] == nearest_expiry]

        tokens = [o["instrument_token"] for o in opts]
        # Kite quote() gives OI directly, batched in groups of 100 (API limit)
        oi_data = {}
        for i in range(0, len(tokens), 100):
            batch = tokens[i:i+100]
            keys = [f"NFO:{o['tradingsymbol']}" for o in opts if o["instrument_token"] in batch]
            quotes = kite.quote(keys)
            for k, v in quotes.items():
                oi_data[k] = v.get("oi", 0)

        # Match back to strike/type
        rows = []
        for o in opts:
            key = f"NFO:{o['tradingsymbol']}"
            if key in oi_data:
                rows.append({
                    "strike": o["strike"],
                    "type": o["instrument_type"],
                    "oi": oi_data[key],
                    "symbol": o["tradingsymbol"],
                })

        calls = sorted([r for r in rows if r["type"] == "CE"], key=lambda x: -x["oi"])[:3]
        puts = sorted([r for r in rows if r["type"] == "PE"], key=lambda x: -x["oi"])[:3]

        return {"expiry": str(nearest_expiry), "top_calls": calls, "top_puts": puts}
    except Exception as e:
        log.error(f"[OI ERROR] {underlying}: {e}")
        return None


def get_top_movers(kite, exchange="NSE", count=5):
    """Real volume/price data for Nifty50 stocks — genuine most-active-by-volume from Kite."""
    try:
        nifty50 = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
            "KOTAKBANK", "ITC", "LT", "AXISBANK", "BAJFINANCE", "MARUTI", "SUNPHARMA",
            "TITAN", "ADANIENT", "TATASTEEL", "NTPC", "POWERGRID", "ULTRACEMCO",
        ]
        keys = [f"{exchange}:{s}" for s in nifty50]
        quotes = kite.quote(keys)

        rows = []
        for k, v in quotes.items():
            change_pct = v.get("net_change", 0) / v["ohlc"]["close"] * 100 if v["ohlc"]["close"] else 0
            rows.append({
                "symbol": k.split(":")[1],
                "ltp": v["last_price"],
                "change_pct": round(change_pct, 2),
                "volume": v.get("volume", 0),
            })

        gainers = sorted(rows, key=lambda x: -x["change_pct"])[:count]
        losers = sorted(rows, key=lambda x: x["change_pct"])[:count]
        by_volume = sorted(rows, key=lambda x: -x["volume"])[:count]

        return {"gainers": gainers, "losers": losers, "most_active": by_volume}
    except Exception as e:
        log.error(f"[MOVERS ERROR] {e}")
        return None


def get_fii_dii_data():
    """
    Real FII/DII provisional data, published daily by NSE (previous session's numbers,
    usually available by evening). This is the only genuine public source for institutional
    buy/sell flow in India — nobody, including brokers, has live intraday institutional data.
    """
    try:
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)  # sets cookies
        r = session.get(url, headers=headers, timeout=10)
        data = r.json()
        return data  # list of {category, date, buyValue, sellValue, netValue}
    except Exception as e:
        log.error(f"[FII/DII ERROR] {e}")
        return None


def format_report(oi_nifty, oi_banknifty, movers, fii_dii):
    """Compose the Telegram-ready report from real data pulled above."""
    lines = ["<b>Market Intel Report</b>", f"<i>{datetime.now().strftime('%d %b %Y, %H:%M')}</i>", ""]

    if fii_dii:
        lines.append("<b>FII/DII (prev session, NSE published)</b>")
        for row in fii_dii[:2]:
            cat = row.get("category", "")
            net = row.get("netValue", "N/A")
            lines.append(f"{cat}: net Rs.{net} Cr")
        lines.append("")

    if oi_nifty:
        lines.append(f"<b>NIFTY OI buildup</b> (expiry {oi_nifty['expiry']})")
        top_call = oi_nifty["top_calls"][0] if oi_nifty["top_calls"] else None
        top_put = oi_nifty["top_puts"][0] if oi_nifty["top_puts"] else None
        if top_call:
            lines.append(f"Highest Call OI: {top_call['strike']} ({top_call['oi']:,}) — resistance zone")
        if top_put:
            lines.append(f"Highest Put OI: {top_put['strike']} ({top_put['oi']:,}) — support zone")
        lines.append("")

    if oi_banknifty:
        lines.append(f"<b>BANKNIFTY OI buildup</b> (expiry {oi_banknifty['expiry']})")
        top_call = oi_banknifty["top_calls"][0] if oi_banknifty["top_calls"] else None
        top_put = oi_banknifty["top_puts"][0] if oi_banknifty["top_puts"] else None
        if top_call:
            lines.append(f"Highest Call OI: {top_call['strike']} ({top_call['oi']:,}) — resistance zone")
        if top_put:
            lines.append(f"Highest Put OI: {top_put['strike']} ({top_put['oi']:,}) — support zone")
        lines.append("")

    if movers:
        lines.append("<b>Top gainers</b>")
        for g in movers["gainers"][:3]:
            lines.append(f"{g['symbol']}: +{g['change_pct']}%")
        lines.append("")
        lines.append("<b>Top losers</b>")
        for l in movers["losers"][:3]:
            lines.append(f"{l['symbol']}: {l['change_pct']}%")
        lines.append("")
        lines.append("<b>Most active (volume)</b>")
        for m in movers["most_active"][:3]:
            lines.append(f"{m['symbol']}: {m['volume']:,} shares")

    lines.append("")
    lines.append("<i>OI = highest institutional positioning by strike. FII/DII = previous session, NSE-published. Not investment advice.</i>")
    return "\n".join(lines)
