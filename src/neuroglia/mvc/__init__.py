"""
Model-View-Controller (MVC) abstractions for building type-safe REST APIs.

This module provides the foundation for building structured web APIs using the MVC pattern
with automatic controller discovery, integrated dependency injection, CQRS mediation,
and comprehensive OpenAPI documentation generation.

Key Features:
    - ControllerBase abstraction for consistent API controller patterns
    - Automatic route discovery and registration from controller classes
    - Integrated CQRS mediation for clean separation of concerns
    - Built-in object mapping between DTOs and domain entities
    - Standardized error handling and HTTP response processing
    - OpenAPI documentation with automatic operation ID generation

Examples:
    ```python
    from neuroglia.mvc import ControllerBase
    from classy_fastapi.decorators import get, post

    class ProductsController(ControllerBase):
        @get("/{product_id}", response_model=ProductDto)
        async def get_product(self, product_id: str) -> ProductDto:
            query = GetProductByIdQuery(product_id=product_id)
            result = await self.mediator.execute_async(query)
            return self.process(result)

        @post("/", response_model=ProductDto, status_code=201)
        async def create_product(self, create_dto: CreateProductDto) -> ProductDto:
            command = self.mapper.map(create_dto, CreateProductCommand)
            result = await self.mediator.execute_async(command)
            return self.process(result)
    ```

See Also:
    - MVC Controllers Guide: https://bvandewe.github.io/pyneuro/features/mvc-controllers/
    - CQRS Integration: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from .controller_base import ControllerBase

__all__ = [
    "ControllerBase",
]
