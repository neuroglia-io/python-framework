"""API authentication endpoints (JWT)"""

from application.services.auth_service import AuthService
from classy_fastapi.decorators import post
from fastapi import Form, HTTPException, status
from pydantic import BaseModel

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthController(ControllerBase):
    """API authentication controller - JWT tokens"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self.auth_service = AuthService()

    @post("/token", response_model=TokenResponse, tags=["Authentication"])
    async def login(
        self,
        username: str = Form(...),
        password: str = Form(...),
    ) -> TokenResponse:
        """
        OAuth2-compatible token endpoint for API authentication.

        Returns JWT access token for API requests.
        """
        user = await self.auth_service.authenticate_user(username, password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = self.auth_service.create_jwt_token(
            user_id=user["id"],
            username=user["username"],
            extra_claims={"role": user.get("role")},
        )

        return TokenResponse(access_token=access_token, token_type="bearer", expires_in=3600)
