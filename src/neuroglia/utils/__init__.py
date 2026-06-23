"""
Comprehensive utility components for string transformations and API compatibility.

This module provides essential utility functions and classes for common programming
operations including case conversion between different naming conventions, Pydantic
model utilities with automatic camelCase serialization, and string transformation
patterns commonly needed in web APIs and data serialization.

Key Components:
    - CamelCaseConverter: Comprehensive case conversion utility
    - Case Conversion Functions: Direct conversion between naming conventions
    - CamelModel: Pydantic base class with automatic camelCase serialization

Features:
    - snake_case ↔ camelCase ↔ PascalCase ↔ kebab-case conversions
    - Automatic API response serialization with camelCase
    - Pydantic model integration for JSON API compatibility
    - Bidirectional conversion with original format preservation
    - Integration with FastAPI and JSON serialization

Examples:
    ```python
    from neuroglia.utils import (
        to_camel_case, to_snake_case, to_pascal_case, to_kebab_case,
        CamelModel
    )

    # Case conversions
    snake_str = "user_first_name"
    camel_str = to_camel_case(snake_str)  # "userFirstName"
    pascal_str = to_pascal_case(snake_str)  # "UserFirstName"
    kebab_str = to_kebab_case(snake_str)  # "user-first-name"

    # API-compatible models
    class UserDto(CamelModel):
        first_name: str  # Serializes as "firstName"
        last_name: str   # Serializes as "lastName"
        email_address: str  # Serializes as "emailAddress"

    user = UserDto(
        first_name="John",
        last_name="Doe",
        email_address="john@example.com"
    )

    # JSON output uses camelCase
    json_output = user.model_dump()
    # {"firstName": "John", "lastName": "Doe", "emailAddress": "john@example.com"}
    ```

See Also:
    - Case Conversion Guide: https://bvandewe.github.io/pyneuro/features/case-conversion-utilities/
    - API Response Formatting: https://bvandewe.github.io/pyneuro/features/mvc-controllers/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from neuroglia.utils.camel_model import CamelModel
from neuroglia.utils.case_conversion import (
    CamelCaseConverter,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
)

__all__ = [
    "CamelCaseConverter",
    "to_camel_case",
    "to_snake_case",
    "to_pascal_case",
    "to_kebab_case",
    "CamelModel",
]
