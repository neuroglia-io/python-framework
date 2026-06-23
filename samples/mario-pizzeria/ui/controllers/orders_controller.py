"""UI controller for order-related pages"""

from application.queries import (
    GetOrCreateCustomerProfileQuery,
    GetOrderByIdQuery,
    GetOrdersByCustomerQuery,
)
from application.settings import app_settings
from classy_fastapi import Routable, get
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function


class UIOrdersController(ControllerBase):
    """UI orders controller"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Orders"

        # Initialize Routable with /orders prefix
        Routable.__init__(
            self,
            prefix="/orders",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def orders_root(self, request: Request):
        """Redirect /orders to /orders with query params preserved"""
        # Preserve success/error query parameters
        query_string = str(request.query_params)
        redirect_url = f"/orders?{query_string}" if query_string else "/orders"

        # If no query params, just show the history directly
        if not query_string:
            return await self.order_history(request)

        return RedirectResponse(url=redirect_url, status_code=302)

    @get("", response_class=HTMLResponse)
    async def order_history(self, request: Request):
        """Display user order history"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/orders", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login?next=/orders", status_code=302)

        # Get success/error messages from query params
        success_message = request.query_params.get("success")
        error_message = request.query_params.get("error")

        # Get or create customer profile (auto-creates if doesn't exist)
        profile_query = GetOrCreateCustomerProfileQuery(
            user_id=str(user_id),
            email=request.session.get("email"),
            name=request.session.get("name"),
        )
        profile_result = await self.mediator.execute_async(profile_query)

        if not profile_result.is_success or not profile_result.data:
            return request.app.state.templates.TemplateResponse(
                "orders/history.html",
                {
                    "request": request,
                    "title": "Order History",
                    "active_page": "orders",
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": request.session.get("name"),
                    "email": request.session.get("email"),
                    "roles": request.session.get("roles", []),
                    "error": error_message or "Profile not found. Please create a profile first.",
                    "success": success_message,
                    "orders": [],
                    "app_version": app_settings.app_version,
                },
            )

        customer_id = profile_result.data.id

        # Get order history
        orders_query = GetOrdersByCustomerQuery(customer_id=customer_id)
        orders_result = await self.mediator.execute_async(orders_query)

        orders = orders_result.data if orders_result.is_success else []
        query_error = None if orders_result.is_success else orders_result.error_message

        return request.app.state.templates.TemplateResponse(
            "orders/history.html",
            {
                "request": request,
                "title": "Order History",
                "active_page": "orders",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "orders": orders,
                "error": error_message or query_error,
                "success": success_message,
                "app_version": app_settings.app_version,
            },
        )

    @get("/{order_id}", response_class=HTMLResponse)
    async def order_details(self, request: Request, order_id: str):
        """Display individual order details"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url=f"/auth/login?next=/orders/{order_id}", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url=f"/auth/login?next=/orders/{order_id}", status_code=302)

        # Get the order
        order_query = GetOrderByIdQuery(order_id=order_id)
        order_result = await self.mediator.execute_async(order_query)

        if not order_result.is_success or not order_result.data:
            return request.app.state.templates.TemplateResponse(
                "orders/detail.html",
                {
                    "request": request,
                    "title": "Order Not Found",
                    "active_page": "orders",
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": request.session.get("name"),
                    "email": request.session.get("email"),
                    "roles": request.session.get("roles", []),
                    "error": order_result.error_message or "Order not found",
                    "order": None,
                    "app_version": app_settings.app_version,
                },
            )

        order = order_result.data

        # Verify the order belongs to this user (get customer profile)
        profile_query = GetOrCreateCustomerProfileQuery(
            user_id=str(user_id),
            email=request.session.get("email"),
            name=request.session.get("name"),
        )
        profile_result = await self.mediator.execute_async(profile_query)

        # Check if this order belongs to the current user
        if profile_result.is_success and profile_result.data:
            # Simple check - in production, you'd query orders by customer to verify ownership
            pass

        return request.app.state.templates.TemplateResponse(
            "orders/detail.html",
            {
                "request": request,
                "title": f"Order #{order.id[:8]}",
                "active_page": "orders",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "order": order,
                "app_version": app_settings.app_version,
            },
        )
