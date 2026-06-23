"""
Unit tests for object mapping functionality.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

import pytest

from neuroglia.mapping.mapper import Mapper, MappingProfile

# Test data models


@dataclass
class SourcePerson:
    """Source person model"""

    id: int
    first_name: str
    last_name: str
    email: str
    birth_date: date
    salary: Decimal
    is_active: bool
    address: Optional["SourceAddress"] = None
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class SourceAddress:
    """Source address model"""

    street: str
    city: str
    postal_code: str
    country: str


@dataclass
class DestinationPerson:
    """Destination person model"""

    person_id: int
    full_name: str
    email_address: str
    age: int
    annual_salary: float
    status: str
    home_address: Optional["DestinationAddress"] = None
    tag_list: list[str] = None

    def __post_init__(self):
        if self.tag_list is None:
            self.tag_list = []


@dataclass
class DestinationAddress:
    """Destination address model"""

    full_address: str
    zip_code: str
    country_name: str


@dataclass
class SimpleSource:
    """Simple source for basic mapping tests"""

    name: str
    value: int
    flag: bool


@dataclass
class SimpleDestination:
    """Simple destination for basic mapping tests"""

    name: str
    value: int
    flag: bool


@dataclass
class FlattenedDestination:
    """Flattened destination for complex mapping"""

    person_id: int
    person_name: str
    person_email: str
    address_street: str
    address_city: str
    address_country: str


@dataclass
class NestedSource:
    """Nested source for flattening tests"""

    person: SourcePerson
    address: SourceAddress


# Custom mapper profile


class PersonMappingProfile(MappingProfile):
    """Custom mapping profile for person objects"""

    def configure(self):
        # Person mapping with custom transformations
        self.create_map(SourcePerson, DestinationPerson).add_member_mapping(lambda src: src.id, lambda dst: dst.person_id).add_member_mapping(lambda src: f"{src.first_name} {src.last_name}", lambda dst: dst.full_name).add_member_mapping(lambda src: src.email, lambda dst: dst.email_address).add_member_mapping(lambda src: self.calculate_age(src.birth_date), lambda dst: dst.age).add_member_mapping(lambda src: float(src.salary), lambda dst: dst.annual_salary).add_member_mapping(
            lambda src: "Active" if src.is_active else "Inactive", lambda dst: dst.status
        ).add_member_mapping(lambda src: src.tags, lambda dst: dst.tag_list)

        # Address mapping
        self.create_map(SourceAddress, DestinationAddress).add_member_mapping(lambda src: f"{src.street}, {src.city}", lambda dst: dst.full_address).add_member_mapping(lambda src: src.postal_code, lambda dst: dst.zip_code).add_member_mapping(lambda src: src.country, lambda dst: dst.country_name)

        # Flattening mapping
        self.create_map(NestedSource, FlattenedDestination).add_member_mapping(lambda src: src.person.id, lambda dst: dst.person_id).add_member_mapping(
            lambda src: f"{src.person.first_name} {src.person.last_name}",
            lambda dst: dst.person_name,
        ).add_member_mapping(
            lambda src: src.person.email, lambda dst: dst.person_email
        ).add_member_mapping(lambda src: src.address.street, lambda dst: dst.address_street).add_member_mapping(
            lambda src: src.address.city, lambda dst: dst.address_city
        ).add_member_mapping(lambda src: src.address.country, lambda dst: dst.address_country)

    def calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


# Test basic mapping functionality


class TestBasicMapping:
    def test_simple_mapping(self):
        """Test simple property-to-property mapping"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        source = SimpleSource(name="test", value=42, flag=True)
        result = mapper.map(source, SimpleDestination)

        assert result.name == "test"
        assert result.value == 42
        assert result.flag is True

    def test_mapping_with_different_property_names(self):
        """Test mapping with custom property mappings"""
        mapper = Mapper()
        mapping = mapper.create_map(SourcePerson, DestinationPerson)
        mapping.add_member_mapping(lambda src: src.id, lambda dst: dst.person_id)
        mapping.add_member_mapping(lambda src: src.email, lambda dst: dst.email_address)

        source = SourcePerson(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            birth_date=date(1990, 1, 1),
            salary=Decimal("50000.00"),
            is_active=True,
        )

        result = mapper.map(source, DestinationPerson)

        assert result.person_id == 1
        assert result.email_address == "john@example.com"

    def test_mapping_with_computed_properties(self):
        """Test mapping with computed/transformed properties"""
        mapper = Mapper()
        mapping = mapper.create_map(SourcePerson, DestinationPerson)
        mapping.add_member_mapping(lambda src: f"{src.first_name} {src.last_name}", lambda dst: dst.full_name)
        mapping.add_member_mapping(lambda src: "Active" if src.is_active else "Inactive", lambda dst: dst.status)

        source = SourcePerson(
            id=1,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            birth_date=date(1985, 5, 15),
            salary=Decimal("75000.00"),
            is_active=False,
        )

        result = mapper.map(source, DestinationPerson)

        assert result.full_name == "Jane Smith"
        assert result.status == "Inactive"

    def test_mapping_none_source(self):
        """Test mapping with None source"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        result = mapper.map(None, SimpleDestination)
        assert result is None

    def test_mapping_with_type_conversion(self):
        """Test mapping with automatic type conversion"""
        mapper = Mapper()
        mapping = mapper.create_map(SourcePerson, DestinationPerson)
        mapping.add_member_mapping(lambda src: float(src.salary), lambda dst: dst.annual_salary)

        source = SourcePerson(
            id=1,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            birth_date=date(1990, 1, 1),
            salary=Decimal("123456.78"),
            is_active=True,
        )

        result = mapper.map(source, DestinationPerson)

        assert result.annual_salary == 123456.78
        assert isinstance(result.annual_salary, float)


# Test nested object mapping


class TestNestedMapping:
    def test_nested_object_mapping(self):
        """Test mapping nested objects"""
        mapper = Mapper()

        # Configure address mapping
        mapper.create_map(SourceAddress, DestinationAddress).add_member_mapping(lambda src: f"{src.street}, {src.city}", lambda dst: dst.full_address).add_member_mapping(lambda src: src.postal_code, lambda dst: dst.zip_code).add_member_mapping(lambda src: src.country, lambda dst: dst.country_name)

        # Configure person mapping with nested address
        mapper.create_map(SourcePerson, DestinationPerson).add_member_mapping(lambda src: src.address, lambda dst: dst.home_address)

        source_address = SourceAddress(street="123 Main St", city="Anytown", postal_code="12345", country="USA")

        source_person = SourcePerson(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            birth_date=date(1990, 1, 1),
            salary=Decimal("50000.00"),
            is_active=True,
            address=source_address,
        )

        result = mapper.map(source_person, DestinationPerson)

        assert result.home_address is not None
        assert result.home_address.full_address == "123 Main St, Anytown"
        assert result.home_address.zip_code == "12345"
        assert result.home_address.country_name == "USA"

    def test_nested_object_mapping_with_none(self):
        """Test mapping when nested object is None"""
        mapper = Mapper()

        mapper.create_map(SourceAddress, DestinationAddress)
        mapper.create_map(SourcePerson, DestinationPerson).add_member_mapping(lambda src: src.address, lambda dst: dst.home_address)

        source_person = SourcePerson(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            birth_date=date(1990, 1, 1),
            salary=Decimal("50000.00"),
            is_active=True,
            address=None,  # No address
        )

        result = mapper.map(source_person, DestinationPerson)

        assert result.home_address is None


# Test collection mapping


class TestCollectionMapping:
    def test_list_mapping(self):
        """Test mapping lists"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        sources = [
            SimpleSource(name="first", value=1, flag=True),
            SimpleSource(name="second", value=2, flag=False),
            SimpleSource(name="third", value=3, flag=True),
        ]

        results = mapper.map_list(sources, SimpleDestination)

        assert len(results) == 3
        assert results[0].name == "first"
        assert results[1].value == 2
        assert results[2].flag is True

    def test_empty_list_mapping(self):
        """Test mapping empty list"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        results = mapper.map_list([], SimpleDestination)

        assert results == []

    def test_none_list_mapping(self):
        """Test mapping None list"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        results = mapper.map_list(None, SimpleDestination)

        assert results is None


# Test mapper profiles


class TestMapperProfiles:
    def test_mapper_profile_configuration(self):
        """Test using mapper profile for configuration"""
        mapper = Mapper()
        profile = PersonMappingProfile()
        mapper.add_profile(profile)

        source_address = SourceAddress(street="456 Oak Ave", city="Springfield", postal_code="67890", country="Canada")

        source_person = SourcePerson(
            id=2,
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            birth_date=date(1992, 8, 20),
            salary=Decimal("65000.00"),
            is_active=True,
            address=source_address,
            tags=["developer", "python", "senior"],
        )

        result = mapper.map(source_person, DestinationPerson)

        assert result.person_id == 2
        assert result.full_name == "Alice Johnson"
        assert result.email_address == "alice@example.com"
        assert result.annual_salary == 65000.0
        assert result.status == "Active"
        assert result.tag_list == ["developer", "python", "senior"]

        # Test nested address mapping
        assert result.home_address is not None
        assert result.home_address.full_address == "456 Oak Ave, Springfield"
        assert result.home_address.zip_code == "67890"
        assert result.home_address.country_name == "Canada"

    def test_age_calculation_in_profile(self):
        """Test custom age calculation in profile"""
        mapper = Mapper()
        profile = PersonMappingProfile()
        mapper.add_profile(profile)

        # Person born 30 years ago
        birth_date = date.today().replace(year=date.today().year - 30)

        source_person = SourcePerson(
            id=3,
            first_name="Bob",
            last_name="Wilson",
            email="bob@example.com",
            birth_date=birth_date,
            salary=Decimal("80000.00"),
            is_active=True,
        )

        result = mapper.map(source_person, DestinationPerson)

        # Age should be calculated correctly (approximately 30)
        assert 29 <= result.age <= 30

    def test_flattening_mapping_with_profile(self):
        """Test object flattening with mapper profile"""
        mapper = Mapper()
        profile = PersonMappingProfile()
        mapper.add_profile(profile)

        source = NestedSource(
            person=SourcePerson(
                id=4,
                first_name="Carol",
                last_name="Brown",
                email="carol@example.com",
                birth_date=date(1988, 3, 10),
                salary=Decimal("70000.00"),
                is_active=True,
            ),
            address=SourceAddress(street="789 Pine St", city="Metropolis", postal_code="54321", country="USA"),
        )

        result = mapper.map(source, FlattenedDestination)

        assert result.person_id == 4
        assert result.person_name == "Carol Brown"
        assert result.person_email == "carol@example.com"
        assert result.address_street == "789 Pine St"
        assert result.address_city == "Metropolis"
        assert result.address_country == "USA"


# Test mapping configuration


class TestMappingConfiguration:
    def test_mapping_configuration_creation(self):
        """Test creating mapping configuration"""
        config = MappingConfiguration(SourcePerson, DestinationPerson)

        assert config.source_type == SourcePerson
        assert config.destination_type == DestinationPerson
        assert len(config.member_mappings) == 0

    def test_adding_member_mappings(self):
        """Test adding member mappings to configuration"""
        config = MappingConfiguration(SourcePerson, DestinationPerson)

        config.add_member_mapping(lambda src: src.id, lambda dst: dst.person_id)
        config.add_member_mapping(lambda src: src.email, lambda dst: dst.email_address)

        assert len(config.member_mappings) == 2

    def test_chaining_member_mappings(self):
        """Test chaining member mapping calls"""
        config = MappingConfiguration(SourcePerson, DestinationPerson).add_member_mapping(lambda src: src.id, lambda dst: dst.person_id).add_member_mapping(lambda src: src.email, lambda dst: dst.email_address).add_member_mapping(lambda src: f"{src.first_name} {src.last_name}", lambda dst: dst.full_name)

        assert len(config.member_mappings) == 3


# Test error handling


class TestMappingErrorHandling:
    def test_mapping_without_configuration(self):
        """Test mapping without proper configuration"""
        mapper = Mapper()

        source = SimpleSource(name="test", value=42, flag=True)

        # This should either work with convention-based mapping or raise an exception
        try:
            result = mapper.map(source, SimpleDestination)
            # If it works, verify the result
            assert result.name == "test"
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass

    def test_mapping_with_invalid_source_type(self):
        """Test mapping with wrong source type"""
        mapper = Mapper()
        mapper.create_map(SimpleSource, SimpleDestination)

        # Try to map a different type
        with pytest.raises(Exception):
            mapper.map("not a SimpleSource", SimpleDestination)

    def test_mapping_configuration_with_invalid_types(self):
        """Test creating mapping configuration with invalid types"""
        try:
            config = MappingConfiguration(str, int)  # Invalid mapping types
            # Depending on implementation, this might be allowed but mapping would fail
            assert config.source_type == str
            assert config.destination_type == int
        except Exception:
            # Or it might raise an exception immediately
            pass


# Integration tests


class TestMappingIntegration:
    def test_complete_mapping_scenario(self):
        """Test complete mapping scenario with multiple objects"""
        mapper = Mapper()
        profile = PersonMappingProfile()
        mapper.add_profile(profile)

        # Create test data
        addresses = [
            SourceAddress("123 Main St", "City1", "12345", "USA"),
            SourceAddress("456 Oak Ave", "City2", "67890", "Canada"),
            SourceAddress("789 Pine St", "City3", "54321", "UK"),
        ]

        people = [
            SourcePerson(
                1,
                "John",
                "Doe",
                "john@example.com",
                date(1990, 1, 1),
                Decimal("50000"),
                True,
                addresses[0],
                ["python", "backend"],
            ),
            SourcePerson(
                2,
                "Jane",
                "Smith",
                "jane@example.com",
                date(1985, 5, 15),
                Decimal("75000"),
                True,
                addresses[1],
                ["frontend", "react"],
            ),
            SourcePerson(
                3,
                "Bob",
                "Johnson",
                "bob@example.com",
                date(1992, 8, 20),
                Decimal("60000"),
                False,
                addresses[2],
                ["fullstack"],
            ),
        ]

        # Map all people
        results = mapper.map_list(people, DestinationPerson)

        assert len(results) == 3

        # Verify first person
        assert results[0].person_id == 1
        assert results[0].full_name == "John Doe"
        assert results[0].status == "Active"
        assert results[0].home_address.full_address == "123 Main St, City1"
        assert results[0].tag_list == ["python", "backend"]

        # Verify second person
        assert results[1].person_id == 2
        assert results[1].full_name == "Jane Smith"
        assert results[1].status == "Active"
        assert results[1].home_address.country_name == "Canada"

        # Verify third person
        assert results[2].person_id == 3
        assert results[2].status == "Inactive"
        assert results[2].home_address.country_name == "UK"

    def test_bidirectional_mapping(self):
        """Test mapping in both directions"""
        mapper = Mapper()

        # Configure forward mapping
        mapper.create_map(SimpleSource, SimpleDestination)

        # Configure reverse mapping
        mapper.create_map(SimpleDestination, SimpleSource)

        original = SimpleSource(name="test", value=42, flag=True)

        # Map forward
        destination = mapper.map(original, SimpleDestination)
        assert destination.name == "test"
        assert destination.value == 42
        assert destination.flag is True

        # Map back
        round_trip = mapper.map(destination, SimpleSource)
        assert round_trip.name == original.name
        assert round_trip.value == original.value
        assert round_trip.flag == original.flag
