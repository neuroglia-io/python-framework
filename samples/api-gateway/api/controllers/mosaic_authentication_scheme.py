import logging
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from application.settings import app_settings

log = logging.getLogger(__name__)

api_key_scheme = APIKeyHeader(name="authorization", description="Requires valid API keys known by Mosaic")


async def validate_mosaic_authentication(api_key: str = Depends(api_key_scheme)) -> Any:
    """Extracts the Authorization header and validates whether it in the expected values."""
    log.debug(f"Validating HTTP Authorization Header: '{api_key}'")

    if api_key not in app_settings.mosaic_api_keys:
        raise HTTPException(status_code=403, detail=f"Invalid API KEY: {api_key}")

    return api_key
