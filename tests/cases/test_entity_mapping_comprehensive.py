import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from neuroglia.mapping.mapper import Mapper, MapperConfiguration, MappingProfile


class StatusEnum(str, Enum):
    """String-based enum for testing"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class PriorityEnum(int, Enum):
    """Integer-based enum for testing"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Money:
    """Value object representing money"""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if isinstance(self.amount, (int, float, str)):
            self.amount = Decimal(str(self.amount))


@dataclass
class MoneyDto:
    """DTO for Money value object"""
    value: str
    currency_code: str


@dataclass
class Address:
    """Nested entity for address information"""
    street: str
    city: str
    postal_code: str
    country: str = "USA"
    created_at: Optional[datetime] = None


@dataclass
class AddressDto:
    """DTO version of Address with different property names"""
    street_address: str
    city_name: str
    zip_code: str
    country_code: str
    creation_date: Optional[str] = None


@dataclass
class Person:
    """Complex entity with various types of attributes"""
    id: str
    first_name: str
    last_name: str
    email: str
    birth_date: date
    registration_date: datetime
    status: StatusEnum
    priority: PriorityEnum
    salary: Money
    address: Address
    phone_numbers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class PersonDto:
    """DTO version of Person with transformed properties"""
    person_id: str
    full_name: str
    email_address: str
    age: int
    registration_timestamp: str
    current_status: str
    priority_level: int
    salary_info: MoneyDto
    home_address: AddressDto
    contact_numbers: List[str] = field(default_factory=list)
    extra_data: Dict[str, Any] = field(default_factory=dict)
    active_flag: bool = True


@dataclass
class Order:
    """Entity with datetime and enum fields"""
    id: str
    order_number: str
    created_at: datetime
    order_date: date
    status: StatusEnum
    priority: PriorityEnum
    total_amount: Money
    items: List[str] = field(default_factory=list)


@dataclass
class OrderDto:
    """DTO for Order with string representations"""
    order_id: str
    number: str
    created_timestamp: str
    order_date_iso: str
    status_name: str
    priority_value: int
    total_price: str
    item_list: List[str] = field(default_factory=list)


class PersonMappingProfile(MappingProfile):
    """Mapping profile for Person to PersonDto conversion"""
    
    def __init__(self):
        # Person to PersonDto mapping
        self.create_map(Person, PersonDto)
        
        # Money to MoneyDto mapping
        self.create_map(Money, MoneyDto)
        
        # Address to AddressDto mapping
        self.create_map(Address, AddressDto)

    def configure_mappings(self, config: MapperConfiguration):
        """Configure custom member mappings"""
        # Person mappings
        person_mapping = config.create_map(Person, PersonDto)
        person_mapping.for_member("person_id", lambda ctx: ctx.source.id)
        person_mapping.for_member("full_name", lambda ctx: f"{ctx.source.first_name} {ctx.source.last_name}")
        person_mapping.for_member("email_address", lambda ctx: ctx.source.email)
        person_mapping.for_member("age", lambda ctx: (datetime.now().date() - ctx.source.birth_date).days // 365)
        person_mapping.for_member("registration_timestamp", lambda ctx: ctx.source.registration_date.isoformat())
        person_mapping.for_member("current_status", lambda ctx: ctx.source.status.value)
        person_mapping.for_member("priority_level", lambda ctx: ctx.source.priority.value)
        person_mapping.for_member("contact_numbers", lambda ctx: ctx.source.phone_numbers)
        person_mapping.for_member("extra_data", lambda ctx: ctx.source.metadata)
        person_mapping.for_member("active_flag", lambda ctx: ctx.source.is_active)
        
        # Money mappings
        money_mapping = config.create_map(Money, MoneyDto)
        money_mapping.for_member("value", lambda ctx: str(ctx.source.amount))
        money_mapping.for_member("currency_code", lambda ctx: ctx.source.currency)
        
        # Address mappings
        address_mapping = config.create_map(Address, AddressDto)
        address_mapping.for_member("street_address", lambda ctx: ctx.source.street)
        address_mapping.for_member("city_name", lambda ctx: ctx.source.city)
        address_mapping.for_member("zip_code", lambda ctx: ctx.source.postal_code)
        address_mapping.for_member("country_code", lambda ctx: ctx.source.country[:2].upper() if ctx.source.country else "US")
        address_mapping.for_member("creation_date", lambda ctx: ctx.source.created_at.isoformat() if ctx.source.created_at else None)


class OrderMappingProfile(MappingProfile):
    """Mapping profile for Order to OrderDto conversion"""
    
    def __init__(self):
        self.create_map(Order, OrderDto)

    def configure_mappings(self, config: MapperConfiguration):
        """Configure custom member mappings"""
        order_mapping = config.create_map(Order, OrderDto)
        order_mapping.for_member("order_id", lambda ctx: ctx.source.id)
        order_mapping.for_member("number", lambda ctx: ctx.source.order_number)
        order_mapping.for_member("created_timestamp", lambda ctx: ctx.source.created_at.isoformat())
        order_mapping.for_member("order_date_iso", lambda ctx: ctx.source.order_date.isoformat())
        order_mapping.for_member("status_name", lambda ctx: ctx.source.status.value)
        order_mapping.for_member("priority_value", lambda ctx: ctx.source.priority.value)
        order_mapping.for_member("total_price", lambda ctx: f"{ctx.source.total_amount.amount} {ctx.source.total_amount.currency}")
        order_mapping.for_member("item_list", lambda ctx: ctx.source.items)


class TestEntityMappingWithComplexTypes:
    """Test entity mapping with datetime, enum, and value objects"""

    def test_basic_entity_mapping(self):
        """Test basic entity mapping functionality"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class SimpleEntity:
            id: str
            name: str
            status: StatusEnum
        
        @dataclass
        class SimpleEntityDto:
            id: str
            name: str
            status: StatusEnum
        
        entity = SimpleEntity(id="123", name="Test Entity", status=StatusEnum.ACTIVE)
        config.create_map(SimpleEntity, SimpleEntityDto)

        # act
        result = mapper.map(entity, SimpleEntityDto)

        # assert
        assert result.id == "123"
        assert result.name == "Test Entity"
        assert result.status == StatusEnum.ACTIVE

    def test_datetime_mapping(self):
        """Test mapping entities with datetime fields"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithDates:
            id: str
            created_at: datetime
            birth_date: date
        
        @dataclass
        class EntityWithDatesDto:
            id: str
            created_timestamp: str
            birth_date_iso: str
        
        now = datetime(2023, 12, 25, 15, 30, 45)
        birth = date(1990, 5, 15)
        entity = EntityWithDates(id="datetime-test", created_at=now, birth_date=birth)
        
        mapping = config.create_map(EntityWithDates, EntityWithDatesDto)
        mapping.for_member("created_timestamp", lambda ctx: ctx.source.created_at.isoformat())
        mapping.for_member("birth_date_iso", lambda ctx: ctx.source.birth_date.isoformat())

        # act
        result = mapper.map(entity, EntityWithDatesDto)

        # assert
        assert result.id == "datetime-test"
        assert result.created_timestamp == "2023-12-25T15:30:45"
        assert result.birth_date_iso == "1990-05-15"

    def test_enum_mapping_with_conversion(self):
        """Test enum mapping with value conversion"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithEnums:
            id: str
            status: StatusEnum
            priority: PriorityEnum
        
        @dataclass
        class EntityWithEnumsDto:
            id: str
            status_value: str
            priority_number: int
        
        entity = EntityWithEnums(id="enum-test", status=StatusEnum.PENDING, priority=PriorityEnum.HIGH)
        
        mapping = config.create_map(EntityWithEnums, EntityWithEnumsDto)
        mapping.for_member("status_value", lambda ctx: ctx.source.status.value)
        mapping.for_member("priority_number", lambda ctx: ctx.source.priority.value)

        # act
        result = mapper.map(entity, EntityWithEnumsDto)

        # assert
        assert result.id == "enum-test"
        assert result.status_value == "pending"
        assert result.priority_number == 3

    def test_value_object_mapping(self):
        """Test mapping value objects like Money"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithMoney:
            id: str
            price: Money
        
        @dataclass
        class EntityWithMoneyDto:
            id: str
            price_display: str
            currency: str
        
        money = Money(amount=Decimal("99.99"), currency="USD")
        entity = EntityWithMoney(id="money-test", price=money)
        
        mapping = config.create_map(EntityWithMoney, EntityWithMoneyDto)
        mapping.for_member("price_display", lambda ctx: str(ctx.source.price.amount))
        mapping.for_member("currency", lambda ctx: ctx.source.price.currency)

        # act
        result = mapper.map(entity, EntityWithMoneyDto)

        # assert
        assert result.id == "money-test"
        assert result.price_display == "99.99"
        assert result.currency == "USD"

    def test_nested_entity_mapping(self):
        """Test mapping nested entities with complex types"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        address = Address(
            street="123 Main St",
            city="Springfield",
            postal_code="12345",
            country="USA",
            created_at=datetime(2023, 1, 1, 10, 0, 0)
        )
        
        money = Money(amount=Decimal("75000.00"), currency="USD")
        
        person = Person(
            id=str(uuid.uuid4()),
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            birth_date=date(1985, 3, 15),
            registration_date=datetime(2023, 6, 1, 9, 30, 0),
            status=StatusEnum.ACTIVE,
            priority=PriorityEnum.MEDIUM,
            salary=money,
            address=address,
            phone_numbers=["555-1234", "555-5678"],
            metadata={"department": "Engineering", "level": "Senior"}
        )

        # Configure mappings manually
        profile = PersonMappingProfile()
        profile.apply_to(config)
        profile.configure_mappings(config)

        # act
        result = mapper.map(person, PersonDto)

        # assert
        assert result.person_id == person.id
        assert result.full_name == "John Doe"
        assert result.email_address == "john.doe@example.com"
        assert result.age > 0  # Should calculate age from birth_date
        assert result.registration_timestamp == "2023-06-01T09:30:00"
        assert result.current_status == "active"
        assert result.priority_level == 2
        assert result.contact_numbers == ["555-1234", "555-5678"]
        assert result.extra_data == {"department": "Engineering", "level": "Senior"}
        
        # Check nested Money mapping
        assert result.salary_info.value == "75000.00"
        assert result.salary_info.currency_code == "USD"
        
        # Check nested Address mapping
        assert result.home_address.street_address == "123 Main St"
        assert result.home_address.city_name == "Springfield"
        assert result.home_address.zip_code == "12345"
        assert result.home_address.country_code == "US"
        assert result.home_address.creation_date == "2023-01-01T10:00:00"

    def test_order_entity_comprehensive_mapping(self):
        """Test comprehensive order entity mapping"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        total = Money(amount=Decimal("149.99"), currency="EUR")
        order = Order(
            id="order-123",
            order_number="ORD-2023-001",
            created_at=datetime(2023, 12, 20, 14, 30, 0),
            order_date=date(2023, 12, 20),
            status=StatusEnum.PENDING,
            priority=PriorityEnum.HIGH,
            total_amount=total,
            items=["Widget A", "Widget B", "Service C"]
        )

        profile = OrderMappingProfile()
        profile.apply_to(config)
        profile.configure_mappings(config)

        # act
        result = mapper.map(order, OrderDto)

        # assert
        assert result.order_id == "order-123"
        assert result.number == "ORD-2023-001"
        assert result.created_timestamp == "2023-12-20T14:30:00"
        assert result.order_date_iso == "2023-12-20"
        assert result.status_name == "pending"
        assert result.priority_value == 3
        assert result.total_price == "149.99 EUR"
        assert result.item_list == ["Widget A", "Widget B", "Service C"]

    def test_optional_datetime_fields(self):
        """Test mapping entities with optional datetime fields"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithOptionalDate:
            id: str
            name: str
            created_at: Optional[datetime] = None
        
        @dataclass
        class EntityWithOptionalDateDto:
            id: str
            name: str
            created_timestamp: Optional[str] = None
        
        entity = EntityWithOptionalDate(id="optional-test", name="Test Entity")
        
        mapping = config.create_map(EntityWithOptionalDate, EntityWithOptionalDateDto)
        mapping.for_member("created_timestamp", lambda ctx: ctx.source.created_at.isoformat() if ctx.source.created_at else None)

        # act
        result = mapper.map(entity, EntityWithOptionalDateDto)

        # assert
        assert result.id == "optional-test"
        assert result.name == "Test Entity"
        assert result.created_timestamp is None

    def test_enum_to_string_mapping(self):
        """Test mapping enums to string values"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithEnum:
            id: str
            status: StatusEnum
            priority: PriorityEnum
        
        @dataclass
        class EntityDto:
            id: str
            status_display: str
            priority_name: str
        
        entity = EntityWithEnum(id="enum-string-test", status=StatusEnum.INACTIVE, priority=PriorityEnum.LOW)
        
        mapping = config.create_map(EntityWithEnum, EntityDto)
        mapping.for_member("status_display", lambda ctx: ctx.source.status.value.upper())
        mapping.for_member("priority_name", lambda ctx: ctx.source.priority.name.lower())

        # act
        result = mapper.map(entity, EntityDto)

        # assert
        assert result.id == "enum-string-test"
        assert result.status_display == "INACTIVE"
        assert result.priority_name == "low"

    def test_decimal_money_precision(self):
        """Test mapping Money with decimal precision"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class Product:
            id: str
            name: str
            price: Money
        
        @dataclass
        class ProductDto:
            id: str
            name: str
            price_formatted: str
            price_cents: int
        
        money = Money(amount=Decimal("19.99"), currency="USD")
        product = Product(id="product-1", name="Test Product", price=money)
        
        mapping = config.create_map(Product, ProductDto)
        mapping.for_member("price_formatted", lambda ctx: f"${ctx.source.price.amount}")
        mapping.for_member("price_cents", lambda ctx: int(ctx.source.price.amount * 100))

        # act
        result = mapper.map(product, ProductDto)

        # assert
        assert result.id == "product-1"
        assert result.name == "Test Product"
        assert result.price_formatted == "$19.99"
        assert result.price_cents == 1999

    def test_collection_with_complex_types(self):
        """Test mapping collections containing complex types"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class OrderItem:
            name: str
            price: Money
            quantity: int
        
        @dataclass
        class OrderItemDto:
            item_name: str
            unit_price: str
            qty: int
            total_price: str
        
        @dataclass
        class OrderWithItems:
            id: str
            items: List[OrderItem]
        
        @dataclass
        class OrderWithItemsDto:
            order_id: str
            item_count: int
            total_value: str
        
        items = [
            OrderItem("Widget", Money(Decimal("10.00")), 2),
            OrderItem("Gadget", Money(Decimal("15.50")), 1)
        ]
        order = OrderWithItems(id="order-with-items", items=items)
        
        mapping = config.create_map(OrderWithItems, OrderWithItemsDto)
        mapping.for_member("order_id", lambda ctx: ctx.source.id)
        mapping.for_member("item_count", lambda ctx: len(ctx.source.items))
        mapping.for_member("total_value", lambda ctx: f"${sum(item.price.amount * item.quantity for item in ctx.source.items)}")

        # act
        result = mapper.map(order, OrderWithItemsDto)

        # assert
        assert result.order_id == "order-with-items"
        assert result.item_count == 2
        assert result.total_value == "$35.50"

    def test_error_handling_with_complex_types(self):
        """Test error handling when mapping complex types"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class EntityWithProblem:
            id: str
            created_at: Optional[datetime]
            status: Optional[StatusEnum]
        
        @dataclass
        class EntityDto:
            id: str
            timestamp: str
            status_name: str
        
        entity = EntityWithProblem(id="error-test", created_at=None, status=None)
        
        # Safe converters that handle None values
        mapping = config.create_map(EntityWithProblem, EntityDto)
        mapping.for_member("timestamp", lambda ctx: ctx.source.created_at.isoformat() if ctx.source.created_at else "N/A")
        mapping.for_member("status_name", lambda ctx: ctx.source.status.value if ctx.source.status else "unknown")

        # act
        result = mapper.map(entity, EntityDto)

        # assert
        assert result.id == "error-test"
        assert result.timestamp == "N/A"
        assert result.status_name == "unknown"

    def test_multiple_nested_value_objects(self):
        """Test mapping entities with multiple nested value objects"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)
        
        @dataclass
        class Price:
            base_amount: Decimal
            tax_amount: Decimal
            currency: str
        
        @dataclass
        class Dimensions:
            length: Decimal
            width: Decimal
            height: Decimal
            unit: str = "cm"
        
        @dataclass
        class Product:
            id: str
            name: str
            price: Price
            dimensions: Dimensions
            created_at: datetime
        
        @dataclass
        class ProductSummaryDto:
            product_id: str
            display_name: str
            total_price: str
            size_description: str
            age_days: int
        
        price = Price(Decimal("99.00"), Decimal("19.80"), "USD")
        dimensions = Dimensions(Decimal("10.5"), Decimal("5.2"), Decimal("3.1"))
        created = datetime(2023, 10, 1, 12, 0, 0)
        product = Product("prod-123", "Test Product", price, dimensions, created)
        
        mapping = config.create_map(Product, ProductSummaryDto)
        mapping.for_member("product_id", lambda ctx: ctx.source.id)
        mapping.for_member("display_name", lambda ctx: ctx.source.name.upper())
        mapping.for_member("total_price", lambda ctx: f"{ctx.source.price.base_amount + ctx.source.price.tax_amount} {ctx.source.price.currency}")
        mapping.for_member("size_description", lambda ctx: f"{ctx.source.dimensions.length}x{ctx.source.dimensions.width}x{ctx.source.dimensions.height} {ctx.source.dimensions.unit}")
        mapping.for_member("age_days", lambda ctx: (datetime.now() - ctx.source.created_at).days)

        # act
        result = mapper.map(product, ProductSummaryDto)

        # assert
        assert result.product_id == "prod-123"
        assert result.display_name == "TEST PRODUCT"
        assert result.total_price == "118.80 USD"
        assert result.size_description == "10.5x5.2x3.1 cm"
        assert result.age_days >= 0  # Should be positive number of days