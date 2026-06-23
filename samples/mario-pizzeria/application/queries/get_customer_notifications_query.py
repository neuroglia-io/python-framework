"""Query for retrieving customer notifications"""

from dataclasses import dataclass

from api.dtos.notification_dtos import CustomerNotificationListDto
from application.services.notification_service import notification_service
from domain.repositories import ICustomerRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetCustomerNotificationsQuery(Query[OperationResult[CustomerNotificationListDto]]):
    """Query to get customer notifications"""

    user_id: str
    page: int = 1
    page_size: int = 20
    include_dismissed: bool = False


class GetCustomerNotificationsHandler(QueryHandler[GetCustomerNotificationsQuery, OperationResult[CustomerNotificationListDto]]):
    """Handler for customer notification queries"""

    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

    async def handle_async(self, request: GetCustomerNotificationsQuery) -> OperationResult[CustomerNotificationListDto]:
        """Handle notification retrieval"""

        try:
            # Find customer by user_id
            all_customers = await self.customer_repository.get_all_async()
            customer = None
            for c in all_customers:
                if hasattr(c.state, "user_id") and c.state.user_id == request.user_id:
                    customer = c
                    break

            if not customer:
                return self.not_found("Customer", request.user_id)

            # Get notifications from notification service (filters out dismissed notifications)
            notification_dtos = notification_service.get_sample_notifications(request.user_id, customer.id())

            # Calculate counts
            total_count = len(notification_dtos)
            unread_count = len([n for n in notification_dtos if n.status == "unread"])

            # Apply pagination
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_notifications = notification_dtos[start_idx:end_idx]

            has_more = end_idx < total_count

            result = CustomerNotificationListDto(
                notifications=paginated_notifications,
                total_count=total_count,
                unread_count=unread_count,
                page=request.page,
                page_size=request.page_size,
                has_more=has_more,
            )

            return self.ok(result)

        except Exception as e:
            return self.bad_request(f"Failed to retrieve notifications: {str(e)}")
