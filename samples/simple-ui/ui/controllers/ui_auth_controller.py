"""UI authentication controller for JWT-based login."""

import logging
from typing import Optional

from application.services.auth_service import AuthService
from classy_fastapi import Routable
from classy_fastapi.decorators import get, post
from fastapi import Form, Header, Request
from fastapi.responses import JSONResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase, generate_unique_id_function

log = logging.getLogger(__name__)


class UIAuthController(ControllerBase):
    """UI authentication controller - handles JWT-based login."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        # Store DI services first
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "UIAuth"

        # Initialize auth service
        self.auth_service = AuthService()

        # Call Routable.__init__ directly with /auth prefix
        Routable.__init__(
            self,
            prefix="/auth",
            tags=["UI Auth"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @post("/login")
    async def login(
        self,
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
    ) -> JSONResponse:
        """Process login form and create session."""
        user = await self.auth_service.authenticate_user(username, password)

        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Invalid username or password"},
            )

        # Extract user information
        user_id = user.get("id") or user.get("sub")
        username_value = user.get("username") or user.get("preferred_username")
        email = user.get("email")
        name = user.get("name") or username_value
        roles = user.get("roles", [])

        log.info(f"User {username_value} authenticated with roles: {roles}")

        # Validate required fields
        if not user_id or not username_value or not email:
            log.error(f"Missing required user information: user_id={user_id}, username={username_value}, email={email}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "User authentication succeeded but profile information is incomplete"},
            )

        # Create JWT token with all user information (session removed - JWT-only auth)
        # Prioritize admin role over others for the token
        primary_role = "admin" if "admin" in roles else (roles[0] if roles else "user")
        jwt_token = self.auth_service.create_jwt_token(
            user_id,
            username_value,
            {
                "roles": roles,
                "role": primary_role,
                "email": email,
                "name": name or username_value,
            },
        )

        log.info(f"User {username_value} logged in successfully with primary role: {primary_role}")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username_value,
                    "email": email,
                    "name": name,
                    "roles": roles,
                },
                "token": jwt_token,
            },
        )

    @post("/logout")
    async def logout(self, request: Request) -> JSONResponse:
        """Logout endpoint (JWT is cleared client-side, no server-side session)."""
        log.info("User logged out")
        return JSONResponse(status_code=200, content={"success": True})

    @get("/me")
    async def get_current_user(self, authorization: Optional[str] = Header(None)) -> JSONResponse:
        """Get current authenticated user from JWT token."""
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"authenticated": False})

        token = authorization.replace("Bearer ", "")

        # Verify JWT token
        payload = self.auth_service.verify_jwt_token(token)
        if not payload:
            return JSONResponse(status_code=401, content={"authenticated": False})

        # Extract user info from token
        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": {
                    "id": payload.get("sub"),
                    "username": payload.get("username"),
                    "email": payload.get("email"),
                    "name": payload.get("name", payload.get("username")),
                    "roles": payload.get("roles", []),
                    "role": payload.get("role", "user"),
                },
            },
        )
