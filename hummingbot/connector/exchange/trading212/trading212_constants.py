from hummingbot.core.api_throttler.data_types import RateLimit


EXCHANGE_NAME = "trading212"

# Base URLs (practice and live). Default to PRACTICE.
PRACTICE_BASE_URL = "https://api-practice.trading212.com"
LIVE_BASE_URL = "https://live.trading212.com"

# REST API base path
API_PREFIX_V0 = "/api/v0"

# Endpoints under /api/v0
CHECK_NETWORK_PATH_URL = f"{API_PREFIX_V0}/equity/account/info"

# Account
GET_ACCOUNT_CASH_PATH_URL = f"{API_PREFIX_V0}/equity/account/cash"
GET_ACCOUNT_INFO_PATH_URL = f"{API_PREFIX_V0}/equity/account/info"

# Portfolio
GET_PORTFOLIO_PATH_URL = f"{API_PREFIX_V0}/equity/portfolio"
GET_PORTFOLIO_TICKER_PATH_URL = f"{API_PREFIX_V0}/equity/portfolio/{{ticker}}"
POST_PORTFOLIO_TICKER_PATH_URL = f"{API_PREFIX_V0}/equity/portfolio/ticker"

# Orders
POST_ORDER_MARKET_PATH_URL = f"{API_PREFIX_V0}/equity/orders/market"
POST_ORDER_LIMIT_PATH_URL = f"{API_PREFIX_V0}/equity/orders/limit"
POST_ORDER_STOP_PATH_URL = f"{API_PREFIX_V0}/equity/orders/stop"
POST_ORDER_STOP_LIMIT_PATH_URL = f"{API_PREFIX_V0}/equity/orders/stop_limit"
GET_ORDERS_PATH_URL = f"{API_PREFIX_V0}/equity/orders"
GET_ORDER_BY_ID_PATH_URL = f"{API_PREFIX_V0}/equity/orders/{{id}}"
DELETE_ORDER_BY_ID_PATH_URL = f"{API_PREFIX_V0}/equity/orders/{{id}}"

# Metadata
GET_METADATA_INSTRUMENTS_PATH_URL = f"{API_PREFIX_V0}/equity/metadata/instruments"
GET_METADATA_EXCHANGES_PATH_URL = f"{API_PREFIX_V0}/equity/metadata/exchanges"

# History (optional - not used initially)
GET_HISTORY_ORDERS_PATH_URL = f"{API_PREFIX_V0}/equity/history/orders"
GET_HISTORY_TRANSACTIONS_PATH_URL = f"{API_PREFIX_V0}/history/transactions"
GET_HISTORY_DIVIDENDS_PATH_URL = f"{API_PREFIX_V0}/history/dividends"

# Header names
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ACCEPT = "Accept"

# Default polling
DEFAULT_PRICE_POLL_INTERVAL = 10
DEFAULT_PRICE_POLL_JITTER_SECONDS = 3
ACCOUNT_POLL_INTERVAL = 10.0
ORDERS_POLL_INTERVAL = 10.0

# Client order id
MAX_ORDER_ID_LEN = 32
HBOT_ORDER_ID_PREFIX = ""

# Rate limits (defined in trading212_rate_limits.py)
RATE_LIMITS: list[RateLimit] = []

