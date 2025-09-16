import asyncio
import json
from typing import Any, Dict, Optional

import httpx

from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from .trading212_constants import (
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)


class Trading212APIError(Exception):
    def __init__(self, status_code: int, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.payload = payload or {}


class Trading212APIClient:
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str],
        throttler: AsyncThrottler,
        timeout: float = 10.0,
        max_retry_attempts: int = 3,
        backoff_seconds: float = 1.2,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._throttler = throttler
        self._timeout = timeout
        self._max_retry_attempts = max_retry_attempts
        self._backoff_seconds = backoff_seconds
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def _headers(self) -> Dict[str, str]:
        headers = {
            HEADER_ACCEPT: "application/json",
            HEADER_CONTENT_TYPE: "application/json",
        }
        if self._api_key:
            headers[HEADER_AUTHORIZATION] = self._api_key
        return headers

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        limit_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = await self._headers()
        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retry_attempts + 1):
            try:
                async with self._throttler.execute_task(limit_id or path):
                    resp = await self._client.request(
                        method=method.upper(), url=url, headers=headers, params=params, json=json_body
                    )
                if resp.status_code >= 400:
                    # Try to parse error body
                    try:
                        payload = resp.json()
                    except Exception:
                        payload = {"text": resp.text}
                    message = payload.get("message") or payload.get("error") or resp.text
                    # Surface scope/rate-limit hints if present
                    if resp.status_code in (401, 403):
                        message = f"Auth/Scope error: {message}. Ensure API key has required scopes."
                    if resp.status_code == 429:
                        message = f"Rate limited: {message}. Slow down or adjust rate limits."
                    raise Trading212APIError(resp.status_code, message, payload)
                if resp.status_code == 204:
                    return {}
                data = resp.json()
                return data
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
            except Trading212APIError as e:
                # Retry only for 5xx and 429
                last_error = e
                if isinstance(e, Trading212APIError) and e.status_code in (429, 500, 502, 503, 504):
                    pass
                else:
                    raise

            # backoff
            await asyncio.sleep(self._backoff_seconds * attempt)

        # After max attempts, raise last error
        if isinstance(last_error, Exception):
            raise last_error
        raise Trading212APIError(599, "Unknown error")

