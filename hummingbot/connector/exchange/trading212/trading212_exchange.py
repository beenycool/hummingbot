import asyncio
from decimal import Decimal
from typing import Any, AsyncIterable, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

from . import trading212_constants as CONSTANTS
from . import trading212_web_utils as web_utils
from .trading212_api_order_book_data_source import Trading212APIOrderBookDataSource
from .trading212_api_user_stream_data_source import Trading212APIUserStreamDataSource
from .trading212_auth import Trading212Auth


class Trading212Exchange(ExchangePyBase):
    """Trading212 connector implementing REST polling for accounts and orders.
    Note: Trading212 does not provide public order book/trade websockets; market-making is not supported.
    """

    UPDATE_ORDER_STATUS_MIN_INTERVAL = 10.0
    SHORT_POLL_INTERVAL = 5.0
    LONG_POLL_INTERVAL = 12.0

    web_utils = web_utils

    def __init__(
        self,
        trading212_api_key: str,
        balance_asset_limit: Optional[Dict[str, Dict[str, Decimal]]] = None,
        rate_limits_share_pct: Decimal = Decimal("100"),
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
    ):
        self._api_key = trading212_api_key
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs or []
        self._domain = domain
        super().__init__(balance_asset_limit, rate_limits_share_pct)
        self.real_time_balance_update = False

    @property
    def name(self) -> str:
        return CONSTANTS.EXCHANGE_NAME

    @property
    def authenticator(self) -> Trading212Auth:
        return Trading212Auth(self._api_key)

    @property
    def rate_limits_rules(self) -> List["RateLimit"]:
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def client_order_id_max_length(self) -> int:
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self) -> str:
        return CONSTANTS.HBOT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self) -> str:
        return CONSTANTS.METADATA_INSTRUMENTS

    @property
    def trading_pairs_request_path(self) -> str:
        return CONSTANTS.METADATA_INSTRUMENTS

    @property
    def check_network_request_path(self) -> str:
        return CONSTANTS.HEALTH_CHECK_ENDPOINT

    @property
    def trading_pairs(self) -> List[str]:
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self) -> List[OrderType]:
        # STOP/STOP_LIMIT are not supported by current Hummingbot OrderType enum
        return [OrderType.MARKET, OrderType.LIMIT]

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        return False

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            auth=self._auth,
        )

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return Trading212APIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return Trading212APIUserStreamDataSource(
            auth=self._auth,
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
        )

    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        return "404" in str(status_update_exception) or "Order not found" in str(status_update_exception)

    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        return "404" in str(cancelation_exception) or "Order not found" in str(cancelation_exception)

    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal = s_decimal_NaN,
        is_maker: Optional[bool] = None,
    ) -> TradeFeeBase:
        trade_base_fee = build_trade_fee(
            exchange=self.name,
            is_maker=is_maker,
            order_side=order_side,
            order_type=order_type,
            amount=amount,
            price=price,
            base_currency=base_currency.upper(),
            quote_currency=quote_currency.upper(),
        )
        return trade_base_fee

    async def _status_polling_loop_fetch_updates(self):
        await asyncio.gather(
            self._update_order_status(),
            self._update_balances(),
        )

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        exchange_order_id = await tracked_order.get_exchange_order_id()
        await self._api_delete(
            path_url=f"{CONSTANTS.ORDERS_BASE}/{exchange_order_id}",
            is_auth_required=True,
            limit_id=CONSTANTS.ORDERS_CANCEL,
        )
        return True

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
        symbol = await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        signed_qty = amount if trade_type is TradeType.BUY else (Decimal("-1") * amount)
        body: Dict[str, Any] = {
            "quantity": float(signed_qty),
            "ticker": symbol,
        }

        time_validity = kwargs.get("t212_time_validity")  # "DAY" or "GOOD_TILL_CANCEL"
        stop_price: Optional[Decimal] = kwargs.get("stop_price")

        path = None
        if order_type is OrderType.MARKET and stop_price is None:
            path = CONSTANTS.ORDERS_MARKET
        elif order_type is OrderType.LIMIT and stop_price is None:
            path = CONSTANTS.ORDERS_LIMIT
            body["limitPrice"] = float(price)
        elif stop_price is not None:
            # Allow placing stop/stop-limit if provided by kwargs
            body["stopPrice"] = float(stop_price)
            if order_type is OrderType.LIMIT:
                path = CONSTANTS.ORDERS_STOP_LIMIT
                body["limitPrice"] = float(price)
            else:
                path = CONSTANTS.ORDERS_STOP
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        if time_validity is not None:
            body["timeValidity"] = str(time_validity)

        order_result = await self._api_post(
            path_url=path,
            data=body,
            is_auth_required=True,
            limit_id=CONSTANTS.ORDERS_EXECUTE,
        )

        exchange_order_id = str(order_result.get("id")) if isinstance(order_result, dict) else ""
        timestamp = self.current_timestamp
        return exchange_order_id, timestamp

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        exchange_order_id = await tracked_order.get_exchange_order_id()
        data = await self._api_get(
            path_url=f"{CONSTANTS.ORDERS_BASE}/{exchange_order_id}",
            is_auth_required=True,
            limit_id=CONSTANTS.ORDERS_LIST,
        )
        status = data.get("status", "LOCAL")
        new_state = CONSTANTS.ORDER_STATUS_MAP.get(status, tracked_order.current_state)
        order_update: OrderUpdate = OrderUpdate(
            trading_pair=tracked_order.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=new_state,
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=str(data.get("id", exchange_order_id)),
        )
        return order_update

    async def _update_balances(self):
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()

        # Cash balances
        cash = await self._api_get(
            path_url=CONSTANTS.ACCOUNT_CASH,
            is_auth_required=True,
            limit_id=CONSTANTS.ACCOUNT_CASH_LIMIT,
        )
        # Determine account currency if available in health check endpoint
        try:
            acct_info = await self._api_get(path_url=CONSTANTS.HEALTH_CHECK_ENDPOINT, is_auth_required=True)
            account_ccy = acct_info.get("currencyCode", "USD")
        except Exception:
            account_ccy = "USD"

        free_balance = Decimal(str(cash.get("free", 0)))
        total_balance = Decimal(str(cash.get("total", cash.get("free", 0))))
        self._account_available_balances[account_ccy] = free_balance
        self._account_balances[account_ccy] = total_balance
        remote_asset_names.add(account_ccy)

        # Portfolio positions (equities as base assets)
        portfolio = await self._api_get(
            path_url=CONSTANTS.PORTFOLIO,
            is_auth_required=True,
            limit_id=CONSTANTS.PORTFOLIO_LIMIT,
        )
        for pos in portfolio:
            ticker: str = pos.get("ticker")
            quantity = Decimal(str(pos.get("quantity", 0)))
            max_sell = Decimal(str(pos.get("maxSell", quantity)))
            # Map exchange ticker to HB trading pair base asset
            base_symbol = ticker.split("_")[0]
            self._account_balances[base_symbol] = quantity
            self._account_available_balances[base_symbol] = max_sell
            remote_asset_names.add(base_symbol)

        # Remove assets not reported remotely
        asset_names_to_remove = local_asset_names.difference(remote_asset_names)
        for asset_name in asset_names_to_remove:
            self._account_available_balances.pop(asset_name, None)
            self._account_balances.pop(asset_name, None)

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List:
        # Not implemented due to limited endpoints for per-order fills
        return []

    async def _make_network_check_request(self):
        await self._api_get(path_url=self.check_network_request_path, is_auth_required=True)

    async def _update_trading_fees(self):
        # Trading212 has zero-commission; rely on default fee schema
        return

    async def _user_stream_event_listener(self):
        async for event_message in self._iter_user_event_queue():
            try:
                if not isinstance(event_message, dict):
                    continue
                if event_message.get("type") == "orders":
                    orders = event_message.get("data", [])
                    # Build lookup for speed
                    tracked_by_ex_id = self._order_tracker.all_updatable_orders_by_exchange_order_id
                    for od in orders:
                        exch_id = str(od.get("id"))
                        tracked = tracked_by_ex_id.get(exch_id)
                        if tracked is None:
                            continue
                        status = od.get("status", "LOCAL")
                        new_state = CONSTANTS.ORDER_STATUS_MAP.get(status, tracked.current_state)
                        order_update = OrderUpdate(
                            trading_pair=tracked.trading_pair,
                            update_timestamp=self.current_timestamp,
                            new_state=new_state,
                            client_order_id=tracked.client_order_id,
                            exchange_order_id=exch_id,
                        )
                        self._order_tracker.process_order_update(order_update=order_update)
                # Portfolio events are ignored; balances are polled in status loop
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().exception("Unexpected error in user stream listener loop.")

    async def _format_trading_rules(self, exchange_info_dict: List[Dict[str, Any]]) -> List[TradingRule]:
        retval: List[TradingRule] = []
        for instrument in exchange_info_dict:
            try:
                ticker = instrument.get("ticker")
                currency = instrument.get("currencyCode", "USD")
                base = ticker.split("_")[0]
                trading_pair = combine_to_hb_trading_pair(base, currency)
                min_order_size = Decimal(str(instrument.get("minTradeQuantity", "0.0001")))
                max_order_size = Decimal(str(instrument.get("maxOpenQuantity", "1000000")))
                retval.append(
                    TradingRule(
                        trading_pair=trading_pair,
                        min_order_size=min_order_size,
                        max_order_size=max_order_size,
                        min_price_increment=Decimal("0.01"),  # typical cent tick
                        min_base_amount_increment=Decimal("0.0001"),  # fractional shares
                    )
                )
            except Exception:
                self.logger().error(
                    f"Error parsing trading rules for instrument {instrument}", exc_info=True
                )
        return retval

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: List[Dict[str, Any]]):
        mapping = bidict()
        for instrument in exchange_info:
            try:
                ticker = instrument.get("ticker")  # e.g., AAPL_US_EQ
                base = ticker.split("_")[0]
                quote = instrument.get("currencyCode", "USD")
                hb_pair = combine_to_hb_trading_pair(base, quote)
                mapping[ticker] = hb_pair
            except Exception:
                continue
        self._set_trading_pair_symbol_map(mapping)

    async def _get_last_traded_price(self, trading_pair: str) -> float:
        # Query portfolio position by ticker to get currentPrice
        exchange_symbol = await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        try:
            data = await self._api_get(
                path_url=CONSTANTS.PORTFOLIO_TICKER.format(ticker=exchange_symbol),
                is_auth_required=True,
                limit_id=CONSTANTS.PORTFOLIO_LIMIT,
            )
            return float(data.get("currentPrice", 0))
        except Exception:
            # Fallback: scan full portfolio
            try:
                portfolio = await self._api_get(
                    path_url=CONSTANTS.PORTFOLIO,
                    is_auth_required=True,
                    limit_id=CONSTANTS.PORTFOLIO_LIMIT,
                )
                for pos in portfolio:
                    if pos.get("ticker") == exchange_symbol:
                        return float(pos.get("currentPrice", 0))
            except Exception:
                pass
        return 0.0

