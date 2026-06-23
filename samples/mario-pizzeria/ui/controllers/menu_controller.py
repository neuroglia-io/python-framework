"""UI controller for menu pages"""

import logging
from typing import Optional

from api.dtos import CreatePizzaDto
from application.commands import PlaceOrderCommand
from application.queries import GetMenuQuery, GetOrCreateCustomerProfileQuery
from application.settings import app_settings
from classy_fastapi import Routable, get, post
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc.controller_base import ControllerBase, generate_unique_id_function

log = logging.getLogger(__name__)


class UIMenuController(ControllerBase):
    """UI menu controller"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        # Store DI services first
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Menu"

        # Call Routable.__init__ directly with /menu prefix
        Routable.__init__(
            self,
            prefix="/menu",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def view_menu(self, request: Request):
        """Display menu page"""
        # Get authentication status
        authenticated = request.session.get("authenticated", False)
        username = request.session.get("username", "Guest")
        name = request.session.get("name")
        email = request.session.get("email")
        user_id = request.session.get("user_id")

        # Get menu
        menu_query = GetMenuQuery()
        menu_result = await self.mediator.execute_async(menu_query)

        pizzas = menu_result.data if menu_result.is_success else []
        error = None if menu_result.is_success else menu_result.error_message

        # Get customer profile if authenticated (for pre-filling order form)
        # Uses GetOrCreateCustomerProfileQuery to auto-create profile if doesn't exist
        customer_profile = None
        if authenticated and user_id:
            profile_query = GetOrCreateCustomerProfileQuery(user_id=str(user_id), email=email, name=name)
            profile_result = await self.mediator.execute_async(profile_query)
            customer_profile = profile_result.data if profile_result.is_success else None

        return request.app.state.templates.TemplateResponse(
            "menu/index.html",
            {
                "request": request,
                "title": "Menu",
                "active_page": "menu",
                "authenticated": authenticated,
                "username": username,
                "name": name,
                "email": email,
                "roles": request.session.get("roles", []),
                "pizzas": pizzas,
                "customer_profile": customer_profile,
                "error": error,
                "app_version": app_settings.app_version,
            },
        )

    @post("/order", response_class=HTMLResponse)
    async def create_order_from_menu(
        self,
        request: Request,
        customer_phone: str = Form(...),
        customer_address: str = Form(...),
        payment_method: str = Form(...),
        notes: Optional[str] = Form(None),
    ):
        """Create order from menu selection"""

        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/menu", status_code=302)

        user_id = request.session.get("user_id")
        user_name = request.session.get("name")  # Get authenticated user's name from Keycloak
        user_email = request.session.get("email")  # Get authenticated user's email from Keycloak

        # DEBUG: Log session data to understand what's happening
        log.info(f"🔍 Order creation - Session data: user_id={user_id}, name={user_name}, email={user_email}")

        if not user_id:
            return RedirectResponse(url="/auth/login?next=/menu", status_code=302)

        # Get or create customer profile for authenticated user
        # This ensures the order is linked to the correct user profile
        profile_query = GetOrCreateCustomerProfileQuery(user_id=str(user_id), email=user_email, name=user_name)
        profile_result = await self.mediator.execute_async(profile_query)

        if not profile_result.is_success or not profile_result.data:
            return RedirectResponse(url="/menu?error=Unable+to+load+customer+profile", status_code=303)

        customer_profile = profile_result.data

        # Ensure profile has required fields
        if not customer_profile.name or not customer_profile.email:
            return RedirectResponse(url="/menu?error=Incomplete+customer+profile", status_code=303)

        # DEBUG: Log what customer profile name we're using
        log.info(f"🔍 Order creation - Using customer_profile: name={customer_profile.name}, email={customer_profile.email}")

        # Get selected pizzas from form data
        form_data = await request.form()

        # Parse pizza selections (format: pizza_<index>_name, pizza_<index>_size, etc.)
        pizzas = []
        pizza_index = 0

        while f"pizza_{pizza_index}_name" in form_data:
            pizza_name_raw = form_data.get(f"pizza_{pizza_index}_name")
            pizza_size_raw = form_data.get(f"pizza_{pizza_index}_size")
            pizza_toppings_raw = form_data.get(f"pizza_{pizza_index}_toppings", "")

            # Convert to strings
            pizza_name = str(pizza_name_raw) if pizza_name_raw else None
            pizza_size = str(pizza_size_raw) if pizza_size_raw else None
            pizza_toppings_str = str(pizza_toppings_raw) if pizza_toppings_raw else ""

            if pizza_name and pizza_size:
                # Parse toppings (comma-separated string)
                toppings_list = []
                if pizza_toppings_str:
                    toppings_list = [t.strip() for t in pizza_toppings_str.split(",") if t.strip()]

                pizzas.append(CreatePizzaDto(name=pizza_name, size=pizza_size, toppings=toppings_list))

            pizza_index += 1

        # Validate we have at least one pizza
        if not pizzas:
            # Redirect back with error
            return RedirectResponse(url="/menu?error=Please+select+at+least+one+pizza", status_code=303)

        # Create order command using authenticated user's profile information
        # This ensures orders are created with the correct customer name and email
        command = PlaceOrderCommand(
            customer_id=customer_profile.id,  # Use customer profile ID (from GetOrCreateCustomerProfile)
            customer_name=customer_profile.name,  # Use profile name (from Keycloak)
            customer_phone=customer_phone,  # Use phone from form (can vary per order)
            customer_address=customer_address,  # Use address from form (can vary per order)
            customer_email=customer_profile.email,  # Use profile email (from Keycloak)
            pizzas=pizzas,
            payment_method=payment_method,
            notes=notes,
        )

        # Execute command
        result = await self.mediator.execute_async(command)

        if result.is_success:
            # Redirect to order confirmation or orders page
            order_id = result.data.id if result.data else None
            if order_id:
                return RedirectResponse(url=f"/orders?success=Order+{order_id}+created", status_code=303)
            else:
                return RedirectResponse(url="/orders?success=Order+created", status_code=303)
        else:
            # Redirect back with error
            error_msg = result.error_message or "Failed to create order"
            return RedirectResponse(url=f"/menu?error={error_msg}", status_code=303)
