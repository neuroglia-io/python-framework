"""
Serialization abstractions and implementations for data conversion and persistence.

This module provides comprehensive serialization capabilities for converting Python objects
to and from various formats including JSON, with intelligent type handling, automatic
conversion, and integration with the framework's dependency injection system.

Key Components:
    - Serializer: Base abstraction for binary serialization
    - TextSerializer: Base abstraction for text-based serialization
    - JsonEncoder: Enhanced JSON encoder for complex Python types
    - JsonSerializer: Full-featured JSON serialization service

Features:
    - Automatic type conversion (enums, datetime, decimals, custom objects)
    - Intelligent type inference during deserialization
    - Generic type support (List[T], Dict[K,V], Optional[T])
    - Dataclass and custom object handling
    - Type registry integration for enum discovery
    - Comprehensive error handling and fallback strategies

Examples:
    ```python
    from neuroglia.serialization import JsonSerializer, Serializer

    # Service registration
    services.add_singleton(JsonSerializer)
    services.add_singleton(Serializer, implementation_factory=lambda p: p.get_service(JsonSerializer))

    # Usage
    serializer = provider.get_service(JsonSerializer)

    # Complex object serialization
    user = User(name="John", status=UserStatus.ACTIVE, created_at=datetime.now())
    json_text = serializer.serialize_to_text(user)

    # Type-safe deserialization
    restored_user = serializer.deserialize_from_text(json_text, User)
    ```

See Also:
    - Serialization Guide: https://bvandewe.github.io/pyneuro/features/serialization/
    - Type Discovery: https://bvandewe.github.io/pyneuro/features/configurable-type-discovery/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from .abstractions import Serializer, TextSerializer
from .json import JsonEncoder, JsonSerializer

__all__ = [
    "Serializer",
    "TextSerializer",
    "JsonEncoder",
    "JsonSerializer",
]
