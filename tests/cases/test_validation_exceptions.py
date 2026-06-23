"""Tests for validation exceptions."""

import pytest
from neuroglia.validation.exceptions import (
    ValidationException,
    BusinessRuleViolationException,
    ConditionalValidationException,
    CompositeValidationException,
)


class TestValidationException:
    def test_basic_creation(self):
        exc = ValidationException("Test message")
        assert str(exc) == "Validation failed: Test message"
        assert exc.message == "Test message"
        assert exc.field is None
        assert exc.code is None
        assert exc.details == {}

    def test_creation_with_field(self):
        exc = ValidationException("Field error", field="test_field")
        assert str(exc) == "Validation failed for field 'test_field': Field error"
        assert exc.field == "test_field"

    def test_creation_with_all_parameters(self):
        details = {"context": "test"}
        exc = ValidationException(
            "Test message", field="test_field", code="test_code", details=details
        )

        assert exc.message == "Test message"
        assert exc.field == "test_field"
        assert exc.code == "test_code"
        assert exc.details == details


class TestBusinessRuleViolationException:
    def test_basic_creation(self):
        exc = BusinessRuleViolationException("Rule violated", "test_rule")
        expected = "Business rule 'test_rule' violated: Rule violated"
        assert str(exc) == expected
        assert exc.rule_name == "test_rule"
        assert exc.entity_type is None
        assert exc.entity_id is None

    def test_creation_with_entity_info(self):
        exc = BusinessRuleViolationException(
            "Rule violated", "test_rule", entity_type="User", entity_id="123"
        )

        expected = "Business rule 'test_rule' violated: Rule violated (Entity: User, ID: 123)"
        assert str(exc) == expected
        assert exc.entity_type == "User"
        assert exc.entity_id == "123"

    def test_creation_with_entity_type_only(self):
        exc = BusinessRuleViolationException("Rule violated", "test_rule", entity_type="User")

        expected = "Business rule 'test_rule' violated: Rule violated (Entity: User)"
        assert str(exc) == expected


class TestConditionalValidationException:
    def test_creation_condition_met(self):
        exc = ConditionalValidationException(
            "Validation failed", "user is active", condition_met=True
        )

        expected = (
            "Conditional validation failed (condition 'user is active' met): Validation failed"
        )
        assert str(exc) == expected
        assert exc.condition == "user is active"
        assert exc.condition_met is True

    def test_creation_condition_not_met(self):
        exc = ConditionalValidationException(
            "Validation failed", "user is active", condition_met=False
        )

        expected = (
            "Conditional validation failed (condition 'user is active' not met): Validation failed"
        )
        assert str(exc) == expected
        assert exc.condition_met is False

    def test_creation_default_condition_met(self):
        exc = ConditionalValidationException("Validation failed", "test condition")
        expected = (
            "Conditional validation failed (condition 'test condition' met): Validation failed"
        )
        assert str(exc) == expected
        assert exc.condition_met is True


class TestCompositeValidationException:
    def test_creation_with_multiple_errors(self):
        error1 = ValidationException("Error 1", field="field1")
        error2 = ValidationException("Error 2", field="field2")
        error3 = BusinessRuleViolationException("Rule error", "test_rule")

        composite = CompositeValidationException([error1, error2, error3])

        assert composite.message == "Multiple validation errors occurred (3 errors)"
        assert len(composite.errors) == 3

        error_str = str(composite)
        assert "Multiple validation errors occurred (3 errors):" in error_str
        assert "1. Validation failed for field 'field1': Error 1" in error_str
        assert "2. Validation failed for field 'field2': Error 2" in error_str
        assert "3. Business rule 'test_rule' violated: Rule error" in error_str

    def test_creation_with_single_error(self):
        error = ValidationException("Single error")
        composite = CompositeValidationException([error])

        assert len(composite.errors) == 1
        assert "Multiple validation errors occurred (1 errors):" in str(composite)

    def test_get_field_errors(self):
        error1 = ValidationException("Error 1", field="field1")
        error2 = ValidationException("Error 2", field="field1")
        error3 = ValidationException("Error 3", field="field2")
        error4 = ValidationException("Error 4")  # No field

        composite = CompositeValidationException([error1, error2, error3, error4])
        field_errors = composite.get_field_errors()

        assert len(field_errors["field1"]) == 2
        assert "Error 1" in field_errors["field1"]
        assert "Error 2" in field_errors["field1"]

        assert len(field_errors["field2"]) == 1
        assert "Error 3" in field_errors["field2"]

        assert len(field_errors["general"]) == 1
        assert "Error 4" in field_errors["general"]

    def test_get_field_errors_empty(self):
        composite = CompositeValidationException([])
        field_errors = composite.get_field_errors()
        assert field_errors == {}


class TestExceptionHierarchy:
    def test_validation_exception_inheritance(self):
        """Test that all validation exceptions inherit from ValidationException."""
        business_exc = BusinessRuleViolationException("Test", "rule")
        conditional_exc = ConditionalValidationException("Test", "condition")
        composite_exc = CompositeValidationException([])

        assert isinstance(business_exc, ValidationException)
        assert isinstance(conditional_exc, ValidationException)
        assert isinstance(composite_exc, ValidationException)

    def test_exception_inheritance_from_base_exception(self):
        """Test that all validation exceptions inherit from base Exception."""
        validation_exc = ValidationException("Test")
        business_exc = BusinessRuleViolationException("Test", "rule")
        conditional_exc = ConditionalValidationException("Test", "condition")
        composite_exc = CompositeValidationException([])

        assert isinstance(validation_exc, Exception)
        assert isinstance(business_exc, Exception)
        assert isinstance(conditional_exc, Exception)
        assert isinstance(composite_exc, Exception)


class TestExceptionUsagePatterns:
    def test_raising_and_catching_validation_exception(self):
        """Test typical usage pattern for raising and catching validation exceptions."""

        def validate_user(name: str):
            if not name:
                raise ValidationException("Name is required", field="name", code="required")
            if len(name) < 2:
                raise ValidationException("Name too short", field="name", code="min_length")

        # Test successful validation
        validate_user("John")  # Should not raise

        # Test validation failures
        with pytest.raises(ValidationException) as exc_info:
            validate_user("")

        assert exc_info.value.field == "name"
        assert exc_info.value.code == "required"

        with pytest.raises(ValidationException) as exc_info:
            validate_user("J")

        assert exc_info.value.code == "min_length"

    def test_collecting_multiple_errors(self):
        """Test pattern for collecting multiple validation errors."""

        def validate_user_comprehensive(name: str, email: str, age: int):
            errors = []

            if not name:
                errors.append(ValidationException("Name required", field="name"))
            elif len(name) < 2:
                errors.append(ValidationException("Name too short", field="name"))

            if not email:
                errors.append(ValidationException("Email required", field="email"))
            elif "@" not in email:
                errors.append(ValidationException("Invalid email", field="email"))

            if age < 0:
                errors.append(ValidationException("Invalid age", field="age"))

            if errors:
                if len(errors) == 1:
                    raise errors[0]
                else:
                    raise CompositeValidationException(errors)

        # Test successful validation
        validate_user_comprehensive("John", "john@example.com", 25)

        # Test single error
        with pytest.raises(ValidationException):
            validate_user_comprehensive("", "john@example.com", 25)

        # Test multiple errors
        with pytest.raises(CompositeValidationException) as exc_info:
            validate_user_comprehensive("", "invalid", -1)

        assert len(exc_info.value.errors) == 3
        field_errors = exc_info.value.get_field_errors()
        assert "name" in field_errors
        assert "email" in field_errors
        assert "age" in field_errors
