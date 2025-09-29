from decimal import Decimal

from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState


EXCHANGE_NAME = "trading212"
DEFAULT_DOMAIN = "trading212"

# Base URL
REST_URLS = {
    DEFAULT_DOMAIN: "https://live.trading212.com"
}

# Health check
HEALTH_CHECK_ENDPOINT = "/api/v0/equity/account/info"

# Order Management
ORDERS_BASE = "/api/v0/equity/orders"
ORDERS_MARKET = f"{ORDERS_BASE}/market"
ORDERS_LIMIT = f"{ORDERS_BASE}/limit"
ORDERS_STOP = f"{ORDERS_BASE}/stop"
ORDERS_STOP_LIMIT = f"{ORDERS_BASE}/stop_limit"

# Account & Portfolio
ACCOUNT_CASH = "/api/v0/equity/account/cash"
PORTFOLIO = "/api/v0/equity/portfolio"
PORTFOLIO_TICKER = f"{PORTFOLIO}/{{ticker}}"

# Metadata
METADATA_INSTRUMENTS = "/api/v0/equity/metadata/instruments"
METADATA_EXCHANGES = "/api/v0/equity/metadata/exchanges"

# History
HISTORY_ORDERS = "/api/v0/equity/history/orders"
HISTORY_TRANSACTIONS = "/api/v0/history/transactions"


# Rate Limits
ORDERS_EXECUTE = "orders_execute"
ORDERS_CANCEL = "orders_cancel"
ORDERS_LIST = "orders_list"
PORTFOLIO_LIMIT = "portfolio"
ACCOUNT_CASH_LIMIT = "account_cash"
METADATA_LIMIT = "metadata"

RATE_LIMITS = [
    RateLimit(limit_id=ORDERS_EXECUTE, limit=1, time_interval=1),
    RateLimit(limit_id=ORDERS_CANCEL, limit=1, time_interval=1),
    RateLimit(limit_id=ORDERS_LIST, limit=1, time_interval=5),
    RateLimit(limit_id=PORTFOLIO_LIMIT, limit=1, time_interval=5),
    RateLimit(limit_id=ACCOUNT_CASH_LIMIT, limit=1, time_interval=2),
    RateLimit(limit_id=METADATA_LIMIT, limit=1, time_interval=30),
]


# Order state mapping
ORDER_STATUS_MAP = {
    "LOCAL": OrderState.PENDING_CREATE,
    "WORKING": OrderState.OPEN,
    "FILLED": OrderState.FILLED,
    "CANCELLED": OrderState.CANCELED,
    "REJECTED": OrderState.FAILED,
}


# Connector identifiers
HBOT_ORDER_ID_PREFIX = "T212-"
MAX_ORDER_ID_LEN = 40


# Misc
WS_HEARTBEAT_TIME_INTERVAL = 30

