import asyncio
import os
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.exchange.trading212 import trading212_constants as CONSTANTS
from hummingbot.connector.exchange.trading212.trading212_api import Trading212APIClient, Trading212APIError
from hummingbot.connector.exchange.trading212.trading212_market_data import Trading212MarketDataProvider
from hummingbot.connector.exchange.trading212.trading212_rate_limits import RATE_LIMITS as T212_RATE_LIMITS
from hummingbot.connector.exchange.trading212.trading212_utils import (
    SymbolMappingCache,
    build_symbol_cache,
    to_yahoo_symbol,
)
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import AddedToCostTradeFee, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

if TYPE_CHECKING:
    from hummingbot.client.config.config_helpers import ClientConfigAdapter


class Trading212Exchange(ExchangePyBase):
    API_CALL_TIMEOUT = 10.0
    POLL_INTERVAL = 5.0
    UPDATE_ORDER_STATUS_MIN_INTERVAL = 10.0
    UPDATE_TRADE_STATUS_MIN_INTERVAL = 10.0

    web_utils = None  # Not using built-in web utils; using dedicated API client

    def __init__(
        self,
        client_config_map: "ClientConfigAdapter",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        practice_mode_only: bool = True,
        enable_live_orders: bool = False,
        symbols_map_path: Optional[str] = None,
        price_poll_interval: int = CONSTANTS.DEFAULT_PRICE_POLL_INTERVAL,
        yfinance_enabled: bool = True,
        max_retry_attempts: int = 3,
        backoff_seconds: float = 1.2,
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
    ):
        self._api_key = api_key or os.getenv("T212_API_KEY")
        self._base_url = (base_url or CONSTANTS.PRACTICE_BASE_URL).rstrip("/")
        self._practice_only = practice_mode_only
        self._enable_live = enable_live_orders
        self._symbols_map_path = symbols_map_path
        self._price_poll_interval = price_poll_interval
        self._yfinance_enabled = yfinance_enabled
        self._max_retry_attempts = max_retry_attempts
        self._backoff_seconds = backoff_seconds
        self._trading_pairs = trading_pairs
        self._trading_required = trading_required

        # Safety guards for live trading
        if self._practice_only and self._base_url.startswith(CONSTANTS.LIVE_BASE_URL):
            raise ValueError(
                "practice_mode_only=true but base_url points to LIVE. Set base_url to practice or disable the guard."
            )
        if self._base_url.startswith(CONSTANTS.LIVE_BASE_URL):
            allow_env = os.getenv("T212_ALLOW_LIVE", "0") == "1"
            if not (self._enable_live and allow_env):
                raise ValueError(
                    "Live trading disabled. Set enable_live_orders=true and T212_ALLOW_LIVE=1 to proceed (double opt-in)."
                )

        # Set up throttler and API client
        self._throttler = AsyncThrottler(rate_limits=T212_RATE_LIMITS)
        self._api = Trading212APIClient(
            base_url=self._base_url,
            api_key=self._api_key,
            throttler=self._throttler,
            timeout=self.API_CALL_TIMEOUT,
            max_retry_attempts=self._max_retry_attempts,
            backoff_seconds=self._backoff_seconds,
        )
        # Symbol mappings and market data provider
        self._symbol_cache: SymbolMappingCache = build_symbol_cache(self._symbols_map_path)
        self._market_data = Trading212MarketDataProvider(
            symbol_cache=self._symbol_cache,
            poll_interval=float(self._price_poll_interval),
            jitter_seconds=float(CONSTANTS.DEFAULT_PRICE_POLL_JITTER_SECONDS),
            yfinance_enabled=self._yfinance_enabled,
        )

        super().__init__(client_config_map)
        self.real_time_balance_update = False

    @property
    def authenticator(self):
        # No special Hummingbot authenticator; handled via API client headers
        return None

    @property
    def name(self) -> str:
        return CONSTANTS.EXCHANGE_NAME

    @property
    def rate_limits_rules(self):
        return T212_RATE_LIMITS

    @property
    def domain(self):
        return ""

    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self):
        return CONSTANTS.HBOT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self):
        # Trading 212 does not provide standard trading rules; we synthesize minimal rules.
        return CONSTANTS.GET_METADATA_INSTRUMENTS_PATH_URL

    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.GET_METADATA_INSTRUMENTS_PATH_URL

    @property
    def check_network_request_path(self):
        return CONSTANTS.CHECK_NETWORK_PATH_URL

    @property
    def trading_pairs(self):
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        return False

    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        if isinstance(status_update_exception, Trading212APIError) and status_update_exception.status_code == 404:
            return True
        return False

    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        if isinstance(cancelation_exception, Trading212APIError) and cancelation_exception.status_code == 404:
            return True
        return False

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        # Not used. We route REST via our API client and don't use WS.
        return WebAssistantsFactory(throttler=self._throttler)

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        # There is no public order book WS; we will not provide order books.
        # Use base class requirements by providing a dummy data source that relies on last price only.
        # For strategies requiring order books, this connector is not suitable.
        from hummingbot.core.data_feed.market_data_provider import MarketDataProvider
        # Use a generic provider that relies on get_last_traded_prices; we'll patch it via _get_last_traded_price
        class _DummyOrderBookDataSource(OrderBookTrackerDataSource):
            async def get_last_traded_prices(self, trading_pairs: List[str], domain: Optional[str] = None) -> Dict[str, float]:
                # Not used by default; Hummingbot will call connector.get_price
                return {tp: 0.0 for tp in trading_pairs}

            async def _order_book_snapshot(self, trading_pair: str):
                raise NotImplementedError

            async def _connected_websocket_assistant(self):
                raise NotImplementedError

            async def _subscribe_channels(self, ws):
                raise NotImplementedError

            async def _parse_trade_message(self, raw_message, message_queue):
                raise NotImplementedError

            async def _parse_order_book_diff_message(self, raw_message, message_queue):
                raise NotImplementedError

            async def _parse_order_book_snapshot_message(self, raw_message, message_queue):
                raise NotImplementedError

            def _channel_originating_message(self, event_message):
                return ""

        return _DummyOrderBookDataSource(trading_pairs=self._trading_pairs or [])

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        # No user WS; rely on polling loops only
        class _DummyUserStream(UserStreamTrackerDataSource):
            async def _connected_websocket_assistant(self):
                raise NotImplementedError

            async def _subscribe_channels(self, websocket_assistant):
                raise NotImplementedError

        return _DummyUserStream()

    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal = s_decimal_NaN,
        is_maker: Optional[bool] = None,
    ) -> AddedToCostTradeFee:
        is_maker = order_type is OrderType.LIMIT
        return AddedToCostTradeFee(percent=self.estimate_fee_pct(is_maker))

    async def _place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        trade_type: TradeType,
        order_type: OrderType,
        price: Decimal,
        **kwargs,
    ) -> Tuple[str, float]:
        # Trading 212 expects instrument ticker in their format, e.g. AAPL_US_EQ
        t212_symbol = await self.exchange_symbol_associated_to_pair(trading_pair)

        if order_type is OrderType.MARKET:
            path = CONSTANTS.POST_ORDER_MARKET_PATH_URL
            body = {
                "ticker": t212_symbol,
                "quantity": float(amount),
                "action": "BUY" if trade_type is TradeType.BUY else "SELL",
            }
        elif order_type is OrderType.LIMIT:
            path = CONSTANTS.POST_ORDER_LIMIT_PATH_URL
            body = {
                "ticker": t212_symbol,
                "quantity": float(amount),
                "limitPrice": float(price),
                "action": "BUY" if trade_type is TradeType.BUY else "SELL",
            }
        else:
            raise ValueError("Unsupported order type for Trading212")

        resp = await self._api.request("POST", path, json_body=body, limit_id=path)
        exchange_order_id = str(resp.get("id") or resp.get("orderId") or resp.get("order_id") or "")
        if not exchange_order_id:
            exchange_order_id = order_id
        return exchange_order_id, self.current_timestamp

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder) -> bool:
        ex_id = await tracked_order.get_exchange_order_id()
        if not ex_id:
            raise Trading212APIError(400, "Order has no exchange id")
        path = CONSTANTS.DELETE_ORDER_BY_ID_PATH_URL.replace("{id}", str(ex_id))
        await self._api.request("DELETE", path, limit_id=path)
        return True

    async def _format_trading_rules(self, exchange_info: Dict[str, Any]) -> List[TradingRule]:
        # Trading 212 metadata instruments do not provide granular trading rules; we set permissive defaults.
        result: List[TradingRule] = []
        symbols_mapping = {}
        instruments = exchange_info if isinstance(exchange_info, list) else exchange_info.get("instruments", [])
        for inst in instruments:
            try:
                t212_symbol = inst.get("ticker") or inst.get("symbol") or inst.get("isin")
                yahoo_symbol = to_yahoo_symbol(t212_symbol, self._symbol_cache)
                base = yahoo_symbol
                quote = "USD"
                trading_pair = combine_to_hb_trading_pair(base, quote)
                symbols_mapping[t212_symbol] = trading_pair
                result.append(
                    TradingRule(
                        trading_pair=trading_pair,
                        min_order_size=Decimal("0.0001"),
                        min_price_increment=Decimal("0.0001"),
                        min_base_amount_increment=Decimal("0.0001"),
                    )
                )
            except Exception:
                continue
        return result

    async def _update_trading_fees(self):
        pass

    async def _update_balances(self):
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()
        cash = await self._api.request("GET", CONSTANTS.GET_ACCOUNT_CASH_PATH_URL, limit_id=CONSTANTS.GET_ACCOUNT_CASH_PATH_URL)
        # Typical structure: {"cash": [{"currencyCode": "USD", "available": 1000.0, "reserved": 0.0, ...}, ...]}
        balances = cash.get("cash") or cash.get("balances") or []
        for entry in balances:
            asset = entry.get("currencyCode") or entry.get("currency")
            available = Decimal(str(entry.get("available") or 0))
            reserved = Decimal(str(entry.get("reserved") or 0))
            self._account_available_balances[asset] = available
            self._account_balances[asset] = available + reserved
            remote_asset_names.add(asset)

        # Remove assets no longer present
        for asset_name in local_asset_names.difference(remote_asset_names):
            self._account_available_balances.pop(asset_name, None)
            self._account_balances.pop(asset_name, None)

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        ex_id = await tracked_order.get_exchange_order_id()
        path = CONSTANTS.GET_ORDER_BY_ID_PATH_URL.replace("{id}", str(ex_id))
        data = await self._api.request("GET", path, limit_id=path)
        state_str = str(data.get("status") or data.get("state") or "")
        state_map = {
            "new": OrderState.OPEN,
            "open": OrderState.OPEN,
            "pending": OrderState.OPEN,
            "filled": OrderState.FILLED,
            "partially_filled": OrderState.PARTIALLY_FILLED,
            "canceled": OrderState.CANCELED,
            "cancelled": OrderState.CANCELED,
            "rejected": OrderState.FAILED,
        }
        new_state = state_map.get(state_str.lower(), OrderState.OPEN)
        update = OrderUpdate(
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=str(ex_id),
            trading_pair=tracked_order.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=new_state,
        )
        return update

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        # Trading 212 API may not expose per-order fills via a separate endpoint in practice; skip for now.
        return []

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):
        mapping = bidict()
        instruments = exchange_info if isinstance(exchange_info, list) else exchange_info.get("instruments", [])
        for inst in instruments:
            t212_symbol = inst.get("ticker") or inst.get("symbol") or inst.get("isin")
            if not t212_symbol:
                continue
            yahoo_symbol = to_yahoo_symbol(t212_symbol, self._symbol_cache)
            trading_pair = combine_to_hb_trading_pair(base=yahoo_symbol, quote="USD")
            mapping[t212_symbol] = trading_pair
        self._set_trading_pair_symbol_map(mapping)

    async def _get_last_traded_price(self, trading_pair: str) -> float:
        # reverse map from trading pair to t212 symbol via bidict
        t212_symbol = await self.exchange_symbol_associated_to_pair(trading_pair)
        price = await self._market_data.get_last_price(t212_symbol)
        return float(price) if price is not None else 0.0

    async def _user_stream_event_listener(self):
        # No WS user stream; nothing to process
        while True:
            await asyncio.sleep(60)

