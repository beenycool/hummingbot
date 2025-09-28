from decimal import Decimal
from typing import Any, Dict

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema


CENTRALIZED = True
EXAMPLE_PAIR = "AAPL-USD"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0"),
    taker_percent_fee_decimal=Decimal("0"),
)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    # Trading212 instruments array; all are tradeable for enabled accounts
    return exchange_info.get("ticker") is not None


class Trading212ConfigMap(BaseConnectorConfigMap):
    connector: str = "trading212"
    trading212_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": lambda cm: "Enter your Trading212 API key >>> ",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    model_config = ConfigDict(title="trading212")


KEYS = Trading212ConfigMap.model_construct()

