# Query definitions and handlers auto-discovery
# Import all query modules to ensure handlers are registered during mediation setup

from .get_active_kitchen_orders_query import (
    GetActiveKitchenOrdersHandler,
    GetActiveKitchenOrdersQuery,
)
from .get_active_orders_query import GetActiveOrdersQuery, GetActiveOrdersQueryHandler
from .get_customer_notifications_query import (
    GetCustomerNotificationsHandler,
    GetCustomerNotificationsQuery,
)
from .get_customer_profile_query import (
    GetCustomerProfileHandler,
    GetCustomerProfileQuery,
)
from .get_delivery_orders_query import GetDeliveryOrdersHandler, GetDeliveryOrdersQuery
from .get_delivery_tour_query import GetDeliveryTourHandler, GetDeliveryTourQuery
from .get_kitchen_performance_query import (
    GetKitchenPerformanceHandler,
    GetKitchenPerformanceQuery,
)
from .get_kitchen_status_query import (
    GetKitchenStatusQuery,
    GetKitchenStatusQueryHandler,
)
from .get_menu_query import GetMenuQuery, GetMenuQueryHandler
from .get_or_create_customer_profile_query import (
    GetOrCreateCustomerProfileHandler,
    GetOrCreateCustomerProfileQuery,
)
from .get_order_by_id_query import GetOrderByIdQuery, GetOrderByIdQueryHandler
from .get_order_status_distribution_query import (
    GetOrderStatusDistributionHandler,
    GetOrderStatusDistributionQuery,
)
from .get_orders_by_customer_query import (
    GetOrdersByCustomerHandler,
    GetOrdersByCustomerQuery,
)
from .get_orders_by_driver_query import GetOrdersByDriverHandler, GetOrdersByDriverQuery
from .get_orders_by_pizza_query import GetOrdersByPizzaHandler, GetOrdersByPizzaQuery
from .get_orders_by_status_query import (
    GetOrdersByStatusQuery,
    GetOrdersByStatusQueryHandler,
)
from .get_orders_timeseries_query import (
    GetOrdersTimeseriesHandler,
    GetOrdersTimeseriesQuery,
)
from .get_overview_statistics_query import (
    GetOverviewStatisticsHandler,
    GetOverviewStatisticsQuery,
)
from .get_ready_orders_query import GetReadyOrdersHandler, GetReadyOrdersQuery
from .get_staff_performance_query import (
    GetStaffPerformanceHandler,
    GetStaffPerformanceQuery,
)
from .get_top_customers_query import GetTopCustomersHandler, GetTopCustomersQuery

# Make queries available for import
__all__ = [
    "GetMenuQuery",
    "GetMenuQueryHandler",
    "GetOrderByIdQuery",
    "GetOrderByIdQueryHandler",
    "GetOrdersByStatusQuery",
    "GetOrdersByStatusQueryHandler",
    "GetActiveOrdersQuery",
    "GetActiveOrdersQueryHandler",
    "GetActiveKitchenOrdersQuery",
    "GetActiveKitchenOrdersHandler",
    "GetKitchenStatusQuery",
    "GetKitchenStatusQueryHandler",
    "GetCustomerProfileQuery",
    "GetCustomerProfileHandler",
    "GetOrCreateCustomerProfileQuery",
    "GetOrCreateCustomerProfileHandler",
    "GetOrdersByCustomerQuery",
    "GetOrdersByCustomerHandler",
    "GetReadyOrdersQuery",
    "GetReadyOrdersHandler",
    "GetDeliveryOrdersQuery",
    "GetDeliveryOrdersHandler",
    "GetDeliveryTourQuery",
    "GetDeliveryTourHandler",
    "GetOverviewStatisticsQuery",
    "GetOverviewStatisticsHandler",
    "GetOrdersTimeseriesQuery",
    "GetOrdersTimeseriesHandler",
    "GetOrdersByPizzaQuery",
    "GetOrdersByPizzaHandler",
    "GetOrderStatusDistributionQuery",
    "GetOrderStatusDistributionHandler",
    "GetOrdersByDriverQuery",
    "GetOrdersByDriverHandler",
    "GetKitchenPerformanceQuery",
    "GetKitchenPerformanceHandler",
    "GetStaffPerformanceQuery",
    "GetStaffPerformanceHandler",
    "GetTopCustomersQuery",
    "GetTopCustomersHandler",
    "GetCustomerNotificationsQuery",
    "GetCustomerNotificationsHandler",
]
