import asyncio
import os
from decimal import Decimal

from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange


class DummyClientConfig:
    def __init__(self):
        self.rate_limits_share_pct = 1.0


async def main():
    api_key = os.getenv("T212_API_KEY")
    base_url = os.getenv("T212_BASE_URL", "https://api-practice.trading212.com")

    ex = Trading212Exchange(
        client_config_map=ClientConfigAdapter(DummyClientConfig()),
        api_key=api_key,
        base_url=base_url,
        practice_mode_only=True,
        enable_live_orders=False,
        trading_pairs=["AAPL-USD"],
    )

    ex._set_trading_pair_symbol_map({"AAPL_US_EQ": "AAPL-USD"})

    # Fetch cash
    await ex._update_balances()
    print("Cash:", ex._account_balances)

    # Price via yfinance
    price = await ex._get_last_traded_price("AAPL-USD")
    print("AAPL last price:", price)

    # Place a small practice market order
    order_id = ex.buy("AAPL-USD", Decimal("0.1"), order_type=ex.supported_order_types()[1])
    await asyncio.sleep(0)

    # Fetch status
    await ex._update_order_status()
    print("In-flight orders:", ex.in_flight_orders)


if __name__ == "__main__":
    asyncio.run(main())

