import asyncio
from typing import Dict, Optional

from .trading212_utils import SymbolMappingCache, to_yahoo_symbol


class Trading212MarketDataProvider:
    def __init__(
        self,
        symbol_cache: SymbolMappingCache,
        poll_interval: float = 10.0,
        jitter_seconds: float = 3.0,
        yfinance_enabled: bool = True,
    ):
        self._symbol_cache = symbol_cache
        self._poll_interval = poll_interval
        self._jitter = jitter_seconds
        self._yfinance_enabled = yfinance_enabled
        self._last_price: Dict[str, float] = {}

    async def get_last_price(self, t212_symbol: str) -> Optional[float]:
        if not self._yfinance_enabled:
            return self._last_price.get(t212_symbol)
        try:
            import random
            import yfinance as yf

            yahoo_symbol = to_yahoo_symbol(t212_symbol, self._symbol_cache)
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(period="1d", interval="1m")
            price = None
            if df is not None and not df.empty:
                # Prefer the latest Close
                price = float(df["Close"].iloc[-1])
            if price is not None and price > 0:
                self._last_price[t212_symbol] = price
                return price
        except Exception:
            # Fall back to last known price
            pass
        return self._last_price.get(t212_symbol)

    async def polling_loop(self, symbols: list[str], stop_event: asyncio.Event):
        import random
        while not stop_event.is_set():
            try:
                for sym in symbols:
                    await self.get_last_price(sym)
            except Exception:
                pass
            delay = self._poll_interval + random.uniform(0, self._jitter)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

