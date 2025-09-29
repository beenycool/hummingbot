import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.logger import HummingbotLogger

from . import trading212_constants as CONSTANTS
from .trading212_auth import Trading212Auth
from .trading212_web_utils import private_rest_url

if TYPE_CHECKING:
    from .trading212_exchange import Trading212Exchange


class Trading212APIUserStreamDataSource(UserStreamTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(
        self,
        auth: Trading212Auth,
        trading_pairs: List[str],
        connector: "Trading212Exchange",
        api_factory: WebAssistantsFactory,
    ):
        super().__init__()
        self._auth = auth
        self._trading_pairs = trading_pairs
        self._connector = connector
        self._api_factory = api_factory

    async def listen_for_user_stream(self, output: asyncio.Queue):
        # Poll portfolio and orders periodically since there is no WS
        while True:
            try:
                rest = await self._api_factory.get_rest_assistant()

                portfolio = await rest.execute_request(
                    url=private_rest_url(CONSTANTS.PORTFOLIO),
                    method=RESTMethod.GET,
                    is_auth_required=True,
                    throttler_limit_id=CONSTANTS.PORTFOLIO_LIMIT,
                )
                output.put_nowait({"type": "portfolio", "data": portfolio})

                orders = await rest.execute_request(
                    url=private_rest_url(CONSTANTS.ORDERS_BASE),
                    method=RESTMethod.GET,
                    is_auth_required=True,
                    throttler_limit_id=CONSTANTS.ORDERS_LIST,
                )
                output.put_nowait({"type": "orders", "data": orders})
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().exception("Error polling Trading212 user stream data")
            finally:
                await self._sleep(5.0)

