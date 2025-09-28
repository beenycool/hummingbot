from typing import Dict, Optional

from hummingbot.core.data_type.common import TradeType
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType


class Trading212OrderBook(OrderBook):
    @classmethod
    def snapshot_message_from_exchange_rest(
        cls,
        msg: Dict[str, any],
        timestamp: float,
        metadata: Optional[Dict] = None,
    ) -> OrderBookMessage:
        # Trading212 does not provide full order book via REST; this is a no-op placeholder to satisfy interface
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(
            OrderBookMessageType.SNAPSHOT,
            {
                "trading_pair": msg.get("trading_pair"),
                "snapshotId": int(timestamp * 1e3),
                "update_id": int(timestamp * 1e3),
                "bids": msg.get("bids", []),
                "asks": msg.get("asks", []),
            },
            timestamp=timestamp,
        )

    @classmethod
    def diff_message_from_exchange(
        cls,
        msg: Dict[str, any],
        timestamp: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(
            OrderBookMessageType.DIFF,
            {
                "trading_pair": msg.get("trading_pair"),
                "snapshotId": msg.get("update_id", 0),
                "update_id": msg.get("update_id", 0),
                "bids": msg.get("bids", []),
                "asks": msg.get("asks", []),
            },
            timestamp=timestamp,
        )

    @classmethod
    def trade_message_from_exchange(
        cls,
        msg: Dict[str, any],
        timestamp: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(
            OrderBookMessageType.TRADE,
            {
                "trading_pair": msg["trading_pair"],
                "trade_type": float(TradeType.BUY.value if msg.get("side", "buy").lower() == "buy" else TradeType.SELL.value),
                "trade_id": msg.get("trade_id", 0),
                "price": msg.get("price", 0),
                "amount": msg.get("amount", 0),
            },
            timestamp=timestamp,
        )

