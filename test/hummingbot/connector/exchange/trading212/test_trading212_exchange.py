import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange
from hummingbot.client.config.config_helpers import ClientConfigAdapter


class DummyClientConfig:
    def __init__(self):
        self.rate_limits_share_pct = 1.0


@pytest.mark.asyncio
async def test_place_cancel_status_market_order(monkeypatch):
    client_cfg = ClientConfigAdapter(DummyClientConfig())
    ex = Trading212Exchange(
        client_config_map=client_cfg,
        api_key="k",
        base_url="https://api-practice.trading212.com",
        practice_mode_only=True,
        enable_live_orders=False,
        trading_pairs=["AAPL-USD"],
    )

    # Map trading pair to t212 symbol
    ex._set_trading_pair_symbol_map({"AAPL_US_EQ": "AAPL-USD"})

    async def fake_request(method, path, params=None, json_body=None, limit_id=None):
        if method == "POST" and path.endswith("/equity/orders/market"):
            return {"id": "123"}
        if method == "GET" and path.endswith("/equity/orders/123"):
            return {"status": "filled"}
        if method == "DELETE" and path.endswith("/equity/orders/123"):
            return {}
        if method == "GET" and path.endswith("/equity/account/cash"):
            return {"cash": [{"currencyCode": "USD", "available": 1000.0, "reserved": 0.0}]}
        return {}

    monkeypatch.setattr(ex._api, "request", fake_request)

    # Place order
    order_id = ex.buy("AAPL-USD", Decimal("0.1"), order_type=ex.supported_order_types()[1])

    # Wait a tick to process
    await asyncio.sleep(0)

    # Poll status
    await ex._update_order_status()

    # Cancel
    for o in list(ex.in_flight_orders.values()):
        await ex._execute_cancel(o.trading_pair, o.client_order_id)

    # Balances
    await ex._update_balances()
    assert ex._account_balances.get("USD") is not None

