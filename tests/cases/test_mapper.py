import unittest
import uuid
from enum import Enum
from dataclasses import dataclass

from neuroglia.mapping.mapper import (
    Mapper,
    MapperConfiguration,
    MappingProfile,
    TypeMappingContext,
    MemberMappingContext,
)
from tests.data import UserDto


class TestEnum(str, Enum):
    """Test enum for mapper tests"""

    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"


@dataclass
class SourceWithEnum:
    """Source class with enum property for mapper tests"""

    id: str
    name: str
    status: TestEnum
    optional_status: TestEnum = None


@dataclass
class DestinationWithEnum:
    """Destination class with enum property for mapper tests"""

    id: str
    name: str
    status: TestEnum
    optional_status: TestEnum = None


class SourceClass:
    """Simple source class for mapper tests"""

    def __init__(self, id=None, name=None, value=None):
        self.id = id if id else str(uuid.uuid4())
        self.name = name if name else "test name"
        self.value = value if value else 42


class DestinationClass:
    """Simple destination class for mapper tests"""

    id: str
    name: str
    value: int


class TestUserMappingProfile(MappingProfile):
    """Test mapping profile for UserDto to DestinationClass"""

    def __init__(self):
        super().__init__()
        self.create_map(SourceClass, DestinationClass)


class EnumMappingProfile(MappingProfile):
    """Test mapping profile for enum handling"""

    def __init__(self):
        super().__init__()
        self.create_map(SourceWithEnum, DestinationWithEnum)


class TestMapper(unittest.TestCase):
    """Test cases for the Mapper class"""

    def test_basic_mapping(self):
        """Test basic object mapping functionality"""
        # Arrange
        source = SourceClass()
        config = MapperConfiguration()
        mapping = config.create_map(SourceClass, DestinationClass)
        mapper = Mapper(config)

        # Act
        destination = mapper.map(source, DestinationClass)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.name, destination.name)
        self.assertEqual(source.value, destination.value)

    def test_mapping_with_profile(self):
        """Test mapping with a mapping profile"""
        # Arrange
        source = SourceClass()
        config = MapperConfiguration()
        profile = TestUserMappingProfile()
        profile.apply_to(config)
        mapper = Mapper(config)

        # Act
        destination = mapper.map(source, DestinationClass)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.name, destination.name)
        self.assertEqual(source.value, destination.value)

    def test_mapping_with_converter(self):
        """Test mapping with a custom converter function"""
        # Arrange
        source = SourceClass()
        config = MapperConfiguration()
        mapping = config.create_map(SourceClass, DestinationClass)

        # Add a custom converter for the "name" property
        mapping.for_member("name", lambda ctx: ctx.source_member_value.upper())

        mapper = Mapper(config)

        # Act
        destination = mapper.map(source, DestinationClass)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.name.upper(), destination.name)
        self.assertEqual(source.value, destination.value)

    def test_enum_mapping(self):
        """Test mapping with enum values"""
        # Arrange
        source = SourceWithEnum(
            id=str(uuid.uuid4()), name="Test Enum Mapping", status=TestEnum.SECOND
        )
        config = MapperConfiguration()
        mapping = config.create_map(SourceWithEnum, DestinationWithEnum)
        mapper = Mapper(config)

        # Act
        destination = mapper.map(source, DestinationWithEnum)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.name, destination.name)
        self.assertEqual(source.status, destination.status)
        self.assertEqual(source.optional_status, destination.optional_status)

        # Verify enum types are preserved
        self.assertIsInstance(destination.status, TestEnum)
        self.assertEqual(destination.status.value, "SECOND")

    def test_enum_mapping_with_string(self):
        """Test mapping string values to enum members using custom converter"""

        # Arrange
        class SourceWithStringEnum:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.status = "FIRST"  # String value that should be mapped to an enum

        config = MapperConfiguration()
        mapping = config.create_map(SourceWithStringEnum, DestinationWithEnum)

        # Add custom converter for string to enum conversion
        mapping.for_member("status", lambda ctx: TestEnum(ctx.source_member_value))

        mapper = Mapper(config)
        source = SourceWithStringEnum()

        # Act
        destination = mapper.map(source, DestinationWithEnum)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.status, destination.status.value)
        self.assertIsInstance(destination.status, TestEnum)

    def test_enum_mapping_with_custom_converter(self):
        """Test mapping with a custom converter for enum values"""

        # Arrange
        class SourceWithStringEnum:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.status = "FIRST"  # String value that will be mapped to an enum

        config = MapperConfiguration()
        mapping = config.create_map(SourceWithStringEnum, DestinationWithEnum)

        # Add a custom converter for the status property
        mapping.for_member("status", lambda ctx: TestEnum(ctx.source_member_value))

        mapper = Mapper(config)
        source = SourceWithStringEnum()

        # Act
        destination = mapper.map(source, DestinationWithEnum)

        # Assert
        self.assertEqual(source.id, destination.id)
        self.assertEqual(source.status, destination.status.value)
        self.assertIsInstance(destination.status, TestEnum)


if __name__ == "__main__":
    unittest.main()
