import asyncio
from unittest.mock import MagicMock

import pytest

from hummingbot.connector.exchange.trading212.trading212_market_data import Trading212MarketDataProvider
from hummingbot.connector.exchange.trading212.trading212_utils import SymbolMappingCache


@pytest.mark.asyncio
async def test_price_polling_with_mocked_yfinance(monkeypatch):
    cache = SymbolMappingCache(t212_to_yahoo={}, yahoo_to_t212={})
    provider = Trading212MarketDataProvider(cache, yfinance_enabled=True)

    class DummyTicker:
        def history(self, period, interval):
            import pandas as pd

            return pd.DataFrame({
                "Close": [100.0]
            })

    class DummyYF:
        def Ticker(self, symbol):
            return DummyTicker()

    monkeypatch.setitem(globals(), 'yfinance', DummyYF())

    price = await provider.get_last_price("AAPL_US_EQ")
    assert price == 100.0

