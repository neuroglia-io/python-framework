import logging
from typing import Any

import jwt  # `poetry add pyjwt`, not `poetry add jwt`
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt.exceptions import ExpiredSignatureError, MissingRequiredClaimError

from api.services.oauth import Oauth2ClientCredentials, fix_public_key, get_public_key
from application.settings import app_settings

log = logging.getLogger(__name__)

auth_url = app_settings.swagger_ui_authorization_url if app_settings.local_dev else app_settings.jwt_authorization_url
token_url = app_settings.swagger_ui_token_url if app_settings.local_dev else app_settings.jwt_token_url

oauth2_client_credentials = Oauth2ClientCredentials(tokenUrl=token_url, scopes={app_settings.required_scope: "Default API RW Access"})
oauth2_authorization_code = OAuth2AuthorizationCodeBearer(authorizationUrl=auth_url, tokenUrl=token_url, scopes={app_settings.required_scope: app_settings.required_scope})

match app_settings.oauth2_scheme:
    case "client_credentials":
        oauth2_scheme = oauth2_client_credentials
    case "authorization_code":
        oauth2_scheme = oauth2_authorization_code
    case _:
        oauth2_scheme = oauth2_client_credentials


async def validate_token(token: str = Depends(oauth2_scheme)) -> Any:
    """Decodes the token, validate it using the JWT Authority's Signing Key, check required audience and expected issuer then returns its payload."""
    # log.debug(f"Validating token... '{token}'")

    def is_subset(arr1, arr2):
        set1 = set(arr1)
        set2 = set(arr2)
        return set1.issubset(set2) or set1 == set2

    if not app_settings.jwt_signing_key:
        # app_settings.jwt_signing_key = await get_public_key(app_settings.jwt_authority)
        raise Exception("Token can not be valided as the JWT Public Key is unknown!")

    app_settings.jwt_signing_key = fix_public_key(app_settings.jwt_signing_key)

    try:
        # payload = jwt.decode(jwt=token, key=app_settings.jwt_signing_key, algorithms=["RS256"], audience=app_settings.jwt_audience, issuer=app_settings.swagger_ui_jwt_authority)
        payload = jwt.decode(jwt=token, key=app_settings.jwt_signing_key, algorithms=["RS256"], audience=app_settings.jwt_audience)

        if "scope" in payload:
            required_scope = app_settings.required_scope.split()
            token_scopes = payload["scope"].split()
            if not is_subset(required_scope, token_scopes):
                raise HTTPException(status_code=403, detail="Insufficient scope")

        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except MissingRequiredClaimError as e:
        raise HTTPException(status_code=401, detail=f"JWT claims validation failed: {e}")
    except jwt.InvalidSignatureError as e:
        log.error(f"The JWT_SIGNING_KEY is WRONG!")
        if app_settings.local_dev:
            log.warning(f"Ignoring the JWT_SIGNING_KEY as we're in LOCAL_DEV!")
            payload = jwt.decode(jwt=token, algorithms=["RS256"], options={"verify_signature": False})
            return payload
        else:
            # try to refresh the public key
            app_settings.jwt_signing_key = await get_public_key(app_settings.jwt_authority)
            raise HTTPException(status_code=401, detail=f"JWT validation failed: {e} - refreshed the key, try again.")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT validation failed: {e}")
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=f"Invalid token: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Weird Invalid token: {e}")


def has_role(role: str):
    def decorator(token: dict = Depends(validate_token)):
        if "role" in token and role in token["role"]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid role {role}")

    return decorator


def has_claim(claim_name: str):
    def decorator(token: dict = Depends(validate_token)):
        if claim_name in token:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")

    return decorator


def has_single_claim_value(claim_name: str, claim_value: str):
    def decorator(token: dict = Depends(validate_token)):
        if claim_name in token and claim_value in token[claim_name]:
            return token
        else:
            raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")

    return decorator


def has_multiple_claims_value(claims: dict[str, str]):
    def decorator(token: dict = Depends(validate_token)):
        for claim_name, claim_value in claims.items():
            if claim_name not in token or claim_value not in token[claim_name]:
                raise HTTPException(status_code=403, detail=f"Missing or invalid {claim_name}")
        return token

    return decorator


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
