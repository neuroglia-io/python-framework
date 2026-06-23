"""Repository implementations for Mario's Pizzeria"""

# Import generic implementations that use the framework's FileSystemRepository
from .generic_file_customer_repository import FileCustomerRepository
from .generic_file_kitchen_repository import (  # DEPRECATED: Use MongoKitchenRepository
    FileKitchenRepository,
)
from .generic_file_order_repository import FileOrderRepository
from .generic_file_pizza_repository import (  # DEPRECATED: Use MongoPizzaRepository
    FilePizzaRepository,
)

# Import MongoDB implementations
from .mongo_customer_repository import MongoCustomerRepository
from .mongo_kitchen_repository import MongoKitchenRepository
from .mongo_order_repository import MongoOrderRepository
from .mongo_pizza_repository import MongoPizzaRepository

__all__ = [
    "FileOrderRepository",
    "FilePizzaRepository",  # DEPRECATED: Use MongoPizzaRepository
    "FileCustomerRepository",
    "FileKitchenRepository",  # DEPRECATED: Use MongoKitchenRepository
    "MongoCustomerRepository",
    "MongoKitchenRepository",
    "MongoOrderRepository",
    "MongoPizzaRepository",
]
