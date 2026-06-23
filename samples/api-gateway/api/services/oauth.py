import logging
from typing import Optional

import httpx
import jwt  # `poetry add pyjwt`, not `poetry add jwt`
from fastapi import HTTPException, Request
from fastapi.openapi.models import OAuthFlowClientCredentials
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from starlette.status import HTTP_401_UNAUTHORIZED

log = logging.getLogger(__name__)


class Oauth2ClientCredentialsSettings(str):
    tokenUrl: str = ""

    def __repr__(self) -> str:
        return super().__repr__()


class Oauth2ClientCredentials(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str | None = None,
        scopes: dict | None = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(clientCredentials=OAuthFlowClientCredentials(tokenUrl=tokenUrl, scopes=scopes))
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        """Extracts the Bearer token from the Authorization Header"""
        authorization: str | None = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


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


async def get_public_key(jwt_authority: str) -> str | None:
    """Downloads the public key of a Keycloak Realm.

    Args:
        jwt_authority (str): The base URL of the Keycloak Realm which returns a JSON with .public_key

    Returns:
        str: The public key encoded as a string
    """
    log.debug(f"get_public_key from {jwt_authority}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jwt_authority)
            response.raise_for_status()
        except httpx.ConnectError as e:
            return None
        if response:
            key = response.json()["public_key"]
            log.debug(f"Public key for {jwt_authority} is {key}")
            return key
        return None
