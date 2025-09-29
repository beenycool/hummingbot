import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.logger import HummingbotLogger

from .trading212_order_book import Trading212OrderBook

if TYPE_CHECKING:
    from .trading212_exchange import Trading212Exchange


class Trading212APIOrderBookDataSource(OrderBookTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(self, trading_pairs: List[str], connector: "Trading212Exchange", api_factory: WebAssistantsFactory):
        super().__init__(trading_pairs)
        self._connector = connector
        self._api_factory = api_factory

    async def get_last_traded_prices(
        self,
        trading_pairs: List[str],
        domain: Optional[str] = None
    ) -> Dict[str, float]:
        _ = domain
        return await self._connector.get_last_traded_prices(trading_pairs=trading_pairs)

    async def _connected_websocket_assistant(self):
        # No websocket; return a dummy assistant via factory if needed but we will not subscribe
        return await self._api_factory.get_ws_assistant()

    async def _subscribe_channels(self, _websocket_assistant):
        # No public streams. Do nothing.
        self.logger().info("Trading212 has no public order book streams; using polling only.")

    def _channel_originating_message(self, _event_message: Dict[str, Any]) -> str:
        return self._snapshot_messages_queue_key

    async def _process_websocket_messages(self, _websocket_assistant):
        # Not used
        await asyncio.sleep(60)

    async def _parse_trade_message(self, _raw_message: Dict[str, Any], _message_queue: asyncio.Queue):
        # Not supported
        return

    async def _parse_order_book_diff_message(self, _raw_message: Dict[str, Any], _message_queue: asyncio.Queue):
        # Not supported
        return

    async def _parse_order_book_snapshot_message(self, _raw_message: Dict[str, Any], _message_queue: asyncio.Queue):
        # Not supported
        return

    async def _order_book_snapshot(self, trading_pair: str) -> OrderBookMessage:
        # Build an empty snapshot since there is no order book
        snapshot: Dict[str, Any] = {"trading_pair": trading_pair, "bids": [], "asks": []}
        return Trading212OrderBook.snapshot_message_from_exchange_rest(snapshot, timestamp=self._time())

