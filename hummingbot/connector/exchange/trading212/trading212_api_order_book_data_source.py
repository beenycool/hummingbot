"""
Trading212 Order Book Data Source

This module implements a polling-based order book data source for Trading212
since they don't provide WebSocket order book feeds.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_tracker import OrderBookTrackerDataSource
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.connector.exchange.trading212.trading212_web_utils import Trading212WebUtils
from hummingbot.connector.exchange.trading212.trading212_constants import POLLING_INTERVALS, REST_URL, ENDPOINTS
from hummingbot.connector.exchange.trading212.trading212_utils import Trading212Utils
import time

class Trading212APIOrderBookDataSource(OrderBookTrackerDataSource):
    """
    Trading212 order book data source using polling-based updates.
    
    Since Trading212 doesn't provide WebSocket order book feeds,
    this class polls the portfolio endpoint to get current prices
    and creates synthetic order book data.
    """
    
    def __init__(self, web_utils: Trading212WebUtils, trading_pairs: List[str]):
        """
        Initialize Trading212 order book data source.
        
        Args:
            web_utils: Trading212 web utilities
            trading_pairs: List of trading pairs to track
        """
        super().__init__(trading_pairs)
        self._web_utils = web_utils
        self._logger = logging.getLogger(__name__)
        self._trading_pairs = trading_pairs
        self._last_prices: Dict[str, Decimal] = {}
        self._polling_task: Optional[asyncio.Task] = None
        self._stop_polling = False
        
    async def start(self):
        """Start the polling task."""
        if self._polling_task is None or self._polling_task.done():
            self._stop_polling = False
            self._polling_task = asyncio.create_task(self._polling_loop())
            
    async def stop(self):
        """Stop the polling task."""
        self._stop_polling = True
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
                
    async def _polling_loop(self):
        """Main polling loop for order book updates."""
        while not self._stop_polling:
            try:
                await self._update_order_books()
                await asyncio.sleep(POLLING_INTERVALS["MARKET_DATA"])
            except Exception as e:
                self._logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(POLLING_INTERVALS["MARKET_DATA"])
                
    async def _update_order_books(self):
        """Update order books for all trading pairs."""
        try:
            # Get portfolio data to extract current prices
            # use the absolute URL constant instead of hard-coded path
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['portfolio']}")

            if response.status == 200 and isinstance(response.data, list):
                for position in response.data:
                    ticker = position.get("ticker", "")
                    trading_pair = self._convert_ticker_to_trading_pair(ticker)

                    if trading_pair in self._trading_pairs:
                        current_price = Decimal(str(position.get("currentPrice", 0)))
                        if current_price > 0:
                            await self._update_order_book(trading_pair, current_price)
                            
        except Exception as e:
            self._logger.error(f"Error updating order books: {e}")
            
    async def _update_order_book(self, trading_pair: str, price: Decimal):
        """
        Update order book for a specific trading pair.
        
        Args:
            trading_pair: Trading pair to update
            price: Current price
        """
        try:
            # Create synthetic order book with current price
            # Since Trading212 doesn't provide order book data,
            # we create a simple order book with the current price
            
            if trading_pair not in self._last_prices or self._last_prices[trading_pair] != price:
                self._last_prices[trading_pair] = price
                
                # Create synthetic order book rows
                bid_rows = [OrderBookRow(price, 1.0, 1)]
                ask_rows = [OrderBookRow(price, 1.0, 1)]
                
                # Create order book message
                order_book_message = OrderBookMessage(
                    message_type=OrderBookMessageType.DIFF,
                    content={
                        "trading_pair": trading_pair,
                        "bids": bid_rows,
                        "asks": ask_rows,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                    timestamp=asyncio.get_event_loop().time()
                )
                
                # Emit the order book message
                await self._emit_order_book_message(order_book_message)
                
        except Exception as e:
            self._logger.error(f"Error updating order book for {trading_pair}: {e}")
            
    def _convert_ticker_to_trading_pair(self, ticker: str) -> str:
        """
        Convert Trading212 ticker to trading pair format.
        
        Args:
            ticker: Trading212 ticker
            
        Returns:
            Trading pair string
        """
        try:
            # Trading212 format: "AAPL_US_EQ" -> Hummingbot format: "AAPL-USD"
            parts = ticker.split("_")
            if len(parts) >= 2:
                symbol = parts[0]
                currency = parts[1]
                return f"{symbol}-{currency}"
            return ticker
        except Exception:
            return ticker
            
    async def get_last_traded_price(self, trading_pair: str) -> Optional[Decimal]:
        """
        Get the last traded price for a trading pair.
        
        Args:
            trading_pair: Trading pair to get price for
            
        Returns:
            Last traded price or None if not available
        """
        return self._last_prices.get(trading_pair)
        
    async def get_order_book_snapshot(self, trading_pair: str) -> Optional[OrderBook]:
        """
        Get order book snapshot for a trading pair.
        
        Args:
            trading_pair: Trading pair to get snapshot for
            
        Returns:
            Order book snapshot or None if not available
        """
        try:
            price = self._last_prices.get(trading_pair)
            if price is None:
                return None
                
            # Create synthetic order book
            bid_rows = [OrderBookRow(price, 1.0, 1)]
            ask_rows = [OrderBookRow(price, 1.0, 1)]
            
            return OrderBook(
                trading_pair=trading_pair,
                bids=bid_rows,
                asks=ask_rows,
                timestamp=asyncio.get_event_loop().time()
            )
            
        except Exception as e:
            self._logger.error(f"Error getting order book snapshot for {trading_pair}: {e}")
            return None
            
    async def listen_for_order_book_snapshots(self, ev_loop: asyncio.AbstractEventLoop, output: asyncio.Queue):
        """
        Listen for order book snapshots.
        
        Args:
            ev_loop: Event loop
            output: Output queue for order book messages
        """
        while True:
            try:
                for trading_pair in self._trading_pairs:
                    order_book = await self.get_order_book_snapshot(trading_pair)
                    if order_book:
                        snapshot_message = OrderBookMessage(
                            message_type=OrderBookMessageType.SNAPSHOT,
                            content=order_book,
                            timestamp=asyncio.get_event_loop().time()
                        )
                        await output.put(snapshot_message)
                        
                await asyncio.sleep(POLLING_INTERVALS["MARKET_DATA"])
                
            except Exception as e:
                self._logger.error(f"Error listening for order book snapshots: {e}")
                await asyncio.sleep(POLLING_INTERVALS["MARKET_DATA"])
                
    async def listen_for_order_book_diffs(self, ev_loop: asyncio.AbstractEventLoop, output: asyncio.Queue):
        """
        Listen for order book diffs.
        
        Args:
            ev_loop: Event loop
            output: Output queue for order book messages
        """
        await self.listen_for_order_book_snapshots(ev_loop, output)
        
    async def listen_for_trades(self, ev_loop: asyncio.AbstractEventLoop, output: asyncio.Queue):
        """
        Listen for trades.
        
        Args:
            ev_loop: Event loop
            output: Output queue for trade messages
        """
        # Trading212 doesn't provide real-time trade feeds
        # This would need to be implemented using historical order data
        # For now, we'll just sleep to prevent busy waiting
        while True:
            await asyncio.sleep(POLLING_INTERVALS["MARKET_DATA"])
            
    async def _emit_order_book_message(self, message: OrderBookMessage):
        """
        Emit order book message to subscribers.
        
        Args:
            message: Order book message to emit
        """
        # This would typically emit to a message queue or event system
        # For now, we'll just log the message
        self._logger.debug(f"Order book message: {message}")
        
    def get_trading_pairs(self) -> List[str]:
        """
        Get list of trading pairs being tracked.
        
        Returns:
            List of trading pairs
        """
        return self._trading_pairs
        
    def add_trading_pair(self, trading_pair: str):
        """
        Add a trading pair to track.
        
        Args:
            trading_pair: Trading pair to add
        """
        if trading_pair not in self._trading_pairs:
            self._trading_pairs.append(trading_pair)
            
    def remove_trading_pair(self, trading_pair: str):
        """
        Remove a trading pair from tracking.
        
        Args:
            trading_pair: Trading pair to remove
        """
        if trading_pair in self._trading_pairs:
            self._trading_pairs.remove(trading_pair)
            if trading_pair in self._last_prices:
                del self._last_prices[trading_pair]