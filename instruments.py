# instruments.py — Dynamic instrument resolution (fixes the "expired contract" bug)
import logging
from datetime import datetime

log = logging.getLogger(__name__)

_cache = {"instruments": None, "fetched_at": None}


def get_nfo_instruments(kite):
    """Fetch + cache NFO instrument list for the day (avoids hammering the API)."""
    today = datetime.now().date()
    if _cache["instruments"] is not None and _cache["fetched_at"] == today:
        return _cache["instruments"]

    log.info("[INSTRUMENTS] Fetching fresh NFO instrument list...")
    data = kite.instruments("NFO")
    _cache["instruments"] = data
    _cache["fetched_at"] = today
    return data


def get_current_month_future(kite, underlying):
    """
    Returns the nearest-expiry FUT contract for an underlying (e.g. NIFTY, BANKNIFTY).
    This replaces hardcoded symbols like 'NIFTY26MAYFUT' which expire and break the bot.
    """
    instruments = get_nfo_instruments(kite)
    today = datetime.now().date()

    futs = [
        i for i in instruments
        if i["name"] == underlying
        and i["instrument_type"] == "FUT"
        and i["expiry"] >= today
    ]
    if not futs:
        log.error(f"[INSTRUMENTS] No future contract found for {underlying}")
        return None

    futs.sort(key=lambda i: i["expiry"])
    nearest = futs[0]
    return {
        "symbol": nearest["tradingsymbol"],
        "token": nearest["instrument_token"],
        "lot_size": nearest["lot_size"],
        "expiry": nearest["expiry"],
    }


def get_mcx_instruments(kite):
    today = datetime.now().date()
    key = "mcx_instruments"
    if _cache.get(key) is not None and _cache.get(key + "_date") == today:
        return _cache[key]
    data = kite.instruments("MCX")
    _cache[key] = data
    _cache[key + "_date"] = today
    return data


def get_current_month_mcx_future(kite, underlying):
    """Same idea for MCX commodities (GOLD, SILVERM, CRUDEOIL, NATURALGAS)."""
    instruments = get_mcx_instruments(kite)
    today = datetime.now().date()

    futs = [
        i for i in instruments
        if i["name"] == underlying
        and i["instrument_type"] == "FUT"
        and i["expiry"] >= today
    ]
    if not futs:
        return None
    futs.sort(key=lambda i: i["expiry"])
    nearest = futs[0]
    return {
        "symbol": nearest["tradingsymbol"],
        "token": nearest["instrument_token"],
        "lot_size": nearest["lot_size"],
        "expiry": nearest["expiry"],
    }
