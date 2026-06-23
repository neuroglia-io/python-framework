"""DTOs for Mario's Pizzeria API"""

# Order DTOs
# Kitchen DTOs
from .kitchen_dtos import KitchenOrderDto, KitchenStatusDto, UpdateKitchenOrderDto

# Menu DTOs
from .menu_dtos import CreateMenuPizzaDto, MenuDto, MenuPizzaDto, UpdateMenuPizzaDto
from .order_dtos import (
    CreateOrderDto,
    CreatePizzaDto,
    CustomerDto,
    OrderDto,
    PizzaDto,
    UpdateOrderStatusDto,
)

# Profile DTOs
from .profile_dtos import CreateProfileDto, CustomerProfileDto, UpdateProfileDto

__all__ = [
    # Order DTOs
    "OrderDto",
    "CreateOrderDto",
    "UpdateOrderStatusDto",
    "PizzaDto",
    "CreatePizzaDto",
    "CustomerDto",
    # Menu DTOs
    "MenuDto",
    "MenuPizzaDto",
    "CreateMenuPizzaDto",
    "UpdateMenuPizzaDto",
    # Kitchen DTOs
    "KitchenStatusDto",
    "KitchenOrderDto",
    "UpdateKitchenOrderDto",
    # Profile DTOs
    "CustomerProfileDto",
    "CreateProfileDto",
    "UpdateProfileDto",
]
