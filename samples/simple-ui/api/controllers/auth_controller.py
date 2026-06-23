"""Authentication controller."""

from datetime import datetime, timedelta
from typing import Optional

from application.settings import app_settings
from classy_fastapi import post
from fastapi import Depends, Form, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jose import JWTError, jwt
from pydantic import BaseModel

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

# JWT Configuration - use same settings as UI auth service
SECRET_KEY = app_settings.jwt_secret_key
ALGORITHM = app_settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = app_settings.jwt_expiration_minutes

# Mock user database (in production, use real database)
USERS_DB = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "manager": {"username": "manager", "password": "manager123", "role": "manager"},
    "john.doe": {"username": "john.doe", "password": "user123", "role": "user"},
    "jane.smith": {"username": "jane.smith", "password": "user123", "role": "user"},
}


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


class TokenResponseWithUser(BaseModel):
    """Token response with user info."""

    access_token: str
    token_type: str
    username: str
    role: str


class UserInfo(BaseModel):
    """User information."""

    username: str
    role: str


security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInfo:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Use 'username' field from token, not 'sub' (which contains user ID)
        username: str = payload.get("username")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return UserInfo(username=username, role=role)
    except JWTError:
        raise credentials_exception


class AuthController(ControllerBase):
    """Authentication controller."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        super().__init__(service_provider, mapper, mediator)

    @post("/login", response_model=TokenResponseWithUser)
    async def login(self, request: LoginRequest) -> TokenResponseWithUser:
        """Authenticate user and return JWT token."""
        # Validate credentials
        user = USERS_DB.get(request.username)
        if not user or user["password"] != request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=access_token_expires,
        )

        return TokenResponseWithUser(
            access_token=access_token,
            token_type="bearer",
            username=user["username"],
            role=user["role"],
        )

    @post("/token", response_model=TokenResponse, tags=["Authentication"])
    async def token(
        self,
        username: str = Form(...),
        password: str = Form(...),
    ) -> TokenResponse:
        """
        OAuth2-compatible token endpoint for Swagger UI authentication.

        This endpoint follows the OAuth2 password flow specification,
        allowing Swagger UI to authenticate and test protected endpoints.
        """
        # Validate credentials
        user = USERS_DB.get(username)
        if not user or user["password"] != password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=access_token_expires,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
        )
