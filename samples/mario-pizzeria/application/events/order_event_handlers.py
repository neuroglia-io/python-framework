"""
Order event handlers for Mario's Pizzeria.

These handlers process order-related domain events to implement side effects like
notifications, kitchen updates, delivery tracking, customer communications,
customer active order management, and customer notification creation.
"""

import logging

from application.events.base_domain_event_handler import BaseDomainEventHandler
from domain.entities import CustomerNotification, NotificationType
from domain.events import (
    CookingStartedEvent,
    OrderCancelledEvent,
    OrderConfirmedEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderReadyEvent,
    PizzaAddedToOrderEvent,
    PizzaRemovedFromOrderEvent,
)
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mediation import DomainEventHandler, Mediator

# Set up logger
logger = logging.getLogger(__name__)


class OrderCreatedEventHandler(BaseDomainEventHandler[OrderCreatedEvent], DomainEventHandler[OrderCreatedEvent]):
    """Handles order created events - updates customer active orders and creates initial notification"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        customer_repository: ICustomerRepository,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)
        self.customer_repository = customer_repository

    async def handle_async(self, event: OrderCreatedEvent) -> None:
        """Process order created event"""
        logger.info(f"🍕 Order {event.aggregate_id} created for customer {event.customer_id}!")

        try:
            # Add order to customer's active orders
            customer = await self.customer_repository.get_async(event.customer_id)
            if customer:
                customer.add_active_order(event.aggregate_id)
                await self.customer_repository.update_async(customer)
                logger.info(f"Added order {event.aggregate_id} to customer {event.customer_id} active orders")
            else:
                logger.warning(f"Customer {event.customer_id} not found when processing OrderCreatedEvent")

        except Exception as e:
            logger.error(f"Error updating customer active orders for order {event.aggregate_id}: {e}")

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class OrderConfirmedEventHandler(BaseDomainEventHandler[OrderConfirmedEvent], DomainEventHandler[OrderConfirmedEvent]):
    """Handles order confirmation events - sends notifications and updates kitchen"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)

    async def handle_async(self, event: OrderConfirmedEvent) -> None:
        """Process order confirmed event"""
        logger.info(f"🍕 Order {event.aggregate_id} confirmed! " f"Total: ${event.total_amount}, Pizzas: {event.pizza_count}")

        # In a real application, you might:
        # - Send SMS notification to customer
        # - Send email receipt
        # - Notify kitchen display system
        # - Update analytics/reporting databases
        # - Create kitchen ticket

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class CookingStartedEventHandler(BaseDomainEventHandler[CookingStartedEvent], DomainEventHandler[CookingStartedEvent]):
    """Handles cooking started events - creates customer notification and updates kitchen display"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, event: CookingStartedEvent) -> None:
        """Process cooking started event"""
        logger.info(f"👨‍🍳 Cooking started for order {event.aggregate_id} by {event.user_name} at {event.cooking_started_time}")

        try:
            # Get order to find customer
            order = await self.order_repository.get_async(event.aggregate_id)
            if order and hasattr(order.state, "customer_id"):
                customer_id = order.state.customer_id

                # Create customer notification
                notification = CustomerNotification(
                    customer_id=customer_id,
                    notification_type=NotificationType.ORDER_COOKING_STARTED,
                    title="👨‍🍳 Cooking Started",
                    message=f"Chef {event.user_name} has started preparing your order! Your delicious pizza is now being made.",
                    order_id=event.aggregate_id,
                )

                # Note: We'll need a notification repository to save this
                logger.info(f"Created cooking started notification for customer {customer_id}, order {event.aggregate_id}")

        except Exception as e:
            logger.error(f"Error creating cooking started notification for order {event.aggregate_id}: {e}")

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class OrderReadyEventHandler(BaseDomainEventHandler[OrderReadyEvent], DomainEventHandler[OrderReadyEvent]):
    """Handles order ready events - creates customer notification and manages pickup systems"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, event: OrderReadyEvent) -> None:
        """Process order ready event"""
        logger.info(f"✅ Order {event.aggregate_id} is ready for pickup/delivery! Ready at: {event.ready_time}")

        # Calculate timing performance
        if event.estimated_ready_time:
            actual_minutes = (event.ready_time - event.estimated_ready_time).total_seconds() / 60
            if actual_minutes > 5:
                logger.warning(f"⏰ Order {event.aggregate_id} was {actual_minutes:.1f} minutes late")
            elif actual_minutes < -5:
                logger.info(f"🚀 Order {event.aggregate_id} was ready {-actual_minutes:.1f} minutes early")

        try:
            # Get order to find customer
            order = await self.order_repository.get_async(event.aggregate_id)
            if order and hasattr(order.state, "customer_id"):
                customer_id = order.state.customer_id
                if customer_id:
                    # Create customer notification
                    notification = CustomerNotification(
                        customer_id=customer_id,
                        notification_type=NotificationType.ORDER_READY,
                        title="🍕 Order Ready!",
                        message=f"Great news! Your order is ready for pickup or delivery. Come get your delicious pizza while it's hot!",
                        order_id=event.aggregate_id,
                    )

                    # Note: We'll need a notification repository to save this
                    logger.info(f"Created order ready notification for customer {customer_id}, order {event.aggregate_id}")

        except Exception as e:
            logger.error(f"Error creating order ready notification for order {event.aggregate_id}: {e}")

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class OrderDeliveredEventHandler(BaseDomainEventHandler[OrderDeliveredEvent], DomainEventHandler[OrderDeliveredEvent]):
    """Handles order delivered events - removes from active orders and completes the order lifecycle"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, event: OrderDeliveredEvent) -> None:
        """Process order delivered event"""
        logger.info(f"🎉 Order {event.aggregate_id} delivered successfully at {event.delivered_time}")

        try:
            # Get order to find customer and remove from active orders
            order = await self.order_repository.get_async(event.aggregate_id)
            if order and hasattr(order.state, "customer_id"):
                customer_id = order.state.customer_id
                if customer_id:
                    customer = await self.customer_repository.get_async(customer_id)
                    if customer:
                        customer.remove_active_order(event.aggregate_id)
                        await self.customer_repository.update_async(customer)
                        logger.info(f"Removed order {event.aggregate_id} from customer {customer_id} active orders")

        except Exception as e:
            logger.error(f"Error removing order from customer active orders for order {event.aggregate_id}: {e}")

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class OrderCancelledEventHandler(BaseDomainEventHandler[OrderCancelledEvent], DomainEventHandler[OrderCancelledEvent]):
    """Handles order cancelled events - removes from active orders, manages refunds and notifications"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, event: OrderCancelledEvent) -> None:
        """Process order cancelled event"""
        reason_msg = f" (Reason: {event.reason})" if event.reason else ""
        logger.info(f"❌ Order {event.aggregate_id} cancelled at {event.cancelled_time}{reason_msg}")

        try:
            # Get order to find customer and remove from active orders
            order = await self.order_repository.get_async(event.aggregate_id)
            if order and hasattr(order.state, "customer_id"):
                customer_id = order.state.customer_id
                if customer_id:
                    customer = await self.customer_repository.get_async(customer_id)
                    if customer:
                        customer.remove_active_order(event.aggregate_id)
                        await self.customer_repository.update_async(customer)
                        logger.info(f"Removed cancelled order {event.aggregate_id} from customer {customer_id} active orders")

        except Exception as e:
            logger.error(f"Error removing cancelled order from customer active orders for order {event.aggregate_id}: {e}")

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class PizzaAddedToOrderEventHandler(BaseDomainEventHandler[PizzaAddedToOrderEvent], DomainEventHandler[PizzaAddedToOrderEvent]):
    """Handles pizza additions to orders"""

    async def handle_async(self, event: PizzaAddedToOrderEvent) -> None:
        """Process pizza added to order event"""
        logger.info(f"🍕 Added {event.pizza_size} {event.pizza_name} (${event.price}) " f"to order {event.aggregate_id}")

        # In a real application, you might:
        # - Update real-time order display for customer
        # - Check ingredient availability
        # - Update order total in UI
        # - Log popular pizza combinations

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class PizzaRemovedFromOrderEventHandler(BaseDomainEventHandler[PizzaRemovedFromOrderEvent], DomainEventHandler[PizzaRemovedFromOrderEvent]):
    """Handles pizza removals from orders"""

    async def handle_async(self, event: PizzaRemovedFromOrderEvent) -> None:
        """Process pizza removed from order event"""
        logger.info(f"Removed line item {event.line_item_id} from order {event.aggregate_id}")

        # In a real application, you might:
        # - Update real-time order display for customer
        # - Release reserved ingredients
        # - Update order total in UI
        # - Log customer behavior patterns

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None
