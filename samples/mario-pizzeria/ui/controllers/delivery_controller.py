"""Delivery controller for managing order delivery operations"""

import asyncio
import json
import logging

from application.commands.assign_order_to_delivery_command import (
    AssignOrderToDeliveryCommand,
)
from application.commands.update_order_status_command import UpdateOrderStatusCommand
from application.queries.get_delivery_orders_query import GetDeliveryOrdersQuery
from application.queries.get_delivery_tour_query import GetDeliveryTourQuery
from application.queries.get_orders_by_status_query import GetOrdersByStatusQuery
from application.settings import app_settings
from classy_fastapi import Routable, get, post
from fastapi import Request
from fastapi.responses import HTMLResponse, StreamingResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function

log = logging.getLogger(__name__)


class UIDeliveryController(ControllerBase):
    """Controller for delivery driver operations"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Delivery"

        # Initialize Routable with /delivery prefix
        Routable.__init__(
            self,
            prefix="/delivery",
            tags=["UI", "Delivery"],
            generate_unique_id_function=generate_unique_id_function,
        )

    def _check_delivery_access(self, request: Request) -> bool:
        """Check if user has delivery driver access"""
        roles = request.session.get("roles", [])
        if not isinstance(roles, list):
            roles = []
        has_access = "delivery_driver" in roles or "manager" in roles
        log.info(f"Delivery access check - User: {request.session.get('username')}, " f"Roles: {roles}, Has access: {has_access}")
        return has_access

    @get("/", response_class=HTMLResponse)
    async def ready_orders(self, request: Request):
        """Display orders ready for delivery pickup (READY status only)"""
        if not self._check_delivery_access(request):
            return request.app.state.templates.TemplateResponse(
                "errors/403.html",
                {
                    "request": request,
                    "title": "Access Denied",
                    "username": request.session.get("username"),
                    "app_version": app_settings.app_version,
                },
                status_code=403,
            )

        # Get ONLY ready orders (not yet assigned to any driver)
        query = GetOrdersByStatusQuery(status="ready")
        result = await self.mediator.execute_async(query)

        orders = result.data if result.is_success else []

        return request.app.state.templates.TemplateResponse(
            "delivery/ready_orders.html",
            {
                "request": request,
                "title": "Ready for Delivery",
                "orders": orders,
                "authenticated": request.session.get("authenticated", False),
                "username": request.session.get("username"),
                "roles": request.session.get("roles", []),
                "app_version": app_settings.app_version,
            },
        )

    @get("/tour", response_class=HTMLResponse)
    async def delivery_tour(self, request: Request):
        """Display driver's active delivery tour"""
        if not self._check_delivery_access(request):
            return request.app.state.templates.TemplateResponse(
                "errors/403.html",
                {
                    "request": request,
                    "title": "Access Denied",
                    "username": request.session.get("username"),
                    "app_version": app_settings.app_version,
                },
                status_code=403,
            )

        # Get delivery tour for this driver
        user_id = request.session.get("user_id")
        query = GetDeliveryTourQuery(delivery_person_id=user_id)
        result = await self.mediator.execute_async(query)

        orders = result.data if result.is_success else []

        return request.app.state.templates.TemplateResponse(
            "delivery/tour.html",
            {
                "request": request,
                "title": "My Delivery Tour",
                "orders": orders,
                "authenticated": request.session.get("authenticated", False),
                "username": request.session.get("username"),
                "roles": request.session.get("roles", []),
                "app_version": app_settings.app_version,
            },
        )

    @get("/stream", response_class=StreamingResponse)
    async def delivery_stream(self, request: Request):
        """SSE stream for real-time delivery updates"""
        if not self._check_delivery_access(request):
            return HTMLResponse(content="Access Denied", status_code=403)

        user_id = request.session.get("user_id")

        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break

                try:
                    # Get delivery orders (READY + DELIVERING) and delivery tour
                    delivery_query = GetDeliveryOrdersQuery()
                    delivery_result = await self.mediator.execute_async(delivery_query)

                    tour_query = GetDeliveryTourQuery(delivery_person_id=user_id)
                    tour_result = await self.mediator.execute_async(tour_query)

                    delivery_orders = delivery_result.data if delivery_result.is_success else []
                    tour_orders = tour_result.data if tour_result.is_success else []

                    # Serialize orders
                    delivery_data = [
                        {
                            "id": o.id,
                            "status": o.status,
                            "customer_name": o.customer_name,
                            "customer_address": o.customer_address,
                            "pizza_count": o.pizza_count,
                            "total_amount": float(o.total_amount) if o.total_amount else 0,
                            "actual_ready_time": (o.actual_ready_time.isoformat() if o.actual_ready_time else None),
                        }
                        for o in delivery_orders
                    ]

                    tour_data = [
                        {
                            "id": o.id,
                            "status": o.status,
                            "customer_name": o.customer_name,
                            "customer_address": o.customer_address,
                            "customer_phone": o.customer_phone,
                            "pizza_count": o.pizza_count,
                            "total_amount": float(o.total_amount) if o.total_amount else 0,
                        }
                        for o in tour_orders
                    ]

                    yield f"data: {json.dumps({'delivery_orders': delivery_data, 'tour_orders': tour_data})}\n\n"

                except Exception as e:
                    log.error(f"Error in delivery stream: {e}")

                await asyncio.sleep(5)  # Update every 5 seconds

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @post("/{order_id}/assign")
    async def assign_order(self, request: Request, order_id: str):
        """Assign order to current driver and add to delivery tour"""
        if not self._check_delivery_access(request):
            return {"success": False, "error": "Access denied"}

        user_id = request.session.get("user_id")

        command = AssignOrderToDeliveryCommand(order_id=order_id, delivery_person_id=user_id)
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return {"success": True, "message": "Order added to your delivery tour"}
        else:
            return {"success": False, "error": result.error_message or "Failed to assign order"}

    @post("/{order_id}/deliver")
    async def mark_delivered(self, request: Request, order_id: str):
        """Mark order as delivered"""
        if not self._check_delivery_access(request):
            return {"success": False, "error": "Access denied"}

        # Extract user context from session
        user_id = request.session.get("user_id")
        user_name = request.session.get("name")

        # Execute command with user tracking
        command = UpdateOrderStatusCommand(order_id=order_id, new_status="delivered", user_id=user_id, user_name=user_name)
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return {"success": True, "message": "Order marked as delivered"}
        else:
            return {
                "success": False,
                "error": result.error_message or "Failed to mark order as delivered",
            }
