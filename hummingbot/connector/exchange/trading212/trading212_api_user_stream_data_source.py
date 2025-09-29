"""
Trading212 User Stream Data Source

This module implements a polling-based user stream data source for Trading212
to track user-specific data like orders, balances, and positions.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.data_type.user_stream_tracker import UserStreamTracker
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.data_type.trade import Trade
from hummingbot.core.data_type.balance import Balance
from hummingbot.core.data_type.position import Position, PositionSide
from hummingbot.core.web_assistant.connections.data_types import RESTResponse
from hummingbot.connector.exchange.trading212.trading212_web_utils import Trading212WebUtils
from hummingbot.connector.exchange.trading212.trading212_utils import Trading212Utils
from hummingbot.connector.exchange.trading212.trading212_constants import POLLING_INTERVALS


class Trading212APIUserStreamDataSource(UserStreamTrackerDataSource):
    """
    Trading212 user stream data source using polling-based updates.
    
    This class polls Trading212's API endpoints to track user-specific
    data like orders, balances, and positions.
    """
    
    def __init__(self, web_utils: Trading212WebUtils):
        """
        Initialize Trading212 user stream data source.
        
        Args:
            web_utils: Trading212 web utilities
        """
        super().__init__()
        self._web_utils = web_utils
        self._logger = logging.getLogger(__name__)
        self._polling_task: Optional[asyncio.Task] = None
        self._stop_polling = False
        self._last_orders: Dict[str, Any] = {}
        self._last_balances: Dict[str, Any] = {}
        self._last_positions: Dict[str, Any] = {}
        
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
        """Main polling loop for user data updates."""
        while not self._stop_polling:
            try:
                await self._update_orders()
                await self._update_balances()
                await self._update_positions()
                await asyncio.sleep(POLLING_INTERVALS["ORDER_STATUS"])
            except Exception as e:
                self._logger.error(f"Error in user stream polling loop: {e}")
                await asyncio.sleep(POLLING_INTERVALS["ORDER_STATUS"])
                
    async def _update_orders(self):
        """Update orders data."""
        try:
            response = await self._web_utils.get("/api/v0/equity/orders")
            
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list):
                    current_orders = {str(order.get("id", "")): order for order in data}
                
                # Check for new or updated orders
                for order_id, order_data in current_orders.items():
                    if order_id not in self._last_orders or self._last_orders[order_id] != order_data:
                        self._last_orders[order_id] = order_data
                        await self._emit_order_update(order_data)
                        
                # Check for cancelled orders
                for order_id in list(self._last_orders.keys()):
                    if order_id not in current_orders:
                        del self._last_orders[order_id]
                        await self._emit_order_cancellation(order_id)
                        
        except Exception as e:
            self._logger.error(f"Error updating orders: {e}")
            
    async def _update_balances(self):
        """Update balances data."""
        try:
            response = await self._web_utils.get("/api/v0/equity/account/cash")
            
            if response.status == 200:
                data = await response.json()
                if isinstance(data, dict):
                    current_balances = data
                
                # Check for balance changes
                if self._last_balances != current_balances:
                    self._last_balances = current_balances
                    await self._emit_balance_update(current_balances)
                    
        except Exception as e:
            self._logger.error(f"Error updating balances: {e}")
            
    async def _update_positions(self):
        """Update positions data."""
        try:
            response = await self._web_utils.get("/api/v0/equity/portfolio")
            
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list):
                    current_positions = {pos.get("ticker", ""): pos for pos in data}
                
                # Check for position changes
                for ticker, position_data in current_positions.items():
                    if ticker not in self._last_positions or self._last_positions[ticker] != position_data:
                        self._last_positions[ticker] = position_data
                        await self._emit_position_update(position_data)
                        
                # Check for closed positions
                for ticker in list(self._last_positions.keys()):
                    if ticker not in current_positions:
                        del self._last_positions[ticker]
                        await self._emit_position_close(ticker)
                        
        except Exception as e:
            self._logger.error(f"Error updating positions: {e}")
            
    async def _emit_order_update(self, order_data: Dict[str, Any]):
        """
        Emit order update event.
        
        Args:
            order_data: Order data from Trading212
        """
        try:
            parsed_order = Trading212Utils.parse_order_data(order_data)
            if parsed_order:
                # Create order book message for order update
                order_message = OrderBookMessage(
                    message_type=OrderBookMessageType.DIFF,
                    content={
                        "order_id": parsed_order["id"],
                        "trading_pair": parsed_order["trading_pair"],
                        "order_type": parsed_order["order_type"],
                        "trade_type": parsed_order["trade_type"],
                        "amount": parsed_order["amount"],
                        "price": parsed_order["price"],
                        "status": parsed_order["status"],
                        "timestamp": parsed_order["timestamp"],
                    },
                    timestamp=parsed_order["timestamp"]
                )
                
                # Emit to user stream tracker
                if hasattr(self, '_user_stream_tracker'):
                    await self._user_stream_tracker._emit_order_update(order_message)
                    
        except Exception as e:
            self._logger.error(f"Error emitting order update: {e}")
            
    async def _emit_order_cancellation(self, order_id: str):
        """
        Emit order cancellation event.
        
        Args:
            order_id: Cancelled order ID
        """
        try:
            # Create order book message for order cancellation
            order_message = OrderBookMessage(
                message_type=OrderBookMessageType.DIFF,
                content={
                    "order_id": order_id,
                    "status": "CANCELLED",
                    "timestamp": asyncio.get_event_loop().time(),
                },
                timestamp=asyncio.get_event_loop().time()
            )
            
            # Emit to user stream tracker
            if hasattr(self, '_user_stream_tracker'):
                await self._user_stream_tracker._emit_order_cancellation(order_message)
                
        except Exception as e:
            self._logger.error(f"Error emitting order cancellation: {e}")
            
    async def _emit_balance_update(self, balance_data: Dict[str, Any]):
        """
        Emit balance update event.
        
        Args:
            balance_data: Balance data from Trading212
        """
        try:
            parsed_balance = Trading212Utils.parse_balance_data(balance_data)
            if parsed_balance:
                # Create balance object
                balance = Balance(
                    asset="USD",  # Default currency
                    total=Decimal(str(parsed_balance["total"])),
                    available=Decimal(str(parsed_balance["free"])),
                    frozen=Decimal(str(parsed_balance["blocked"])),
                )
                
                # Emit to user stream tracker
                if hasattr(self, '_user_stream_tracker'):
                    await self._user_stream_tracker._emit_balance_update(balance)
                    
        except Exception as e:
            self._logger.error(f"Error emitting balance update: {e}")
            
    async def _emit_position_update(self, position_data: Dict[str, Any]):
        """
        Emit position update event.
        
        Args:
            position_data: Position data from Trading212
        """
        try:
            parsed_position = Trading212Utils.parse_position_data(position_data)
            if parsed_position:
                # Create position object
                position = Position(
                    trading_pair=parsed_position["trading_pair"],
                    position_side=PositionSide.LONG if parsed_position["amount"] > 0 else PositionSide.SHORT,
                    amount=Decimal(str(abs(parsed_position["amount"]))),
                    entry_price=Decimal(str(parsed_position["average_price"])),
                    unrealized_pnl=Decimal(str(parsed_position["unrealized_pnl"])),
                )
                
                # Emit to user stream tracker
                if hasattr(self, '_user_stream_tracker'):
                    await self._user_stream_tracker._emit_position_update(position)
                    
        except Exception as e:
            self._logger.error(f"Error emitting position update: {e}")
            
    async def _emit_position_close(self, ticker: str):
        """
        Emit position close event.
        
        Args:
            ticker: Closed position ticker
        """
        try:
            trading_pair = Trading212Utils.convert_trading212_ticker_to_hummingbot(ticker)
            
            # Create position close message
            position_message = OrderBookMessage(
                message_type=OrderBookMessageType.DIFF,
                content={
                    "trading_pair": trading_pair,
                    "status": "CLOSED",
                    "timestamp": asyncio.get_event_loop().time(),
                },
                timestamp=asyncio.get_event_loop().time()
            )
            
            # Emit to user stream tracker
            if hasattr(self, '_user_stream_tracker'):
                await self._user_stream_tracker._emit_position_close(position_message)
                
        except Exception as e:
            self._logger.error(f"Error emitting position close: {e}")
            
    async def listen_for_user_stream(self, output: asyncio.Queue):
        """
        Listen for user stream updates.
        
        Args:
            ev_loop: Event loop
            output: Output queue for user stream messages
        """
        self._output_queue = output
        self._stop_polling = False
        # Per-endpoint scheduling to respect POLLING_INTERVALS
        import time
        last_orders = last_bal = last_pos = 0.0
        while not self._stop_polling:
            now = time.monotonic()
            try:
                if now - last_orders >= POLLING_INTERVALS["ORDER_STATUS"]:
                    await self._update_orders()
                    last_orders = now
                if now - last_bal >= POLLING_INTERVALS["BALANCE_UPDATE"]:
                    await self._update_balances()
                    last_bal = now
                if now - last_pos >= POLLING_INTERVALS["PORTFOLIO_UPDATE"]:
                    await self._update_positions()
                    last_pos = now
            except asyncio.CancelledError:
                raise
            except Exception:
                self._logger.exception("Error in user stream polling loop")
            await asyncio.sleep(0.2)
    def get_last_orders(self) -> Dict[str, Any]:
        """
        Get last known orders.
        
        Returns:
            Dictionary of last known orders
        """
        return self._last_orders.copy()
        
    def get_last_balances(self) -> Dict[str, Any]:
        """
        Get last known balances.
        
        Returns:
            Dictionary of last known balances
        """
        return self._last_balances.copy()
        
    def get_last_positions(self) -> Dict[str, Any]:
        """
        Get last known positions.
        
        Returns:
            Dictionary of last known positions
        """
        return self._last_positions.copy()
        
    def set_user_stream_tracker(self, user_stream_tracker: UserStreamTracker):
        """
        Set the user stream tracker reference.
        
        Args:
            user_stream_tracker: User stream tracker instance
        """
        self._user_stream_tracker = user_stream_tracker