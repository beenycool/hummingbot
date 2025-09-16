import json
import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SymbolMappingCache:
    t212_to_yahoo: Dict[str, str]
    yahoo_to_t212: Dict[str, str]


def default_symbol_to_yahoo(t212_symbol: str) -> str:
    # Trading 212 tickers often like "AAPL_US_EQ" -> Yahoo: "AAPL"
    # Heuristic: split by '_' and take the first part
    if not t212_symbol:
        return t212_symbol
    return t212_symbol.split("_")[0]


def load_symbols_map(symbols_map_path: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if symbols_map_path and os.path.exists(symbols_map_path):
        try:
            with open(symbols_map_path, "r") as f:
                text = f.read()
                try:
                    mapping = json.loads(text)
                except json.JSONDecodeError:
                    # Try basic YAML (key: value per line)
                    for line in text.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if ":" in line:
                            k, v = line.split(":", 1)
                            mapping[k.strip()] = v.strip()
        except Exception:
            # If map fails to load, fallback to empty
            mapping = {}
    return mapping


def build_symbol_cache(symbols_map_path: Optional[str]) -> SymbolMappingCache:
    override_map = load_symbols_map(symbols_map_path)
    t212_to_yahoo: Dict[str, str] = {}
    yahoo_to_t212: Dict[str, str] = {}

    for t212, yahoo in override_map.items():
        t212_to_yahoo[t212] = yahoo
        yahoo_to_t212[yahoo] = t212

    return SymbolMappingCache(t212_to_yahoo=t212_to_yahoo, yahoo_to_t212=yahoo_to_t212)


def to_yahoo_symbol(t212_symbol: str, cache: SymbolMappingCache) -> str:
    if t212_symbol in cache.t212_to_yahoo:
        return cache.t212_to_yahoo[t212_symbol]
    return default_symbol_to_yahoo(t212_symbol)


def to_t212_symbol(yahoo_symbol: str, cache: SymbolMappingCache) -> Optional[str]:
    return cache.yahoo_to_t212.get(yahoo_symbol)


def is_market_hours_open() -> bool:
    # Simple placeholder; can be enhanced to check exchange calendars.
    return True

