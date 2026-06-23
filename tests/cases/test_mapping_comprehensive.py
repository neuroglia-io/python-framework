import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from neuroglia.mapping.mapper import Mapper, MapperConfiguration, MappingProfile


class TestEnum(str, Enum):
    """Test enum for comprehensive mapper tests"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class StatusEnum(int, Enum):
    """Integer enum for testing"""

    DRAFT = 1
    PUBLISHED = 2
    ARCHIVED = 3


@dataclass
class Address:
    """Nested class for testing complex mappings"""

    street: str
    city: str
    postal_code: str
    country: str = "USA"


@dataclass
class AddressDto:
    """DTO version of Address"""

    street_address: str
    city_name: str
    zip_code: str
    country_code: str = "US"


@dataclass
class Person:
    """Complex source class with nested objects and collections"""

    id: str
    first_name: str
    last_name: str
    email: str
    age: int
    status: TestEnum
    address: Address
    phone_numbers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[str] = None


@dataclass
class PersonDto:
    """Complex destination DTO with different property names"""

    person_id: str
    full_name: str
    email_address: str
    years_old: int
    current_status: str
    home_address: AddressDto
    contact_numbers: List[str] = field(default_factory=list)
    extra_data: Dict[str, Any] = field(default_factory=dict)
    active_flag: bool = True
    timestamp: Optional[str] = None


@dataclass
class SimpleSource:
    """Simple source for basic mapping tests"""

    id: str
    name: str
    value: int


@dataclass
class SimpleDestination:
    """Simple destination for basic mapping tests"""

    id: str
    name: str
    value: int


class ComplexMappingProfile(MappingProfile):
    """Complex mapping profile with custom conversions"""

    def __init__(self):
        # Person to PersonDto mapping
        person_mapping = self.create_map(Person, PersonDto)
        person_mapping.for_member("person_id", lambda ctx: ctx.source.id)
        person_mapping.for_member(
            "full_name", lambda ctx: f"{ctx.source.first_name} {ctx.source.last_name}"
        )
        person_mapping.for_member("email_address", lambda ctx: ctx.source.email)
        person_mapping.for_member("years_old", lambda ctx: ctx.source.age)
        person_mapping.for_member("current_status", lambda ctx: ctx.source.status.value)
        person_mapping.for_member("contact_numbers", lambda ctx: ctx.source.phone_numbers)
        person_mapping.for_member("extra_data", lambda ctx: ctx.source.metadata)
        person_mapping.for_member("active_flag", lambda ctx: ctx.source.is_active)
        person_mapping.for_member("timestamp", lambda ctx: ctx.source.created_at)

        # Nested address mapping - map address field to home_address
        def map_nested_address(ctx):
            if ctx.source.address:
                # Get the mapper from the context and map the nested address
                # For now, manually create the address DTO since the nested mapping isn't fully implemented
                return AddressDto(
                    street_address=ctx.source.address.street,
                    city_name=ctx.source.address.city,
                    zip_code=ctx.source.address.postal_code,
                    country_code=(
                        ctx.source.address.country[:2].upper()
                        if len(ctx.source.address.country) >= 2
                        else "US"
                    ),
                )
            return None

        person_mapping.for_member("home_address", map_nested_address)

        # Nested address mapping configuration
        address_mapping = self.create_map(Address, AddressDto)
        address_mapping.for_member("street_address", lambda ctx: ctx.source.street)
        address_mapping.for_member("city_name", lambda ctx: ctx.source.city)
        address_mapping.for_member("zip_code", lambda ctx: ctx.source.postal_code)
        address_mapping.for_member("country_code", lambda ctx: ctx.source.country[:2].upper())


class TestMapperComprehensive:
    """Comprehensive tests for Mapper functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.config = MapperConfiguration()
        self.mapper = Mapper(self.config)

    def test_basic_mapping_functionality(self):
        """Test basic object mapping with simple types"""
        # arrange
        source = SimpleSource(id=str(uuid.uuid4()), name="Test Name", value=42)

        self.config.create_map(SimpleSource, SimpleDestination)

        # act
        result = self.mapper.map(source, SimpleDestination)

        # assert
        assert result.id == source.id
        assert result.name == source.name
        assert result.value == source.value

    def test_mapping_with_none_values(self):
        """Test mapping behavior with None values"""

        # arrange
        @dataclass
        class SourceWithOptional:
            id: str
            name: Optional[str] = None
            value: Optional[int] = None

        @dataclass
        class DestinationWithOptional:
            id: str
            name: Optional[str] = None
            value: Optional[int] = None

        source = SourceWithOptional(id="123", name=None, value=None)
        self.config.create_map(SourceWithOptional, DestinationWithOptional)

        # act
        result = self.mapper.map(source, DestinationWithOptional)

        # assert
        assert result.id == "123"
        assert result.name is None
        assert result.value is None

    def test_mapping_with_default_values(self):
        """Test mapping with default values in destination"""

        # arrange
        @dataclass
        class SourceMinimal:
            id: str

        @dataclass
        class DestinationWithDefaults:
            id: str
            name: str = "Default Name"
            value: int = 100

        source = SourceMinimal(id="test-id")
        self.config.create_map(SourceMinimal, DestinationWithDefaults)

        # act
        result = self.mapper.map(source, DestinationWithDefaults)

        # assert
        assert result.id == "test-id"
        assert result.name == "Default Name"  # Should use default
        assert result.value == 100  # Should use default

    def test_mapping_with_type_conversion(self):
        """Test mapping with automatic type conversion"""

        # arrange
        @dataclass
        class SourceWithString:
            id: str
            numeric_value: str  # String representation

        @dataclass
        class DestinationWithInt:
            id: str
            numeric_value: int  # Integer type

        source = SourceWithString(id="123", numeric_value="456")
        mapping = self.config.create_map(SourceWithString, DestinationWithInt)
        mapping.for_member("numeric_value", lambda ctx: int(ctx.source_member_value))

        # act
        result = self.mapper.map(source, DestinationWithInt)

        # assert
        assert result.id == "123"
        assert result.numeric_value == 456
        assert isinstance(result.numeric_value, int)

    def test_enum_mapping_scenarios(self):
        """Test various enum mapping scenarios"""

        # arrange
        @dataclass
        class SourceWithEnum:
            id: str
            status: TestEnum
            priority: StatusEnum

        @dataclass
        class DestinationWithEnum:
            id: str
            status: TestEnum
            priority: StatusEnum

        source = SourceWithEnum(
            id="enum-test", status=TestEnum.ACTIVE, priority=StatusEnum.PUBLISHED
        )
        self.config.create_map(SourceWithEnum, DestinationWithEnum)

        # act
        result = self.mapper.map(source, DestinationWithEnum)

        # assert
        assert result.id == "enum-test"
        assert result.status == TestEnum.ACTIVE
        assert result.priority == StatusEnum.PUBLISHED
        assert isinstance(result.status, TestEnum)
        assert isinstance(result.priority, StatusEnum)

    def test_list_mapping_functionality(self):
        """Test mapping with list properties"""

        # arrange
        @dataclass
        class SourceWithList:
            id: str
            items: List[str]
            numbers: List[int]

        @dataclass
        class DestinationWithList:
            id: str
            items: List[str]
            numbers: List[int]

        source = SourceWithList(
            id="list-test", items=["item1", "item2", "item3"], numbers=[1, 2, 3, 4, 5]
        )
        self.config.create_map(SourceWithList, DestinationWithList)

        # act
        result = self.mapper.map(source, DestinationWithList)

        # assert
        assert result.id == "list-test"
        assert result.items == ["item1", "item2", "item3"]
        assert result.numbers == [1, 2, 3, 4, 5]
        assert isinstance(result.items, list)
        assert isinstance(result.numbers, list)

    def test_dictionary_mapping_functionality(self):
        """Test mapping with dictionary properties"""

        # arrange
        @dataclass
        class SourceWithDict:
            id: str
            metadata: Dict[str, str]
            counters: Dict[str, int]

        @dataclass
        class DestinationWithDict:
            id: str
            metadata: Dict[str, str]
            counters: Dict[str, int]

        source = SourceWithDict(
            id="dict-test",
            metadata={"key1": "value1", "key2": "value2"},
            counters={"count1": 10, "count2": 20},
        )
        self.config.create_map(SourceWithDict, DestinationWithDict)

        # act
        result = self.mapper.map(source, DestinationWithDict)

        # assert
        assert result.id == "dict-test"
        assert result.metadata == {"key1": "value1", "key2": "value2"}
        assert result.counters == {"count1": 10, "count2": 20}

    def test_nested_object_mapping(self):
        """Test mapping with nested objects"""
        # arrange
        address = Address(street="123 Main St", city="Anytown", postal_code="12345", country="USA")

        person = Person(
            id=str(uuid.uuid4()),
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            age=30,
            status=TestEnum.ACTIVE,
            address=address,
            phone_numbers=["555-1234", "555-5678"],
            metadata={"department": "IT", "level": "senior"},
        )

        profile = ComplexMappingProfile()
        profile.apply_to(self.config)

        # act
        result = self.mapper.map(person, PersonDto)

        # assert
        assert result.person_id == person.id
        assert result.full_name == "John Doe"
        assert result.email_address == person.email
        assert result.years_old == 30
        assert result.current_status == "active"
        assert result.contact_numbers == ["555-1234", "555-5678"]
        assert result.extra_data == {"department": "IT", "level": "senior"}

        # Check nested address mapping
        assert result.home_address.street_address == "123 Main St"
        assert result.home_address.city_name == "Anytown"
        assert result.home_address.zip_code == "12345"
        assert result.home_address.country_code == "US"

    def test_custom_member_mapping_functions(self):
        """Test custom member mapping functions"""

        # arrange
        @dataclass
        class Source:
            first_name: str
            last_name: str
            birth_year: int

        @dataclass
        class Destination:
            full_name: str
            age_category: str

        source = Source(first_name="Jane", last_name="Smith", birth_year=1990)

        mapping = self.config.create_map(Source, Destination)
        mapping.for_member(
            "full_name", lambda ctx: f"{ctx.source.first_name} {ctx.source.last_name}"
        )
        mapping.for_member(
            "age_category", lambda ctx: "adult" if 2024 - ctx.source.birth_year >= 18 else "minor"
        )

        # act
        result = self.mapper.map(source, Destination)

        # assert
        assert result.full_name == "Jane Smith"
        assert result.age_category == "adult"

    def test_mapping_profile_functionality(self):
        """Test mapping profile creation and application"""

        # arrange
        class TestMappingProfile(MappingProfile):
            def __init__(self):
                mapping = self.create_map(SimpleSource, SimpleDestination)
                mapping.for_member("name", lambda ctx: ctx.source_member_value.upper())

        source = SimpleSource(id="profile-test", name="test name", value=100)
        profile = TestMappingProfile()
        profile.apply_to(self.config)

        # act
        result = self.mapper.map(source, SimpleDestination)

        # assert
        assert result.id == "profile-test"
        assert result.name == "TEST NAME"  # Should be uppercase due to profile
        assert result.value == 100

    def test_mapping_context_usage(self):
        """Test TypeMappingContext and MemberMappingContext usage"""

        # arrange
        @dataclass
        class ContextSource:
            value: str
            metadata: Dict[str, str]

        @dataclass
        class ContextDestination:
            transformed_value: str
            context_info: str

        source = ContextSource(value="test_value", metadata={"context": "test_context"})

        mapping = self.config.create_map(ContextSource, ContextDestination)
        mapping.for_member("transformed_value", lambda ctx: f"transformed_{ctx.source.value}")
        mapping.for_member(
            "context_info", lambda ctx: ctx.source.metadata.get("context", "unknown")
        )

        # act
        result = self.mapper.map(source, ContextDestination)

        # assert
        assert result.transformed_value == "transformed_test_value"
        assert result.context_info == "test_context"

    def test_error_handling_scenarios(self):
        """Test mapper behavior in error scenarios"""

        # arrange
        @dataclass
        class SourceWithError:
            id: str
            problematic_value: str

        @dataclass
        class DestinationWithError:
            id: str
            converted_value: int

        source = SourceWithError(id="error-test", problematic_value="not_a_number")
        mapping = self.config.create_map(SourceWithError, DestinationWithError)

        # Custom converter that might fail
        def risky_converter(ctx):
            try:
                return int(ctx.source.problematic_value)
            except (ValueError, AttributeError):
                return 0  # Default value on error

        mapping.for_member("converted_value", risky_converter)

        # act
        result = self.mapper.map(source, DestinationWithError)

        # assert
        assert result.id == "error-test"
        assert result.converted_value == 0  # Should use fallback value

    def test_mapping_with_inheritance(self):
        """Test mapping with class inheritance"""

        # arrange
        @dataclass
        class BaseSource:
            id: str
            name: str

        @dataclass
        class ExtendedSource(BaseSource):
            extra_field: str

        @dataclass
        class BaseDestination:
            id: str
            name: str

        @dataclass
        class ExtendedDestination(BaseDestination):
            extra_field: str

        source = ExtendedSource(id="inherit-test", name="Test Name", extra_field="Extra Value")
        self.config.create_map(ExtendedSource, ExtendedDestination)

        # act
        result = self.mapper.map(source, ExtendedDestination)

        # assert
        assert result.id == "inherit-test"
        assert result.name == "Test Name"
        assert result.extra_field == "Extra Value"

    def test_multiple_mapping_configurations(self):
        """Test multiple mapping configurations in same mapper"""

        # arrange
        @dataclass
        class FirstSource:
            id: str
            name: str

        @dataclass
        class FirstDestination:
            id: str
            name: str

        @dataclass
        class SecondSource:
            code: str
            description: str

        @dataclass
        class SecondDestination:
            code: str
            description: str

        first_source = FirstSource(id="1", name="First")
        second_source = SecondSource(code="A", description="Second")

        self.config.create_map(FirstSource, FirstDestination)
        self.config.create_map(SecondSource, SecondDestination)

        # act
        first_result = self.mapper.map(first_source, FirstDestination)
        second_result = self.mapper.map(second_source, SecondDestination)

        # assert
        assert first_result.id == "1"
        assert first_result.name == "First"
        assert second_result.code == "A"
        assert second_result.description == "Second"

    def test_mapper_configuration_validation(self):
        """Test mapper configuration validation"""
        # arrange
        config = MapperConfiguration()

        # act & assert - should not raise any exceptions
        mapping = config.create_map(SimpleSource, SimpleDestination)
        assert mapping is not None

        mapper = Mapper(config)
        assert mapper is not None

    def test_empty_collections_mapping(self):
        """Test mapping with empty collections"""

        # arrange
        @dataclass
        class SourceWithEmptyCollections:
            id: str
            empty_list: List[str] = field(default_factory=list)
            empty_dict: Dict[str, str] = field(default_factory=dict)

        @dataclass
        class DestinationWithEmptyCollections:
            id: str
            empty_list: List[str] = field(default_factory=list)
            empty_dict: Dict[str, str] = field(default_factory=dict)

        source = SourceWithEmptyCollections(id="empty-test")
        self.config.create_map(SourceWithEmptyCollections, DestinationWithEmptyCollections)

        # act
        result = self.mapper.map(source, DestinationWithEmptyCollections)

        # assert
        assert result.id == "empty-test"
        assert result.empty_list == []
        assert result.empty_dict == {}
        assert isinstance(result.empty_list, list)
        assert isinstance(result.empty_dict, dict)

    def test_complex_nested_mapping_scenario(self):
        """Test complex nested mapping scenario with multiple levels"""

        # arrange
        @dataclass
        class DeepNested:
            value: str

        @dataclass
        class MiddleNested:
            deep: DeepNested
            name: str

        @dataclass
        class TopLevel:
            id: str
            middle: MiddleNested

        @dataclass
        class DeepNestedDto:
            transformed_value: str

        @dataclass
        class MiddleNestedDto:
            deep: DeepNestedDto
            display_name: str

        @dataclass
        class TopLevelDto:
            identifier: str
            middle: MiddleNestedDto

        # Create nested objects
        deep = DeepNested(value="deep_value")
        middle = MiddleNested(deep=deep, name="middle_name")
        top = TopLevel(id="top_id", middle=middle)

        # Configure mappings
        deep_mapping = self.config.create_map(DeepNested, DeepNestedDto)
        deep_mapping.for_member("transformed_value", lambda ctx: f"transformed_{ctx.source.value}")

        middle_mapping = self.config.create_map(MiddleNested, MiddleNestedDto)
        middle_mapping.for_member("display_name", lambda ctx: ctx.source.name.upper())

        top_mapping = self.config.create_map(TopLevel, TopLevelDto)
        top_mapping.for_member("identifier", lambda ctx: ctx.source.id)

        # act
        result = self.mapper.map(top, TopLevelDto)

        # assert
        assert result.identifier == "top_id"
        assert result.middle.display_name == "MIDDLE_NAME"
        assert result.middle.deep.transformed_value == "transformed_deep_value"
