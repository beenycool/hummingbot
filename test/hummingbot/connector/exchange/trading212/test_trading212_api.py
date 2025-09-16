import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.connector.exchange.trading212.trading212_api import Trading212APIClient, Trading212APIError


@pytest.mark.asyncio
async def test_happy_path_get(monkeypatch):
    throttler = AsyncThrottler(rate_limits=[])
    client = Trading212APIClient("https://example.com", "api-key", throttler)

    class DummyResp:
        status_code = 200

        def json(self):
            return {"ok": True}

    async def fake_request(*args, **kwargs):
        return DummyResp()

    monkeypatch.setattr(client._client, "request", fake_request)
    data = await client.request("GET", "/ping")
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_401_raises(monkeypatch):
    throttler = AsyncThrottler(rate_limits=[])
    client = Trading212APIClient("https://example.com", None, throttler, max_retry_attempts=1)

    class DummyResp:
        status_code = 401

        def json(self):
            return {"message": "unauthorized"}

        @property
        def text(self):
            return "unauthorized"

    async def fake_request(*args, **kwargs):
        return DummyResp()

    monkeypatch.setattr(client._client, "request", fake_request)
    with pytest.raises(Trading212APIError) as ei:
        await client.request("GET", "/secure")
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_429_retries_then_raises(monkeypatch):
    throttler = AsyncThrottler(rate_limits=[])
    client = Trading212APIClient("https://example.com", "k", throttler, max_retry_attempts=2, backoff_seconds=0.0)

    class DummyResp429:
        status_code = 429

        def json(self):
            return {"message": "rate limit"}

        @property
        def text(self):
            return "rate limit"

    async def fake_request(*args, **kwargs):
        return DummyResp429()

    monkeypatch.setattr(client._client, "request", fake_request)
    with pytest.raises(Trading212APIError) as ei:
        await client.request("GET", "/orders")
    assert ei.value.status_code == 429

