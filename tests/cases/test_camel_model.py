"""Tests for CamelModel Pydantic utility."""

import pytest

# Check if pydantic is available
try:
    import pydantic  # noqa: F401

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from neuroglia.utils.camel_model import (
    CamelModel,
    create_camel_model,
    add_camel_case_aliases,
    PYDANTIC_AVAILABLE,
)


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
class TestCamelModel:
    """Test the CamelModel base class."""

    def test_camel_model_creation(self):
        """Test creating a CamelModel."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        user = UserModel(first_name="John", last_name="Doe", email_address="john@example.com")

        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email_address == "john@example.com"

    def test_camel_model_serialization_camel_case(self):
        """Test CamelModel serialization with camelCase."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        user = UserModel(first_name="John", last_name="Doe", email_address="john@example.com")

        # Should serialize with camelCase keys
        camel_dict = user.to_camel_case_dict()
        expected = {"firstName": "John", "lastName": "Doe", "emailAddress": "john@example.com"}
        assert camel_dict == expected

    def test_camel_model_serialization_snake_case(self):
        """Test CamelModel serialization with snake_case."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        user = UserModel(first_name="John", last_name="Doe", email_address="john@example.com")

        # Should serialize with snake_case keys
        snake_dict = user.to_snake_case_dict()
        expected = {"first_name": "John", "last_name": "Doe", "email_address": "john@example.com"}
        assert snake_dict == expected

    def test_camel_model_deserialization_camel_case(self):
        """Test CamelModel deserialization from camelCase."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        # Should accept camelCase input
        camel_data = {"firstName": "Jane", "lastName": "Smith", "emailAddress": "jane@example.com"}

        user = UserModel.from_camel_case_dict(camel_data)
        assert user.first_name == "Jane"
        assert user.last_name == "Smith"
        assert user.email_address == "jane@example.com"

    def test_camel_model_deserialization_snake_case(self):
        """Test CamelModel deserialization from snake_case."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        # Should accept snake_case input
        snake_data = {
            "first_name": "Bob",
            "last_name": "Johnson",
            "email_address": "bob@example.com",
        }

        user = UserModel.from_snake_case_dict(snake_data)
        assert user.first_name == "Bob"
        assert user.last_name == "Johnson"
        assert user.email_address == "bob@example.com"

    def test_camel_model_mixed_deserialization(self):
        """Test CamelModel can handle mixed case formats."""

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            email_address: str

        # Mixed format should work due to populate_by_name=True
        mixed_data = {
            "firstName": "Alice",
            "last_name": "Brown",  # snake_case
            "emailAddress": "alice@example.com",
        }

        user = UserModel.model_validate(mixed_data)
        assert user.first_name == "Alice"
        assert user.last_name == "Brown"
        assert user.email_address == "alice@example.com"

    def test_camel_model_nested_objects(self):
        """Test CamelModel with nested objects."""

        class AddressModel(CamelModel):
            street_address: str
            city_name: str
            postal_code: str

        class UserModel(CamelModel):
            first_name: str
            last_name: str
            home_address: AddressModel

        user_data = {
            "firstName": "John",
            "lastName": "Doe",
            "homeAddress": {
                "streetAddress": "123 Main St",
                "cityName": "Anytown",
                "postalCode": "12345",
            },
        }

        user = UserModel.model_validate(user_data)
        assert user.first_name == "John"
        assert user.home_address.street_address == "123 Main St"
        assert user.home_address.city_name == "Anytown"

        # Test serialization maintains camelCase
        serialized = user.to_camel_case_dict()
        assert "homeAddress" in serialized
        assert "streetAddress" in serialized["homeAddress"]


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
class TestCreateCamelModel:
    """Test the create_camel_model function."""

    def test_create_camel_model_basic(self):
        """Test creating a basic CamelModel dynamically."""

        UserModel = create_camel_model(
            "UserModel", {"first_name": str, "last_name": str, "age": int}
        )

        user = UserModel(first_name="John", last_name="Doe", age=30)
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.age == 30

        # Should have camelCase serialization
        camel_dict = user.to_camel_case_dict()
        expected = {"firstName": "John", "lastName": "Doe", "age": 30}
        assert camel_dict == expected

    def test_create_camel_model_with_custom_base(self):
        """Test creating CamelModel with custom base class."""

        class CustomBase(CamelModel):
            id: int = 1

        UserModel = create_camel_model(
            "UserModel",
            {
                "first_name": str,
                "last_name": str,
            },
            base_class=CustomBase,
        )

        user = UserModel(first_name="Jane", last_name="Smith")
        assert user.first_name == "Jane"
        assert user.id == 1  # From base class


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
class TestAddCamelCaseAliases:
    """Test the add_camel_case_aliases function."""

    def test_add_camel_case_aliases_to_existing_model(self):
        """Test adding camelCase aliases to existing model."""
        from pydantic import BaseModel

        class OriginalModel(BaseModel):
            first_name: str
            last_name: str
            email_address: str

        # Add camelCase aliases
        EnhancedModel = add_camel_case_aliases(OriginalModel)

        # Should now accept camelCase input
        camel_data = {"firstName": "John", "lastName": "Doe", "emailAddress": "john@example.com"}

        user = EnhancedModel.model_validate(camel_data)
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email_address == "john@example.com"


@pytest.mark.skipif(PYDANTIC_AVAILABLE, reason="Testing without Pydantic")
class TestCamelModelWithoutPydantic:
    """Test CamelModel behavior when Pydantic is not available."""

    def test_camel_model_creation_fails_without_pydantic(self):
        """Test that CamelModel operations fail gracefully without Pydantic."""

        # The class should still be creatable but methods should fail
        class TestModel(CamelModel):
            pass

        model = TestModel()

        with pytest.raises(RuntimeError, match="Pydantic is required"):
            model.to_camel_case_dict()

        with pytest.raises(RuntimeError, match="Pydantic is required"):
            model.to_snake_case_dict()

        with pytest.raises(RuntimeError, match="Pydantic is required"):
            TestModel.from_camel_case_dict({})

    def test_create_camel_model_fails_without_pydantic(self):
        """Test that create_camel_model fails without Pydantic."""

        with pytest.raises(RuntimeError, match="Pydantic is required"):
            create_camel_model("TestModel", {"field": str})

    def test_add_camel_case_aliases_fails_without_pydantic(self):
        """Test that add_camel_case_aliases fails without Pydantic."""

        class TestModel:
            pass

        with pytest.raises(RuntimeError, match="Pydantic is required"):
            add_camel_case_aliases(TestModel)


class TestPydanticAvailability:
    """Test the Pydantic availability detection."""

    def test_pydantic_available_flag(self):
        """Test that the PYDANTIC_AVAILABLE flag is set correctly."""
        try:
            import pydantic  # noqa: F401

            assert PYDANTIC_AVAILABLE is True
        except ImportError:
            assert PYDANTIC_AVAILABLE is False
