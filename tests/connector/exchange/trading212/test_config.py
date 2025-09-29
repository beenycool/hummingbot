"""
Test configuration and setup for Trading212 connector tests.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

# Test configuration
TEST_CONFIG = {
    "api_key": os.environ.get("TRADING212_TEST_API_KEY", "REPLACE_WITH_DUMMY_KEY"),
    "trading_pairs": ["AAPL-USD", "MSFT-USD", "GOOGL-USD"],
    "test_data": {
        "order_data": {
            "id": 12345,
            "ticker": "AAPL_US_EQ",
            "type": "LIMIT",
            "quantity": 10.0,
            "limitPrice": 150.0,
            "status": "WORKING",
            "creationTime": "2023-01-01T12:00:00Z",
            "filledQuantity": 0.0,
            "filledValue": 0.0,
            "stopPrice": 0.0,
            "timeValidity": "DAY"
        },
        "position_data": {
            "ticker": "AAPL_US_EQ",
            "quantity": 10.0,
            "averagePrice": 150.0,
            "currentPrice": 155.0,
            "ppl": 50.0,
            "fxPpl": 0.0,
            "maxBuy": 100.0,
            "maxSell": 10.0,
            "pieQuantity": 0.0,
            "initialFillDate": "2023-01-01T12:00:00Z"
        },
        "balance_data": {
            "total": 10000.0,
            "free": 8000.0,
            "blocked": 2000.0,
            "invested": 5000.0,
            "pieCash": 0.0,
            "ppl": 100.0,
            "result": 100.0
        },
        "instrument_data": {
            "ticker": "AAPL_US_EQ",
            "name": "Apple Inc.",
            "shortName": "Apple",
            "currencyCode": "USD",
            "isin": "US0378331005",
            "type": "EQUITY",
            "minTradeQuantity": 0.0001,
            "maxOpenQuantity": 1000000,
            "workingScheduleId": 1,
            "addedOn": "2023-01-01T12:00:00Z"
        }
    }
}