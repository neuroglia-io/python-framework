"""Tests for property and entity validators."""

import pytest
from neuroglia.validation.validators import (
    ValidatorBase,
    PropertyValidator,
    EntityValidator,
    CompositeValidator,
    validate_with,
    required,
    min_length,
    max_length,
    email_format,
    numeric_range,
    custom_validator,
)
from neuroglia.validation.business_rules import ValidationResult
from neuroglia.validation.exceptions import ValidationException, CompositeValidationException


# Test entities
class User:
    def __init__(self, name: str = None, email: str = None, age: int = None):
        self.name = name
        self.email = email
        self.age = age


class TestPropertyValidator:
    def test_property_validator_valid(self):
        validator = PropertyValidator(
            lambda value: value is not None and len(str(value)) > 0, "Value cannot be empty"
        )

        result = validator.validate("test", "field1")
        assert result.is_valid
        assert validator.is_valid("test")

    def test_property_validator_invalid(self):
        validator = PropertyValidator(
            lambda value: value is not None and len(str(value)) > 0,
            "Value cannot be empty",
            "required",
        )

        result = validator.validate("", "field1")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].message == "Value cannot be empty"
        assert result.errors[0].field == "field1"
        assert result.errors[0].code == "required"
        assert not validator.is_valid("")

    def test_property_validator_without_field(self):
        validator = PropertyValidator(lambda value: value is not None, "Value is required")

        result = validator.validate(None)
        assert not result.is_valid
        assert result.errors[0].field is None


class TestEntityValidator:
    def test_entity_validator_empty(self):
        validator = EntityValidator(User)
        user = User("John", "john@example.com", 25)

        result = validator.validate(user)
        assert result.is_valid

    def test_entity_validator_with_property_validators(self):
        validator = EntityValidator(User)
        validator.add_property_validator("name", required())
        validator.add_property_validator("email", email_format())
        validator.add_property_validator("age", numeric_range(18, 100))

        # Valid user
        user = User("John", "john@example.com", 25)
        result = validator.validate(user)
        assert result.is_valid

    def test_entity_validator_with_invalid_properties(self):
        validator = EntityValidator(User)
        validator.add_property_validator("name", required())
        validator.add_property_validator("email", email_format())
        validator.add_property_validator("age", numeric_range(18, 100))

        # Invalid user
        user = User("", "invalid-email", 16)
        result = validator.validate(user)
        assert not result.is_valid
        assert len(result.errors) == 3

    def test_entity_validator_missing_property(self):
        validator = EntityValidator(User)
        validator.add_property_validator("nonexistent", required())

        user = User("John", "john@example.com", 25)
        result = validator.validate(user)
        assert not result.is_valid
        assert "not found on entity" in result.errors[0].message

    def test_entity_validator_with_entity_rules(self):
        def age_name_consistency(user):
            result = ValidationResult([])
            if user.age and user.age < 18 and user.name and "Jr." not in user.name:
                result.add_error(
                    "Minors should have 'Jr.' in their name", code="age_name_consistency"
                )
            return result

        validator = EntityValidator(User)
        validator.add_entity_validator(age_name_consistency)

        # Valid adult
        adult = User("John", "john@example.com", 25)
        result = validator.validate(adult)
        assert result.is_valid

        # Valid minor with Jr.
        minor_jr = User("John Jr.", "john@example.com", 16)
        result = validator.validate(minor_jr)
        assert result.is_valid

        # Invalid minor without Jr.
        minor = User("John", "john@example.com", 16)
        result = validator.validate(minor)
        assert not result.is_valid

    def test_entity_validator_fluent_interface(self):
        validator = (
            EntityValidator(User)
            .add_property_validator("name", required())
            .add_property_validator("email", email_format())
            .add_entity_validator(lambda user: ValidationResult([]))
        )

        user = User("John", "john@example.com", 25)
        result = validator.validate(user)
        assert result.is_valid


class TestCompositeValidator:
    def test_composite_validator_and_all_valid(self):
        validators = [required(), min_length(3), max_length(20)]
        composite = CompositeValidator(validators, "AND")

        result = composite.validate("John", "name")
        assert result.is_valid

    def test_composite_validator_and_some_invalid(self):
        validators = [required(), min_length(10), max_length(20)]
        composite = CompositeValidator(validators, "AND")

        result = composite.validate("John", "name")
        assert not result.is_valid
        assert len(result.errors) == 1  # min_length fails

    def test_composite_validator_or_one_valid(self):
        validators = [
            min_length(10),  # Will fail
            email_format(),  # Will fail
            max_length(20),  # Will pass
        ]
        composite = CompositeValidator(validators, "OR")

        result = composite.validate("John", "field")
        assert result.is_valid  # One validator passes

    def test_composite_validator_or_all_invalid(self):
        validators = [
            min_length(10),  # Will fail
            email_format(),  # Will fail
            numeric_range(1, 5),  # Will fail (not numeric)
        ]
        composite = CompositeValidator(validators, "OR")

        result = composite.validate("John", "field")
        assert not result.is_valid
        assert len(result.errors) == 3  # All fail

    def test_composite_validator_invalid_operator(self):
        validators = [required()]
        with pytest.raises(ValueError, match="Operator must be 'AND' or 'OR'"):
            CompositeValidator(validators, "XOR")


class TestValidatorFactories:
    def test_required_validator(self):
        validator = required()

        assert validator.validate("test").is_valid
        assert validator.validate("  test  ").is_valid
        assert not validator.validate(None).is_valid
        assert not validator.validate("").is_valid
        assert not validator.validate("   ").is_valid
        assert not validator.validate([]).is_valid

    def test_min_length_validator(self):
        validator = min_length(5)

        assert validator.validate("hello").is_valid
        assert validator.validate("hello world").is_valid
        assert not validator.validate("hi").is_valid
        assert not validator.validate(None).is_valid
        assert not validator.validate("").is_valid

    def test_max_length_validator(self):
        validator = max_length(5)

        assert validator.validate("hello").is_valid
        assert validator.validate("hi").is_valid
        assert validator.validate(None).is_valid  # None is valid for max length
        assert validator.validate("").is_valid
        assert not validator.validate("hello world").is_valid

    def test_email_format_validator(self):
        validator = email_format()

        assert validator.validate("test@example.com").is_valid
        assert validator.validate("user.name@domain.co.uk").is_valid
        assert not validator.validate("invalid-email").is_valid
        assert not validator.validate("@example.com").is_valid
        assert not validator.validate("test@").is_valid
        assert not validator.validate(None).is_valid
        assert not validator.validate(123).is_valid

    def test_numeric_range_validator(self):
        validator = numeric_range(10, 100)

        assert validator.validate(50).is_valid
        assert validator.validate(10).is_valid  # Min boundary
        assert validator.validate(100).is_valid  # Max boundary
        assert validator.validate(50.5).is_valid  # Float
        assert not validator.validate(5).is_valid
        assert not validator.validate(150).is_valid
        assert not validator.validate("50").is_valid  # String
        assert not validator.validate(None).is_valid

    def test_numeric_range_min_only(self):
        validator = numeric_range(min_val=10)

        assert validator.validate(10).is_valid
        assert validator.validate(1000).is_valid
        assert not validator.validate(5).is_valid

    def test_numeric_range_max_only(self):
        validator = numeric_range(max_val=100)

        assert validator.validate(50).is_valid
        assert validator.validate(-1000).is_valid
        assert not validator.validate(150).is_valid

    def test_custom_validator(self):
        validator = custom_validator(
            lambda value: isinstance(value, str) and value.startswith("test_"),
            "Value must start with 'test_'",
            "custom_prefix",
        )

        assert validator.validate("test_value").is_valid
        assert not validator.validate("value").is_valid

        result = validator.validate("value", "field1")
        assert result.errors[0].message == "Value must start with 'test_'"
        assert result.errors[0].code == "custom_prefix"


class TestValidateWithDecorator:
    def test_validate_with_decorator_success(self):
        class TestService:
            @validate_with(required(), min_length(3))
            def process_name(self, name: str):
                return f"Processed: {name}"

        service = TestService()
        result = service.process_name("John")
        assert result == "Processed: John"

    def test_validate_with_decorator_single_failure(self):
        class TestService:
            @validate_with(required())
            def process_name(self, name: str):
                return f"Processed: {name}"

        service = TestService()
        with pytest.raises(ValidationException):
            service.process_name("")

    def test_validate_with_decorator_multiple_failures(self):
        class TestService:
            @validate_with(min_length(5), max_length(3))  # Impossible to satisfy both
            def process_name(self, name: str):
                return f"Processed: {name}"

        service = TestService()
        with pytest.raises(CompositeValidationException):
            service.process_name("test")


class TestValidatorIntegration:
    def test_complex_entity_validation(self):
        """Test complex entity validation with multiple validator types."""

        def password_strength_check(user):
            result = ValidationResult([])
            # Check if username appears in email (indicating weak security)
            # This is just a demo rule - "john" appears in "john@example.com"
            if user.name and user.email and user.name.lower() == user.email.split("@")[0].lower():
                result.add_error(
                    "Email should not match username exactly",
                    field="email",
                    code="username_in_email",
                )
            return result

        validator = (
            EntityValidator(User)
            .add_property_validator("name", CompositeValidator([required(), min_length(2)], "AND"))
            .add_property_validator(
                "email", CompositeValidator([required(), email_format()], "AND")
            )
            .add_property_validator("age", numeric_range(13, 120))
            .add_entity_validator(password_strength_check)
        )

        # Valid user
        valid_user = User("Johnny", "john@example.com", 25)
        result = validator.validate(valid_user)
        assert result.is_valid

        # User with multiple issues
        invalid_user = User(
            "J", "j@j.com", 200
        )  # Short name (1 char), contains username in email, invalid age
        result = validator.validate(invalid_user)
        assert not result.is_valid

        field_errors = result.get_field_errors()
        assert "name" in field_errors  # Short name
        assert "age" in field_errors  # Invalid age
        assert "email" in field_errors  # Username in email

    def test_validator_error_aggregation(self):
        """Test that validators properly aggregate errors."""
        validator = EntityValidator(User)
        validator.add_property_validator("name", required("Name is required"))
        validator.add_property_validator(
            "name", min_length(5, "Name must be at least 5 characters")
        )
        validator.add_property_validator("email", required("Email is required"))
        validator.add_property_validator("email", email_format("Invalid email format"))

        user = User("Jo", "invalid")  # Multiple validation errors
        result = validator.validate(user)

        assert not result.is_valid
        field_errors = result.get_field_errors()
        assert len(field_errors["name"]) == 1  # min_length (required passes)
        assert len(field_errors["email"]) == 1  # email_format (required passes)
