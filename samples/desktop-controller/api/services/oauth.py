import logging
import typing

import httpx
import jwt  # `poetry add pyjwt`, not `poetry add jwt`
from fastapi import HTTPException, Request
from fastapi.openapi.models import OAuthFlowClientCredentials
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jwt.algorithms import RSAAlgorithm
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

    async def __call__(self, request: Request) -> typing.Optional[str]:
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

    if not key.startswith("-----BEGIN PUBLIC KEY-----"):
        key = f"\n-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----\n"
    return key


async def get_public_key(jwt_authority: str):
    # http://localhost:8080 wont work when in Docker Desktop!
    # base_url = settings.jwt_authority_base_url_internal if settings.jwt_authority_base_url_internal else settings.jwt_authority_base_url
    # e.g. https://mykeycloak.com/auth/realms/mozart
    jwks_url = f"{jwt_authority}/protocol/openid-connect/certs"
    log.debug(f"get_public_key from {jwks_url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        keys = response.json()["keys"]
        for key in keys:
            if key.get("alg") == "RS256":
                # https://github.com/jpadilla/pyjwt/issues/359#issuecomment-406277697
                public_key = RSAAlgorithm.from_jwk(key)
                return public_key
        raise Exception("No key with 'alg' value of 'RS256' found")


# def validate_token(token: str = Depends(oauth2_scheme)):
#     if not settings.jwt_public_key:
#         raise Exception("Token can not be valided as the JWT Public Key is unknown!")
#     try:
#         # payload = jwt.decode(jwt=token, key=settings.jwt_public_key, algorithms=["RS256"], options={"verify_aud": False})
#         payload = jwt.decode(jwt=token, key=settings.jwt_public_key, algorithms=["RS256"], audience=settings.expected_audience)

#         def is_subset(arr1, arr2):
#             set1 = set(arr1)
#             set2 = set(arr2)
#             return set1.issubset(set2) or set1 == set2

#         if "scope" in payload:
#             required_scopes = settings.required_scopes.split()
#             token_scopes = payload["scope"].split()
#             if not is_subset(required_scopes, token_scopes):
#                 raise HTTPException(status_code=403, detail="Insufficient scope")

#         if settings.expected_audience not in payload["aud"]:
#             raise HTTPException(status_code=401, detail="Invalid audience")

#         return payload

#     except ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token has expired")
#     except MissingRequiredClaimError:
#         raise HTTPException(status_code=401, detail="JWT claims validation failed")
#     except HTTPException as e:
#         raise HTTPException(status_code=e.status_code, detail=f"Invalid token: {e.detail}")
#     except Exception as e:
#         raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# def has_role(role: str):
#     def decorator(token: dict = Depends(validate_token)):
#         if "role" in token and role in token["role"]:
#             return token
#         else:
#             raise HTTPException(status_code=403, detail=f"Missing or invalid role {role}")
#     return decorator


# def has_claim(claim_name: str):
#     def decorator(token: dict = Depends(validate_token)):
#         if claim_name in token:
#             return token
#         else:
#             raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
#     return decorator


# def has_single_claim_value(claim_name: str, claim_value: str):
#     def decorator(token: dict = Depends(validate_token)):
#         if claim_name in token and claim_value in token[claim_name]:
#             return token
#         else:
#             raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
#     return decorator


# def has_multiple_claims_value(claims: typing.Dict[str, str]):
#     def decorator(token: dict = Depends(validate_token)):
#         for claim_name, claim_value in claims.items():
#             if claim_name not in token or claim_value not in token[claim_name]:
#                 raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
#         return token
#     return decorator


# USAGE:
#
# @app.get(path="/api/v1/secured/claims_values",
#          tags=['Restricted'],
#          operation_id="requires_multiple_claims_each_with_specific_value",
#          response_description="A simple message object")
# async def requires_multiple_claims_each_with_specific_value(token: dict = Depends(has_multiple_claims_value(claims={
#     "custom_claim": "my_claim_value",
#     "role": "tester"
# }))):
#     """This route expects a valid token that includes the presence of multiple custom claims, each with a specific value; that is:
#     ```
#     ...
#     "custom_claim": [
#         "my_claim_value"
#     ],
#     "role": [
#         "tester"
#     ]
#     ...
#     ```

#     Args:
#         token (dict, optional): The JWT. Defaults to Depends(validate_token).

#     Returns:
#         Dict: Simple message and the token content
#     """
#     return {"message": "This route is restricted to users with custom claims `custom_claim: my_claim_value, role: tester`", "token": token}
