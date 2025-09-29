"""
Trading212 Web Utilities

This module provides HTTP request utilities and error handling for
the Trading212 exchange connector.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple
from aiohttp import ClientSession, ClientTimeout, ClientError
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, RESTResponse
from hummingbot.core.web_assistant.web_assistant import WebAssistant
from hummingbot.core.web_assistant.rest_assistant import RESTAssistant
from hummingbot.core.web_assistant.rate_limiter import RateLimiter
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.connector.exchange.trading212.trading212_constants import (
    RATE_LIMITS, ERROR_MESSAGES, HTTP_STATUS_CODES, TIMEOUTS, RETRY_SETTINGS
)
from hummingbot.connector.exchange.trading212.trading212_auth import Trading212Auth


class Trading212WebUtils:
    """
    Utility class for handling HTTP requests to Trading212 API.
    
    This class provides methods for making authenticated requests,
    handling errors, and managing rate limits.
    """
    
    def __init__(self, auth: Trading212Auth):
        """
        Initialize Trading212 web utilities.
        
        Args:
            auth: Trading212 authentication object
        """
        self._auth = auth
        self._logger = logging.getLogger(__name__)
        self._rate_limiter = RateLimiter(RATE_LIMITS)
        self._session: Optional[ClientSession] = None
        
    async def initialize(self):
        """Initialize the HTTP session."""
        timeout = ClientTimeout(
            total=TIMEOUTS["REQUEST_TIMEOUT"],
            connect=TIMEOUTS["CONNECT_TIMEOUT"],
            sock_read=TIMEOUTS["READ_TIMEOUT"]
        )
        self._session = ClientSession(timeout=timeout)
        
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            
    async def _make_request(
        self,
        request: RESTRequest,
        max_retries: int = RETRY_SETTINGS["MAX_RETRIES"]
    ) -> RESTResponse:
        """
        Make an authenticated HTTP request with retry logic.
        
        Args:
            request: The REST request to make
            max_retries: Maximum number of retry attempts
            
        Returns:
            RESTResponse object
            
        Raises:
            Various exceptions based on API errors
        """
        if not self._session:
            await self.initialize()
            
        # Add authentication headers
        auth_headers = self._auth.add_auth_to_headers(request)
        request.headers.update(auth_headers)
        
        # Apply rate limiting
        await self._rate_limiter.acquire_token(request.url)
        
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                async with self._session.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    params=request.params,
                    data=request.data,
                    json=request.json_data
                ) as response:
                    response_data = await response.json() if response.content_type == "application/json" else await response.text()
                    
                    rest_response = RESTResponse(
                        status=response.status,
                        headers=dict(response.headers),
                        data=response_data,
                        url=str(response.url)
                    )
                    
                    # Check for errors
                    await self._check_response_errors(rest_response)
                    
                    return rest_response
                    
            except ClientError as e:
                last_exception = e
                self._logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    delay = RETRY_SETTINGS["RETRY_DELAY"] * (RETRY_SETTINGS["BACKOFF_FACTOR"] ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise
                    
        if last_exception:
            raise last_exception
            
    async def _check_response_errors(self, response: RESTResponse):
        """
        Check response for Trading212-specific errors.
        
        Args:
            response: The REST response to check
            
        Raises:
            Various exceptions based on error conditions
        """
        status = response.status
        
        # Handle specific error cases
        if status == 400:
            if isinstance(response.data, str) and ERROR_MESSAGES["NOT_AVAILABLE_REAL_MONEY"] in response.data:
                from hummingbot.connector.exchange.trading212.trading212_exchange import MarketNotReady
                raise MarketNotReady("Live trading not enabled for this account")
            else:
                from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212APIException
                raise Trading212APIException(f"Bad request: {response.data}")
                
        elif status == 401:
            from hummingbot.connector.exchange.trading212.trading212_exchange import AuthenticationError
            raise AuthenticationError(ERROR_MESSAGES["INVALID_API_KEY"])
            
        elif status == 403:
            if isinstance(response.data, str) and "Scope" in response.data:
                from hummingbot.connector.exchange.trading212.trading212_exchange import AuthenticationError
                raise AuthenticationError(ERROR_MESSAGES["INSUFFICIENT_SCOPE"])
            else:
                from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212APIException
                raise Trading212APIException(f"Forbidden: {response.data}")
                
        elif status == 404:
            if isinstance(response.data, str) and ERROR_MESSAGES["ORDER_NOT_FOUND"] in response.data:
                from hummingbot.connector.exchange.trading212.trading212_exchange import OrderNotFound
                raise OrderNotFound("Order not found")
            else:
                from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212APIException
                raise Trading212APIException(f"Not found: {response.data}")
                
        elif status == 408:
            from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212APIException
            raise Trading212APIException(ERROR_MESSAGES["TIMEOUT"])
            
        elif status == 429:
            from hummingbot.connector.exchange.trading212.trading212_exchange import RateLimitExceeded
            raise RateLimitExceeded(ERROR_MESSAGES["RATE_LIMIT_EXCEEDED"])
            
        elif status >= 500:
            from hummingbot.connector.exchange.trading212.trading212_exchange import Trading212APIException
            raise Trading212APIException(f"Server error: {response.data}")
            
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> RESTResponse:
        """
        Make a GET request.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            
        Returns:
            RESTResponse object
        """
        request = RESTRequest(
            method="GET",
            url=url,
            params=params,
            headers=headers or {}
        )
        return await self._make_request(request)
        
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> RESTResponse:
        """
        Make a POST request.
        
        Args:
            url: Request URL
            data: Form data
            json_data: JSON data
            headers: Additional headers
            
        Returns:
            RESTResponse object
        """
        request = RESTRequest(
            method="POST",
            url=url,
            data=data,
            json_data=json_data,
            headers=headers or {}
        )
        return await self._make_request(request)
        
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> RESTResponse:
        """
        Make a DELETE request.
        
        Args:
            url: Request URL
            headers: Additional headers
            
        Returns:
            RESTResponse object
        """
        request = RESTRequest(
            method="DELETE",
            url=url,
            headers=headers or {}
        )
        return await self._make_request(request)
        
    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> RESTResponse:
        """
        Make a PUT request.
        
        Args:
            url: Request URL
            data: Form data
            json_data: JSON data
            headers: Additional headers
            
        Returns:
            RESTResponse object
        """
        request = RESTRequest(
            method="PUT",
            url=url,
            data=data,
            headers=headers or {}
        )
        return await self._make_request(request, json_body=json_data)
        
    def get_rate_limiter(self) -> RateLimiter:
        """
        Get the rate limiter instance.
        
        Returns:
            RateLimiter object
        """
        return self._rate_limiter
        
    def get_auth(self) -> Trading212Auth:
        """
        Get the authentication object.
        
        Returns:
            Trading212Auth object
        """
        return self._auth
        
    async def health_check(self) -> bool:
        """
        Perform a health check on the Trading212 API.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            from hummingbot.connector.exchange.trading212.trading212_constants import HEALTH_CHECK_ENDPOINT, REST_URL
            response = await self.get(f"{REST_URL}{HEALTH_CHECK_ENDPOINT}")
            return response.status == 200
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return False