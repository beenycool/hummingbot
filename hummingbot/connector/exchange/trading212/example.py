#!/usr/bin/env python3
"""
Trading212 Connector Example

This script demonstrates how to use the Trading212 connector
for basic trading operations.
"""

import asyncio
import logging
from decimal import Decimal
from typing import List

from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212Exchange


async def main():
    """Main example function."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Configuration
    API_KEY = "your_api_key_here"  # Replace with your actual API key
    TRADING_PAIRS = ["AAPL-USD", "MSFT-USD", "GOOGL-USD"]
    
    # Initialize the exchange
    exchange = Trading212Exchange(
        trading_pairs=TRADING_PAIRS,
        trading_required=True
    )
    
    try:
        # Set API key
        exchange.set_api_key(API_KEY)
        
        # Initialize the connector
        logger.info("Initializing Trading212 connector...")
        await exchange.initialize()
        
        # Get account information
        logger.info("Getting account information...")
        balances = exchange.balances
        positions = exchange.positions
        
        logger.info(f"Account balances: {balances}")
        logger.info(f"Open positions: {positions}")
        
        # Get trading rules
        logger.info("Getting trading rules...")
        trading_rules = exchange.trading_rules
        for pair, rules in trading_rules.items():
            logger.info(f"{pair}: Min={rules['min_trade_quantity']}, Max={rules['max_open_quantity']}")
        
        # Example: Place a small limit order (for demonstration only)
        # WARNING: This will place a real order if you have sufficient balance
        logger.info("Placing a small limit order...")
        
        # Get minimum trade quantity for AAPL-USD
        if "AAPL-USD" in trading_rules:
            min_quantity = trading_rules["AAPL-USD"]["min_trade_quantity"]
            
            # Place a limit order with a low price to avoid execution
            order_id = await exchange._place_order(
                trading_pair="AAPL-USD",
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                amount=min_quantity,
                price=Decimal("50.0")  # Low price to avoid execution
            )
            
            logger.info(f"Order placed with ID: {order_id}")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Get order status
            status = await exchange._request_order_status(order_id)
            logger.info(f"Order status: {status}")
            
            # Cancel the order
            logger.info("Cancelling order...")
            success = await exchange._place_cancel(order_id)
            logger.info(f"Order cancelled: {success}")
        
        # Get market status
        logger.info("Getting market status...")
        market_status = exchange.get_market_status()
        logger.info(f"Market status: {market_status}")
        
        # Get connector status
        logger.info("Getting connector status...")
        connector_status = exchange.get_connector_status()
        logger.info(f"Connector status: {connector_status}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        # Stop the connector
        logger.info("Stopping Trading212 connector...")
        await exchange.stop()
        logger.info("Trading212 connector stopped")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())