import datetime
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
import jwt
from neuroglia.hosting.abstractions import ApplicationSettings
from neuroglia.serialization.json import JsonSerializer
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class ApiClientException(Exception):
    """Exception raised for errors in the ApiClient."""


class ApiClient(ABC):
    base_url: str

    headers: dict[str, str]

    json_serializer: JsonSerializer

    endpoints: dict[str, tuple[str, str]]

    default_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    @abstractmethod
    def call_api(self, method: str, endpoint: str) -> Any:
        raise NotImplementedError()

    @abstractmethod
    async def call_api_async(self, method: str, endpoint: str) -> Any:
        raise NotImplementedError()

    def set_base_url(self, base_url: str) -> Any:
        # TODO: ADD VALIDATION
        self.base_url = base_url


class UnsecureApiClientOptions(BaseModel):
    base_url: str


class UnsecureApiClient(ApiClient):
    def __init__(
        self, unsecure_api_options: UnsecureApiClientOptions, json_serializer: JsonSerializer
    ):
        """
        Initializes the UnsecureApiClient with the given serializer.

        Args:
            json_serializer (JsonSerializer): Serializer for JSON data.
        """
        self.headers = self.default_headers.copy()
        self.json_serializer = json_serializer
        self.base_url = unsecure_api_options.base_url

        super().__init__()

    def _call_api(self, method: str, endpoint: str, params=None, data=None, headers=None) -> Any:
        """
        Makes an API call to an unsecure API.

        Args:
            method: HTTP method for the request (GET, POST, etc.)
            endpoint: API endpoint to call (relative to base URL).
            params: Additional query parameters for the request.
            data: Data to be sent in the request body (for POST, PUT).
            headers: Additional headers to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            ApiClientException: If the API call fails.
        """
        req_id = str(uuid.uuid4())
        url = urljoin(self.base_url, endpoint)
        response = None
        headers = (
            {"Content-Type": "application/json"}
            if headers is None
            else headers.update({"Content-Type": "application/json"})
        )

        try:
            log.debug(
                f"Req#{req_id}: Calling {method} {url} {params} type(data):{type(data)} headers: {headers}"
            )
            if data is not None:
                data = self.json_serializer.serialize(data)
                log.debug(f"Req#{req_id}: Serialized data: {data}")

            match method:
                case "GET":
                    response = httpx.get(url, params=params, headers=headers)
                case "POST":
                    response = httpx.post(url, params=params, data=data, headers=headers)
                case "PATCH":
                    response = httpx.patch(url, data=data, headers=headers)
                case "PUT":
                    response = httpx.put(url, data=data, headers=headers)
                case "DELETE":
                    response = httpx.delete(url, headers=headers)
                case _:
                    raise ApiClientException(f"Unsupported HTTP method: {method}")

            if response:
                log.debug(f"Res#{req_id}: Response {response}")
                response.raise_for_status()
                if response.text:
                    return response.json()
                else:
                    return response.status_code

        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            raise ApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(
                    f"Req#{req_id}: HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}"
                )
            else:
                log.debug(f"Req#{req_id}: NO RESPONSE")


class HttpBasicAuthApiClientOptions(BaseModel):
    base_url: str

    username: str

    password: str


class HttpBasicApiClient(ApiClient):
    base_url: str

    username: str

    password: str

    def __init__(
        self, http_basic_api_options: HttpBasicAuthApiClientOptions, json_serializer: JsonSerializer
    ):
        """
        Initializes the HttpBasicApiClient with the given options and serializer.

        Args:
            http_basic_api_options (HttpBasicAuthApiClientOptions): Configuration options for the client.
            json_serializer (JsonSerializer): Serializer for JSON data.
        """
        self.headers = self.default_headers.copy()
        self.json_serializer = json_serializer
        self.base_url = http_basic_api_options.base_url
        self.username = http_basic_api_options.username
        self.password = http_basic_api_options.password
        super().__init__()

    def call_api(self, method: str, endpoint: str, params=None, data=None, headers=None) -> Any:
        """
        Makes an API call to an API protected by HTTP Basic Auth.

        Args:
            method: HTTP method for the request (GET, POST, etc.)
            endpoint: API endpoint to call (relative to base URL).
            params: Additional query parameters for the request.
            data: Data to be sent in the request body (for POST, PUT).
            headers: Additional headers to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            ApiClientException: If the API call fails.
        """
        url = urljoin(self.base_url, endpoint)
        response = None
        headers = (
            {"Content-Type": "application/json"}
            if headers is None
            else headers.update({"Content-Type": "application/json"})
        )
        auth = (self.username, self.password)

        try:
            log.debug(
                f"Calling {method} {url} {params} type(data):{type(data)} headers: {headers} auth.username: {auth[0]}"
            )
            if data is not None:
                data = self.json_serializer.serialize(data)
                log.debug(f"Serialized data: {data}")

            match method:
                case "GET":
                    response = httpx.get(url, params=params, headers=headers, auth=auth)
                case "POST":
                    response = httpx.post(url, params=params, data=data, headers=headers, auth=auth)
                case "PATCH":
                    response = httpx.patch(url, data=data, headers=headers, auth=auth)
                case "PUT":
                    response = httpx.put(url, data=data, headers=headers, auth=auth)
                case "DELETE":
                    response = httpx.delete(url, headers=headers, auth=auth)
                case _:
                    raise ApiClientException(f"Unsupported HTTP method: {method}")

            if response:
                log.debug(f"Response {response}")
                response.raise_for_status()
                if response.text:
                    return response.json(), response.status_code
                else:
                    return {}, response.status_code

        except httpx.HTTPStatusError as e:
            raise ApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(
                    f"HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}"
                )
            else:
                log.debug(f"NO RESPONSE")

    async def call_api_async(
        self,
        method: str,
        endpoint: str,
        path_params: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
        data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> tuple[Any, int]:
        """
        Internal async method to call the Mozart API.

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The API endpoint to call.
            params (dict, optional): Query parameters for the request.
            data (Any, optional): The data to send in the request body.
            headers (dict, optional): Additional headers to send with the request.

        Returns:
            Any: The response from the API call.

        Raises:
            MozartSessionManagerApiClientException: If the API request fails.
        """
        if path_params:
            endpoint = endpoint.format(**path_params)

        url = urljoin(self.base_url, endpoint)
        response = None
        new_headers = {"Content-Type": "application/json"}
        if headers is not None:
            new_headers.update(headers)
        auth = (self.username, self.password)

        try:
            log.debug(
                f"Calling {method} {url} {params} type(data):{type(data)} headers: {new_headers} auth.username: {auth[0]}"
            )
            if data is not None:
                data = self.json_serializer.serialize(data)
                log.debug(f"Serialized data: {data}")

            async with httpx.AsyncClient() as client:
                match method:
                    case "GET":
                        response = await client.get(
                            url, params=params, headers=new_headers, auth=auth, timeout=timeout
                        )
                    case "POST":
                        response = await client.post(
                            url,
                            params=params,
                            data=data,
                            headers=new_headers,
                            auth=auth,
                            timeout=timeout,
                        )
                    case "PATCH":
                        response = await client.patch(
                            url,
                            params=params,
                            data=data,
                            headers=new_headers,
                            auth=auth,
                            timeout=timeout,
                        )
                    case "PUT":
                        response = await client.put(
                            url,
                            params=params,
                            data=data,
                            headers=new_headers,
                            auth=auth,
                            timeout=timeout,
                        )
                    case "DELETE":
                        response = await client.delete(
                            url, params=params, headers=new_headers, auth=auth, timeout=timeout
                        )
                    case _:
                        raise ApiClientException(f"Unsupported HTTP method: {method}")

            log.debug(f"Response {response}")
            response.raise_for_status()
            if response.text:
                return response.json(), response.status_code
            else:
                return {}, response.status_code

        except httpx.HTTPStatusError as e:
            raise ApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(
                    f"HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}"
                )
            else:
                log.debug(" NO RESPONSE")


class OAuthApiClientException(Exception):
    """Exception raised for errors in the OAuthApiClient."""


class OauthClientCredentialsAuthApiOptions(BaseModel):
    base_url: str

    client_id: str

    client_secret: str

    token_url: str

    scopes: Optional[list[str]] = Field(default_factory=list)

    token: Optional[str] = None

    refresh_token: Optional[str] = None

    oauth2_scheme: str = "client_credentials"  # or authorization_code


class OauthApiClient(ApiClient):
    client_id: str

    client_secret: str

    token_url: str

    scopes: Optional[list[str]]

    oauth2_scheme: Optional[str] = "client_credentials"  # or authorization_code

    token: Optional[str] = None

    refresh_token: Optional[str] = None

    app_settings: ApplicationSettings

    def __init__(
        self,
        api_client_options: OauthClientCredentialsAuthApiOptions,
        json_serializer: JsonSerializer,
        app_settings: ApplicationSettings,
    ):
        self.headers = self.default_headers.copy()
        self.json_serializer = json_serializer
        self.base_url = api_client_options.base_url
        self.app_settings = app_settings

        self.client_id = api_client_options.client_id
        self.client_secret = api_client_options.client_secret
        self.token_url = api_client_options.token_url
        self.scopes = api_client_options.scopes
        self.oauth2_scheme = api_client_options.oauth2_scheme or "client_credentials"
        self.token = None
        self.refresh_token = None

    def call_api(
        self,
        method: str,
        endpoint: str,
        path_params: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
        data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[Any, int]:
        """
        Internal method to call the Mozart API.

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The API endpoint to call.
            params (dict, optional): Query parameters for the request.
            data (Any, optional): The data to send in the request body.
            headers (dict, optional): Additional headers to send with the request.

        Returns:
            Any: The response from the API call.

        Raises:
            MozartSessionManagerApiClientException: If the API request fails.
        """
        if path_params:
            endpoint = endpoint.format(**path_params)

        url = urljoin(self.base_url, endpoint)
        response = None
        try:
            log.debug(f"Calling {method} {url} {params} type(data):{type(data)}")
            if data is not None:
                data = self.json_serializer.serialize(data)
                log.debug(f"Serialized data: {data}")

            self.headers.update(self.refresh_authorization_header())
            match method:
                case "GET":
                    response = httpx.get(url, params=params, headers=self.headers)
                case "POST":
                    response = httpx.post(url, params=params, data=data, headers=self.headers)
                case "PATCH":
                    response = httpx.patch(url, params=params, data=data, headers=self.headers)
                case "PUT":
                    response = httpx.put(url, params=params, data=data, headers=self.headers)
                case "DELETE":
                    response = httpx.delete(url, params=params, headers=self.headers)
                case _:
                    raise OAuthApiClientException(f"Unsupported HTTP method: {method}")

            log.debug(f"Response {response}")
            response.raise_for_status()
            if response.text:
                return response.json(), response.status_code
            else:
                return {}, response.status_code

        except httpx.HTTPStatusError as e:
            raise OAuthApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(
                    f"HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}"
                )
            else:
                log.debug(" NO RESPONSE")

    async def call_api_async(
        self,
        method: str,
        endpoint: str,
        path_params: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
        data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[Any, int]:
        """
        Internal async method to call the Mozart API.

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The API endpoint to call.
            params (dict, optional): Query parameters for the request.
            data (Any, optional): The data to send in the request body.
            headers (dict, optional): Additional headers to send with the request.

        Returns:
            Any: The response from the API call.

        Raises:
            MozartSessionManagerApiClientException: If the API request fails.
        """
        if path_params:
            endpoint = endpoint.format(**path_params)

        url = urljoin(self.base_url, endpoint)
        response = None
        try:
            log.debug(f"Calling {method} {url} {params} type(data):{type(data)}")
            if data is not None:
                data = self.json_serializer.serialize(data)
                log.debug(f"Serialized data: {data}")

            auth_header = await self.refresh_authorization_header_async()
            self.headers.update(auth_header)
            log.debug(f"Headers: {self.headers.keys()}")
            async with httpx.AsyncClient() as client:
                match method:
                    case "GET":
                        response = await client.get(url, params=params, headers=self.headers)
                    case "POST":
                        response = await client.post(
                            url, params=params, data=data, headers=self.headers
                        )
                    case "PATCH":
                        response = await client.patch(
                            url, params=params, data=data, headers=self.headers
                        )
                    case "PUT":
                        response = await client.put(
                            url, params=params, data=data, headers=self.headers
                        )
                    case "DELETE":
                        response = await client.delete(url, params=params, headers=self.headers)
                    case _:
                        raise OAuthApiClientException(f"Unsupported HTTP method: {method}")

            log.debug(f"Response {response}")
            response.raise_for_status()
            if response.text:
                return response.json(), response.status_code
            else:
                return {}, response.status_code

        except httpx.HTTPStatusError as e:
            raise OAuthApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(
                    f"HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}"
                )
            else:
                log.debug(" No Response or Error status code.")

    def refresh_authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    async def refresh_authorization_header_async(self) -> dict[str, str]:
        token = await self._get_access_token_async()
        return {"Authorization": f"Bearer {token}"}

    def _get_access_token(self) -> Optional[str]:
        if self.token is None or self._is_token_expired(self.token):
            self._refresh_tokens()
        return self.token

    async def _get_access_token_async(self) -> Optional[str]:
        # log.debug(f"Old Token: {self.token}")
        if self.token is None or self._is_token_expired(self.token):
            await self._refresh_tokens_async()
        log.debug(f"New Token: {self.token}")
        return self.token

    def _refresh_tokens(self):
        try:
            log.debug(f"Refreshing Token from {self.token_url} for client {self.client_id}")
            payload = {
                "grant_type": self.oauth2_scheme,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scopes,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = httpx.post(self.token_url, data=payload, headers=headers)
            response.raise_for_status()
            new_token_data = response.json()
            self.token = new_token_data.get("access_token")
            self.refresh_token = new_token_data.get(
                "refresh_token", self.refresh_token
            )  # Update refresh token if provided
            log.info(f"Refreshed Token from {self.token_url} for client {self.client_id}")
        except Exception as ex:
            raise OAuthApiClientException(f"while refreshing token to {self.token_url}: {ex}")

    async def _refresh_tokens_async(self):
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "grant_type": self.oauth2_scheme,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": ",".join(self.scopes),
                }
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.token_url, data=payload, headers=headers)
                    response.raise_for_status()
                    new_token_data = response.json()

                if new_token_data:
                    self.token = new_token_data.get("access_token")
                    self.refresh_token = new_token_data.get(
                        "refresh_token", self.refresh_token
                    )  # Update refresh token if provided
                    log.info(f"Refreshed Token from {self.token_url} for client {self.client_id}")
            except Exception as ex:
                raise OAuthApiClientException(f"while refreshing token to {self.token_url}: {ex}")

    def _is_token_expired(self, token: str, leeway: int = 1) -> bool:
        """
        This function checks if the JWT token is expired.

        Args:
            exp: The decoded 'exp' token claims
            leeway: A timedelta object representing a buffer to account for clock skew (optional).

        Returns:
            True if the token is expired, False otherwise.
        """
        try:
            payload = self._decode_token(token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return True

        if payload and "exp" not in payload:
            log.debug(f"Token expiration claim is not set... Refreshing.")
            return True
        exp = payload["exp"]
        leeway_timedelta = datetime.timedelta(seconds=leeway)
        expiration_time = datetime.datetime.fromtimestamp(exp).replace(tzinfo=timezone.utc)
        current_time = datetime.datetime.now(timezone.utc) - leeway_timedelta
        expired = expiration_time < current_time
        log.debug(f"Token is {'not' if not expired else ''} expired...")
        return expired

    def _decode_token(self, token: str) -> Any:
        try:
            self.app_settings.jwt_signing_key = fix_public_key(self.app_settings.jwt_signing_key)  # type: ignore
            payload = jwt.decode(jwt=token, key=self.app_settings.jwt_signing_key, algorithms=["RS256"])  # type: ignore
            return payload
        except jwt.InvalidKeyError as e:
            log.error(f"Invalid Key: {e}")
            raise jwt.InvalidKeyError(e)
        except jwt.ExpiredSignatureError as e:
            log.error(f"Token has expired: {e}")
            raise jwt.ExpiredSignatureError(e)
        except jwt.InvalidTokenError as e:
            log.error(f"Invalid token: {e}")
            raise jwt.InvalidTokenError(e)


def fix_public_key(key: str) -> str:
    """Fixes the format of a public key by adding headers and footers if missing.

    Args:
        key: The public key string.

    Returns:
        The public key string with proper formatting.
    """

    if "-----BEGIN PUBLIC KEY-----" not in key:
        key = f"\n-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----\n"
    return key
