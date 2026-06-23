"""FastAPI dependencies for authentication using DualAuthService.

This module provides FastAPI dependency functions that integrate with DualAuthService
for both JWT and session-based authentication, while maintaining OAuth2 scheme
integration for Swagger UI documentation.
"""

import logging
from typing import Any, Optional

from application.settings import app_settings
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

log = logging.getLogger(__name__)


def _get_oauth2_scheme():
    """Create OAuth2 scheme with dynamically computed URLs from settings.

    This function is called at import time to create the oauth2_scheme instance.
    """
    # Access computed fields from settings instance
    if app_settings.local_dev:
        auth_url = str(app_settings.swagger_ui_authorization_url)
        token_url = str(app_settings.swagger_ui_token_url)
    else:
        auth_url = str(app_settings.jwt_authorization_url)
        token_url = str(app_settings.jwt_token_url)

    return OAuth2AuthorizationCodeBearer(
        authorizationUrl=auth_url,
        tokenUrl=token_url,
        scopes={app_settings.required_scope: app_settings.required_scope},
        auto_error=True,
    )


# Create OAuth2 scheme for Swagger UI integration
oauth2_scheme = _get_oauth2_scheme()


def get_auth_service(request: Request):
    """Get DualAuthService from request state (injected by middleware).

    Args:
        request: FastAPI request with auth_service in state

    Returns:
        DualAuthService instance

    Raises:
        HTTPException: If auth service not found in request state
    """
    if not hasattr(request.state, "auth_service"):
        log.error("DualAuthService not found in request.state - middleware not configured?")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication service not available",
        )
    return request.state.auth_service


async def get_current_user_from_jwt(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Extract and validate JWT token, return user info.

    This dependency uses DualAuthService for JWT verification with:
    - RS256 verification via JWKS (Keycloak standard)
    - HS256 fallback for legacy tokens
    - User claim normalization

    Args:
        request: FastAPI request with auth_service in state
        token: Bearer token from Authorization header

    Returns:
        User info dict with normalized claims:
        {
            "sub": str,
            "username": str,
            "user_id": str,
            "email": str,
            "name": str,
            "roles": list[str],
            "department": str | None,
            "legacy": bool
        }

    Raises:
        HTTPException: If token is invalid or expired
    """
    auth_service = get_auth_service(request)
    user = auth_service.get_user_from_jwt(token)

    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_from_session(request: Request) -> dict[str, Any]:
    """Extract user info from session cookie.

    This dependency uses DualAuthService for session management with:
    - Redis or in-memory session store
    - Automatic session expiration
    - Token refresh support

    Args:
        request: FastAPI request with session cookie

    Returns:
        User info dict from session

    Raises:
        HTTPException: If session is invalid or expired
    """
    auth_service = get_auth_service(request)
    session_id = request.session.get("session_id")

    if not session_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = auth_service.get_user_from_session(session_id)

    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    return user


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Get current user from either JWT or session (dual authentication).

    This dependency tries JWT first, then falls back to session authentication.
    Useful for endpoints that support both authentication methods.

    Args:
        request: FastAPI request
        token: Optional Bearer token from Authorization header

    Returns:
        User info dict

    Raises:
        HTTPException: If neither JWT nor session authentication succeeds
    """
    auth_service = get_auth_service(request)

    # Try JWT authentication first
    if token:
        user = auth_service.get_user_from_jwt(token)
        if user:
            return user

    # Fall back to session authentication
    session_id = request.session.get("session_id")
    if session_id:
        user = auth_service.get_user_from_session(session_id)
        if user:
            return user

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: str):
    """Dependency factory for role-based access control.

    Usage:
        @get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role("admin"))):
            ...

    Args:
        required_role: Role name required for access

    Returns:
        FastAPI dependency function that validates user has required role
    """

    async def role_checker(user: dict = Depends(get_current_user_from_jwt)) -> dict:
        user_roles = user.get("roles", [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {required_role}",
            )
        return user

    return role_checker


def require_any_role(*required_roles: str):
    """Dependency factory for role-based access control (any of multiple roles).

    Usage:
        @get("/staff")
        async def staff_endpoint(user: dict = Depends(require_any_role("admin", "manager"))):
            ...

    Args:
        required_roles: One or more role names, user must have at least one

    Returns:
        FastAPI dependency function that validates user has at least one required role
    """

    async def role_checker(user: dict = Depends(get_current_user_from_jwt)) -> dict:
        user_roles = user.get("roles", [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"User does not have any of required roles: {', '.join(required_roles)}",
            )
        return user

    return role_checker


def require_all_roles(*required_roles: str):
    """Dependency factory for role-based access control (all roles required).

    Usage:
        @get("/super-admin")
        async def super_admin_endpoint(user: dict = Depends(require_all_roles("admin", "super-user"))):
            ...

    Args:
        required_roles: One or more role names, user must have all

    Returns:
        FastAPI dependency function that validates user has all required roles
    """

    async def role_checker(user: dict = Depends(get_current_user_from_jwt)) -> dict:
        user_roles = user.get("roles", [])
        if not all(role in user_roles for role in required_roles):
            missing_roles = [role for role in required_roles if role not in user_roles]
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"User is missing required roles: {', '.join(missing_roles)}",
            )
        return user

    return role_checker


# Legacy compatibility - maps old validate_token to new dependency
# Use get_current_user_from_jwt instead for new code
validate_token = get_current_user_from_jwt
