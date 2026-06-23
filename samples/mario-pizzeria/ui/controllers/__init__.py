# This file is needed to make the ui controllers package importable
# Import all controllers to ensure they are registered
from ui.controllers.delivery_controller import UIDeliveryController
from ui.controllers.home_controller import HomeController
from ui.controllers.kitchen_controller import UIKitchenController
from ui.controllers.management_controller import UIManagementController
from ui.controllers.notifications_controller import UINotificationsController

__all__ = [
    "HomeController",
    "UIKitchenController",
    "UIDeliveryController",
    "UIManagementController",
    "UINotificationsController",
]
