"""
State-based aggregate serialization for domain-driven design patterns.

DEPRECATED: This module is deprecated and will be removed in a future version.

Use JsonSerializer instead - it now automatically handles AggregateRoot serialization:
- Automatically detects and extracts state from AggregateRoot
- Stores clean state JSON without metadata wrappers
- Reconstructs aggregates from clean state during deserialization
- Backward compatible with old AggregateSerializer format

Migration Guide:
    Before (deprecated):
    ```python
    from neuroglia.serialization.aggregate_serializer import AggregateSerializer

    serializer = AggregateSerializer()
    json_text = serializer.serialize_to_text(order)
    # Result: {"aggregate_type": "Order", "state": {...}}
    ```

    After (recommended):
    ```python
    from neuroglia.serialization.json import JsonSerializer

    serializer = JsonSerializer()
    json_text = serializer.serialize_to_text(order)
    # Result: {...} - clean state, no wrapper
    ```

This module provides specialized serialization support for AggregateRoot objects
that use state-based persistence (as opposed to event sourcing). It handles the
proper serialization and deserialization of aggregate state while maintaining
the separation between aggregate behavior and state data.

Key Features:
    - Automatic detection of AggregateRoot types
    - Proper state extraction and reconstruction
    - Support for value objects and primitive types
    - NO nested aggregates (use value objects instead - proper DDD)
    - Integration with existing JsonSerializer

Examples:
    ```python
    # Service registration
    services.add_singleton(AggregateSerializer)
    serializer = provider.get_service(AggregateSerializer)

    # Serialize aggregate with value objects
    order = Order(customer_id="123")
    order_item = OrderItem(pizza_id="p1", name="Margherita", size=PizzaSize.LARGE, ...)
    order.add_order_item(order_item)
    json_text = serializer.serialize_to_text(order)

    # Result structure:
    # {
    #   "aggregate_type": "Order",
    #   "state": {
    #     "id": "order-123",
    #     "customer_id": "123",
    #     "order_items": [  # Value objects, not aggregates!
    #       {"pizza_id": "p1", "name": "Margherita", "size": "LARGE", ...}
    #     ],
    #     "status": "PENDING"
    #   }
    # }

    # Deserialize aggregate
    restored_order = serializer.deserialize_from_text(json_text, Order)
    assert restored_order.state.customer_id == "123"
    assert len(restored_order.state.order_items) > 0
    ```

Note:
    Events are NOT persisted - this is state-based persistence only.
    Events should be dispatched and handled immediately, not saved with state.
    For event sourcing, use EventStore instead.

See Also:
    - Domain-Driven Design: https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/
    - State-Based Persistence: https://bvandewe.github.io/pyneuro/features/data-access/
    - JSON Serialization: https://bvandewe.github.io/pyneuro/features/serialization/
"""

import json
from typing import Any, Optional, get_args

from neuroglia.data.abstractions import AggregateState
from neuroglia.serialization.json import JsonEncoder, JsonSerializer


class AggregateJsonEncoder(JsonEncoder):
    """
    Enhanced JSON encoder with special handling for AggregateRoot types.

    This encoder extends JsonEncoder to properly serialize AggregateRoot objects
    by extracting their state and pending events, creating a structure that can
    be reliably deserialized back into a functioning aggregate.

    Serialization Structure:
        ```json
        {
          "aggregate_type": "Order",
          "state": {
            "id": "123",
            "customer_id": "456",
            "status": "PENDING",
            ...
          },
          "pending_events": [
            {
              "event_type": "OrderCreatedEvent",
              "aggregate_id": "123",
              ...
            }
          ]
        }
        ```

    Examples:
        ```python
        # Automatic aggregate handling
        order = Order(customer_id="123")
        json_str = json.dumps(order, cls=AggregateJsonEncoder)

        # Mixed content (aggregates and regular objects)
        data = {
            "order": order,
            "timestamp": datetime.now(),
            "metadata": {"source": "api"}
        }
        json_str = json.dumps(data, cls=AggregateJsonEncoder)
        ```
    """

    def default(self, obj):
        # Check if this is an AggregateRoot
        if self._is_aggregate_root(obj):
            return self._serialize_aggregate(obj)

        # Check if this is an AggregateState
        if self._is_aggregate_state(obj):
            return self._serialize_state(obj)

        # Fall back to base encoder
        return super().default(obj)

    def _is_aggregate_root(self, obj: Any) -> bool:
        """Check if an object is an AggregateRoot."""
        try:
            # Check if it's an instance of AggregateRoot by looking for state attribute
            # and the characteristic methods
            return hasattr(obj, "state") and hasattr(obj, "register_event") and hasattr(obj, "domain_events") and hasattr(obj, "__orig_bases__")
        except Exception:
            return False

    def _is_aggregate_state(self, obj: Any) -> bool:
        """Check if an object is an AggregateState."""
        try:
            return isinstance(obj, AggregateState) or (hasattr(obj, "id") and hasattr(obj, "state_version") and hasattr(obj, "created_at"))
        except Exception:
            return False

    def _serialize_aggregate(self, aggregate: Any) -> dict:
        """
        Serialize an AggregateRoot to a dict structure for STATE-BASED persistence.

        Structure:
            - aggregate_type: The class name of the aggregate
            - state: The serialized state object

        Note: This is for STATE-BASED persistence, not event sourcing.
        Events should be dispatched and cleared BEFORE persistence, not saved.
        Events are ephemeral and represent "what just happened" - they should
        be processed immediately by event handlers, not persisted with state.

        For event sourcing (saving events only), use an EventStore instead.
        """
        result = {
            "aggregate_type": type(aggregate).__name__,
            "state": self._serialize_state(aggregate.state),
        }

        # DO NOT include pending_events - this is state-based persistence!
        # Events should have been dispatched and cleared before saving.
        # If you need event sourcing, use EventStore, not this serializer.

        return result

    def _serialize_state(self, state: Any) -> dict:
        """
        Serialize an AggregateState to a dict.

        Filters out private attributes and methods.
        Serializes only the state data - does not handle nested aggregates.
        Use value objects (not nested aggregates) for complex data within state.
        """
        result = {}
        for key, value in state.__dict__.items():
            if not key.startswith("_") and value is not None:
                result[key] = value
        return result


class AggregateSerializer(JsonSerializer):
    """
    Specialized serializer for STATE-BASED aggregate persistence.

    DEPRECATED: Use JsonSerializer directly - it now handles AggregateRoot automatically.

    JsonSerializer now includes all functionality of AggregateSerializer:
    - Automatic AggregateRoot detection
    - State extraction during serialization
    - Aggregate reconstruction during deserialization
    - Backward compatibility with old AggregateSerializer format

    This serializer extends JsonSerializer with specific handling for AggregateRoot
    objects, ensuring proper serialization and deserialization of aggregate state
    while maintaining the separation between behavior and data.

    IMPORTANT: This is for STATE-BASED persistence, NOT event sourcing.
    - Saves only the current state snapshot
    - Does NOT save events (events are ephemeral and should be dispatched immediately)
    - For event sourcing, use EventStore instead
    Key Features:
        - Automatic AggregateRoot detection and handling
        - Proper state extraction and reconstruction
        - Support for value objects and primitive types
        - NO nested aggregates (violates DDD aggregate boundaries)
        - Backward compatible with JsonSerializer

    Usage Patterns:

        1. **Direct Serialization**:
        ```python
        serializer = AggregateSerializer()
        order = Order(customer_id="123")

        # Serialize
        json_text = serializer.serialize_to_text(order)

        # Deserialize
        restored_order = serializer.deserialize_from_text(json_text, Order)
        ```

        2. **Repository Integration**:
        ```python
        class OrderRepository(StateBasedRepository[Order, str]):
            def __init__(self):
                super().__init__(
                    data_directory="data",
                    entity_type=Order,
                    serializer=AggregateSerializer()
                )
        ```

        3. **Mixed Content**:
        ```python
        # Can handle both aggregates and regular objects
        data = {
            "order": order,  # AggregateRoot
            "customer": customer,  # Regular entity
            "timestamp": datetime.now()
        }
        json_text = serializer.serialize_to_text(data)
        ```

    Serialization Format:
        ```json
        {
          "aggregate_type": "Order",
          "state": {
            "id": "order-123",
            "customer_id": "customer-456",
            "order_items": [  // Value objects, not nested aggregates!
              {
                "pizza_id": "pizza-789",
                "name": "Margherita",
                "size": "LARGE",
                "base_price": 12.99,
                "toppings": ["basil", "mozzarella"],
                "total_price": 20.78
              }
            ],
            "status": "PENDING"
          }
        }
        ```

    Note:
        Events are NOT included in serialization - this is state-based persistence.
        Events should be dispatched immediately and handled by event handlers,
        not persisted with aggregate state. For event sourcing, use EventStore.

    See Also:
        - Domain-Driven Design: https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/
        - State-Based Repositories: https://bvandewe.github.io/pyneuro/features/data-access/
        - JSON Serialization: https://bvandewe.github.io/pyneuro/features/serialization/
    """

    def serialize_to_text(self, value: Any) -> str:
        """
        Serialize a value to JSON text with aggregate support.

        Args:
            value: The object to serialize (can be AggregateRoot, regular object, or mixed)

        Returns:
            JSON string representation
        """
        return json.dumps(value, cls=AggregateJsonEncoder)

    def deserialize_from_text(self, input: str, expected_type: Optional[type] = None) -> Any:
        """
        Deserialize JSON text to an object with aggregate reconstruction.

        Args:
            input: JSON string to deserialize
            expected_type: Expected type for deserialization

        Returns:
            Deserialized object (AggregateRoot or regular object)
        """
        data = json.loads(input)

        if expected_type is None or not isinstance(data, dict):
            return data

        # Check if this is a serialized aggregate
        if "aggregate_type" in data and "state" in data:
            return self._deserialize_aggregate(data, expected_type)

        # Fall back to base deserialization
        return super().deserialize_from_text(input, expected_type)

    def _deserialize_aggregate(self, data: dict, expected_type: type) -> Any:
        """
        Deserialize an aggregate from the special aggregate structure.

        Args:
            data: Dictionary with 'aggregate_type' and 'state' keys
            expected_type: The aggregate class to instantiate

        Returns:
            Reconstructed aggregate instance
        """
        # Create aggregate instance without calling __init__
        aggregate = object.__new__(expected_type)

        # Initialize the state
        state_type = self._get_state_type(expected_type)
        if state_type:
            # Deserialize the state
            state_instance = self._deserialize_state(data["state"], state_type)
            aggregate.state = state_instance
        else:
            # Fallback: create empty state
            aggregate.state = object.__new__(object)

        # Initialize pending events as empty list
        # Events are NOT persisted in state-based persistence - they should have been
        # dispatched and cleared before the aggregate was saved
        aggregate._pending_events = []

        return aggregate

    def _get_state_type(self, aggregate_type: type) -> Optional[type]:
        """
        Extract the state type from an AggregateRoot type annotation.

        Args:
            aggregate_type: The AggregateRoot class

        Returns:
            The state class, or None if not found
        """
        try:
            # Get the generic type arguments from AggregateRoot[TState, TKey]
            if hasattr(aggregate_type, "__orig_bases__"):
                for base in aggregate_type.__orig_bases__:
                    if hasattr(base, "__origin__") and hasattr(base, "__args__"):
                        # This is a generic base like AggregateRoot[OrderState, str]
                        args = get_args(base)
                        if args and len(args) >= 1:
                            return args[0]  # Return TState
            return None
        except Exception:
            return None

    def _deserialize_state(self, state_data: dict, state_type: type) -> Any:
        """
        Deserialize state data into a state object.

        Args:
            state_data: Dictionary of state fields
            state_type: The state class to instantiate

        Returns:
            Reconstructed state instance

        Note:
            This handles only value objects and primitive types.
            If you need nested aggregates, refactor to use value objects instead.
            Nested aggregates violate DDD aggregate boundaries.
        """
        # Deserialize the state using base JSON deserialization
        state_json = json.dumps(state_data)
        state_instance = super().deserialize_from_text(state_json, state_type)

        return state_instance
