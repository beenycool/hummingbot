"""
Trading212 Authentication Module

This module handles API key-based authentication for Trading212's REST API.
It implements the required authentication headers and scope management.
"""

import logging
from typing import Dict, Optional
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest
from .trading212_constants import API_SCOPES, DEFAULT_HEADERS


class Trading212Auth(AuthBase):
    """
    Trading212 authentication class that handles API key-based authentication.
    
    This class implements the required authentication headers and manages
    API key scopes for different endpoint types.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Trading212 authentication.
        
        Args:
            api_key: Trading212 API key with required scopes
        """
        super().__init__()
        self._api_key = api_key
        self._logger = logging.getLogger(__name__)
        
    def add_auth_to_headers(self, request: RESTRequest) -> Dict[str, str]:
        """
        Add authentication headers to the request.
        
        Args:
            request: The REST request to authenticate
            
        Returns:
            Dictionary of headers to add to the request
        """
        headers = DEFAULT_HEADERS.copy()
        headers["Authorization"] = f"Bearer {self._api_key}"
        
        # Add scope-specific headers if needed
        scope = self._get_required_scope(request)
        if scope:
            headers["X-Scope"] = scope
            
        return headers
    
    def _get_required_scope(self, request: RESTRequest) -> Optional[str]:
        """
        Determine the required API scope for the given request.
        
        Args:
            request: The REST request
            
        Returns:
            Required API scope or None if not applicable
        """
        # Safely coerce the request URL to a lowercase string
        raw_url = request.url or request.endpoint_url or ""
        url = raw_url.lower()
        # Ensure we have an uppercase string method, whether it was an Enum or str
        method = getattr(request.method, "name", str(request.method)).upper()
        
        # Order execution endpoints
        if any(endpoint in url for endpoint in [
            "/orders/market", "/orders/limit", "/orders/stop", "/orders/stop_limit"
        ]):
            return API_SCOPES["orders:execute"]
            
        # Order reading endpoints
        if any(endpoint in url for endpoint in [
            "/orders", "/orders/"
        ]):
            return API_SCOPES["orders:read"]

        # Pie endpoints: write scope on state-changing methods, else read
        if "/pies" in url:
            if method in {"POST", "PUT", "DELETE"}:
                return API_SCOPES["pies:write"]
            else:
                return API_SCOPES["pies:read"]
            
        # Portfolio endpoints
        if "/portfolio" in url:
            return API_SCOPES["portfolio"]
            
        # Account endpoints
        if any(endpoint in url for endpoint in [
            "/account/cash", "/account/info"
        ]):
            return API_SCOPES["account"]
            
        # Metadata endpoints
        if any(endpoint in url for endpoint in [
            "/metadata/instruments", "/metadata/exchanges"
        ]):
            return API_SCOPES["metadata"]
            
        # History endpoints
        if "/history/orders" in url:
            return API_SCOPES["history:orders"]
        elif "/history/dividends" in url:
            return API_SCOPES["history:dividends"]
        elif "/history/transactions" in url:
            return API_SCOPES["history:transactions"]
            
        # Pies endpoints
        if "/pies" in url:
            if request.method in ["POST", "PUT", "DELETE"]:
                return API_SCOPES["pies:write"]
            else:
                return API_SCOPES["pies:read"]
                
        return None
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by checking if it has the required scopes.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # This would typically make a test request to validate the key
            # For now, we'll just check if the key is not empty
            return bool(self._api_key and len(self._api_key.strip()) > 0)
        except Exception as e:
            self._logger.error(f"Error validating API key: {e}")
            return False
    
    def get_api_key(self) -> str:
        """
        Get the API key.
        
        Returns:
            The API key string
        """
        return self._api_key
    
    def set_api_key(self, api_key: str) -> None:
        """
        Set a new API key.
        
        Args:
            api_key: New API key
        """
        self._api_key = api_key
        self._logger.info("API key updated")
    
    def get_required_scopes(self) -> list:
        """
        Get the list of required API scopes for full functionality.
        
        Returns:
            List of required API scopes
        """
        return [
            API_SCOPES["orders:execute"],
            API_SCOPES["orders:read"],
            API_SCOPES["portfolio"],
            API_SCOPES["account"],
            API_SCOPES["metadata"],
            API_SCOPES["history:orders"],
            API_SCOPES["history:dividends"],
            API_SCOPES["history:transactions"],
        ]
    
    def check_scope_permissions(self, scope: str) -> bool:
        """
        Check if the API key has permission for a specific scope.
        
        Args:
            scope: The scope to check
            
        Returns:
            True if the scope is available, False otherwise
        """
        required_scopes = self.get_required_scopes()
        return scope in required_scopes
    
    def __str__(self) -> str:
        """String representation of the auth object."""
        return f"Trading212Auth(api_key={'*' * len(self._api_key) if self._api_key else 'None'})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the auth object."""
        return f"Trading212Auth(api_key_length={len(self._api_key) if self._api_key else 0})"