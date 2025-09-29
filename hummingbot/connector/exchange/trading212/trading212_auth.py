from typing import Dict

from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest


class Trading212Auth(AuthBase):
    """
    Trading212 uses simple API key in header (apiKeyHeader security scheme).
    We assume header name is 'Authorization' with 'ApiKey {key}' if not otherwise specified by docs.
    If docs require a different header (e.g., 'X-API-KEY'), adjust header_for_authentication accordingly.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        headers.update(self.header_for_authentication())
        request.headers = headers
        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        return request

    def header_for_authentication(self) -> Dict[str, str]:
        # Default to authorization header with ApiKey scheme
        return {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

