# executor.py — order placement, stop-loss, square-off, risk tracking
import logging
from kiteconnect import KiteConnect

log = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, kite):
        self.kite = kite
        self.daily_pnl = 0
        self.trade_count = 0

    def get_ltp(self, exchange, symbol):
        try:
            ltp_data = self.kite.ltp(f"{exchange}:{symbol}")
            return ltp_data[f"{exchange}:{symbol}"]["last_price"]
        except Exception as e:
            log.error(f"[LTP ERROR] {symbol}: {e}")
            return None

    def place_order(self, symbol, exchange, action, quantity, product="MIS"):
        try:
            transaction = KiteConnect.TRANSACTION_TYPE_BUY if action == "BUY" else KiteConnect.TRANSACTION_TYPE_SELL
            product_type = KiteConnect.PRODUCT_MIS if product == "MIS" else KiteConnect.PRODUCT_NRML

            ltp = self.get_ltp(exchange, symbol)
            if not ltp:
                log.error(f"[ORDER FAILED] No LTP for {symbol}")
                return None

            price = round(ltp * 1.002, 1) if action == "BUY" else round(ltp * 0.998, 1)

            order_id = self.kite.place_order(
                variety=KiteConnect.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=transaction,
                quantity=quantity,
                product=product_type,
                order_type=KiteConnect.ORDER_TYPE_LIMIT,
                price=price,
            )
            log.info(f"[ORDER OK] {action} {symbol} qty={quantity} price={price} id={order_id}")
            self.trade_count += 1
            return order_id
        except Exception as e:
            log.error(f"[ORDER FAILED] {symbol}: {e}")
            return None

    def set_stop_loss(self, symbol, exchange, action, quantity, sl_price, product="MIS"):
        try:
            sl_transaction = KiteConnect.TRANSACTION_TYPE_SELL if action == "BUY" else KiteConnect.TRANSACTION_TYPE_BUY
            product_type = KiteConnect.PRODUCT_MIS if product == "MIS" else KiteConnect.PRODUCT_NRML
            order_id = self.kite.place_order(
                variety=KiteConnect.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=sl_transaction,
                quantity=quantity,
                product=product_type,
                order_type=KiteConnect.ORDER_TYPE_SL_M,
                trigger_price=sl_price,
            )
            log.info(f"[SL SET] {symbol} sl={sl_price} id={order_id}")
            return order_id
        except Exception as e:
            log.error(f"[SL FAILED] {symbol}: {e}")
            return None

    def square_off_all(self, product="MIS"):
        log.info(f"[SQUAREOFF] Closing {product} positions...")
        try:
            positions = self.kite.positions()
            for pos in positions.get("net", []):
                if pos["quantity"] != 0:
                    action = "SELL" if pos["quantity"] > 0 else "BUY"
                    self.place_order(pos["tradingsymbol"], pos["exchange"], action, abs(pos["quantity"]), product)
            log.info("[SQUAREOFF] Done")
        except Exception as e:
            log.error(f"[SQUAREOFF ERROR] {e}")

    def update_pnl(self):
        try:
            positions = self.kite.positions()
            self.daily_pnl = sum(pos.get("pnl", 0) for pos in positions.get("net", []))
            return self.daily_pnl
        except Exception:
            return self.daily_pnl

    def reset_daily(self):
        self.daily_pnl = 0
        self.trade_count = 0
