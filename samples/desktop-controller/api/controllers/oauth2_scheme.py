import logging
from typing import Any

import jwt  # `poetry add pyjwt`, not `poetry add jwt`
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt.exceptions import ExpiredSignatureError, MissingRequiredClaimError

from api.services.oauth import Oauth2ClientCredentials, fix_public_key
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
    """Decodes the token using the JWT Authority's Signing Key and returns its payload."""
    log.debug(f"Validating token... '{token}'")

    if not app_settings.jwt_signing_key:
        # jwt_signing_key = get_public_key(app_settings.jwt_authority)
        raise Exception("Token can not be valided as the JWT Public Key is unknown!")

    jwt_signing_key = fix_public_key(app_settings.jwt_signing_key)
    try:
        # payload = jwt.decode(jwt=token, key=settings.jwt_public_key, algorithms=["RS256"], options={"verify_aud": False})

        # enforce audience:
        payload = jwt.decode(jwt=token, key=jwt_signing_key, algorithms=["RS256"], audience=app_settings.jwt_audience)

        def is_subset(arr1, arr2):
            set1 = set(arr1)
            set2 = set(arr2)
            return set1.issubset(set2) or set1 == set2

        # enforce required scope in the token
        if "scope" in payload:
            required_scope = app_settings.required_scope.split()
            token_scopes = payload["scope"].split()
            if not is_subset(required_scope, token_scopes):
                raise HTTPException(status_code=403, detail="Insufficient scope")

        # enforce required audience in the token if not done in jwt.decode...
        # if app_settings.jwt_audience not in payload["aud"]:
        #     raise HTTPException(status_code=401, detail="Invalid audience")

        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except MissingRequiredClaimError as e:
        raise HTTPException(status_code=401, detail=f"JWT claims validation failed: {e}")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT validation failed: {e}")
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=f"Invalid token: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Weird Invalid token: {e}")
