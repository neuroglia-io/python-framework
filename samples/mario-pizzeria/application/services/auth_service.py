"""Authentication service for both session and JWT"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import jwt
from application.settings import app_settings
from passlib.context import CryptContext

log = logging.getLogger(__name__)


class AuthService:
    """Handles authentication for both UI (sessions) and API (JWT)"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Password hashing
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    # JWT Token Management (for API)
    def create_jwt_token(self, user_id: str, username: str, extra_claims: Optional[dict[str, Any]] = None) -> str:
        """Create a JWT access token for API authentication"""
        payload = {
            "sub": user_id,
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=app_settings.jwt_expiration_minutes),
            "iat": datetime.now(timezone.utc),
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, app_settings.jwt_secret_key, algorithm=app_settings.jwt_algorithm)

    def verify_jwt_token(self, token: str) -> Optional[dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token,
                app_settings.jwt_secret_key,
                algorithms=[app_settings.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # User Authentication (placeholder - implement with real user repo)
    async def authenticate_user(self, username: str, password: str) -> Optional[dict[str, Any]]:
        """
        Authenticate a user with username/password via Keycloak.

        Uses Keycloak's Direct Access Grants (Resource Owner Password Credentials) flow.
        """
        # Try Keycloak authentication first
        keycloak_user = await self._authenticate_with_keycloak(username, password)
        if keycloak_user:
            return keycloak_user

        # Fallback to demo user for development
        if username == "demo" and password == "demo123":
            return {
                "id": "demo-user-id",
                "sub": "demo-user-id",
                "username": "demo",
                "preferred_username": "demo",
                "email": "demo@mariospizzeria.com",
                "name": "Demo User",
                "role": "customer",
            }

        return None

    async def _authenticate_with_keycloak(self, username: str, password: str) -> Optional[dict[str, Any]]:
        """
        Authenticate with Keycloak using Direct Access Grants flow.

        Returns user information extracted from the access token.
        """
        try:
            keycloak_url = app_settings.keycloak_server_url
            realm = app_settings.keycloak_realm
            client_id = app_settings.keycloak_client_id

            if not keycloak_url or not realm or not client_id:
                log.warning("Keycloak not configured, skipping Keycloak authentication")
                return None

            # Token endpoint
            token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

            # Prepare token request data
            token_data = {
                "grant_type": "password",
                "client_id": client_id,
                "username": username,
                "password": password,
            }

            # Add client secret if configured (for confidential clients)
            if app_settings.keycloak_client_secret:
                token_data["client_secret"] = app_settings.keycloak_client_secret

            # Request access token
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    log.warning(f"Keycloak authentication failed: {response.status_code} - {response.text}")
                    return None

                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    log.error("No access token in Keycloak response")
                    return None

                # Decode token to extract user info (without verification for simplicity)
                # In production, verify the token signature
                decoded_token = jwt.decode(
                    access_token,
                    options={"verify_signature": False},  # Skip signature verification for dev
                )

                # Extract user information
                user_info = {
                    "id": decoded_token.get("sub"),
                    "sub": decoded_token.get("sub"),
                    "username": decoded_token.get("preferred_username"),
                    "preferred_username": decoded_token.get("preferred_username"),
                    "email": decoded_token.get("email"),
                    # Build full name from multiple sources with fallback chain:
                    # 1. Use 'name' claim if present
                    # 2. Construct from given_name + family_name if both present
                    # 3. Use given_name only if present
                    # 4. Fall back to username as last resort
                    "name": (decoded_token.get("name") or (f"{decoded_token.get('given_name', '')} {decoded_token.get('family_name', '')}".strip() if decoded_token.get("given_name") or decoded_token.get("family_name") else None) or decoded_token.get("preferred_username")),
                    "given_name": decoded_token.get("given_name"),
                    "family_name": decoded_token.get("family_name"),
                    "roles": decoded_token.get("realm_access", {}).get("roles", []),
                }

                log.info(f"Successfully authenticated user via Keycloak: {user_info.get('username')} " f"(name: {user_info.get('name')})")
                return user_info

        except httpx.TimeoutException:
            log.error("Keycloak authentication timeout")
            return None
        except httpx.ConnectError:
            log.error("Cannot connect to Keycloak server")
            return None
        except Exception as ex:
            log.error(f"Keycloak authentication error: {ex}", exc_info=True)
            return None
