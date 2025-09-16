from hummingbot.core.api_throttler.data_types import RateLimit
from .trading212_constants import (
    CHECK_NETWORK_PATH_URL,
    GET_ACCOUNT_CASH_PATH_URL,
    GET_ACCOUNT_INFO_PATH_URL,
    GET_PORTFOLIO_PATH_URL,
    GET_PORTFOLIO_TICKER_PATH_URL,
    POST_PORTFOLIO_TICKER_PATH_URL,
    POST_ORDER_MARKET_PATH_URL,
    POST_ORDER_LIMIT_PATH_URL,
    POST_ORDER_STOP_PATH_URL,
    POST_ORDER_STOP_LIMIT_PATH_URL,
    GET_ORDERS_PATH_URL,
    GET_ORDER_BY_ID_PATH_URL,
    DELETE_ORDER_BY_ID_PATH_URL,
    GET_METADATA_INSTRUMENTS_PATH_URL,
    GET_METADATA_EXCHANGES_PATH_URL,
    GET_HISTORY_ORDERS_PATH_URL,
    GET_HISTORY_TRANSACTIONS_PATH_URL,
    GET_HISTORY_DIVIDENDS_PATH_URL,
)


# Conservative rate limits aligned with Trading 212 public documentation and safe defaults.
# Adjust as needed based on official limits. We scope by route to allow AsyncThrottler to handle bursts.
RATE_LIMITS = [
    # General/check
    RateLimit(limit_id=CHECK_NETWORK_PATH_URL, limit=6, time_interval=60),

    # Account/portfolio
    RateLimit(limit_id=GET_ACCOUNT_CASH_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=GET_ACCOUNT_INFO_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=GET_PORTFOLIO_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=GET_PORTFOLIO_TICKER_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=POST_PORTFOLIO_TICKER_PATH_URL, limit=6, time_interval=60),

    # Orders - place ~1 req/sec
    RateLimit(limit_id=POST_ORDER_MARKET_PATH_URL, limit=60, time_interval=60),
    RateLimit(limit_id=POST_ORDER_LIMIT_PATH_URL, limit=60, time_interval=60),
    RateLimit(limit_id=POST_ORDER_STOP_PATH_URL, limit=60, time_interval=60),
    RateLimit(limit_id=POST_ORDER_STOP_LIMIT_PATH_URL, limit=60, time_interval=60),

    # Orders - list/status ~1 req/5s
    RateLimit(limit_id=GET_ORDERS_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=GET_ORDER_BY_ID_PATH_URL, limit=12, time_interval=60),
    RateLimit(limit_id=DELETE_ORDER_BY_ID_PATH_URL, limit=60, time_interval=60),

    # Metadata
    RateLimit(limit_id=GET_METADATA_INSTRUMENTS_PATH_URL, limit=6, time_interval=60),
    RateLimit(limit_id=GET_METADATA_EXCHANGES_PATH_URL, limit=6, time_interval=60),

    # History
    RateLimit(limit_id=GET_HISTORY_ORDERS_PATH_URL, limit=6, time_interval=60),
    RateLimit(limit_id=GET_HISTORY_TRANSACTIONS_PATH_URL, limit=6, time_interval=60),
    RateLimit(limit_id=GET_HISTORY_DIVIDENDS_PATH_URL, limit=6, time_interval=60),
]

