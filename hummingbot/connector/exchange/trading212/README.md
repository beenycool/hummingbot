# Trading212 Hummingbot Connector

A complete Hummingbot spot exchange connector for Trading212 that enables live equity trading through their public API. This connector follows Hummingbot's v2.1 spot connector architecture and passes the official developer checklist.

## Features

- **Live Equity Trading**: Full support for Trading212's equity trading API
- **Multiple Order Types**: Market, Limit, Stop, and Stop-Limit orders
- **Real-time Updates**: Polling-based order status and balance updates
- **Portfolio Management**: Track positions and account balances
- **Rate Limiting**: Built-in rate limit compliance
- **Error Handling**: Robust error handling for API-specific conditions
- **Zero Commission**: Trading212's zero commission trading

## Supported Order Types

- **Market Orders**: Execute immediately at current market price
- **Limit Orders**: Execute at specified price or better
- **Stop Orders**: Trigger market order when stop price is reached
- **Stop-Limit Orders**: Trigger limit order when stop price is reached

## Installation

1. Clone the Hummingbot repository
2. Copy the `trading212` connector to `hummingbot/connector/exchange/trading212/`
3. Install required dependencies:
   ```bash
   pip install aiohttp
   ```

## Configuration

### API Key Setup

1. Log in to your Trading212 account
2. Navigate to Settings > API
3. Generate a new API key with the following scopes:
   - `orders:execute` - For placing and cancelling orders
   - `orders:read` - For reading order status
   - `portfolio` - For accessing portfolio data
   - `account` - For accessing account information
   - `metadata` - For accessing instrument metadata
   - `history:orders` - For accessing order history
   - `history:dividends` - For accessing dividend history
   - `history:transactions` - For accessing transaction history

### Hummingbot Configuration

Add the following to your Hummingbot configuration:

```yaml
trading212_api_key: "your_api_key_here"
```

## Usage

### Basic Setup

```python
from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange

# Initialize the exchange
exchange = Trading212Exchange(
    trading_pairs=["AAPL-USD", "MSFT-USD", "GOOGL-USD"],
    trading_required=True
)

# Set API key
exchange.set_api_key("your_api_key_here")

# Initialize the connector
await exchange.initialize()
```

### Placing Orders

```python
# Place a market order
order_id = await exchange._place_order(
    trading_pair="AAPL-USD",
    order_type=OrderType.MARKET,
    trade_type=TradeType.BUY,
    amount=Decimal("10.0")
)

# Place a limit order
order_id = await exchange._place_order(
    trading_pair="AAPL-USD",
    order_type=OrderType.LIMIT,
    trade_type=TradeType.BUY,
    amount=Decimal("10.0"),
    price=Decimal("150.0")
)

# Place a stop order
order_id = await exchange._place_order(
    trading_pair="AAPL-USD",
    order_type=OrderType.STOP,
    trade_type=TradeType.SELL,
    amount=Decimal("10.0"),
    stop_price=Decimal("140.0")
)
```

### Order Management

```python
# Cancel an order
success = await exchange._place_cancel(order_id)

# Get order status
status = await exchange._request_order_status(order_id)

# Get all orders
orders = exchange.orders
```

### Portfolio Management

```python
# Get account balances
balances = exchange.balances

# Get open positions
positions = exchange.positions

# Get specific position
position = exchange.get_position("AAPL-USD")
```

## API Endpoints

The connector implements the following Trading212 API endpoints:

### Order Management
- `POST /api/v0/equity/orders/market` - Place market orders
- `POST /api/v0/equity/orders/limit` - Place limit orders
- `POST /api/v0/equity/orders/stop` - Place stop orders
- `POST /api/v0/equity/orders/stop_limit` - Place stop-limit orders
- `GET /api/v0/equity/orders` - List all orders
- `GET /api/v0/equity/orders/{id}` - Get order details
- `DELETE /api/v0/equity/orders/{id}` - Cancel order

### Account & Portfolio
- `GET /api/v0/equity/account/cash` - Get account cash balance
- `GET /api/v0/equity/account/info` - Get account information
- `GET /api/v0/equity/portfolio` - Get all positions
- `GET /api/v0/equity/portfolio/{ticker}` - Get specific position

### Metadata
- `GET /api/v0/equity/metadata/instruments` - Get available instruments
- `GET /api/v0/equity/metadata/exchanges` - Get exchange schedules

### History
- `GET /api/v0/equity/history/orders` - Get order history
- `GET /api/v0/equity/history/dividends` - Get dividend history
- `GET /api/v0/history/transactions` - Get transaction history

## Rate Limits

The connector implements the following rate limits:

- **Order Execution**: 1 request per second
- **Order Cancellation**: 1 request per second
- **Order Listing**: 1 request per 5 seconds
- **Portfolio Data**: 1 request per 5 seconds
- **Account Cash**: 1 request per 2 seconds
- **Metadata**: 1 request per 30 seconds
- **History**: 6 requests per minute

## Error Handling

The connector handles the following Trading212-specific errors:

- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Invalid API key
- **403 Forbidden**: Insufficient API key permissions
- **404 Not Found**: Order or resource not found
- **408 Request Timeout**: Request timed out
- **429 Too Many Requests**: Rate limit exceeded
- **500+ Server Error**: Server-side errors

## Market Data

Since Trading212 doesn't provide WebSocket order book feeds, the connector uses a polling-based approach:

- **Price Updates**: Polls portfolio data for current prices
- **Order Book**: Creates synthetic order book data
- **Trade Data**: Uses historical order data for trade information

## Trading Rules

The connector enforces Trading212's trading rules:

- **Minimum Trade Quantity**: Varies by instrument (typically 0.0001)
- **Maximum Open Quantity**: Varies by instrument
- **Market Hours**: Respects exchange working schedules
- **Time Validity**: Supports DAY and GOOD_TILL_CANCEL
- **Fractional Shares**: Supports fractional share trading

## Testing

### Unit Tests

Run the unit tests:

```bash
python -m pytest tests/connector/exchange/trading212/test_trading212_connector.py -v
```

### Integration Tests

For integration tests with the actual Trading212 API:

1. Set up a practice account
2. Generate an API key
3. Update the test configuration with your API key
4. Run the integration tests:

```bash
python -m pytest tests/connector/exchange/trading212/test_trading212_integration.py -v
```

## Limitations

- **No WebSocket Support**: Trading212 doesn't provide WebSocket feeds
- **No Order Book Data**: Limited to current price information
- **No Real-time Trades**: Trade data is based on order fills
- **Market Making**: Not suitable for high-frequency market making strategies

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure your API key has the required scopes
   - Check that the API key is correctly configured

2. **Rate Limit Errors**
   - The connector automatically handles rate limits
   - Reduce the frequency of requests if needed

3. **Order Placement Errors**
   - Check that the trading pair is supported
   - Verify that the order amount meets minimum requirements
   - Ensure the market is open for trading

4. **Balance Errors**
   - Ensure sufficient account balance
   - Check that funds are not blocked for other orders

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("hummingbot.connector.exchange.trading212").setLevel(logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This connector is licensed under the same terms as Hummingbot.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the Trading212 API documentation
3. Open an issue on the Hummingbot repository
4. Join the Hummingbot Discord community

## Changelog

### Version 1.0.0
- Initial release
- Support for all Trading212 order types
- Polling-based data updates
- Comprehensive error handling
- Full test coverage

## Disclaimer

This connector is provided as-is for educational and development purposes. Always test thoroughly with small amounts before using in production. Trading212's API and terms of service apply to all usage.