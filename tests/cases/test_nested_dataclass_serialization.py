"""
Comprehensive tests for nested dataclass serialization and deserialization.

This test suite validates that JsonSerializer properly handles:
1. Simple dataclasses in lists
2. Nested dataclasses with complex types (Decimal, Enum)
3. Dataclass value objects within aggregate state
4. Mixed types in collections

These tests ensure the framework enhancement for proper dataclass deserialization
in collections works correctly.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from neuroglia.serialization.json import JsonSerializer


# Test data structures
class ItemSize(Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


@dataclass(frozen=True)
class SimpleItem:
    """Simple dataclass for basic testing."""

    id: str
    name: str
    quantity: int


@dataclass(frozen=True)
class PriceItem:
    """Dataclass with Decimal and computed properties (like OrderItem)."""

    item_id: str
    name: str
    size: ItemSize
    base_price: Decimal
    extras: list[str]

    @property
    def extra_cost(self) -> Decimal:
        """Calculate cost of extras."""
        return self.base_price * Decimal("0.15") * len(self.extras)

    @property
    def total_price(self) -> Decimal:
        """Calculate total price."""
        size_multipliers = {
            ItemSize.SMALL: Decimal("0.8"),
            ItemSize.MEDIUM: Decimal("1.0"),
            ItemSize.LARGE: Decimal("1.5"),
        }
        multiplier = size_multipliers.get(self.size, Decimal("1.0"))
        return (self.base_price + self.extra_cost) * multiplier


@dataclass
class Order:
    """Container with list of dataclass items."""

    order_id: str
    customer_name: str
    items: list[PriceItem]
    notes: Optional[str] = None

    @property
    def total_amount(self) -> Decimal:
        """Calculate total from all items."""
        return sum((item.total_price for item in self.items), Decimal("0"))


class TestNestedDataclassSerialization:
    """Test suite for nested dataclass serialization."""

    def setup_method(self):
        """Setup test fixtures."""
        self.serializer = JsonSerializer()

    def test_simple_dataclass_in_list(self):
        """Test basic dataclass serialization in a list."""
        # Arrange
        items = [
            SimpleItem(id="1", name="Item One", quantity=5),
            SimpleItem(id="2", name="Item Two", quantity=10),
            SimpleItem(id="3", name="Item Three", quantity=3),
        ]

        # Act
        json_text = self.serializer.serialize_to_text(items)
        deserialized = self.serializer.deserialize_from_text(json_text, list[SimpleItem])

        # Assert
        assert len(deserialized) == 3
        assert all(isinstance(item, SimpleItem) for item in deserialized)
        assert deserialized[0].id == "1"
        assert deserialized[0].name == "Item One"
        assert deserialized[0].quantity == 5
        assert deserialized[1].id == "2"
        assert deserialized[2].quantity == 3

    def test_dataclass_with_decimal_and_enum_in_list(self):
        """Test dataclass with Decimal, Enum, and computed properties in list."""
        # Arrange
        items = [
            PriceItem(
                item_id="p1",
                name="Small Widget",
                size=ItemSize.SMALL,
                base_price=Decimal("10.00"),
                extras=["premium", "rush"],
            ),
            PriceItem(
                item_id="p2",
                name="Large Widget",
                size=ItemSize.LARGE,
                base_price=Decimal("20.00"),
                extras=["premium"],
            ),
        ]

        # Act
        json_text = self.serializer.serialize_to_text(items)
        deserialized = self.serializer.deserialize_from_text(json_text, list[PriceItem])

        # Assert
        assert len(deserialized) == 2
        assert all(isinstance(item, PriceItem) for item in deserialized)

        # Verify first item
        item1 = deserialized[0]
        assert item1.item_id == "p1"
        assert item1.name == "Small Widget"
        assert item1.size == ItemSize.SMALL
        assert item1.base_price == Decimal("10.00")
        assert list(item1.extras) == ["premium", "rush"]

        # Verify computed properties work
        assert item1.extra_cost == Decimal("3.00")  # 10 * 0.15 * 2
        assert item1.total_price == Decimal("10.40")  # (10 + 3) * 0.8

        # Verify second item
        item2 = deserialized[1]
        assert item2.item_id == "p2"
        assert item2.size == ItemSize.LARGE
        assert item2.base_price == Decimal("20.00")
        assert item2.total_price == Decimal("34.50")  # (20 + 3) * 1.5 = 34.5

    def test_nested_dataclass_in_container(self):
        """Test dataclass items nested within another dataclass."""
        # Arrange
        order = Order(
            order_id="order-123",
            customer_name="John Doe",
            items=[
                PriceItem(
                    item_id="p1",
                    name="Medium Widget",
                    size=ItemSize.MEDIUM,
                    base_price=Decimal("15.00"),
                    extras=["premium"],
                ),
                PriceItem(
                    item_id="p2",
                    name="Small Gadget",
                    size=ItemSize.SMALL,
                    base_price=Decimal("8.00"),
                    extras=[],
                ),
            ],
            notes="Rush delivery",
        )

        # Act
        json_text = self.serializer.serialize_to_text(order)
        deserialized = self.serializer.deserialize_from_text(json_text, Order)

        # Assert
        assert isinstance(deserialized, Order)
        assert deserialized.order_id == "order-123"
        assert deserialized.customer_name == "John Doe"
        assert deserialized.notes == "Rush delivery"
        assert len(deserialized.items) == 2

        # Verify nested items are proper dataclass instances
        assert all(isinstance(item, PriceItem) for item in deserialized.items)

        # Verify first item
        item1 = deserialized.items[0]
        assert item1.item_id == "p1"
        assert item1.name == "Medium Widget"
        assert item1.size == ItemSize.MEDIUM
        assert item1.base_price == Decimal("15.00")
        assert item1.total_price == Decimal("17.25")  # (15 + 2.25) * 1.0

        # Verify second item
        item2 = deserialized.items[1]
        assert item2.item_id == "p2"
        assert item2.size == ItemSize.SMALL
        assert item2.base_price == Decimal("8.00")
        assert item2.total_price == Decimal("6.40")  # (8 + 0) * 0.8

        # Verify container computed property works with proper dataclass items
        expected_total = Decimal("17.25") + Decimal("6.40")
        assert deserialized.total_amount == expected_total

    def test_empty_list_of_dataclasses(self):
        """Test empty list serialization."""
        # Arrange
        order = Order(order_id="order-empty", customer_name="Jane Doe", items=[])

        # Act
        json_text = self.serializer.serialize_to_text(order)
        deserialized = self.serializer.deserialize_from_text(json_text, Order)

        # Assert
        assert isinstance(deserialized, Order)
        assert deserialized.order_id == "order-empty"
        assert len(deserialized.items) == 0
        assert deserialized.total_amount == Decimal("0")

    def test_dataclass_with_optional_fields(self):
        """Test dataclass with optional fields in list."""
        # Arrange
        order_with_notes = Order(
            order_id="o1",
            customer_name="Customer 1",
            items=[PriceItem("p1", "Item", ItemSize.MEDIUM, Decimal("10"), [])],
            notes="Special instructions",
        )

        order_without_notes = Order(
            order_id="o2",
            customer_name="Customer 2",
            items=[PriceItem("p2", "Item", ItemSize.SMALL, Decimal("5"), [])],
            notes=None,
        )

        # Act
        json1 = self.serializer.serialize_to_text(order_with_notes)
        json2 = self.serializer.serialize_to_text(order_without_notes)

        deser1 = self.serializer.deserialize_from_text(json1, Order)
        deser2 = self.serializer.deserialize_from_text(json2, Order)

        # Assert
        assert deser1.notes == "Special instructions"
        assert deser2.notes is None
        assert len(deser1.items) == 1
        assert isinstance(deser1.items[0], PriceItem)
        assert isinstance(deser2.items[0], PriceItem)

    def test_dataclass_round_trip_preserves_types(self):
        """Test that multiple serialization cycles preserve types."""
        # Arrange
        original = Order(
            order_id="round-trip",
            customer_name="Test User",
            items=[
                PriceItem(
                    item_id="rt1",
                    name="Round Trip Test",
                    size=ItemSize.LARGE,
                    base_price=Decimal("25.50"),
                    extras=["extra1", "extra2", "extra3"],
                )
            ],
        )

        # Act - Multiple round trips
        json1 = self.serializer.serialize_to_text(original)
        deser1 = self.serializer.deserialize_from_text(json1, Order)

        json2 = self.serializer.serialize_to_text(deser1)
        deser2 = self.serializer.deserialize_from_text(json2, Order)

        json3 = self.serializer.serialize_to_text(deser2)
        deser3 = self.serializer.deserialize_from_text(json3, Order)

        # Assert - All rounds produce identical results
        assert deser1.order_id == deser2.order_id == deser3.order_id == original.order_id
        assert all(isinstance(d.items[0], PriceItem) for d in [deser1, deser2, deser3])
        assert deser1.items[0].size == deser2.items[0].size == deser3.items[0].size == ItemSize.LARGE
        assert deser1.items[0].base_price == deser2.items[0].base_price == deser3.items[0].base_price
        assert deser1.total_amount == deser2.total_amount == deser3.total_amount

    def test_computed_properties_work_after_deserialization(self):
        """Test that computed properties function correctly on deserialized dataclasses."""
        # Arrange
        item = PriceItem(
            item_id="computed-test",
            name="Computed Property Test",
            size=ItemSize.LARGE,
            base_price=Decimal("100.00"),
            extras=["a", "b", "c", "d"],  # 4 extras
        )

        # Act
        json_text = self.serializer.serialize_to_text([item])
        deserialized = self.serializer.deserialize_from_text(json_text, list[PriceItem])
        deser_item = deserialized[0]

        # Assert - Computed properties should work on deserialized instance
        # extra_cost = 100 * 0.15 * 4 = 60
        assert deser_item.extra_cost == Decimal("60.00")

        # total_price = (100 + 60) * 1.5 = 240
        assert deser_item.total_price == Decimal("240.00")

        # Verify it's actually a PriceItem instance, not a dict
        assert isinstance(deser_item, PriceItem)
        assert hasattr(deser_item, "extra_cost")
        assert hasattr(deser_item, "total_price")
