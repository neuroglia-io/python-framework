"""UI controller for kitchen management"""
import asyncio
import json
from collections.abc import AsyncGenerator

from application.commands import UpdateOrderStatusCommand
from application.queries import GetActiveKitchenOrdersQuery
from application.settings import app_settings
from classy_fastapi import Routable, get, post
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function


class UIKitchenController(ControllerBase):
    """UI kitchen controller for staff"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Kitchen"

        # Initialize Routable with /kitchen prefix
        Routable.__init__(
            self,
            prefix="/kitchen",
            tags=["UI", "Kitchen"],
            generate_unique_id_function=generate_unique_id_function,
        )

    def _check_kitchen_access(self, request: Request) -> bool:
        """Check if user has kitchen access (chef or manager role)"""
        roles = request.session.get("roles", [])

        # Ensure roles is a list
        if not isinstance(roles, list):
            roles = []

        has_access = "chef" in roles or "manager" in roles

        # Debug logging
        import logging

        log = logging.getLogger(__name__)
        log.info(f"Kitchen access check - User: {request.session.get('username')}, Roles: {roles}, Has access: {has_access}")

        return has_access

    @get("/debug-session", response_class=HTMLResponse)
    async def debug_session(self, request: Request):
        """Debug endpoint to show session data"""
        session_data = dict(request.session)

        html_content = f"""
        <html>
            <head><title>Session Debug</title></head>
            <body>
                <h1>Session Debug Information</h1>
                <pre>{json.dumps(session_data, indent=2, default=str)}</pre>
                <hr>
                <a href="/kitchen">Back to Kitchen</a> | <a href="/auth/logout">Logout</a>
            </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    @get("", response_class=HTMLResponse)
    @get("/", response_class=HTMLResponse)
    async def kitchen_dashboard(self, request: Request):
        """Kitchen dashboard for managing orders"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/kitchen", status_code=302)

        # Check kitchen access
        if not self._check_kitchen_access(request):
            return request.app.state.templates.TemplateResponse(
                "errors/403.html",
                {
                    "request": request,
                    "title": "Access Denied",
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": request.session.get("name"),
                    "email": request.session.get("email"),
                    "message": "You don't have permission to access the kitchen dashboard. Kitchen access requires 'chef' or 'manager' role.",
                    "app_version": app_settings.app_version,
                },
            )

        # Get success/error messages
        success_message = request.query_params.get("success")
        error_message = request.query_params.get("error")

        # Get active orders
        orders_query = GetActiveKitchenOrdersQuery()
        orders_result = await self.mediator.execute_async(orders_query)

        orders = orders_result.data if orders_result.is_success else []

        return request.app.state.templates.TemplateResponse(
            "kitchen/dashboard.html",
            {
                "request": request,
                "title": "Kitchen Dashboard",
                "active_page": "kitchen",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "orders": orders,
                "success": success_message,
                "error": error_message,
                "app_version": app_settings.app_version,
            },
        )

    @get("/stream", response_class=StreamingResponse)
    async def kitchen_stream(self, request: Request):
        """Server-Sent Events stream for real-time kitchen updates"""
        # Check authentication and authorization
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login", status_code=302)

        if not self._check_kitchen_access(request):
            return RedirectResponse(url="/", status_code=403)

        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events for kitchen updates"""
            try:
                while True:
                    # Check if client is still connected
                    if await request.is_disconnected():
                        break

                    # Get current orders
                    orders_query = GetActiveKitchenOrdersQuery()
                    orders_result = await self.mediator.execute_async(orders_query)

                    if orders_result.is_success:
                        # Convert orders to JSON-serializable format
                        orders_data = []
                        for order in orders_result.data:
                            orders_data.append(
                                {
                                    "id": order.id,
                                    "customer_name": order.customer_name,
                                    "status": order.status,
                                    "pizza_count": order.pizza_count,
                                    "total_amount": float(order.total_amount),
                                    "order_time": (order.order_time.isoformat() if order.order_time else None),
                                    "estimated_ready_time": (order.estimated_ready_time.isoformat() if order.estimated_ready_time else None),
                                    "pizzas": [
                                        {
                                            "name": p.name,
                                            "size": p.size,
                                            "toppings": p.toppings,
                                        }
                                        for p in order.pizzas
                                    ],
                                }
                            )

                        # Send SSE event
                        yield f"data: {json.dumps({'orders': orders_data})}\n\n"

                    # Wait before next update (5 seconds)
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                # Client disconnected
                pass
            except Exception as e:
                # Log error and close connection
                print(f"SSE error: {str(e)}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @post("/{order_id}/status")
    async def update_order_status(self, request: Request, order_id: str):
        """Update order status (AJAX endpoint)"""
        # Check authentication and authorization
        if not request.session.get("authenticated"):
            return {"success": False, "error": "Not authenticated"}

        if not self._check_kitchen_access(request):
            return {"success": False, "error": "Access denied"}

        # Get form data
        form = await request.form()
        new_status = form.get("status")

        if not new_status:
            return {"success": False, "error": "Status is required"}

        # Extract user context from session
        user_id = request.session.get("user_id")
        user_name = request.session.get("name")

        # Execute command with user tracking
        command = UpdateOrderStatusCommand(order_id=order_id, new_status=new_status, user_id=user_id, user_name=user_name)
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return {
                "success": True,
                "order": {
                    "id": result.data.id,
                    "status": result.data.status,
                },
            }
        else:
            return {"success": False, "error": result.error_message}
