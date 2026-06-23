# Command definitions and handlers auto-discovery
# Import all command modules to ensure handlers are registered during mediation setup

from .add_pizza_command import AddPizzaCommand, AddPizzaCommandHandler
from .assign_order_to_delivery_command import (
    AssignOrderToDeliveryCommand,
    AssignOrderToDeliveryHandler,
)
from .complete_order_command import CompleteOrderCommand, CompleteOrderCommandHandler
from .create_customer_profile_command import (
    CreateCustomerProfileCommand,
    CreateCustomerProfileHandler,
)
from .dismiss_customer_notification_command import (
    DismissCustomerNotificationCommand,
    DismissCustomerNotificationHandler,
)
from .place_order_command import PlaceOrderCommand, PlaceOrderCommandHandler
from .remove_pizza_command import RemovePizzaCommand, RemovePizzaCommandHandler
from .start_cooking_command import StartCookingCommand, StartCookingCommandHandler
from .update_customer_profile_command import (
    UpdateCustomerProfileCommand,
    UpdateCustomerProfileHandler,
)
from .update_order_status_command import (
    UpdateOrderStatusCommand,
    UpdateOrderStatusHandler,
)
from .update_pizza_command import UpdatePizzaCommand, UpdatePizzaCommandHandler

# Make commands available for import
__all__ = [
    "PlaceOrderCommand",
    "PlaceOrderCommandHandler",
    "StartCookingCommand",
    "StartCookingCommandHandler",
    "CompleteOrderCommand",
    "CompleteOrderCommandHandler",
    "CreateCustomerProfileCommand",
    "CreateCustomerProfileHandler",
    "UpdateCustomerProfileCommand",
    "UpdateCustomerProfileHandler",
    "UpdateOrderStatusCommand",
    "UpdateOrderStatusHandler",
    "AssignOrderToDeliveryCommand",
    "AssignOrderToDeliveryHandler",
    "AddPizzaCommand",
    "AddPizzaCommandHandler",
    "UpdatePizzaCommand",
    "UpdatePizzaCommandHandler",
    "RemovePizzaCommand",
    "RemovePizzaCommandHandler",
    "DismissCustomerNotificationCommand",
    "DismissCustomerNotificationHandler",
]
