"""
Test to verify that enum serialization change (name -> value) works correctly
for both serialization and deserialization, including nested objects.

This test ensures backward compatibility with old uppercase enum names
while using lowercase enum values going forward.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from neuroglia.serialization.json import JsonSerializer


class OrderStatus(Enum):
    """Test enum with lowercase values"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COOKING = "cooking"
    READY = "ready"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PizzaSize(Enum):
    """Test enum with lowercase values"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class Pizza:
    """Nested object with enum"""

    name: str
    size: PizzaSize
    price: float


@dataclass
class Order:
    """Main object with enum and nested objects containing enums"""

    id: str
    status: OrderStatus
    pizzas: list[Pizza]
    notes: Optional[str] = None


class TestEnumSerializationFix:
    """Test suite for enum serialization fix"""

    def setup_method(self):
        """Setup test fixtures"""
        self.serializer = JsonSerializer()

    def test_enum_serializes_as_lowercase_value(self):
        """Test that enums serialize using their lowercase value, not uppercase name"""
        status = OrderStatus.READY
        json_text = self.serializer.serialize_to_text({"status": status})

        assert '"ready"' in json_text  # Should use value
        assert '"READY"' not in json_text  # Should NOT use name

    def test_enum_deserializes_from_lowercase_value(self):
        """Test that enums can be deserialized from lowercase values (new format)"""
        json_text = '{"status": "ready"}'
        result = self.serializer.deserialize_from_text(json_text, dict)

        # When deserializing without type hint, it stays as string
        assert result["status"] == "ready"

    def test_enum_deserializes_from_uppercase_name(self):
        """Test backward compatibility: enums can still be deserialized from uppercase names (old format)"""
        json_text = '{"status": "READY"}'
        result = self.serializer.deserialize_from_text(json_text, dict)

        # When deserializing without type hint, it stays as string
        assert result["status"] == "READY"

    def test_typed_enum_deserialization_from_value(self):
        """Test that typed deserialization works with lowercase values"""

        @dataclass
        class StatusContainer:
            status: OrderStatus

        json_text = '{"status": "ready"}'
        result = self.serializer.deserialize_from_text(json_text, StatusContainer)

        assert isinstance(result.status, OrderStatus)
        assert result.status == OrderStatus.READY
        assert result.status.value == "ready"

    def test_typed_enum_deserialization_from_name_backward_compat(self):
        """Test backward compatibility: typed deserialization works with uppercase names"""

        @dataclass
        class StatusContainer:
            status: OrderStatus

        json_text = '{"status": "READY"}'
        result = self.serializer.deserialize_from_text(json_text, StatusContainer)

        assert isinstance(result.status, OrderStatus)
        assert result.status == OrderStatus.READY
        assert result.status.value == "ready"

    def test_nested_enum_serialization(self):
        """Test that enums in nested objects serialize as lowercase values"""
        order = Order(
            id="order-123",
            status=OrderStatus.READY,
            pizzas=[
                Pizza(name="Margherita", size=PizzaSize.LARGE, price=12.99),
                Pizza(name="Pepperoni", size=PizzaSize.MEDIUM, price=10.99),
            ],
        )

        json_text = self.serializer.serialize_to_text(order)

        # Check that status uses lowercase value
        assert '"status": "ready"' in json_text
        assert '"READY"' not in json_text

        # Check that nested pizza sizes use lowercase values
        assert '"size": "large"' in json_text
        assert '"size": "medium"' in json_text
        assert '"LARGE"' not in json_text
        assert '"MEDIUM"' not in json_text

    def test_nested_enum_deserialization_from_values(self):
        """Test that nested enums deserialize correctly from lowercase values"""
        json_text = """{
            "id": "order-123",
            "status": "ready",
            "pizzas": [
                {"name": "Margherita", "size": "large", "price": 12.99},
                {"name": "Pepperoni", "size": "medium", "price": 10.99}
            ],
            "notes": null
        }"""

        result = self.serializer.deserialize_from_text(json_text, Order)

        # Check main object enum
        assert isinstance(result.status, OrderStatus)
        assert result.status == OrderStatus.READY
        assert result.status.value == "ready"

        # Check nested object enums
        assert len(result.pizzas) == 2
        assert isinstance(result.pizzas[0].size, PizzaSize)
        assert result.pizzas[0].size == PizzaSize.LARGE
        assert result.pizzas[0].size.value == "large"
        assert isinstance(result.pizzas[1].size, PizzaSize)
        assert result.pizzas[1].size == PizzaSize.MEDIUM
        assert result.pizzas[1].size.value == "medium"

    def test_nested_enum_deserialization_backward_compat(self):
        """Test backward compatibility: nested enums deserialize from uppercase names"""
        json_text = """{
            "id": "order-123",
            "status": "READY",
            "pizzas": [
                {"name": "Margherita", "size": "LARGE", "price": 12.99},
                {"name": "Pepperoni", "size": "MEDIUM", "price": 10.99}
            ],
            "notes": null
        }"""

        result = self.serializer.deserialize_from_text(json_text, Order)

        # Check main object enum
        assert isinstance(result.status, OrderStatus)
        assert result.status == OrderStatus.READY

        # Check nested object enums
        assert isinstance(result.pizzas[0].size, PizzaSize)
        assert result.pizzas[0].size == PizzaSize.LARGE
        assert isinstance(result.pizzas[1].size, PizzaSize)
        assert result.pizzas[1].size == PizzaSize.MEDIUM

    def test_mixed_enum_formats_backward_compat(self):
        """Test that we can handle mixed uppercase and lowercase enum values (during migration)"""
        json_text = """{
            "id": "order-123",
            "status": "READY",
            "pizzas": [
                {"name": "Margherita", "size": "large", "price": 12.99},
                {"name": "Pepperoni", "size": "MEDIUM", "price": 10.99}
            ],
            "notes": null
        }"""

        result = self.serializer.deserialize_from_text(json_text, Order)

        # All should deserialize correctly regardless of case
        assert result.status == OrderStatus.READY
        assert result.pizzas[0].size == PizzaSize.LARGE
        assert result.pizzas[1].size == PizzaSize.MEDIUM

    def test_round_trip_serialization(self):
        """Test complete round-trip: serialize then deserialize"""
        original = Order(
            id="order-456",
            status=OrderStatus.DELIVERING,
            pizzas=[Pizza(name="Hawaiian", size=PizzaSize.SMALL, price=8.99)],
            notes="Extra pineapple",
        )

        # Serialize
        json_text = self.serializer.serialize_to_text(original)

        # Should use lowercase values
        assert '"delivering"' in json_text
        assert '"small"' in json_text

        # Deserialize
        restored = self.serializer.deserialize_from_text(json_text, Order)

        # Should match original
        assert restored.id == original.id
        assert restored.status == original.status
        assert restored.status == OrderStatus.DELIVERING
        assert len(restored.pizzas) == len(original.pizzas)
        assert restored.pizzas[0].name == original.pizzas[0].name
        assert restored.pizzas[0].size == original.pizzas[0].size
        assert restored.pizzas[0].size == PizzaSize.SMALL
        assert restored.notes == original.notes
