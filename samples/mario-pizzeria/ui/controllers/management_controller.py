"""Management controller for dashboard, analytics, and menu management"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from application.queries.get_active_kitchen_orders_query import (
    GetActiveKitchenOrdersQuery,
)
from application.queries.get_kitchen_performance_query import GetKitchenPerformanceQuery
from application.queries.get_orders_by_driver_query import GetOrdersByDriverQuery
from application.queries.get_orders_by_pizza_query import GetOrdersByPizzaQuery
from application.queries.get_orders_timeseries_query import GetOrdersTimeseriesQuery
from application.queries.get_overview_statistics_query import GetOverviewStatisticsQuery
from application.queries.get_ready_orders_query import GetReadyOrdersQuery
from application.queries.get_staff_performance_query import GetStaffPerformanceQuery
from application.queries.get_top_customers_query import GetTopCustomersQuery
from application.settings import app_settings
from classy_fastapi import Routable, get
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function

log = logging.getLogger(__name__)


def convert_decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_decimal_to_float(item) for item in obj]
    return obj


class UIManagementController(ControllerBase):
    """Controller for management dashboard operations"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Management"

        # Initialize Routable with /management prefix
        Routable.__init__(
            self,
            prefix="/management",
            tags=["UI", "Management"],
            generate_unique_id_function=generate_unique_id_function,
        )

    def _check_manager_access(self, request: Request) -> bool:
        """Check if user has manager access"""
        roles = request.session.get("roles", [])
        if not isinstance(roles, list):
            roles = []
        has_access = "manager" in roles
        log.info(f"Manager access check - User: {request.session.get('username')}, " f"Roles: {roles}, Has access: {has_access}")
        return has_access

    @get("/", response_class=HTMLResponse)
    async def dashboard_overview(self, request: Request):
        """Display management dashboard overview"""
        if not self._check_manager_access(request):
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

        # Get overview statistics
        stats_query = GetOverviewStatisticsQuery()
        stats_result = await self.mediator.execute_async(stats_query)

        statistics = stats_result.data if stats_result.is_success else None

        return request.app.state.templates.TemplateResponse(
            "management/dashboard.html",
            {
                "request": request,
                "title": "Management Dashboard",
                "active_page": "management",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "statistics": statistics,
                "app_version": app_settings.app_version,
            },
        )

    @get("/operations", response_class=HTMLResponse)
    async def operations_monitor(self, request: Request):
        """Display people-centric operations monitor (staff performance and customer activity)"""
        if not self._check_manager_access(request):
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

        # Get period from query params (default: today)
        period = request.query_params.get("period", "today")

        # Calculate date range based on period
        end_date = datetime.now(timezone.utc)
        if period == "today":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_days = 1
        elif period == "week":
            start_date = end_date - timedelta(days=7)
            period_days = 7
        elif period == "month":
            start_date = end_date - timedelta(days=30)
            period_days = 30
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
            period_days = 90
        else:  # all
            start_date = end_date - timedelta(days=365)
            period_days = 365

        # Get staff performance (drivers)
        staff_query = GetStaffPerformanceQuery(date=start_date if period == "today" else None, limit=10)
        staff_result = await self.mediator.execute_async(staff_query)
        staff_performance = staff_result.data if staff_result.is_success else []

        # Get driver performance details
        driver_query = GetOrdersByDriverQuery(start_date=start_date, end_date=end_date, limit=10)
        driver_result = await self.mediator.execute_async(driver_query)
        driver_performance = driver_result.data if driver_result.is_success else []

        # Get top customers
        customers_query = GetTopCustomersQuery(period_days=period_days, limit=10)
        customers_result = await self.mediator.execute_async(customers_query)
        top_customers = customers_result.data if customers_result.is_success else []

        # Get kitchen performance
        kitchen_perf_query = GetKitchenPerformanceQuery(start_date=start_date, end_date=end_date)
        kitchen_perf_result = await self.mediator.execute_async(kitchen_perf_query)
        kitchen_performance = kitchen_perf_result.data if kitchen_perf_result.is_success else None

        return request.app.state.templates.TemplateResponse(
            "management/operations.html",
            {
                "request": request,
                "title": "Operations Monitor",
                "active_page": "management",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "staff_performance": staff_performance,
                "driver_performance": driver_performance,
                "top_customers": top_customers,
                "kitchen_performance": kitchen_performance,
                "selected_period": period,
                "app_version": app_settings.app_version,
            },
        )

    @get("/stream")
    async def management_stream(self, request: Request):
        """SSE stream for real-time management updates"""
        if not self._check_manager_access(request):
            return request.app.state.templates.TemplateResponse(
                "errors/403.html",
                {
                    "request": request,
                    "title": "Access Denied",
                },
                status_code=403,
            )

        async def event_generator():
            """Generate SSE events with management data"""
            try:
                while True:
                    # Get overview statistics
                    stats_query = GetOverviewStatisticsQuery()
                    stats_result = await self.mediator.execute_async(stats_query)

                    # Get kitchen orders
                    kitchen_query = GetActiveKitchenOrdersQuery()
                    kitchen_result = await self.mediator.execute_async(kitchen_query)

                    # Get ready orders
                    ready_query = GetReadyOrdersQuery()
                    ready_result = await self.mediator.execute_async(ready_query)

                    # Build response data
                    data = {
                        "statistics": {
                            "total_orders_today": (stats_result.data.total_orders_today if stats_result.is_success else 0),
                            "revenue_today": (float(stats_result.data.revenue_today) if stats_result.is_success else 0.0),
                            "active_orders": (stats_result.data.active_orders if stats_result.is_success else 0),
                            "orders_pending": (stats_result.data.orders_pending if stats_result.is_success else 0),
                            "orders_cooking": (stats_result.data.orders_cooking if stats_result.is_success else 0),
                            "orders_ready": (stats_result.data.orders_ready if stats_result.is_success else 0),
                            "orders_delivering": (stats_result.data.orders_delivering if stats_result.is_success else 0),
                            "orders_confirmed": (stats_result.data.orders_confirmed if stats_result.is_success else 0),
                            "orders_change_percent": (float(stats_result.data.orders_change_percent) if stats_result.is_success else 0.0),
                            "revenue_change_percent": (float(stats_result.data.revenue_change_percent) if stats_result.is_success else 0.0),
                        },
                        "kitchen_orders_count": (len(kitchen_result.data) if kitchen_result.is_success else 0),
                        "ready_orders_count": (len(ready_result.data) if ready_result.is_success else 0),
                        "timestamp": asyncio.get_event_loop().time(),
                    }

                    # Convert any remaining Decimal objects to float
                    data = convert_decimal_to_float(data)

                    yield f"data: {json.dumps(data)}\n\n"

                    # Wait 5 seconds before next update
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                log.info("Management SSE stream cancelled")
            except Exception as e:
                log.error(f"Error in management SSE stream: {e}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @get("/menu", response_class=HTMLResponse)
    async def menu_management(self, request: Request):
        """Display menu management page"""
        if not self._check_manager_access(request):
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

        return request.app.state.templates.TemplateResponse(
            "management/menu.html",
            {
                "request": request,
                "title": "Menu Management",
                "active_page": "management",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "app_version": app_settings.app_version,
            },
        )

    @get("/analytics", response_class=HTMLResponse)
    async def analytics_dashboard(self, request: Request):
        """Display analytics dashboard with charts"""
        if not self._check_manager_access(request):
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

        return request.app.state.templates.TemplateResponse(
            "management/analytics.html",
            {
                "request": request,
                "title": "Sales Analytics",
                "active_page": "management",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "app_version": app_settings.app_version,
            },
        )

    @get("/analytics/data")
    async def analytics_data(
        self,
        request: Request,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "day",
    ):
        """AJAX endpoint for analytics data"""
        if not self._check_manager_access(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=403)

        try:
            # Parse dates
            start = None
            end = None

            if start_date:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)

            if end_date:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

            # Get timeseries data
            timeseries_query = GetOrdersTimeseriesQuery(start_date=start, end_date=end, period=period)  # type: ignore
            timeseries_result = await self.mediator.execute_async(timeseries_query)

            # Get pizza analytics
            pizza_query = GetOrdersByPizzaQuery(start_date=start, end_date=end, limit=10)
            pizza_result = await self.mediator.execute_async(pizza_query)

            # Build response data
            data = {
                "timeseries": [
                    {
                        "period": dp.period,
                        "total_orders": dp.total_orders,
                        "total_revenue": dp.total_revenue,
                        "average_order_value": dp.average_order_value,
                        "orders_delivered": dp.orders_delivered,
                        "orders_cancelled": dp.orders_cancelled,
                    }
                    for dp in (timeseries_result.data if timeseries_result.is_success else [])
                ],
                "pizza_analytics": [
                    {
                        "pizza_name": pa.pizza_name,
                        "total_orders": pa.total_orders,
                        "total_revenue": pa.total_revenue,
                        "average_price": pa.average_price,
                        "percentage_of_total": pa.percentage_of_total,
                    }
                    for pa in (pizza_result.data if pizza_result.is_success else [])
                ],
            }

            # Safety net for any remaining Decimal objects
            data = convert_decimal_to_float(data)

            return JSONResponse(content=data)

        except ValueError as e:
            log.error(f"Invalid date format in analytics request: {e}")
            return JSONResponse({"error": f"Invalid date format: {str(e)}"}, status_code=400)
        except Exception as e:
            log.error(f"Error in analytics data endpoint: {e}", exc_info=True)
            return JSONResponse({"error": "Internal server error"}, status_code=500)
