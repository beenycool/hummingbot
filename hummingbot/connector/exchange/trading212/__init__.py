"""
Trading212 Exchange Connector for Hummingbot

This module provides integration with Trading212's equity trading API,
enabling live trading through Hummingbot's strategy framework.
"""

from .trading212_exchange import Trading212Exchange

__all__ = ["Trading212Exchange"]