# API Controllers
#
# Controllers are auto-discovered by the framework based on their class names.
# Each controller file should contain a single controller class that inherits from ControllerBase.
# The framework automatically routes based on controller class names (e.g., OrdersController -> /orders).

from api.controllers.auth_controller import AuthController
from api.controllers.delivery_controller import DeliveryController
from api.controllers.kitchen_controller import KitchenController
from api.controllers.menu_controller import MenuController
from api.controllers.orders_controller import OrdersController
from api.controllers.profile_controller import ProfileController

__all__ = [
    "AuthController",
    "DeliveryController",
    "KitchenController",
    "MenuController",
    "OrdersController",
    "ProfileController",
]
