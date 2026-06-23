"""UI authentication endpoints (sessions)"""

import logging
from typing import Optional

from application.commands import CreateCustomerProfileCommand
from application.queries import GetCustomerProfileQuery
from application.services.auth_service import AuthService
from application.settings import app_settings
from classy_fastapi import Routable
from classy_fastapi.decorators import get, post
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase, generate_unique_id_function
from neuroglia.serialization.json import JsonSerializer

log = logging.getLogger(__name__)


class UIAuthController(ControllerBase):
    """UI authentication controller - session cookies"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        # Store DI services first
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = service_provider.get_required_service(JsonSerializer)
        self.name = "Auth"

        # Initialize auth service
        self.auth_service = AuthService()

        # Call Routable.__init__ directly with /auth prefix
        Routable.__init__(
            self,
            prefix="/auth",  # Auth routes prefix
            tags=["UI Auth"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/login", response_class=HTMLResponse)
    async def login_page(self, request: Request) -> HTMLResponse:
        """Render login page"""
        return request.app.state.templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "title": "Login", "app_version": app_settings.app_version},
        )

    @post("/login")
    async def login(
        self,
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next_url: Optional[str] = Form(None),
    ) -> RedirectResponse:
        """Process login form and create session"""
        user = await self.auth_service.authenticate_user(username, password)

        if not user:
            # Re-render login with error
            return request.app.state.templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "title": "Login",
                    "error": "Invalid username or password",
                    "app_version": app_settings.app_version,
                },
                status_code=401,
            )

        # Debug: Log the full user object to see what we're getting from Keycloak
        log.info(f"Keycloak user object keys: {list(user.keys())}")
        log.info(f"Keycloak user object: {user}")

        # Extract user information
        user_id = user.get("id") or user.get("sub")  # Keycloak uses 'sub' for user ID
        username_value = user.get("username") or user.get("preferred_username")
        email = user.get("email")
        name = user.get("name") or username_value

        # Extract roles - the auth service already extracted them for us!
        roles = user.get("roles", [])

        log.info(f"Extracted roles for user {username_value}: {roles}")

        # Validate required fields
        if not user_id or not username_value or not email:
            log.error(f"Missing required user information: user_id={user_id}, username={username_value}, email={email}")
            return request.app.state.templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "title": "Login",
                    "error": "User authentication succeeded but profile information is incomplete",
                    "app_version": app_settings.app_version,
                },
                status_code=500,
            )

        # Create session with user info
        request.session["user_id"] = user_id
        request.session["username"] = username_value
        request.session["email"] = email
        request.session["name"] = name or username_value
        request.session["roles"] = roles  # Store user roles
        request.session["authenticated"] = True

        # Auto-create customer profile if it doesn't exist
        await self._ensure_customer_profile(user_id, name or username_value, email)

        log.info(f"User {username_value} logged in successfully")
        return RedirectResponse(url=next_url or "/", status_code=303)

    async def _ensure_customer_profile(self, user_id: str, name: str, email: str) -> None:
        """Ensure customer profile exists, create if not"""
        try:
            # Check if profile exists
            query = GetCustomerProfileQuery(user_id=user_id)
            result = await self.mediator.execute_async(query)

            if not result.is_success:
                # Profile doesn't exist, create it
                log.info(f"Creating customer profile for user_id={user_id}")

                # Parse name into first/last
                name_parts = name.split(" ", 1)
                first_name = name_parts[0] if name_parts else name
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                command = CreateCustomerProfileCommand(
                    user_id=user_id,
                    name=f"{first_name} {last_name}".strip(),
                    email=email,
                    phone=None,
                    address=None,
                )

                create_result = await self.mediator.execute_async(command)

                if create_result.is_success:
                    log.info(f"Successfully created profile for user_id={user_id}")
                else:
                    log.warning(f"Failed to create profile for user_id={user_id}: {create_result.error_message}")
        except Exception as ex:
            log.error(f"Error ensuring customer profile for user_id={user_id}: {ex}", exc_info=True)

    @get("/logout")
    async def logout(self, request: Request) -> RedirectResponse:
        """Clear session and redirect to home"""
        username = request.session.get("username", "Unknown")
        request.session.clear()
        log.info(f"User {username} logged out")
        return RedirectResponse(url="/", status_code=303)
