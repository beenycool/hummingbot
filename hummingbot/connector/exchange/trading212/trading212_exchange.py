"""
Trading212 Exchange Connector

This module implements the main Trading212 exchange connector for Hummingbot,
providing integration with Trading212's equity trading API.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from hummingbot.connector.exchange.ExchangeBase import ExchangeBase
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import OrderState
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.trade import Trade
from hummingbot.core.data_type.balance import Balance
from hummingbot.core.data_type.position import Position
from hummingbot.core.data_type.order import Order
from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.event.events import (
    OrderFilledEvent, OrderCancelledEvent, OrderExpiredEvent,
    BuyOrderCreatedEvent, SellOrderCreatedEvent, MarketOrderFailureEvent
)
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.connector.exchange.trading212.trading212_auth import Trading212Auth
from hummingbot.connector.exchange.trading212.trading212_web_utils import Trading212WebUtils
from hummingbot.connector.exchange.trading212.trading212_utils import Trading212Utils
from hummingbot.connector.exchange.trading212.trading212_constants import (
    EXCHANGE_NAME, REST_URL, ENDPOINTS, DEFAULT_FEES, ORDER_STATUS_MAP,
    ORDER_TYPES, TIME_VALIDITY_OPTIONS, POLLING_INTERVALS
)


class Trading212APIException(Exception):
    """Trading212 API exception."""
    pass


class AuthenticationError(Trading212APIException):
    """Authentication error."""
    pass


class RateLimitExceeded(Trading212APIException):
    """Rate limit exceeded error."""
    pass


class OrderNotFound(Trading212APIException):
    """Order not found error."""
    pass


class MarketNotReady(Trading212APIException):
    """Market not ready error."""
    pass


class Trading212Exchange(ExchangeBase):
    """
    Trading212 exchange connector for Hummingbot.
    
    This class provides integration with Trading212's equity trading API,
    enabling live trading through Hummingbot's strategy framework.
    """
    
    def __init__(self, trading_pairs: List[str], trading_required: bool = True):
        """
        Initialize Trading212 exchange connector.
        
        Args:
            trading_pairs: List of trading pairs to support
            trading_required: Whether trading is required
        """
        super().__init__()
        self._trading_pairs = trading_pairs
        self._trading_required = trading_required
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._auth: Optional[Trading212Auth] = None
        self._web_utils: Optional[Trading212WebUtils] = None
        self._utils = Trading212Utils()
        
        # State tracking
        self._orders: Dict[str, Order] = {}
        self._balances: Dict[str, Balance] = {}
        self._positions: Dict[str, Position] = {}
        self._trading_rules: Dict[str, Dict[str, Any]] = {}
        
        # Polling tasks
        self._polling_task: Optional[asyncio.Task] = None
        self._stop_polling = False
        
    async def initialize(self):
        """Initialize the exchange connector."""
        try:
            # Initialize authentication
            api_key = self._get_api_key()
            if not api_key:
                raise AuthenticationError("API key not configured")
                
            self._auth = Trading212Auth(api_key)
            self._web_utils = Trading212WebUtils(self._auth)
            
            # Initialize web utilities
            await self._web_utils.initialize()
            
            # Validate API key
            if not await self._web_utils.health_check():
                raise AuthenticationError("API key validation failed")
                
            # Load trading rules
            await self._load_trading_rules()
            
            # Start polling
            await self._start_polling()
            
            self._logger.info("Trading212 exchange connector initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Error initializing Trading212 exchange: {e}")
            raise
            
    async def stop(self):
        """Stop the exchange connector."""
        try:
            self._stop_polling = True
            
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                    
            if self._web_utils:
                await self._web_utils.close()
                
            self._logger.info("Trading212 exchange connector stopped")
            
        except Exception as e:
            self._logger.error(f"Error stopping Trading212 exchange: {e}")
            
    def _get_api_key(self) -> Optional[str]:
        """Get API key from configuration."""
        # This would typically get the API key from Hummingbot's configuration
        # For now, we'll return None and expect it to be set externally
        return getattr(self, '_api_key', None)
        
    def set_api_key(self, api_key: str):
        """Set API key."""
        self._api_key = api_key
        
    async def _load_trading_rules(self):
        """Load trading rules from Trading212 API."""
        try:
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['instruments']}")
            
            if response.status == 200 and isinstance(response.data, list):
                for instrument in response.data:
                    ticker = instrument.get("ticker", "")
                    trading_pair = self._utils.convert_trading212_ticker_to_hummingbot(ticker)
                    
                    if trading_pair in self._trading_pairs:
                        self._trading_rules[trading_pair] = {
                            "min_trade_quantity": Decimal(str(instrument.get("minTradeQuantity", 0))),
                            "max_open_quantity": Decimal(str(instrument.get("maxOpenQuantity", 0))),
                            "currency": instrument.get("currencyCode", "USD"),
                            "working_schedule_id": instrument.get("workingScheduleId", 0),
                        }
                        
        except Exception as e:
            self._logger.error(f"Error loading trading rules: {e}")
            
    async def _start_polling(self):
        """Start polling for updates."""
        if self._polling_task is None or self._polling_task.done():
            self._stop_polling = False
            self._polling_task = asyncio.create_task(self._polling_loop())
            
    async def _polling_loop(self):
        """Main polling loop."""
        while not self._stop_polling:
            try:
                await self._update_orders()
                await self._update_balances()
                await self._update_positions()
                await asyncio.sleep(POLLING_INTERVALS["ORDER_STATUS"])
            except Exception as e:
                self._logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(POLLING_INTERVALS["ORDER_STATUS"])
                
    async def _update_orders(self):
        """Update orders from API."""
        try:
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['orders']}")
            
        if response.status == 200 and isinstance(response.data, list):
            for order_data in response.data:
                order_id = str(order_data.get("id", ""))
                parsed_order = self._utils.parse_order_data(order_data)
                
                if parsed_order:
                    # Coerce enums safely
                    ot = parsed_order["order_type"]
                    if not isinstance(ot, OrderType):
                        ot = OrderType[ot] if isinstance(ot, str) and ot in OrderType.__members__ else OrderType.LIMIT
                    tt = parsed_order["trade_type"]
                    if not isinstance(tt, TradeType):
                        tt = TradeType[tt] if isinstance(tt, str) and tt in TradeType.__members__ else TradeType.BUY
                    st = parsed_order["status"]
                    state_map = ORDER_STATUS_MAP.get(st, None)
                    if isinstance(state_map, OrderState):
                        os_ = state_map
                    elif isinstance(state_map, str) and state_map in OrderState.__members__:
                        os_ = OrderState[state_map]
                    elif isinstance(state_map, int):
                        os_ = OrderState(state_map)
                    else:
                        os_ = OrderState.FAILED

                    order = Order(
                        client_order_id=order_id,
                        trading_pair=parsed_order["trading_pair"],
                        order_type=ot,
                        trade_type=tt,
                        amount=Decimal(str(parsed_order["amount"])),
                        price=Decimal(str(parsed_order["price"])),
                        status=os_,
                        timestamp=parsed_order["timestamp"],
                    )
                    
                    self._orders[order_id] = order
                        
        except Exception as e:
            self._logger.error(f"Error updating orders: {e}")
            
    async def _update_balances(self):
        """Update balances from API."""
        try:
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['account_cash']}")
            
            if response.status == 200 and isinstance(response.data, dict):
                parsed_balance = self._utils.parse_balance_data(response.data)
                
                if parsed_balance:
                    balance = Balance(
                        asset="USD",  # Default currency
                        total=Decimal(str(parsed_balance["total"])),
                        available=Decimal(str(parsed_balance["free"])),
                        frozen=Decimal(str(parsed_balance["blocked"])),
                    )
                    
                    self._balances["USD"] = balance
                    
        except Exception as e:
            self._logger.error(f"Error updating balances: {e}")
            
    async def _update_positions(self):
        """Update positions from API."""
        try:
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['portfolio']}")
            
            if response.status == 200 and isinstance(response.data, list):
                for position_data in response.data:
                    parsed_position = self._utils.parse_position_data(position_data)
                    
                    if parsed_position:
                        position = Position(
                            trading_pair=parsed_position["trading_pair"],
                            position_side="LONG" if parsed_position["amount"] > 0 else "SHORT",
                            amount=Decimal(str(abs(parsed_position["amount"]))),
                            entry_price=Decimal(str(parsed_position["average_price"])),
                            unrealized_pnl=Decimal(str(parsed_position["unrealized_pnl"])),
                        )
                        
                        self._positions[parsed_position["trading_pair"]] = position
                        
        except Exception as e:
            self._logger.error(f"Error updating positions: {e}")
            
    # ExchangeBase required methods
    @property
    def name(self) -> str:
        """Exchange name."""
        return EXCHANGE_NAME
        
    @property
    def trading_pairs(self) -> List[str]:
        """Supported trading pairs."""
        return self._trading_pairs
        
    @property
    def trading_required(self) -> bool:
        """Whether trading is required."""
        return self._trading_required
        
    @property
    def trading_rules(self) -> Dict[str, Dict[str, Any]]:
        """Trading rules for each pair."""
        return self._trading_rules
        
    @property
    def balances(self) -> Dict[str, Balance]:
        """Account balances."""
        return self._balances.copy()
        
    @property
    def orders(self) -> Dict[str, Order]:
        """Active orders."""
        return self._orders.copy()
        
    @property
    def positions(self) -> Dict[str, Position]:
        """Open positions."""
        return self._positions.copy()
        
    def supported_order_types(self) -> List[OrderType]:
        """Supported order types."""
        types = [OrderType.MARKET, OrderType.LIMIT]
        if hasattr(OrderType, "STOP"):
            types.append(OrderType.STOP)
        if hasattr(OrderType, "STOP_LIMIT"):
            types.append(OrderType.STOP_LIMIT)
        return types
    def get_order_book(self, trading_pair: str) -> Optional[OrderBook]:
        """Get order book for trading pair."""
        # Trading212 doesn't provide order book data
        return None
        
    def get_last_traded_price(self, trading_pair: str) -> Optional[Decimal]:
        """Get last traded price for trading pair."""
        position = self._positions.get(trading_pair)
        if position:
            return position.entry_price
        return None
        
    def get_trading_fees(self) -> TradeFeeBase:
        """Get trading fees."""
        return DEFAULT_FEES
        
    def get_balance(self, asset: str) -> Optional[Balance]:
        """Get balance for asset."""
        return self._balances.get(asset)
        
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)
        
    def get_position(self, trading_pair: str) -> Optional[Position]:
        """Get position for trading pair."""
        return self._positions.get(trading_pair)
        
    def is_market_open(self, trading_pair: str) -> bool:
        """Check if market is open for trading pair."""
        # This would need to be implemented based on working schedules
        return True
        
    def validate_trading_pair(self, trading_pair: str) -> bool:
        """Validate trading pair."""
        return trading_pair in self._trading_pairs
        
    def validate_order_type(self, order_type: OrderType) -> bool:
        """Validate order type."""
        return order_type in self.supported_order_types()
        
    def validate_trade_type(self, trade_type: TradeType) -> bool:
        """Validate trade type."""
        return trade_type in [TradeType.BUY, TradeType.SELL]
        
    def validate_amount(self, trading_pair: str, amount: Decimal) -> bool:
        """Validate order amount."""
        if trading_pair not in self._trading_rules:
            return False
            
        rules = self._trading_rules[trading_pair]
        return rules["min_trade_quantity"] <= amount <= rules["max_open_quantity"]
        
    def validate_price(self, trading_pair: str, price: Decimal) -> bool:
        """Validate order price."""
        return price > 0
        
    def calculate_order_value(self, trading_pair: str, amount: Decimal, price: Decimal) -> Decimal:
        """Calculate order value."""
        return amount * price
        
    def calculate_fees(self, trading_pair: str, amount: Decimal, price: Decimal) -> Decimal:
        """Calculate trading fees."""
        return Decimal("0")  # Trading212 is zero commission
        
    def get_order_status(self, order_id: str) -> Optional[OrderState]:
        """Get order status."""
        order = self._orders.get(order_id)
        return order.status if order else None
        
    def get_order_fills(self, order_id: str) -> List[Trade]:
        """Get order fills."""
        # This would need to be implemented based on historical order data
        return []
        
    def get_trade_history(self, trading_pair: str, limit: int = 100) -> List[Trade]:
        """Get trade history."""
        # This would need to be implemented based on historical order data
        return []
        
    def get_account_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get account history."""
        # This would need to be implemented based on historical transaction data
        return []
        
    def get_market_status(self) -> Dict[str, Any]:
        """Get market status."""
        return {
            "exchange": self.name,
            "trading_pairs": self._trading_pairs,
            "trading_rules": self._trading_rules,
            "balances": {k: v.to_dict() for k, v in self._balances.items()},
            "orders": {k: v.to_dict() for k, v in self._orders.items()},
            "positions": {k: v.to_dict() for k, v in self._positions.items()},
        }
        
    def get_connector_status(self) -> Dict[str, Any]:
        """Get connector status."""
        return {
            "exchange": self.name,
            "status": "connected" if self._web_utils else "disconnected",
            "trading_pairs": self._trading_pairs,
            "trading_rules_loaded": len(self._trading_rules) > 0,
            "balances_loaded": len(self._balances) > 0,
            "orders_loaded": len(self._orders) > 0,
            "positions_loaded": len(self._positions) > 0,
        }
        
    # Order Management Methods
    async def _place_order(
        self,
        trading_pair: str,
        order_type: OrderType,
        trade_type: TradeType,
        amount: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_validity: str = "DAY"
    ) -> str:
        """
        Place an order on Trading212.
        
        Args:
            trading_pair: Trading pair
            order_type: Order type
            trade_type: Trade type
            amount: Order amount
            price: Order price (for limit orders)
            stop_price: Stop price (for stop orders)
            time_validity: Time validity
            
        Returns:
            Order ID
        """
        try:
            # Validate inputs
            if not self.validate_trading_pair(trading_pair):
                raise ValueError(f"Invalid trading pair: {trading_pair}")
                
            if not self.validate_order_type(order_type):
                raise ValueError(f"Invalid order type: {order_type}")
                
            if not self.validate_trade_type(trade_type):
                raise ValueError(f"Invalid trade type: {trade_type}")
                
            if not self.validate_amount(trading_pair, amount):
                rules = self._trading_rules.get(trading_pair, {})
                raise ValueError(f"Invalid amount: {amount}. Min: {rules.get('min_trade_quantity', 0)}, Max: {rules.get('max_open_quantity', 0)}")
                
            if price and not self.validate_price(trading_pair, price):
                raise ValueError(f"Invalid price: {price}")
                
            # Format order request
            order_request = self._utils.format_order_request(
                trading_pair=trading_pair,
                order_type=order_type,
                trade_type=trade_type,
                amount=amount,
                price=price,
                stop_price=stop_price,
                time_validity=time_validity
            )
            
            # Determine endpoint based on order type
            if order_type == OrderType.MARKET:
                endpoint = f"{REST_URL}{ENDPOINTS['order_market']}"
            elif order_type == OrderType.LIMIT:
                endpoint = f"{REST_URL}{ENDPOINTS['order_limit']}"
            elif hasattr(OrderType, "STOP") and order_type == OrderType.STOP:
                endpoint = f"{REST_URL}{ENDPOINTS['order_stop']}"
            elif hasattr(OrderType, "STOP_LIMIT") and order_type == OrderType.STOP_LIMIT:
                endpoint = f"{REST_URL}{ENDPOINTS['order_stop_limit']}"
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
                raise ValueError(f"Unsupported order type: {order_type}")
                
            # Place order
            response = await self._web_utils.post(endpoint, json_data=order_request)
            
            if response.status == 200 and isinstance(response.data, dict):
                order_id = str(response.data.get("id", ""))
                
                # Create order object
                order = Order(
                    client_order_id=order_id,
                    trading_pair=trading_pair,
                    order_type=order_type,
                    trade_type=trade_type,
                    amount=amount,
                    price=price or Decimal("0"),
                    status=OrderState.PENDING_CREATE,
                    timestamp=asyncio.get_event_loop().time(),
                )
                
                self._orders[order_id] = order
                
                # Emit order created event
                if trade_type == TradeType.BUY:
                    self.trigger_event(BuyOrderCreatedEvent(
                        order_id=order_id,
                        trading_pair=trading_pair,
                        order_type=order_type,
                        amount=amount,
                        price=price or Decimal("0"),
                        timestamp=order.timestamp
                    ))
                else:
                    self.trigger_event(SellOrderCreatedEvent(
                        order_id=order_id,
                        trading_pair=trading_pair,
                        order_type=order_type,
                        amount=amount,
                        price=price or Decimal("0"),
                        timestamp=order.timestamp
                    ))
                
                return order_id
            else:
                raise Trading212APIException(f"Failed to place order: {response.data}")
                
        except Exception as e:
            self._logger.error(f"Error placing order: {e}")
            raise
            
    async def _place_cancel(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if order_id not in self._orders:
                raise OrderNotFound(f"Order not found: {order_id}")
                
            endpoint = f"{REST_URL}{ENDPOINTS['order_by_id'].format(id=order_id)}"
            response = await self._web_utils.delete(endpoint)
            
            if response.status == 200:
                # Update order status
                if order_id in self._orders:
                    self._orders[order_id].status = OrderState.CANCELLED
                    
                # Emit order cancelled event
                self.trigger_event(OrderCancelledEvent(
                    order_id=order_id,
                    timestamp=asyncio.get_event_loop().time()
                ))
                
                return True
            else:
                raise Trading212APIException(f"Failed to cancel order: {response.data}")
                
        except Exception as e:
            self._logger.error(f"Error cancelling order: {e}")
            raise
            
    async def _request_order_status(self, order_id: str) -> Optional[OrderState]:
        """
        Request order status from API.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order state or None if not found
        """
        try:
            endpoint = f"{REST_URL}{ENDPOINTS['order_by_id'].format(id=order_id)}"
            response = await self._web_utils.get(endpoint)
            
            if response.status == 200 and isinstance(response.data, dict):
                order_data = response.data
                status = order_data.get("status", "")
                
                # Convert Trading212 status to Hummingbot order state
                mapped = ORDER_STATUS_MAP.get(status)
                if isinstance(mapped, OrderState):
                    order_state = mapped
                elif isinstance(mapped, str) and mapped in OrderState.__members__:
                    order_state = OrderState[mapped]
                elif isinstance(mapped, int):
                    order_state = OrderState(mapped)
                else:
                    order_state = OrderState.FAILED
                
                # Update local order if exists
                if order_id in self._orders:
                    self._orders[order_id].status = order_state
                    
                return order_state
            else:
                return None
                
        except Exception as e:
            self._logger.error(f"Error requesting order status: {e}")
            return None
            
    async def _status_polling_loop_fetch_updates(self) -> List[Dict[str, Any]]:
        """
        Fetch updates from status polling loop.
        
        Returns:
            List of updates
        """
        updates = []
        
        try:
            # Get all orders
            response = await self._web_utils.get(f"{REST_URL}{ENDPOINTS['orders']}")
            
            if response.status == 200 and isinstance(response.data, list):
                for order_data in response.data:
                    order_id = str(order_data.get("id", ""))
                    status = order_data.get("status", "")
                    filled_quantity = float(order_data.get("filledQuantity", 0))
                    filled_value = float(order_data.get("filledValue", 0))
                    
                    # Check for fills
                    if order_id in self._orders:
                        local_order = self._orders[order_id]
                        
                        if filled_quantity > 0 and local_order.status != OrderState.FILLED:
                            # Order was filled
                            local_order.status = OrderState.FILLED
                            
                            # Emit order filled event
                            self.trigger_event(OrderFilledEvent(
                                order_id=order_id,
                                trading_pair=local_order.trading_pair,
                                trade_type=local_order.trade_type,
                                order_type=local_order.order_type,
                                amount=Decimal(str(filled_quantity)),
                                price=Decimal(str(filled_value / filled_quantity)) if filled_quantity > 0 else local_order.price,
                                trade_fee=DEFAULT_FEES,
                                timestamp=asyncio.get_event_loop().time()
                            ))
                            
                            updates.append({
                                "type": "order_filled",
                                "order_id": order_id,
                                "filled_quantity": filled_quantity,
                                "filled_value": filled_value
                            })
                            
                        elif status == "CANCELLED" and local_order.status != OrderState.CANCELLED:
                            # Order was cancelled
                            local_order.status = OrderState.CANCELLED
                            
                            # Emit order cancelled event
                            self.trigger_event(OrderCancelledEvent(
                                order_id=order_id,
                                timestamp=asyncio.get_event_loop().time()
                            ))
                            
                            updates.append({
                                "type": "order_cancelled",
                                "order_id": order_id
                            })
                            
                        elif status == "REJECTED" and local_order.status != OrderState.FAILED:
                            # Order was rejected
                            local_order.status = OrderState.FAILED
                            
                            # Emit order failure event
                            self.trigger_event(MarketOrderFailureEvent(
                                order_id=order_id,
                                timestamp=asyncio.get_event_loop().time()
                            ))
                            
                            updates.append({
                                "type": "order_rejected",
                                "order_id": order_id
                            })
                            
        except Exception as e:
            self._logger.error(f"Error fetching updates: {e}")
            
        return updates