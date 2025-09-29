"""
Trading212 Constants and Configuration

This module contains all constants, URLs, rate limits, and configuration
settings for the Trading212 exchange connector.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.web_assistant.connections.data_types import RateLimit
from hummingbot.client.config.config_var import ConfigVar


# Exchange Information
EXCHANGE_NAME = "trading212"
REST_URL = "https://live.trading212.com"
HEALTH_CHECK_ENDPOINT = "/api/v0/equity/account/info"

# API Endpoints
ENDPOINTS = {
    # Account & Portfolio
    "account_cash": "/api/v0/equity/account/cash",
    "account_info": "/api/v0/equity/account/info",
    "portfolio": "/api/v0/equity/portfolio",
    "portfolio_ticker": "/api/v0/equity/portfolio/ticker",
    "portfolio_by_ticker": "/api/v0/equity/portfolio/{ticker}",
    
    # Order Management
    "orders": "/api/v0/equity/orders",
    "order_by_id": "/api/v0/equity/orders/{id}",
    "order_market": "/api/v0/equity/orders/market",
    "order_limit": "/api/v0/equity/orders/limit",
    "order_stop": "/api/v0/equity/orders/stop",
    "order_stop_limit": "/api/v0/equity/orders/stop_limit",
    
    # Metadata
    "instruments": "/api/v0/equity/metadata/instruments",
    "exchanges": "/api/v0/equity/metadata/exchanges",
    
    # History
    "history_orders": "/api/v0/equity/history/orders",
    "history_dividends": "/api/v0/equity/history/dividends",
    "history_transactions": "/api/v0/history/transactions",
    "history_exports": "/api/v0/history/exports",
    
    # Pies (Investment Pies)
    "pies": "/api/v0/equity/pies",
    "pie_by_id": "/api/v0/equity/pies/{id}",
    "pie_duplicate": "/api/v0/equity/pies/{id}/duplicate",
}

# Rate Limits (requests per time interval)
RATE_LIMITS = [
    # Order Management
    RateLimit(limit_id="orders_execute", limit=1, time_interval=1),     # Order placement
    RateLimit(limit_id="orders_cancel", limit=1, time_interval=1),     # Order cancel
    RateLimit(limit_id="orders_list", limit=1, time_interval=5),       # List orders
    RateLimit(limit_id="order_details", limit=1, time_interval=1),     # Order details
    
    # Account & Portfolio
    RateLimit(limit_id="portfolio", limit=1, time_interval=5),         # Portfolio data
    RateLimit(limit_id="account_cash", limit=1, time_interval=2),     # Account cash
    RateLimit(limit_id="account_info", limit=1, time_interval=30),    # Account info
    
    # Metadata
    RateLimit(limit_id="metadata", limit=1, time_interval=30),         # Instruments/exchanges
    
    # History
    RateLimit(limit_id="history_orders", limit=6, time_interval=60),   # Historical orders
    RateLimit(limit_id="history_dividends", limit=6, time_interval=60), # Historical dividends
    RateLimit(limit_id="history_transactions", limit=6, time_interval=60), # Transactions
    
    # Pies
    RateLimit(limit_id="pies_read", limit=1, time_interval=30),        # Read pies
    RateLimit(limit_id="pies_write", limit=1, time_interval=5),        # Write pies
]

# Order Status Mapping
ORDER_STATUS_MAP = {
    "LOCAL": "PENDING_CREATE",
    "WORKING": "OPEN",
    "FILLED": "FILLED",
    "CANCELLED": "CANCELLED",
    "REJECTED": "FAILED",
}

# Order Types
ORDER_TYPES = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "STOP": "STOP",
    "STOP_LIMIT": "STOP_LIMIT",
}

# Time Validity Options
TIME_VALIDITY_OPTIONS = {
    "DAY": "DAY",
    "GOOD_TILL_CANCEL": "GOOD_TILL_CANCEL",
}

# from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.data_type.trade_fee import TradeFeeSchema
from decimal import Decimal

# Default Fees (Trading212 is zero commission)
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0"),
    taker_percent_fee_decimal=Decimal("0"),
)
# Trading212 Configuration Variables
REQUIRED_CONNECTORS_SETTINGS = {
    "trading212_api_key": ConfigVar(
        key="trading212_api_key",
        prompt="Enter your Trading212 API key >>> ",
        required_if=lambda: True,
        is_secure=True,
        is_connect_key=True,
    )
}

# Error Messages
ERROR_MESSAGES = {
    "INVALID_API_KEY": "Bad API key",
    "INSUFFICIENT_SCOPE": "Scope missing for API key",
    "NOT_AVAILABLE_REAL_MONEY": "Not available for real money accounts",
    "ORDER_NOT_FOUND": "Order not found",
    "INVALID_TICKER": "Invalid ticker supplied",
    "NO_POSITION": "No open position with that ticker",
    "RATE_LIMIT_EXCEEDED": "Limited",
    "TIMEOUT": "Timed-out",
}

# HTTP Status Codes
HTTP_STATUS_CODES = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    408: "Request Timeout",
    429: "Too Many Requests",
}

# API Scopes
API_SCOPES = {
    "orders:execute": "orders:execute",
    "orders:read": "orders:read",
    "portfolio": "portfolio",
    "account": "account",
    "metadata": "metadata",
    "history:orders": "history:orders",
    "history:dividends": "history:dividends",
    "history:transactions": "history:transactions",
    "pies:read": "pies:read",
    "pies:write": "pies:write",
}

# Trading212 Specific Constants
MIN_TRADE_QUANTITY = Decimal("0.0001")  # Minimum fractional share
MAX_TRADE_QUANTITY = Decimal("999999")  # Maximum trade quantity
PRICE_PRECISION = 2  # Price precision for most instruments
QUANTITY_PRECISION = 4  # Quantity precision for fractional shares

# Market Hours Constants
MARKET_HOURS_TYPES = {
    "OPEN": "OPEN",
    "CLOSE": "CLOSE",
}

# Instrument Types
INSTRUMENT_TYPES = {
    "EQUITY": "EQUITY",
    "ETF": "ETF",
    "BOND": "BOND",
    "COMMODITY": "COMMODITY",
    "CRYPTO": "CRYPTO",
}

# Currency Codes
CURRENCY_CODES = {
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "CHF": "CHF",
    "CAD": "CAD",
    "AUD": "AUD",
    "JPY": "JPY",
}

# Request Headers
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Polling Intervals (in seconds)
POLLING_INTERVALS = {
    "ORDER_STATUS": 1,      # Check order status every 1 second
    "BALANCE_UPDATE": 5,    # Update balances every 5 seconds
    "PORTFOLIO_UPDATE": 5,   # Update portfolio every 5 seconds
    "MARKET_DATA": 10,      # Update market data every 10 seconds
}

# Timeout Settings (in seconds)
TIMEOUTS = {
    "REQUEST_TIMEOUT": 30,   # HTTP request timeout
    "CONNECT_TIMEOUT": 10,   # Connection timeout
    "READ_TIMEOUT": 30,      # Read timeout
}

# Retry Settings
RETRY_SETTINGS = {
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 1,        # Initial delay in seconds
    "BACKOFF_FACTOR": 2,     # Exponential backoff factor
}

# Logging Configuration
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL",
}

# WebSocket Settings (if implemented in future)
WEBSOCKET_SETTINGS = {
    "PING_INTERVAL": 30,     # Ping interval in seconds
    "PONG_TIMEOUT": 10,      # Pong timeout in seconds
    "RECONNECT_DELAY": 5,    # Reconnect delay in seconds
    "MAX_RECONNECT_ATTEMPTS": 5,
}