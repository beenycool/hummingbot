"""
Unit Tests for Trading212 Exchange Connector

This module contains comprehensive unit tests for the Trading212
exchange connector, covering all major functionality.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from typing import Dict, Any, List
import json

from hummingbot.core.data_type.common import OrderType, TradeType, OrderState
from hummingbot.core.data_type.order import Order
from hummingbot.core.data_type.balance import Balance
from hummingbot.core.data_type.position import Position
from hummingbot.core.web_assistant.connections.data_types import RESTResponse

from hummingbot.connector.exchange.trading212.trading212_auth import Trading212Auth
from hummingbot.connector.exchange.trading212.trading212_web_utils import Trading212WebUtils
from hummingbot.connector.exchange.trading212.trading212_utils import Trading212Utils
from hummingbot.connector.exchange.trading212.trading212_exchange import (
    Trading212Exchange, Trading212APIException, AuthenticationError,
    RateLimitExceeded, OrderNotFound, MarketNotReady
)
from hummingbot.connector.exchange.trading212.trading212_constants import (
    ORDER_STATUS_MAP, ORDER_TYPES, TIME_VALIDITY_OPTIONS
)


class TestTrading212Auth(unittest.TestCase):
    """Test cases for Trading212Auth class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key_12345"
        self.auth = Trading212Auth(self.api_key)
        
    def test_init(self):
        """Test authentication initialization."""
        self.assertEqual(self.auth.get_api_key(), self.api_key)
        self.assertTrue(self.auth.validate_api_key())
        
    def test_add_auth_to_headers(self):
        """Test adding authentication headers."""
        from hummingbot.core.web_assistant.connections.data_types import RESTRequest
        
        request = RESTRequest(method="GET", url="/api/v0/equity/orders")
        headers = self.auth.add_auth_to_headers(request)
        
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], f"Bearer {self.api_key}")
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        
    def test_get_required_scope(self):
        """Test getting required scope for different endpoints."""
        from hummingbot.core.web_assistant.connections.data_types import RESTRequest
        
        # Test order execution endpoint
        request = RESTRequest(method="POST", url="/api/v0/equity/orders/market")
        scope = self.auth._get_required_scope(request)
        self.assertEqual(scope, "orders:execute")
        
        # Test order reading endpoint
        request = RESTRequest(method="GET", url="/api/v0/equity/orders")
        scope = self.auth._get_required_scope(request)
        self.assertEqual(scope, "orders:read")
        
        # Test portfolio endpoint
        request = RESTRequest(method="GET", url="/api/v0/equity/portfolio")
        scope = self.auth._get_required_scope(request)
        self.assertEqual(scope, "portfolio")
        
    def test_set_api_key(self):
        """Test setting new API key."""
        new_key = "new_api_key_67890"
        self.auth.set_api_key(new_key)
        self.assertEqual(self.auth.get_api_key(), new_key)


class TestTrading212Utils(unittest.TestCase):
    """Test cases for Trading212Utils class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utils = Trading212Utils()
        
    def test_convert_trading212_ticker_to_hummingbot(self):
        """Test converting Trading212 ticker to Hummingbot format."""
        # Test valid ticker
        result = self.utils.convert_trading212_ticker_to_hummingbot("AAPL_US_EQ")
        self.assertEqual(result, "AAPL-USD")
        
        # Test invalid ticker
        result = self.utils.convert_trading212_ticker_to_hummingbot("INVALID")
        self.assertEqual(result, "INVALID")
        
    def test_convert_hummingbot_ticker_to_trading212(self):
        """Test converting Hummingbot trading pair to Trading212 format."""
        # Test valid trading pair
        result = self.utils.convert_hummingbot_ticker_to_trading212("AAPL-USD")
        self.assertEqual(result, "AAPL_US_EQ")
        
        # Test invalid trading pair
        result = self.utils.convert_hummingbot_ticker_to_trading212("INVALID")
        self.assertEqual(result, "INVALID")
        
    def test_convert_order_type_to_trading212(self):
        """Test converting order types."""
        self.assertEqual(self.utils.convert_order_type_to_trading212(OrderType.MARKET), "MARKET")
        self.assertEqual(self.utils.convert_order_type_to_trading212(OrderType.LIMIT), "LIMIT")
        self.assertEqual(self.utils.convert_order_type_to_trading212(OrderType.STOP), "STOP")
        self.assertEqual(self.utils.convert_order_type_to_trading212(OrderType.STOP_LIMIT), "STOP_LIMIT")
        
    def test_convert_trade_type_to_trading212(self):
        """Test converting trade types."""
        self.assertEqual(self.utils.convert_trade_type_to_trading212(TradeType.BUY), "BUY")
        self.assertEqual(self.utils.convert_trade_type_to_trading212(TradeType.SELL), "SELL")
        
    def test_convert_trading212_order_status(self):
        """Test converting order status."""
        self.assertEqual(self.utils.convert_trading212_order_status("LOCAL"), "PENDING_CREATE")
        self.assertEqual(self.utils.convert_trading212_order_status("WORKING"), "OPEN")
        self.assertEqual(self.utils.convert_trading212_order_status("FILLED"), "FILLED")
        self.assertEqual(self.utils.convert_trading212_order_status("CANCELLED"), "CANCELLED")
        self.assertEqual(self.utils.convert_trading212_order_status("REJECTED"), "FAILED")
        
    def test_validate_quantity(self):
        """Test quantity validation."""
        self.assertTrue(self.utils.validate_quantity(Decimal("1.0")))
        self.assertTrue(self.utils.validate_quantity(Decimal("0.0001")))
        self.assertTrue(self.utils.validate_quantity(Decimal("999999")))
        self.assertFalse(self.utils.validate_quantity(Decimal("0.00001")))
        self.assertFalse(self.utils.validate_quantity(Decimal("1000000")))
        
    def test_validate_price(self):
        """Test price validation."""
        self.assertTrue(self.utils.validate_price(Decimal("100.0")))
        self.assertTrue(self.utils.validate_price(Decimal("0.01")))
        self.assertFalse(self.utils.validate_price(Decimal("0")))
        self.assertFalse(self.utils.validate_price(Decimal("-1")))
        
    def test_round_price(self):
        """Test price rounding."""
        self.assertEqual(self.utils.round_price(Decimal("100.123")), Decimal("100.12"))
        self.assertEqual(self.utils.round_price(Decimal("100.126")), Decimal("100.13"))
        
    def test_round_quantity(self):
        """Test quantity rounding."""
        self.assertEqual(self.utils.round_quantity(Decimal("1.12345")), Decimal("1.1235"))
        self.assertEqual(self.utils.round_quantity(Decimal("1.12344")), Decimal("1.1234"))
        
    def test_parse_order_data(self):
        """Test parsing order data."""
        order_data = {
            "id": 12345,
            "ticker": "AAPL_US_EQ",
            "type": "LIMIT",
            "quantity": 10.0,
            "limitPrice": 150.0,
            "status": "WORKING",
            "creationTime": "2023-01-01T12:00:00Z",
            "filledQuantity": 0.0,
            "filledValue": 0.0,
            "stopPrice": 0.0,
            "timeValidity": "DAY"
        }
        
        parsed = self.utils.parse_order_data(order_data)
        
        self.assertEqual(parsed["id"], "12345")
        self.assertEqual(parsed["trading_pair"], "AAPL-USD")
        self.assertEqual(parsed["order_type"], "LIMIT")
        self.assertEqual(parsed["amount"], 10.0)
        self.assertEqual(parsed["price"], 150.0)
        self.assertEqual(parsed["status"], "OPEN")
        
    def test_parse_position_data(self):
        """Test parsing position data."""
        position_data = {
            "ticker": "AAPL_US_EQ",
            "quantity": 10.0,
            "averagePrice": 150.0,
            "currentPrice": 155.0,
            "ppl": 50.0,
            "fxPpl": 0.0,
            "maxBuy": 100.0,
            "maxSell": 10.0,
            "pieQuantity": 0.0,
            "initialFillDate": "2023-01-01T12:00:00Z"
        }
        
        parsed = self.utils.parse_position_data(position_data)
        
        self.assertEqual(parsed["trading_pair"], "AAPL-USD")
        self.assertEqual(parsed["amount"], 10.0)
        self.assertEqual(parsed["average_price"], 150.0)
        self.assertEqual(parsed["current_price"], 155.0)
        self.assertEqual(parsed["unrealized_pnl"], 50.0)
        
    def test_parse_balance_data(self):
        """Test parsing balance data."""
        balance_data = {
            "total": 10000.0,
            "free": 8000.0,
            "blocked": 2000.0,
            "invested": 5000.0,
            "pieCash": 0.0,
            "ppl": 100.0,
            "result": 100.0
        }
        
        parsed = self.utils.parse_balance_data(balance_data)
        
        self.assertEqual(parsed["total"], 10000.0)
        self.assertEqual(parsed["free"], 8000.0)
        self.assertEqual(parsed["blocked"], 2000.0)
        self.assertEqual(parsed["invested"], 5000.0)
        
    def test_format_order_request(self):
        """Test formatting order request."""
        request = self.utils.format_order_request(
            trading_pair="AAPL-USD",
            order_type=OrderType.LIMIT,
            trade_type=TradeType.BUY,
            amount=Decimal("10.0"),
            price=Decimal("150.0"),
            time_validity="DAY"
        )
        
        self.assertEqual(request["ticker"], "AAPL_US_EQ")
        self.assertEqual(request["quantity"], 10.0)
        self.assertEqual(request["limitPrice"], 150.0)
        self.assertEqual(request["timeValidity"], "DAY")


class TestTrading212WebUtils(unittest.TestCase):
    """Test cases for Trading212WebUtils class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.auth = Trading212Auth("test_api_key")
        self.web_utils = Trading212WebUtils(self.auth)
        
    @patch('aiohttp.ClientSession.request')
    async def test_get_success(self, mock_request):
        """Test successful GET request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test GET request
        response = await self.web_utils.get("https://test.com/api")
        
        self.assertEqual(response.status, 200)
        self.assertEqual(response.data, {"data": "test"})
        
    @patch('aiohttp.ClientSession.request')
    async def test_post_success(self, mock_request):
        """Test successful POST request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": 12345})
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test POST request
        response = await self.web_utils.post("https://test.com/api", json_data={"test": "data"})
        
        self.assertEqual(response.status, 200)
        self.assertEqual(response.data, {"id": 12345})
        
    @patch('aiohttp.ClientSession.request')
    async def test_delete_success(self, mock_request):
        """Test successful DELETE request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test DELETE request
        response = await self.web_utils.delete("https://test.com/api")
        
        self.assertEqual(response.status, 200)
        self.assertEqual(response.data, {})
        
    @patch('aiohttp.ClientSession.request')
    async def test_error_handling_401(self, mock_request):
        """Test error handling for 401 status."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Bad API key")
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test error handling
        with self.assertRaises(AuthenticationError):
            await self.web_utils.get("https://test.com/api")
            
    @patch('aiohttp.ClientSession.request')
    async def test_error_handling_403(self, mock_request):
        """Test error handling for 403 status."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Scope missing for API key")
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test error handling
        with self.assertRaises(AuthenticationError):
            await self.web_utils.get("https://test.com/api")
            
    @patch('aiohttp.ClientSession.request')
    async def test_error_handling_429(self, mock_request):
        """Test error handling for 429 status."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.text = AsyncMock(return_value="Limited")
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://test.com/api"
        
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Test error handling
        with self.assertRaises(RateLimitExceeded):
            await self.web_utils.get("https://test.com/api")


class TestTrading212Exchange(unittest.TestCase):
    """Test cases for Trading212Exchange class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.trading_pairs = ["AAPL-USD", "MSFT-USD"]
        self.exchange = Trading212Exchange(self.trading_pairs)
        
    def test_init(self):
        """Test exchange initialization."""
        self.assertEqual(self.exchange.name, "trading212")
        self.assertEqual(self.exchange.trading_pairs, self.trading_pairs)
        self.assertTrue(self.exchange.trading_required)
        
    def test_supported_order_types(self):
        """Test supported order types."""
        order_types = self.exchange.supported_order_types()
        self.assertIn(OrderType.MARKET, order_types)
        self.assertIn(OrderType.LIMIT, order_types)
        self.assertIn(OrderType.STOP, order_types)
        self.assertIn(OrderType.STOP_LIMIT, order_types)
        
    def test_validate_trading_pair(self):
        """Test trading pair validation."""
        self.assertTrue(self.exchange.validate_trading_pair("AAPL-USD"))
        self.assertFalse(self.exchange.validate_trading_pair("INVALID-PAIR"))
        
    def test_validate_order_type(self):
        """Test order type validation."""
        self.assertTrue(self.exchange.validate_order_type(OrderType.MARKET))
        self.assertTrue(self.exchange.validate_order_type(OrderType.LIMIT))
        self.assertFalse(self.exchange.validate_order_type("INVALID"))
        
    def test_validate_trade_type(self):
        """Test trade type validation."""
        self.assertTrue(self.exchange.validate_trade_type(TradeType.BUY))
        self.assertTrue(self.exchange.validate_trade_type(TradeType.SELL))
        self.assertFalse(self.exchange.validate_trade_type("INVALID"))
        
    def test_validate_price(self):
        """Test price validation."""
        self.assertTrue(self.exchange.validate_price("AAPL-USD", Decimal("100.0")))
        self.assertFalse(self.exchange.validate_price("AAPL-USD", Decimal("0")))
        self.assertFalse(self.exchange.validate_price("AAPL-USD", Decimal("-1")))
        
    def test_calculate_order_value(self):
        """Test order value calculation."""
        value = self.exchange.calculate_order_value("AAPL-USD", Decimal("10.0"), Decimal("150.0"))
        self.assertEqual(value, Decimal("1500.0"))
        
    def test_calculate_fees(self):
        """Test fee calculation."""
        fees = self.exchange.calculate_fees("AAPL-USD", Decimal("10.0"), Decimal("150.0"))
        self.assertEqual(fees, Decimal("0"))  # Trading212 is zero commission
        
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_initialize_success(self, mock_web_utils_class):
        """Test successful initialization."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils.health_check.return_value = True
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set API key
        self.exchange.set_api_key("test_api_key")
        
        # Mock trading rules response
        mock_web_utils.get.return_value = RESTResponse(
            status=200,
            headers={},
            data=[
                {
                    "ticker": "AAPL_US_EQ",
                    "minTradeQuantity": 0.0001,
                    "maxOpenQuantity": 1000000,
                    "currencyCode": "USD",
                    "workingScheduleId": 1
                }
            ],
            url="https://test.com/api"
        )
        
        # Test initialization
        await self.exchange.initialize()
        
        self.assertIsNotNone(self.exchange._auth)
        self.assertIsNotNone(self.exchange._web_utils)
        self.assertIn("AAPL-USD", self.exchange._trading_rules)
        
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_initialize_failure(self, mock_web_utils_class):
        """Test initialization failure."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils.health_check.return_value = False
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set API key
        self.exchange.set_api_key("test_api_key")
        
        # Test initialization failure
        with self.assertRaises(AuthenticationError):
            await self.exchange.initialize()
            
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_place_order_success(self, mock_web_utils_class):
        """Test successful order placement."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils.post.return_value = RESTResponse(
            status=200,
            headers={},
            data={"id": 12345, "status": "LOCAL"},
            url="https://test.com/api"
        )
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set up exchange
        self.exchange._web_utils = mock_web_utils
        self.exchange._trading_rules = {
            "AAPL-USD": {
                "min_trade_quantity": Decimal("0.0001"),
                "max_open_quantity": Decimal("1000000"),
                "currency": "USD"
            }
        }
        
        # Test order placement
        order_id = await self.exchange._place_order(
            trading_pair="AAPL-USD",
            order_type=OrderType.LIMIT,
            trade_type=TradeType.BUY,
            amount=Decimal("10.0"),
            price=Decimal("150.0")
        )
        
        self.assertEqual(order_id, "12345")
        self.assertIn("12345", self.exchange._orders)
        
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_cancel_order_success(self, mock_web_utils_class):
        """Test successful order cancellation."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils.delete.return_value = RESTResponse(
            status=200,
            headers={},
            data={},
            url="https://test.com/api"
        )
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set up exchange
        self.exchange._web_utils = mock_web_utils
        self.exchange._orders = {
            "12345": Order(
                client_order_id="12345",
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=Decimal("10.0"),
                price=Decimal("150.0"),
                status=OrderState.OPEN,
                timestamp=1234567890.0
            )
        }
        
        # Test order cancellation
        result = await self.exchange._place_cancel("12345")
        
        self.assertTrue(result)
        self.assertEqual(self.exchange._orders["12345"].status, OrderState.CANCELLED)
        
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_cancel_order_not_found(self, mock_web_utils_class):
        """Test order cancellation when order not found."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set up exchange
        self.exchange._web_utils = mock_web_utils
        self.exchange._orders = {}
        
        # Test order cancellation failure
        with self.assertRaises(OrderNotFound):
            await self.exchange._place_cancel("12345")
            
    @patch('hummingbot.connector.exchange.trading212.trading212_exchange.Trading212WebUtils')
    async def test_request_order_status_success(self, mock_web_utils_class):
        """Test successful order status request."""
        # Mock web utils
        mock_web_utils = AsyncMock()
        mock_web_utils.get.return_value = RESTResponse(
            status=200,
            headers={},
            data={"id": 12345, "status": "WORKING"},
            url="https://test.com/api"
        )
        mock_web_utils_class.return_value = mock_web_utils
        
        # Set up exchange
        self.exchange._web_utils = mock_web_utils
        self.exchange._orders = {
            "12345": Order(
                client_order_id="12345",
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=Decimal("10.0"),
                price=Decimal("150.0"),
                status=OrderState.PENDING_CREATE,
                timestamp=1234567890.0
            )
        }
        
        # Test order status request
        status = await self.exchange._request_order_status("12345")
        
        self.assertEqual(status, OrderState.OPEN)
        self.assertEqual(self.exchange._orders["12345"].status, OrderState.OPEN)


class TestTrading212Constants(unittest.TestCase):
    """Test cases for Trading212 constants."""
    
    def test_exchange_name(self):
        """Test exchange name constant."""
        from hummingbot.connector.exchange.trading212.trading212_constants import EXCHANGE_NAME
        self.assertEqual(EXCHANGE_NAME, "trading212")
        
    def test_rest_url(self):
        """Test REST URL constant."""
        from hummingbot.connector.exchange.trading212.trading212_constants import REST_URL
        self.assertEqual(REST_URL, "https://live.trading212.com")
        
    def test_endpoints(self):
        """Test endpoints constants."""
        from hummingbot.connector.exchange.trading212.trading212_constants import ENDPOINTS
        
        self.assertIn("account_cash", ENDPOINTS)
        self.assertIn("portfolio", ENDPOINTS)
        self.assertIn("orders", ENDPOINTS)
        self.assertIn("order_market", ENDPOINTS)
        self.assertIn("order_limit", ENDPOINTS)
        self.assertIn("order_stop", ENDPOINTS)
        self.assertIn("order_stop_limit", ENDPOINTS)
        
    def test_rate_limits(self):
        """Test rate limits constants."""
        from hummingbot.connector.exchange.trading212.trading212_constants import RATE_LIMITS
        
        self.assertGreater(len(RATE_LIMITS), 0)
        
        # Check that all rate limits have required fields
        for rate_limit in RATE_LIMITS:
            self.assertIsNotNone(rate_limit.limit_id)
            self.assertGreater(rate_limit.limit, 0)
            self.assertGreater(rate_limit.time_interval, 0)
            
    def test_order_status_map(self):
        """Test order status mapping."""
        from hummingbot.connector.exchange.trading212.trading212_constants import ORDER_STATUS_MAP
        
        self.assertEqual(ORDER_STATUS_MAP["LOCAL"], "PENDING_CREATE")
        self.assertEqual(ORDER_STATUS_MAP["WORKING"], "OPEN")
        self.assertEqual(ORDER_STATUS_MAP["FILLED"], "FILLED")
        self.assertEqual(ORDER_STATUS_MAP["CANCELLED"], "CANCELLED")
        self.assertEqual(ORDER_STATUS_MAP["REJECTED"], "FAILED")
        
    def test_order_types(self):
        """Test order types constants."""
        from hummingbot.connector.exchange.trading212.trading212_constants import ORDER_TYPES
        
        self.assertEqual(ORDER_TYPES["MARKET"], "MARKET")
        self.assertEqual(ORDER_TYPES["LIMIT"], "LIMIT")
        self.assertEqual(ORDER_TYPES["STOP"], "STOP")
        self.assertEqual(ORDER_TYPES["STOP_LIMIT"], "STOP_LIMIT")
        
    def test_time_validity_options(self):
        """Test time validity options."""
        from hummingbot.connector.exchange.trading212.trading212_constants import TIME_VALIDITY_OPTIONS
        
        self.assertEqual(TIME_VALIDITY_OPTIONS["DAY"], "DAY")
        self.assertEqual(TIME_VALIDITY_OPTIONS["GOOD_TILL_CANCEL"], "GOOD_TILL_CANCEL")
        
    def test_default_fees(self):
        """Test default fees."""
        from hummingbot.connector.exchange.trading212.trading212_constants import DEFAULT_FEES
        
        self.assertEqual(DEFAULT_FEES.maker_percent_fee_decimal, Decimal("0"))
        self.assertEqual(DEFAULT_FEES.taker_percent_fee_decimal, Decimal("0"))


if __name__ == "__main__":
    unittest.main()