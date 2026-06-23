"""Authentication service with dual authentication support.

Enhancements:
- Supports RS256 verification of Keycloak issued access tokens using JWKS.
- Falls back to deprecated HS256 secret only if token header/algorithm indicates HS256.
- Caches JWKS for configurable TTL to avoid frequent network calls.
"""
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

import httpx
import jwt
from application.settings import app_settings
from infrastructure import InMemorySessionStore, RedisSessionStore, SessionStore
from jwt import PyJWTError, algorithms
from starlette.responses import Response

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

    from neuroglia.hosting.web import WebApplicationBuilder


class DualAuthService:
    """Service for authentication operations supporting both session and JWT auth."""

    _log = logging.getLogger("AuthService")

    def __init__(self, session_store: SessionStore):
        """Initialize auth service with session store from DI.

        Args:
            session_store: Session store instance injected by DI container
        """
        self.session_store = session_store

    def get_user_from_session(self, session_id: str) -> dict | None:
        """Get user info from session ID.

        Args:
            session_id: Session ID from cookie

        Returns:
            User info dict or None if session not found
        """
        if not session_id:
            return None

        session = self.session_store.get_session(session_id)
        if session:
            return session.get("user_info")

        return None

    # JWKS cache (in-memory). Structure: {"keys": [...], "fetched_at": epoch_seconds}
    _jwks_cache: dict | None = None
    _jwks_ttl_seconds: int = 3600  # 1 hour cache TTL

    def _jwks_url(self) -> str:
        """Construct JWKS endpoint URL for the configured realm."""
        return f"{app_settings.keycloak_server_url}/realms/{app_settings.keycloak_realm}/protocol/openid-connect/certs"

    def _fetch_jwks(self) -> dict | None:
        """Fetch JWKS from Keycloak with basic caching."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache.get("fetched_at", 0) < self._jwks_ttl_seconds):
            return self._jwks_cache
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(self._jwks_url())
                resp.raise_for_status()
                data = resp.json()
                if "keys" in data:
                    self._jwks_cache = {"keys": data["keys"], "fetched_at": now}
                    return self._jwks_cache
        except Exception as e:
            self._log.warning(f"JWKS fetch failed: {e}")
            return None
        return None

    def _get_public_key_for_token(self, token: str) -> Optional[Any]:
        """Resolve RSA public key from JWKS using the token's 'kid' header.

        Returns PEM-compatible key object usable by PyJWT or None if not found.
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            self._log.debug(f"Failed to parse token header: {e}")
            return None
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg")
        if not kid or not alg:
            return None
        if alg != "RS256":  # We only handle RS256 here; HS256 fallback handled elsewhere
            return None
        jwks = self._fetch_jwks()
        if not jwks:
            return None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                try:
                    return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))  # returns key object
                except Exception:
                    return None
        return None

    def get_user_from_jwt(self, token: str) -> dict | None:
        """Get user info from JWT token (prefers RS256 Keycloak access token).

        Verification strategy:
        1. Attempt RS256 verification via JWKS (Keycloak standard access token).
        2. If header indicates HS256 OR RS256 fails due to missing JWKS, attempt legacy secret decode (deprecated).
        3. Return enriched user info mapping including roles from realm_access if present.
        """
        if not token:
            return None

        # Try RS256 path first
        public_key = self._get_public_key_for_token(token)
        rs256_payload = None
        if public_key:
            try:
                verify_aud = app_settings.verify_audience and bool(app_settings.expected_audience)
                options = {"verify_aud": verify_aud}
                rs256_payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience=app_settings.expected_audience if verify_aud else None,
                    options=options,
                )
                if app_settings.verify_issuer and app_settings.expected_issuer:
                    iss = rs256_payload.get("iss")
                    if iss != app_settings.expected_issuer:
                        self._log.info(f"Issuer mismatch: got '{iss}', expected '{app_settings.expected_issuer}'")
                        rs256_payload = None
            except jwt.ExpiredSignatureError:
                self._log.info("RS256 token expired")
            except jwt.InvalidTokenError as e:
                self._log.info(f"RS256 token invalid: {e}")

        if rs256_payload:
            return self._map_claims(rs256_payload)

        # Fallback: legacy HS256 secret (deprecated)
        try:
            unverified = jwt.get_unverified_header(token)
            if unverified.get("alg") == app_settings.jwt_algorithm:
                legacy_payload = jwt.decode(
                    token,
                    app_settings.jwt_secret_key,
                    algorithms=[app_settings.jwt_algorithm],
                    options={"verify_aud": False},
                )
                return self._map_claims(legacy_payload, legacy=True)
        except jwt.ExpiredSignatureError:
            self._log.info("Legacy HS256 token expired")
        except jwt.InvalidTokenError as e:
            self._log.debug(f"Legacy HS256 token invalid: {e}")
        except Exception as e:
            self._log.debug(f"Legacy HS256 decode error: {e}")
        return None

    def _map_claims(self, payload: dict, legacy: bool = False) -> dict:
        """Normalize JWT claims to internal user representation."""
        # Roles may appear under realm_access.roles in Keycloak access tokens
        roles: list[Any] = []
        if isinstance(payload.get("realm_access"), dict):
            roles = payload.get("realm_access", {}).get("roles", []) or []
        elif isinstance(payload.get("roles"), list):
            roles = list(payload.get("roles") or [])
        return {
            "sub": payload.get("sub"),
            "username": payload.get("preferred_username") or payload.get("username"),
            "user_id": payload.get("user_id") or payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name") or payload.get("given_name"),
            "roles": roles,
            "department": payload.get("department"),
            "legacy": legacy,
        }

    def authenticate(self, session_id: str | None = None, token: str | None = None) -> dict | None:
        """Authenticate user via session or JWT token.

        Args:
            session_id: Optional session ID from cookie
            token: Optional JWT Bearer token

        Returns:
            User info dict or None if authentication fails
        """
        # Try session-based authentication first (OAuth2)
        if session_id:
            session = self.session_store.get_session(session_id) if session_id else None
            if session:
                # Auto-refresh logic if access token near expiry and refresh token available
                tokens = session.get("tokens", {})
                access_token = tokens.get("access_token")
                refresh_token = tokens.get("refresh_token")
                exp_near = False
                if access_token:
                    try:
                        unverified = jwt.decode(access_token, options={"verify_signature": False})
                        exp = unverified.get("exp")
                        if isinstance(exp, int):
                            import time as _t

                            remaining = exp - int(_t.time())
                            if remaining < app_settings.refresh_auto_leeway_seconds and refresh_token:
                                exp_near = True
                    except (PyJWTError, ValueError, TypeError):
                        exp_near = False
                if exp_near and refresh_token:
                    try:
                        # Perform refresh
                        # Keycloak token endpoint via httpx (avoid circular import of controller)
                        token_url = f"{app_settings.keycloak_server_url}/realms/{app_settings.keycloak_realm}/protocol/openid-connect/token"
                        with httpx.Client(timeout=5.0) as client:
                            resp = client.post(
                                token_url,
                                data={
                                    "grant_type": "refresh_token",
                                    "refresh_token": refresh_token,
                                    "client_id": app_settings.keycloak_client_id,
                                    "client_secret": app_settings.keycloak_client_secret,
                                },
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                            )
                            if resp.status_code == 200:
                                new_tokens = resp.json()
                                if "refresh_token" not in new_tokens:
                                    new_tokens["refresh_token"] = refresh_token
                                if "id_token" not in new_tokens and tokens.get("id_token"):
                                    new_tokens["id_token"] = tokens.get("id_token")
                                self.session_store.refresh_session(session_id, new_tokens)
                                session = self.session_store.get_session(session_id)
                            else:
                                self._log.info(f"Auto-refresh failed status={resp.status_code}")
                    except Exception as e:
                        self._log.info(f"Auto-refresh error: {e}")
                user = session.get("user_info") if session else None
                if user:
                    return user

        # Try JWT Bearer token authentication
        if token:
            user = self.get_user_from_jwt(token)
            if user:
                return user

        return None

    def check_roles(self, user: dict, required_roles: list[str]) -> bool:
        """Check if user has any of the required roles.

        Args:
            user: User info dictionary
            required_roles: List of required role names

        Returns:
            True if user has at least one required role, False otherwise
        """
        user_roles = user.get("roles", [])
        return any(role in user_roles for role in required_roles)

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> None:
        """Configure authentication services in the application builder.

        This method:
        1. Creates and registers the appropriate SessionStore (Redis or in-memory)
        2. Creates a DualAuthService instance with the session store
        3. Pre-warms the JWKS cache for faster first request
        4. Registers both services in the DI container

        Args:
            builder: WebApplicationBuilder instance for service registration
        """
        log = logging.getLogger(__name__)

        # Create session store based on configuration
        session_store: SessionStore
        if app_settings.redis_enabled:
            log.info(f"🔴 Using RedisSessionStore (url={app_settings.redis_url})")
            try:
                session_store = RedisSessionStore(
                    redis_url=app_settings.redis_url,
                    session_timeout_hours=app_settings.session_timeout_hours,
                    key_prefix=app_settings.redis_key_prefix,
                )
                # Test connection
                if session_store.ping():
                    log.info("✅ Redis connection successful")
                else:
                    log.warning("⚠️ Redis ping failed - sessions may not persist")
            except Exception as e:
                log.error(f"❌ Failed to connect to Redis: {e}")
                log.warning("⚠️ Falling back to InMemorySessionStore")
                session_store = InMemorySessionStore(session_timeout_hours=app_settings.session_timeout_hours)
        else:
            log.info("💾 Using InMemorySessionStore (development only)")
            session_store = InMemorySessionStore(session_timeout_hours=app_settings.session_timeout_hours)

        # Register session store
        builder.services.add_singleton(SessionStore, singleton=session_store)

        # Create and configure auth service
        auth_service = DualAuthService(session_store)

        # Pre-warm JWKS cache (ignore failure silently; will retry on first token usage)
        try:
            auth_service._fetch_jwks()
            log.info("🔐 JWKS cache pre-warmed")
        except Exception as e:
            log.debug(f"JWKS pre-warm skipped: {e}")

        # Register auth service
        builder.services.add_singleton(DualAuthService, singleton=auth_service)

    @staticmethod
    def configure_middleware(app: "FastAPI") -> None:
        """Configure authentication middleware for the FastAPI application.

        This middleware injects the DualAuthService instance from the DI container
        into the request state, making it available to FastAPI dependencies.

        Args:
            app: FastAPI application instance
        """

        @app.middleware("http")
        async def inject_auth_service(request: "Request", call_next: Callable[["Request"], Awaitable[Response]]) -> Response:
            """Middleware to inject AuthService into FastAPI request state.

            This middleware injects the AuthService instance into request state
            so FastAPI dependencies can access it. We retrieve the same instance
            that's registered in Neuroglia's DI container for consistency.
            """
            # Retrieve auth service from DI container
            request.state.auth_service = app.state.services.get_required_service(DualAuthService)
            response = await call_next(request)
            return response
