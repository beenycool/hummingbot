from hummingbot.connector.exchange.trading212.trading212_utils import (
    build_symbol_cache,
    default_symbol_to_yahoo,
    to_yahoo_symbol,
)


def test_default_symbol_to_yahoo():
    assert default_symbol_to_yahoo("AAPL_US_EQ") == "AAPL"
    assert default_symbol_to_yahoo("TSLA") == "TSLA"


def test_symbol_cache_overrides(tmp_path):
    f = tmp_path / "map.json"
    f.write_text('{"AAPL_US_EQ": "AAPL", "BRK-B_US_EQ": "BRK-B"}')
    cache = build_symbol_cache(str(f))
    assert to_yahoo_symbol("AAPL_US_EQ", cache) == "AAPL"
    assert to_yahoo_symbol("BRK-B_US_EQ", cache) == "BRK-B"

