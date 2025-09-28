"""
Integration tests for Trading212 connector.

This module contains integration tests that test the connector
against the actual Trading212 API (using practice/demo accounts).
"""

import asyncio
import unittest
from decimal import Decimal
from typing import Dict, Any

from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange
from hummingbot.connector.exchange.trading212.trading212_constants import EXCHANGE_NAME


class TestTrading212Integration(unittest.TestCase):
    """Integration tests for Trading212 connector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.trading_pairs = ["AAPL-USD", "MSFT-USD"]
        self.exchange = Trading212Exchange(self.trading_pairs)
        
        # Note: In a real integration test, you would need to provide
        # actual API credentials for a practice account
        self.api_key = "YOUR_PRACTICE_API_KEY_HERE"
        
    @unittest.skip("Requires actual API key")
    async def test_api_connection(self):
        """Test API connection."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            self.assertTrue(True, "API connection successful")
        except Exception as e:
            self.fail(f"API connection failed: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_trading_rules(self):
        """Test getting trading rules."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            trading_rules = self.exchange.trading_rules
            self.assertGreater(len(trading_rules), 0)
            
            # Check that trading rules have required fields
            for pair, rules in trading_rules.items():
                self.assertIn("min_trade_quantity", rules)
                self.assertIn("max_open_quantity", rules)
                self.assertIn("currency", rules)
                
        except Exception as e:
            self.fail(f"Failed to get trading rules: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_balances(self):
        """Test getting account balances."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            balances = self.exchange.balances
            self.assertIsInstance(balances, dict)
            
            # Check that balances have required fields
            for asset, balance in balances.items():
                self.assertIsNotNone(balance.total)
                self.assertIsNotNone(balance.available)
                self.assertIsNotNone(balance.frozen)
                
        except Exception as e:
            self.fail(f"Failed to get balances: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_positions(self):
        """Test getting open positions."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            positions = self.exchange.positions
            self.assertIsInstance(positions, dict)
            
            # Check that positions have required fields
            for pair, position in positions.items():
                self.assertIsNotNone(position.amount)
                self.assertIsNotNone(position.entry_price)
                self.assertIsNotNone(position.unrealized_pnl)
                
        except Exception as e:
            self.fail(f"Failed to get positions: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_place_market_order(self):
        """Test placing a market order."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Place a small market order
            order_id = await self.exchange._place_order(
                trading_pair="AAPL-USD",
                order_type=OrderType.MARKET,
                trade_type=TradeType.BUY,
                amount=Decimal("0.001")  # Very small amount for testing
            )
            
            self.assertIsNotNone(order_id)
            self.assertIn(order_id, self.exchange.orders)
            
        except Exception as e:
            self.fail(f"Failed to place market order: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_place_limit_order(self):
        """Test placing a limit order."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Place a small limit order
            order_id = await self.exchange._place_order(
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=Decimal("0.001"),  # Very small amount for testing
                price=Decimal("100.0")    # Low price to avoid execution
            )
            
            self.assertIsNotNone(order_id)
            self.assertIn(order_id, self.exchange.orders)
            
        except Exception as e:
            self.fail(f"Failed to place limit order: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_cancel_order(self):
        """Test cancelling an order."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Place a small limit order
            order_id = await self.exchange._place_order(
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=Decimal("0.001"),  # Very small amount for testing
                price=Decimal("100.0")    # Low price to avoid execution
            )
            
            # Cancel the order
            result = await self.exchange._place_cancel(order_id)
            
            self.assertTrue(result)
            
        except Exception as e:
            self.fail(f"Failed to cancel order: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_order_status(self):
        """Test getting order status."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Place a small limit order
            order_id = await self.exchange._place_order(
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=Decimal("0.001"),  # Very small amount for testing
                price=Decimal("100.0")    # Low price to avoid execution
            )
            
            # Get order status
            status = await self.exchange._request_order_status(order_id)
            
            self.assertIsNotNone(status)
            
        except Exception as e:
            self.fail(f"Failed to get order status: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_market_hours(self):
        """Test market hours checking."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Check if market is open
            is_open = self.exchange.is_market_open("AAPL-USD")
            
            self.assertIsInstance(is_open, bool)
            
        except Exception as e:
            self.fail(f"Failed to check market hours: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_last_traded_price(self):
        """Test getting last traded price."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Get last traded price
            price = self.exchange.get_last_traded_price("AAPL-USD")
            
            if price is not None:
                self.assertGreater(price, Decimal("0"))
            
        except Exception as e:
            self.fail(f"Failed to get last traded price: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_market_status(self):
        """Test getting market status."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Get market status
            status = self.exchange.get_market_status()
            
            self.assertIsInstance(status, dict)
            self.assertIn("exchange", status)
            self.assertIn("trading_pairs", status)
            self.assertIn("trading_rules", status)
            self.assertIn("balances", status)
            self.assertIn("orders", status)
            self.assertIn("positions", status)
            
        except Exception as e:
            self.fail(f"Failed to get market status: {e}")
        finally:
            await self.exchange.stop()
            
    @unittest.skip("Requires actual API key")
    async def test_get_connector_status(self):
        """Test getting connector status."""
        self.exchange.set_api_key(self.api_key)
        
        try:
            await self.exchange.initialize()
            
            # Get connector status
            status = self.exchange.get_connector_status()
            
            self.assertIsInstance(status, dict)
            self.assertIn("exchange", status)
            self.assertIn("status", status)
            self.assertIn("trading_pairs", status)
            self.assertIn("trading_rules_loaded", status)
            self.assertIn("balances_loaded", status)
            self.assertIn("orders_loaded", status)
            self.assertIn("positions_loaded", status)
            
        except Exception as e:
            self.fail(f"Failed to get connector status: {e}")
        finally:
            await self.exchange.stop()


if __name__ == "__main__":
    unittest.main()