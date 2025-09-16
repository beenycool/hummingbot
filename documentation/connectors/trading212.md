### Trading 212 Connector (Practice-first, price via yfinance)

This connector integrates Trading 212's PRACTICE REST API for account, portfolio, and order management, and uses yfinance for market prices (last close/last trade approximation). No order book or trades WebSocket is available.

Important limitations:
- No L2/L3 market data streams. Market-making strategies are not supported.
- Practice mode by default; live trading is disabled unless explicitly double opt-in.

Scopes and limits:
- Auth via header `Authorization: <API_KEY>`.
- Respect per-endpoint rate limits. Order placement ~1 req/sec; list/status ~1 req/5s; history ~6 req/min.

Config (conf/conf_trading212.yml):
```yaml
api_key: ${T212_API_KEY:}
base_url: "https://api-practice.trading212.com"
practice_mode_only: true
enable_live_orders: false
symbols_map_path: ""
price_poll_interval: 10
yfinance_enabled: true
max_retry_attempts: 3
backoff_seconds: 1.2
```

Live trading safeguard:
- To enable live trading you must set `enable_live_orders: true` and export `T212_ALLOW_LIVE=1`. If `practice_mode_only` is true or `T212_ALLOW_LIVE` is not set, the connector will refuse to operate against the live host.

Quickstart (Practice):
1. Create an API key in Trading 212 Practice.
2. Export `T212_API_KEY`.
3. Configure `conf/conf_trading212.yml` (keep defaults for practice).
4. Run the quickcheck script:
```bash
python scripts/dev/trading212_quickcheck.py
```
It will: fetch cash, fetch portfolio, poll yfinance price for `AAPL`, place a small practice market order for `AAPL_US_EQ` quantity 0.1, and print order status.

