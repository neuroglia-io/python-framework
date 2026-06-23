"""JWT authentication middleware for API endpoints"""

from typing import Optional

from application.services.auth_service import AuthService
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


class JWTAuthMiddleware:
    """Middleware to validate JWT tokens on API endpoints"""

    def __init__(self):
        self.auth_service = AuthService()

    async def __call__(self, request: Request, credentials: Optional[HTTPAuthorizationCredentials]):
        """Validate JWT token from Authorization header"""

        # Skip auth for docs and auth endpoints
        if request.url.path in [
            "/api/docs",
            "/api/openapi.json",
            "/api/auth/token",
        ]:
            return None

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        payload = self.auth_service.verify_jwt_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Attach user info to request state
        request.state.user = payload
        return payload
