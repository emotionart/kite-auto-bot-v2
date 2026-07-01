# signals.py — VWAP + EMA(9/21) + RSI + MACD triple-confirmation strategy
import pandas as pd
from config import EMA_FAST, EMA_SLOW, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL


def calculate_ema(prices, period):
    return pd.Series(prices).ewm(span=period, adjust=False).mean().values


def calculate_rsi(prices, period=14):
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).values


def calculate_macd(prices, fast=12, slow=26, signal=9):
    prices = pd.Series(prices)
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.values, signal_line.values


def calculate_vwap(df):
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()


def get_signal(df):
    """
    Returns ("BUY" | "SELL" | "WAIT", indicators_dict)
    BUY  = price>VWAP + EMA9 crosses above EMA21 + RSI 40-65 + MACD bullish cross
    SELL = price<VWAP + EMA9 crosses below EMA21 + RSI 35-60 + MACD bearish cross
    """
    if len(df) < 30:
        return "WAIT", {}

    closes = df["close"].values
    ema_fast = calculate_ema(closes, EMA_FAST)
    ema_slow = calculate_ema(closes, EMA_SLOW)
    rsi = calculate_rsi(closes, RSI_PERIOD)
    macd_line, signal_line = calculate_macd(closes, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    vwap = calculate_vwap(df)

    curr_price = closes[-1]
    curr_vwap = vwap.iloc[-1]
    curr_rsi = rsi[-1]

    ema_bullish_cross = (ema_fast[-2] <= ema_slow[-2]) and (ema_fast[-1] > ema_slow[-1])
    ema_bearish_cross = (ema_fast[-2] >= ema_slow[-2]) and (ema_fast[-1] < ema_slow[-1])
    macd_bullish = (macd_line[-2] <= signal_line[-2]) and (macd_line[-1] > signal_line[-1])
    macd_bearish = (macd_line[-2] >= signal_line[-2]) and (macd_line[-1] < signal_line[-1])

    indicators = {
        "price": round(float(curr_price), 2),
        "vwap": round(float(curr_vwap), 2),
        "ema9": round(float(ema_fast[-1]), 2),
        "ema21": round(float(ema_slow[-1]), 2),
        "rsi": round(float(curr_rsi), 2),
        "macd": round(float(macd_line[-1]), 4),
    }

    if curr_price > curr_vwap and ema_bullish_cross and 40 <= curr_rsi <= 65 and macd_bullish:
        return "BUY", indicators
    elif curr_price < curr_vwap and ema_bearish_cross and 35 <= curr_rsi <= 60 and macd_bearish:
        return "SELL", indicators
    else:
        return "WAIT", indicators
