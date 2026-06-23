"""
Test suite for JsonSerializer AggregateRoot support.

This test suite validates that JsonSerializer properly handles both Entity
and AggregateRoot types with automatic state extraction and reconstruction.
"""

import json
from dataclasses import dataclass
from enum import Enum

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, Entity
from neuroglia.serialization.json import JsonSerializer


# Test Enums
class OrderStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CustomerType(Enum):
    REGULAR = "regular"
    VIP = "vip"


# Test Entity (simple class with id property)
class Customer(Entity[str]):
    def __init__(self, id: str, name: str, email: str, customer_type: CustomerType):
        super().__init__()
        self.id = id
        self.name = name
        self.email = email
        self.customer_type = customer_type


# Test AggregateState
@dataclass
class OrderItem:
    product_id: str
    name: str
    quantity: int
    price: float


class OrderState(AggregateState[str]):
    """State for Order aggregate - contains all persisted data"""

    # Class-level type annotations (required for JsonSerializer deserialization)
    id: str
    customer_id: str
    status: OrderStatus
    items: list[OrderItem]
    total: float

    def __init__(self):
        super().__init__()
        self.id = ""
        self.customer_id = ""
        self.status = OrderStatus.PENDING
        self.items = []
        self.total = 0.0


# Test AggregateRoot
class Order(AggregateRoot[OrderState, str]):
    def __init__(self, customer_id: str = "c1", status: OrderStatus = OrderStatus.PENDING):
        super().__init__()
        # State is created automatically by AggregateRoot.__init__()
        # Now we set the fields
        self.state.id = f"o-{customer_id}"
        self.state.customer_id = customer_id
        self.state.status = status
        self.state.items = []
        self.state.total = 0.0

    def id(self) -> str:
        return self.state.id


class TestJsonSerializerEntitySupport:
    """Test Entity serialization (should be unchanged)."""

    def setup_method(self):
        self.serializer = JsonSerializer()

    def test_entity_serialization_produces_clean_json(self):
        """Entity serialization should produce clean JSON without metadata."""
        customer = Customer(id="c1", name="John Doe", email="john@example.com", customer_type=CustomerType.REGULAR)

        json_text = self.serializer.serialize_to_text(customer)
        data = json.loads(json_text)

        # Should NOT have metadata wrappers
        assert "aggregate_type" not in data
        assert "state" not in data

        # Should have direct fields
        assert data["id"] == "c1"
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["customer_type"] == "REGULAR"

    def test_entity_deserialization_works(self):
        """Entity deserialization should work normally."""
        json_text = '{"id": "c1", "name": "Jane Doe", "email": "jane@example.com", "customer_type": "VIP"}'

        customer = self.serializer.deserialize_from_text(json_text, Customer)

        assert isinstance(customer, Customer)
        assert customer.id == "c1"
        assert customer.name == "Jane Doe"
        assert customer.email == "jane@example.com"
        assert customer.customer_type == CustomerType.VIP

    def test_entity_round_trip_preservation(self):
        """Entity should survive serialization round-trip."""
        original = Customer(id="c2", name="Alice Smith", email="alice@example.com", customer_type=CustomerType.VIP)

        json_text = self.serializer.serialize_to_text(original)
        restored = self.serializer.deserialize_from_text(json_text, Customer)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.email == original.email
        assert restored.customer_type == original.customer_type


class TestJsonSerializerAggregateRootSupport:
    """Test AggregateRoot serialization with automatic state extraction."""

    def setup_method(self):
        self.serializer = JsonSerializer()

    def test_aggregate_root_detection(self):
        """Serializer should correctly detect AggregateRoot instances."""
        order = Order(customer_id="c1", status=OrderStatus.PENDING)

        # Internal method test
        assert self.serializer._is_aggregate_root(order) is True
        assert self.serializer._is_aggregate_root(order.state) is False

    def test_aggregate_root_type_detection(self):
        """Serializer should correctly detect AggregateRoot types."""
        assert self.serializer._is_aggregate_root_type(Order) is True
        assert self.serializer._is_aggregate_root_type(Customer) is False
        assert self.serializer._is_aggregate_root_type(OrderState) is False

    def test_state_type_extraction(self):
        """Serializer should extract state type from AggregateRoot generic."""
        state_type = self.serializer._get_state_type(Order)

        assert state_type == OrderState

    def test_aggregate_serialization_extracts_state_automatically(self):
        """AggregateRoot serialization should extract and serialize state only."""
        order = Order(customer_id="c1", status=OrderStatus.PENDING)
        order.state.items = [
            OrderItem(product_id="p1", name="Widget", quantity=2, price=10.0),
            OrderItem(product_id="p2", name="Gadget", quantity=1, price=25.0),
        ]
        order.state.total = 45.0

        json_text = self.serializer.serialize_to_text(order)
        data = json.loads(json_text)

        # Should NOT have aggregate metadata
        assert "aggregate_type" not in data
        assert "state" not in data

        # Should have direct state fields (clean!)
        assert data["customer_id"] == "c1"
        assert data["status"] == "PENDING"
        assert len(data["items"]) == 2
        assert data["items"][0]["product_id"] == "p1"
        assert data["items"][0]["name"] == "Widget"
        assert data["total"] == 45.0

    def test_aggregate_deserialization_reconstructs_from_clean_state(self):
        """AggregateRoot deserialization should reconstruct from clean state JSON."""
        json_text = json.dumps(
            {
                "id": "o2",
                "customer_id": "c2",
                "status": "IN_PROGRESS",
                "items": [{"product_id": "p3", "name": "Tool", "quantity": 1, "price": 15.0}],
                "total": 15.0,
            }
        )

        order = self.serializer.deserialize_from_text(json_text, Order)

        # Should reconstruct aggregate properly
        assert isinstance(order, Order)
        assert isinstance(order.state, OrderState)

        # State should be properly deserialized
        assert order.state.id == "o2"
        assert order.state.customer_id == "c2"
        assert order.state.status == OrderStatus.IN_PROGRESS
        assert len(order.state.items) == 1
        assert order.state.items[0].product_id == "p3"
        assert order.state.items[0].name == "Tool"
        assert order.state.total == 15.0

        # Should have empty event list (events are ephemeral)
        assert order.domain_events == []

    def test_aggregate_round_trip_preservation(self):
        """AggregateRoot should survive serialization round-trip."""
        original_order = Order(customer_id="c3", status=OrderStatus.COMPLETED)
        original_order.state.items = [
            OrderItem(product_id="p4", name="Item A", quantity=3, price=8.0),
            OrderItem(product_id="p5", name="Item B", quantity=2, price=12.0),
        ]
        original_order.state.total = 48.0

        # Serialize
        json_text = self.serializer.serialize_to_text(original_order)

        # Deserialize
        restored_order = self.serializer.deserialize_from_text(json_text, Order)

        # Validate
        assert restored_order.state.customer_id == original_order.state.customer_id
        assert restored_order.state.status == original_order.state.status
        assert len(restored_order.state.items) == len(original_order.state.items)
        assert restored_order.state.items[0].product_id == original_order.state.items[0].product_id
        assert restored_order.state.total == original_order.state.total


class TestBackwardCompatibility:
    """Test backward compatibility with old AggregateSerializer format."""

    def setup_method(self):
        self.serializer = JsonSerializer()

    def test_deserialize_old_format_with_metadata_wrapper(self):
        """Should handle old format with aggregate_type and state wrapper."""
        old_format_json = json.dumps(
            {
                "aggregate_type": "Order",
                "state": {
                    "id": "o4",
                    "customer_id": "c4",
                    "status": "PENDING",
                    "items": [],
                    "total": 0.0,
                },
            }
        )

        order = self.serializer.deserialize_from_text(old_format_json, Order)

        # Should successfully extract state from old format
        assert isinstance(order, Order)
        assert order.state.id == "o4"
        assert order.state.customer_id == "c4"
        assert order.state.status == OrderStatus.PENDING

    def test_deserialize_new_format_without_wrapper(self):
        """Should handle new format (clean state)."""
        new_format_json = json.dumps({"id": "o5", "customer_id": "c5", "status": "COMPLETED", "items": [], "total": 100.0})

        order = self.serializer.deserialize_from_text(new_format_json, Order)

        # Should successfully deserialize new format
        assert isinstance(order, Order)
        assert order.state.id == "o5"
        assert order.state.customer_id == "c5"
        assert order.state.status == OrderStatus.COMPLETED
        assert order.state.total == 100.0


class TestStorageFormatComparison:
    """Compare storage formats to demonstrate improvements."""

    def setup_method(self):
        self.serializer = JsonSerializer()

    def test_storage_format_is_clean_and_queryable(self):
        """New format should be clean and directly queryable."""
        order = Order(customer_id="c6", status=OrderStatus.IN_PROGRESS)
        order.state.items = [OrderItem("p1", "Product", 1, 10.0)]
        order.state.total = 10.0

        json_text = self.serializer.serialize_to_text(order)
        data = json.loads(json_text)

        # Format should allow direct queries (e.g., MongoDB)
        # Instead of: db.orders.find({"state.status": "IN_PROGRESS"})  ❌
        # We can do: db.orders.find({"status": "IN_PROGRESS"})  ✅

        assert "status" in data  # Direct field access
        assert data["status"] == "IN_PROGRESS"

        # No nested "state" wrapper
        assert "state" not in data

        # No metadata pollution
        assert "aggregate_type" not in data

    def test_storage_size_comparison(self):
        """New format should be smaller (no metadata overhead)."""
        order = Order(customer_id="c7", status=OrderStatus.PENDING)
        order.state.total = 0.0

        # New format (clean state)
        new_format = self.serializer.serialize_to_text(order)

        # Simulate old format (with wrapper)
        old_format = json.dumps({"aggregate_type": "Order", "state": json.loads(new_format)})

        # New format should be smaller
        assert len(new_format) < len(old_format)

        # Difference is the metadata overhead
        overhead_bytes = len(old_format) - len(new_format)
        assert overhead_bytes > 20  # At least the aggregate_type field


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
