"""
Tests for MongoDB serialization helper functionality.

This module tests the MongoSerializationHelper's ability to serialize and deserialize
complex domain objects including enums, datetime objects, nested entities, and value objects.
"""

from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from neuroglia.data.infrastructure.mongo.serialization_helper import MongoSerializationHelper


class StatusEnum(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class PriorityEnum(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Money:
    amount: Decimal
    currency: str


@dataclass
class Address:
    street: str
    city: str
    country: str
    zip_code: Optional[str] = None


@dataclass
class Person:
    name: str
    email: str
    birth_date: date
    status: StatusEnum
    priority: PriorityEnum
    salary: Money
    address: Address
    created_at: datetime
    tags: List[str]


class TestMongoSerializationHelper:
    """Test suite for MongoSerializationHelper serialization and deserialization"""

    def test_serialize_simple_types(self):
        """Test serialization of simple types"""
        # Test basic types
        assert MongoSerializationHelper.serialize_to_dict("test") == "test"
        assert MongoSerializationHelper.serialize_to_dict(42) == 42
        assert MongoSerializationHelper.serialize_to_dict(3.14) == 3.14
        assert MongoSerializationHelper.serialize_to_dict(True) is True
        assert MongoSerializationHelper.serialize_to_dict(None) is None

        # Test datetime
        dt = datetime(2023, 6, 15, 10, 30, 45)
        assert MongoSerializationHelper.serialize_to_dict(dt) == dt

    def test_serialize_enum_types(self):
        """Test serialization of enum types"""
        # String enum
        status = StatusEnum.ACTIVE
        assert MongoSerializationHelper.serialize_to_dict(status) == "ACTIVE"
        
        # Integer enum
        priority = PriorityEnum.HIGH
        assert MongoSerializationHelper.serialize_to_dict(priority) == "HIGH"

    def test_serialize_complex_objects(self):
        """Test serialization of complex objects with nested structures"""
        money = Money(amount=Decimal("1500.00"), currency="USD")
        address = Address(street="123 Main St", city="New York", country="USA", zip_code="10001")
        person = Person(
            name="John Doe",
            email="john@example.com",
            birth_date=date(1990, 5, 15),
            status=StatusEnum.ACTIVE,
            priority=PriorityEnum.HIGH,
            salary=money,
            address=address,
            created_at=datetime(2023, 6, 15, 10, 30, 45),
            tags=["employee", "senior", "tech"]
        )

        result = MongoSerializationHelper.serialize_to_dict(person)
        
        # Verify basic fields
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert result["birth_date"] == date(1990, 5, 15)
        
        # Verify enum serialization
        assert result["status"] == "ACTIVE"
        assert result["priority"] == "HIGH"
        
        # Verify nested object serialization
        assert result["salary"]["amount"] == "1500.00"  # Decimal serialized to string
        assert result["salary"]["currency"] == "USD"
        
        assert result["address"]["street"] == "123 Main St"
        assert result["address"]["city"] == "New York"
        assert result["address"]["country"] == "USA"
        assert result["address"]["zip_code"] == "10001"
        
        # Verify list serialization
        assert result["tags"] == ["employee", "senior", "tech"]

    def test_serialize_collections(self):
        """Test serialization of lists and dictionaries"""
        # Test list serialization
        enum_list = [StatusEnum.ACTIVE, StatusEnum.PENDING]
        result = MongoSerializationHelper.serialize_to_dict(enum_list)
        assert result == ["ACTIVE", "PENDING"]
        
        # Test dictionary serialization
        enum_dict = {"current": StatusEnum.ACTIVE, "previous": StatusEnum.INACTIVE}
        result = MongoSerializationHelper.serialize_to_dict(enum_dict)
        assert result == {"current": "ACTIVE", "previous": "INACTIVE"}

    def test_deserialize_simple_entity(self):
        """Test deserialization of simple entities"""
        @dataclass
        class SimpleEntity:
            name: str
            age: int
            active: bool
        
        data = {"name": "Test", "age": 25, "active": True}
        result = MongoSerializationHelper.deserialize_to_entity(data, SimpleEntity)
        
        assert isinstance(result, SimpleEntity)
        assert result.name == "Test"
        assert result.age == 25
        assert result.active is True

    def test_deserialize_entity_with_enums(self):
        """Test deserialization of entities with enum fields"""
        @dataclass
        class EntityWithEnums:
            name: str
            status: StatusEnum
            priority: PriorityEnum
        
        data = {"name": "Test", "status": "ACTIVE", "priority": "HIGH"}
        result = MongoSerializationHelper.deserialize_to_entity(data, EntityWithEnums)
        
        assert isinstance(result, EntityWithEnums)
        assert result.name == "Test"
        assert result.status == StatusEnum.ACTIVE
        assert result.priority == PriorityEnum.HIGH

    def test_deserialize_entity_with_nested_objects(self):
        """Test deserialization of entities with nested objects"""
        @dataclass
        class EntityWithNested:
            name: str
            address: Address
            salary: Money
        
        data = {
            "name": "Test",
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "country": "USA",
                "zip_code": "10001"
            },
            "salary": {
                "amount": Decimal("2000.00"),
                "currency": "USD"
            }
        }
        
        result = MongoSerializationHelper.deserialize_to_entity(data, EntityWithNested)
        
        assert isinstance(result, EntityWithNested)
        assert result.name == "Test"
        assert isinstance(result.address, Address)
        assert result.address.street == "123 Main St"
        assert result.address.city == "New York"
        assert isinstance(result.salary, Money)
        assert result.salary.currency == "USD"

    def test_deserialize_with_id_handling(self):
        """Test deserialization with proper ID field handling"""
        @dataclass
        class EntityWithId:
            name: str
            id: Optional[str] = None
        
        data = {"id": "test-123", "name": "Test Entity"}
        result = MongoSerializationHelper.deserialize_to_entity(data, EntityWithId)
        
        assert isinstance(result, EntityWithId)
        assert result.id == "test-123"
        assert result.name == "Test Entity"

    def test_deserialize_with_mongodb_id(self):
        """Test deserialization with MongoDB _id field handling"""
        @dataclass
        class EntityForMongo:
            name: str
            value: int
            id: Optional[str] = None
        
        data = {"_id": "mongodb-object-id", "name": "Test", "value": 42, "id": "entity-123"}
        result = MongoSerializationHelper.deserialize_to_entity(data, EntityForMongo)
        
        assert isinstance(result, EntityForMongo)
        assert result.name == "Test"
        assert result.value == 42
        assert result.id == "entity-123"  # Should use entity id, not MongoDB _id

    def test_deserialize_complex_entity(self):
        """Test deserialization of complex entity with all supported features"""
        data = {
            "name": "John Doe",
            "email": "john@example.com", 
            "birth_date": date(1990, 5, 15),
            "status": "ACTIVE",
            "priority": "HIGH",
            "salary": {
                "amount": Decimal("1500.00"),
                "currency": "USD"
            },
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "country": "USA", 
                "zip_code": "10001"
            },
            "created_at": datetime(2023, 6, 15, 10, 30, 45),
            "tags": ["employee", "senior", "tech"]
        }
        
        result = MongoSerializationHelper.deserialize_to_entity(data, Person)
        
        assert isinstance(result, Person)
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        assert result.birth_date == date(1990, 5, 15)
        assert result.status == StatusEnum.ACTIVE
        assert result.priority == PriorityEnum.HIGH
        assert isinstance(result.salary, Money)
        assert result.salary.amount == Decimal("1500.00")
        assert result.salary.currency == "USD"
        assert isinstance(result.address, Address)
        assert result.address.street == "123 Main St"
        assert result.created_at == datetime(2023, 6, 15, 10, 30, 45)
        assert result.tags == ["employee", "senior", "tech"]

    def test_deserialize_error_handling(self):
        """Test deserialization error handling and fallback behavior"""
        @dataclass
        class EntityWithRequiredField:
            required_field: str
        
        # Missing required field should return original data
        incomplete_data = {"optional_field": "value"}
        result = MongoSerializationHelper.deserialize_to_entity(incomplete_data, EntityWithRequiredField)
        
        # Should return original data when deserialization fails
        assert result == incomplete_data

    def test_round_trip_serialization(self):
        """Test complete round-trip serialization and deserialization"""
        # Create a complex entity
        money = Money(amount=Decimal("2500.50"), currency="EUR")
        address = Address(street="456 Oak Ave", city="Boston", country="USA")
        original_person = Person(
            name="Jane Smith",
            email="jane@example.com",
            birth_date=date(1985, 3, 20),
            status=StatusEnum.PENDING,
            priority=PriorityEnum.MEDIUM,
            salary=money,
            address=address,
            created_at=datetime(2023, 7, 20, 14, 45, 30),
            tags=["manager", "experienced"]
        )
        
        # Serialize to dict
        serialized = MongoSerializationHelper.serialize_to_dict(original_person)
        
        # Deserialize back to entity
        deserialized = MongoSerializationHelper.deserialize_to_entity(serialized, Person)
        
        # Verify they match
        assert isinstance(deserialized, Person)
        assert deserialized.name == original_person.name
        assert deserialized.email == original_person.email
        assert deserialized.birth_date == original_person.birth_date
        assert deserialized.status == original_person.status
        assert deserialized.priority == original_person.priority
        assert deserialized.salary.amount == original_person.salary.amount
        assert deserialized.salary.currency == original_person.salary.currency
        assert deserialized.address.street == original_person.address.street
        assert deserialized.address.city == original_person.address.city
        assert deserialized.created_at == original_person.created_at
        assert deserialized.tags == original_person.tags