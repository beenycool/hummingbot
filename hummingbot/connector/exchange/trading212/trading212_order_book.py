"""
Trading212 Order Book

This module implements a minimal order book for Trading212 since they don't
provide real-time order book data. It creates synthetic order book data
based on current prices from portfolio data.
"""

import logging
from typing import Dict, List, Optional
from decimal import Decimal
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.connector.exchange.trading212.trading212_utils import Trading212Utils


class Trading212OrderBook(OrderBook):
    """
    Trading212 order book implementation.
    
    Since Trading212 doesn't provide real-time order book data,
    this class creates synthetic order book data based on current
    prices from portfolio positions.
    """
    
    def __init__(self, trading_pair: str, current_price: Optional[Decimal] = None):
        """
        Initialize Trading212 order book.
        
        Args:
            trading_pair: Trading pair for this order book
            current_price: Current price for the trading pair
        """
        super().__init__()
        self._trading_pair = trading_pair
        self._current_price = current_price or Decimal("0")
        self._logger = logging.getLogger(__name__)
        self._utils = Trading212Utils()
        
        # Initialize with synthetic data
        self._update_synthetic_data()
        
    def _update_synthetic_data(self):
        """Update synthetic order book data."""
        if self._current_price > 0:
            # Create synthetic bid and ask rows
            bid_price = self._current_price * Decimal("0.999")  # Slightly below current price
            ask_price = self._current_price * Decimal("1.001")  # Slightly above current price
            
            self._bids = [OrderBookRow(bid_price, Decimal("1.0"), 1)]
            self._asks = [OrderBookRow(ask_price, Decimal("1.0"), 1)]
        else:
            self._bids = []
            self._asks = []
            
    def update_price(self, new_price: Decimal):
        """
        Update the current price and refresh synthetic data.
        
        Args:
            new_price: New current price
        """
        if new_price != self._current_price:
            self._current_price = new_price
            self._update_synthetic_data()
            
    def get_current_price(self) -> Optional[Decimal]:
        """
        Get the current price.
        
        Returns:
            Current price or None if not available
        """
        return self._current_price if self._current_price > 0 else None
        
    def get_best_bid(self) -> Optional[Decimal]:
        """
        Get the best bid price.
        
        Returns:
            Best bid price or None if not available
        """
        if self._bids:
            return self._bids[0].price
        return None
        
    def get_best_ask(self) -> Optional[Decimal]:
        """
        Get the best ask price.
        
        Returns:
            Best ask price or None if not available
        """
        if self._asks:
            return self._asks[0].price
        return None
        
    def get_spread(self) -> Optional[Decimal]:
        """
        Get the bid-ask spread.
        
        Returns:
            Spread or None if not available
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
        
    def get_mid_price(self) -> Optional[Decimal]:
        """
        Get the mid price (average of best bid and ask).
        
        Returns:
            Mid price or None if not available
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return (best_bid + best_ask) / Decimal("2")
        return None
        
    def get_order_book_snapshot(self) -> Dict[str, any]:
        """
        Get order book snapshot.
        
        Returns:
            Dictionary containing order book data
        """
        return {
            "trading_pair": self._trading_pair,
            "current_price": float(self._current_price),
            "best_bid": float(self.get_best_bid() or 0),
            "best_ask": float(self.get_best_ask() or 0),
            "spread": float(self.get_spread() or 0),
            "mid_price": float(self.get_mid_price() or 0),
            "bids": [{"price": float(row.price), "amount": float(row.amount)} for row in self._bids],
            "asks": [{"price": float(row.price), "amount": float(row.amount)} for row in self._asks],
        }
        
    def create_order_book_message(self, message_type: OrderBookMessageType) -> OrderBookMessage:
        """
        Create order book message.
        
        Args:
            message_type: Type of order book message
            
        Returns:
            Order book message
        """
        import asyncio
        
        return OrderBookMessage(
            message_type=message_type,
            content={
                "trading_pair": self._trading_pair,
                "bids": self._bids,
                "asks": self._asks,
                "timestamp": asyncio.get_event_loop().time(),
            },
            timestamp=asyncio.get_event_loop().time()
        )
        
    def __str__(self) -> str:
        """String representation of the order book."""
        return f"Trading212OrderBook({self._trading_pair}, price={self._current_price})"
        
    def __repr__(self) -> str:
        """Detailed string representation of the order book."""
        return f"Trading212OrderBook(trading_pair='{self._trading_pair}', current_price={self._current_price}, bids={len(self._bids)}, asks={len(self._asks)})"