import asyncio
from decimal import Decimal

import pytest

from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange


@pytest.mark.asyncio
async def test_supported_order_types():
    ex = Trading212Exchange(trading212_api_key="test", trading_pairs=["AAPL-USD"], trading_required=False)
    types = ex.supported_order_types()
    assert len(types) >= 2


@pytest.mark.asyncio
async def test_format_trading_rules():
    ex = Trading212Exchange(trading212_api_key="test", trading_pairs=["AAPL-USD"], trading_required=False)
    instruments = [
        {
            "ticker": "AAPL_US_EQ",
            "currencyCode": "USD",
            "minTradeQuantity": 0.001,
            "maxOpenQuantity": 1000,
        }
    ]
    rules = await ex._format_trading_rules(instruments)
    assert len(rules) == 1
    r = rules[0]
    assert r.trading_pair == "AAPL-USD"
    assert r.min_order_size == Decimal("0.001")

