"""
Trading212 Utility Functions and Helpers

This module provides utility functions for data conversion, validation,
and other helper operations for the Trading212 exchange connector.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.trade import Trade
from hummingbot.core.data_type.order import Order
from hummingbot.core.data_type.balance import Balance
from hummingbot.core.data_type.position import Position
from hummingbot.connector.exchange.trading212.trading212_constants import (
    ORDER_STATUS_MAP, ORDER_TYPES, TIME_VALIDITY_OPTIONS, MIN_TRADE_QUANTITY,
    MAX_TRADE_QUANTITY, PRICE_PRECISION, QUANTITY_PRECISION, MARKET_HOURS_TYPES
)


class Trading212Utils:
    """
    Utility class for Trading212-specific operations.
    
    This class provides methods for data conversion, validation,
    and other helper operations.
    """
    
    def __init__(self):
        """Initialize Trading212 utilities."""
        self._logger = logging.getLogger(__name__)
        
    @staticmethod
    def convert_trading212_ticker_to_hummingbot(ticker: str) -> str:
        """
        Convert Trading212 ticker format to Hummingbot format.
        
        Args:
            ticker: Trading212 ticker (e.g., "AAPL_US_EQ")
            
        Returns:
            Hummingbot trading pair (e.g., "AAPL-USD")
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
            
    @staticmethod
    def convert_hummingbot_ticker_to_trading212(trading_pair: str) -> str:
        """
        Convert Hummingbot trading pair to Trading212 ticker format.
        
        Args:
            trading_pair: Hummingbot trading pair (e.g., "AAPL-USD")
            
        Returns:
            Trading212 ticker (e.g., "AAPL_US_EQ")
        """
        try:
            # Hummingbot format: "AAPL-USD" -> Trading212 format: "AAPL_US_EQ"
            symbol, currency = trading_pair.split("-")
            return f"{symbol}_{currency}_EQ"
        except Exception:
            return trading_pair
            
    @staticmethod
    def convert_order_type_to_trading212(order_type: OrderType) -> str:
        """
        Convert Hummingbot order type to Trading212 order type.
        
        Args:
            order_type: Hummingbot order type
            
        Returns:
            Trading212 order type string
        """
        mapping = {
            OrderType.MARKET: ORDER_TYPES["MARKET"],
            OrderType.LIMIT: ORDER_TYPES["LIMIT"],
            getattr(OrderType, "LIMIT_MAKER", OrderType.LIMIT): ORDER_TYPES["LIMIT"],
        }
        return mapping.get(order_type, ORDER_TYPES.get("LIMIT_MAKER", ORDER_TYPES["LIMIT"]))
        
    @staticmethod
    def convert_trade_type_to_trading212(trade_type: TradeType) -> str:
        """
        Convert Hummingbot trade type to Trading212 side.
        
        Args:
            trade_type: Hummingbot trade type
            
        Returns:
            Trading212 side string ("BUY" or "SELL")
        """
        return "BUY" if trade_type == TradeType.BUY else "SELL"
        
    @staticmethod
    def convert_trading212_order_status(status: str) -> str:
        """
        Convert Trading212 order status to Hummingbot order state.
        
        Args:
            status: Trading212 order status
            
        Returns:
            Hummingbot order state
        """
        return ORDER_STATUS_MAP.get(status, "UNKNOWN")
        
    @staticmethod
    def convert_time_validity_to_trading212(time_validity: str) -> str:
        """
        Convert time validity to Trading212 format.
        
        Args:
            time_validity: Time validity string
            
        Returns:
            Trading212 time validity
        """
        return TIME_VALIDITY_OPTIONS.get(time_validity, TIME_VALIDITY_OPTIONS["DAY"])
        
    @staticmethod
    def parse_trading212_timestamp(timestamp_str: str) -> float:
        """
        Parse Trading212 timestamp string to Unix timestamp.
        
        Args:
            timestamp_str: Trading212 timestamp string
            
        Returns:
            Unix timestamp as float
        """
        try:
            # Trading212 uses ISO 8601 format
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except Exception:
            return 0.0
            
    @staticmethod
    def format_trading212_timestamp(timestamp: float) -> str:
        """
        Format Unix timestamp to Trading212 format.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Trading212 timestamp string
        """
        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception:
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
    @staticmethod
    def validate_quantity(quantity: Decimal) -> bool:
        """
        Validate trade quantity.
        
        Args:
            quantity: Trade quantity
            
        Returns:
            True if valid, False otherwise
        """
        return MIN_TRADE_QUANTITY <= quantity <= MAX_TRADE_QUANTITY
        
    @staticmethod
    def validate_price(price: Decimal) -> bool:
        """
        Validate trade price.
        
        Args:
            price: Trade price
            
        Returns:
            True if valid, False otherwise
        """
        return price > 0
        
    @staticmethod
    def round_price(price: Decimal) -> Decimal:
        """
        Round price to appropriate precision.
        
        Args:
            price: Price to round
            
        Returns:
            Rounded price
        """
        return price.quantize(Decimal('0.01'))
        
    @staticmethod
    def round_quantity(quantity: Decimal) -> Decimal:
        """
        Round quantity to appropriate precision.
        
        Args:
            quantity: Quantity to round
            
        Returns:
            Rounded quantity
        """
        return quantity.quantize(Decimal('0.0001'))
        
    @staticmethod
    def parse_order_data(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Trading212 order data to Hummingbot format.
        
        Args:
            order_data: Raw order data from Trading212
            
        Returns:
            Parsed order data
        """
        try:
            return {
                "id": str(order_data.get("id", "")),
                "trading_pair": Trading212Utils.convert_trading212_ticker_to_hummingbot(
                    order_data.get("ticker", "")
                ),
                "order_type": order_data.get("type", ""),
                "trade_type": "BUY" if order_data.get("quantity", 0) > 0 else "SELL",
                "amount": abs(float(order_data.get("quantity", 0))),
                "price": float(order_data.get("limitPrice", 0)),
                "status": Trading212Utils.convert_trading212_order_status(
                    order_data.get("status", "")
                ),
                "timestamp": Trading212Utils.parse_trading212_timestamp(
                    order_data.get("creationTime", "")
                ),
                "filled_amount": float(order_data.get("filledQuantity", 0)),
                "filled_value": float(order_data.get("filledValue", 0)),
                "stop_price": float(order_data.get("stopPrice", 0)),
                "time_validity": order_data.get("timeValidity", "DAY"),
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"Error parsing order data: {e}")
            return {}
            
    @staticmethod
    def parse_position_data(position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Trading212 position data to Hummingbot format.
        
        Args:
            position_data: Raw position data from Trading212
            
        Returns:
            Parsed position data
        """
        try:
            return {
                "trading_pair": Trading212Utils.convert_trading212_ticker_to_hummingbot(
                    position_data.get("ticker", "")
                ),
                "amount": float(position_data.get("quantity", 0)),
                "average_price": float(position_data.get("averagePrice", 0)),
                "current_price": float(position_data.get("currentPrice", 0)),
                "unrealized_pnl": float(position_data.get("ppl", 0)),
                "fx_unrealized_pnl": float(position_data.get("fxPpl", 0)),
                "max_buy": float(position_data.get("maxBuy", 0)),
                "max_sell": float(position_data.get("maxSell", 0)),
                "pie_quantity": float(position_data.get("pieQuantity", 0)),
                "initial_fill_date": Trading212Utils.parse_trading212_timestamp(
                    position_data.get("initialFillDate", "")
                ),
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"Error parsing position data: {e}")
            return {}
            
    @staticmethod
    def parse_balance_data(balance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Trading212 balance data to Hummingbot format.
        
        Args:
            balance_data: Raw balance data from Trading212
            
        Returns:
            Parsed balance data
        """
        try:
            return {
                "total": float(balance_data.get("total", 0)),
                "free": float(balance_data.get("free", 0)),
                "blocked": float(balance_data.get("blocked", 0)),
                "invested": float(balance_data.get("invested", 0)),
                "pie_cash": float(balance_data.get("pieCash", 0)),
                "ppl": float(balance_data.get("ppl", 0)),
                "result": float(balance_data.get("result", 0)),
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"Error parsing balance data: {e}")
            return {}
            
    @staticmethod
    def parse_instrument_data(instrument_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Trading212 instrument data to Hummingbot format.
        
        Args:
            instrument_data: Raw instrument data from Trading212
            
        Returns:
            Parsed instrument data
        """
        try:
            return {
                "ticker": instrument_data.get("ticker", ""),
                "trading_pair": Trading212Utils.convert_trading212_ticker_to_hummingbot(
                    instrument_data.get("ticker", "")
                ),
                "name": instrument_data.get("name", ""),
                "short_name": instrument_data.get("shortName", ""),
                "currency": instrument_data.get("currencyCode", ""),
                "isin": instrument_data.get("isin", ""),
                "type": instrument_data.get("type", ""),
                "min_trade_quantity": float(instrument_data.get("minTradeQuantity", 0)),
                "max_open_quantity": float(instrument_data.get("maxOpenQuantity", 0)),
                "working_schedule_id": instrument_data.get("workingScheduleId", 0),
                "added_on": Trading212Utils.parse_trading212_timestamp(
                    instrument_data.get("addedOn", "")
                ),
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"Error parsing instrument data: {e}")
            return {}
            
    @staticmethod
    def is_market_open(working_schedules: List[Dict[str, Any]]) -> bool:
        """
        Check if market is currently open based on working schedules.
        
        Args:
            working_schedules: List of working schedules
            
        Returns:
            True if market is open, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)
            
            for schedule in working_schedules:
                time_events = schedule.get("timeEvents", [])
                for event in time_events:
                    event_time = Trading212Utils.parse_trading212_timestamp(event.get("date", ""))
                    event_type = event.get("type", "")
                    
                    if event_type == MARKET_HOURS_TYPES["OPEN"]:
                        # Check if we're past the open time
                        if now.timestamp() >= event_time:
                            return True
                    elif event_type == MARKET_HOURS_TYPES["CLOSE"]:
                        # Check if we're past the close time
                        if now.timestamp() >= event_time:
                            return False
                            
            return False
        except Exception:
            return False
            
    @staticmethod
    def calculate_order_value(quantity: Decimal, price: Decimal) -> Decimal:
        """
        Calculate order value.
        
        Args:
            quantity: Order quantity
            price: Order price
            
        Returns:
            Order value
        """
        return quantity * price
        
    @staticmethod
    def calculate_fees(order_value: Decimal) -> Decimal:
        """
        Calculate trading fees (Trading212 is zero commission).
        
        Args:
            order_value: Order value
            
        Returns:
            Trading fees (always 0 for Trading212)
        """
        return Decimal("0")
        
    @staticmethod
    def format_order_request(
        trading_pair: str,
        order_type: OrderType,
        trade_type: TradeType,
        amount: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_validity: str = "DAY"
    ) -> Dict[str, Any]:
        """
        Format order request for Trading212 API.
        
        Args:
            trading_pair: Trading pair
            order_type: Order type
            trade_type: Trade type
            amount: Order amount
            price: Order price (for limit orders)
            stop_price: Stop price (for stop orders)
            time_validity: Time validity
            
        Returns:
            Formatted order request
        """
        ticker = Trading212Utils.convert_hummingbot_ticker_to_trading212(trading_pair)
        quantity = amount if trade_type == TradeType.BUY else -amount
        
        request_data = {
            "ticker": ticker,
            "quantity": float(quantity),
            "timeValidity": Trading212Utils.convert_time_validity_to_trading212(time_validity),
        }
        
        if order_type == OrderType.LIMIT and price:
            request_data["limitPrice"] = float(price)
        elif hasattr(OrderType, "STOP") and order_type == getattr(OrderType, "STOP") and stop_price:
            request_data["stopPrice"] = float(stop_price)
        elif hasattr(OrderType, "STOP_LIMIT") and order_type == getattr(OrderType, "STOP_LIMIT") and price and stop_price:
            request_data["limitPrice"] = float(price)
            request_data["stopPrice"] = float(stop_price)
            
        return request_data