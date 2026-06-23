"""Tests for business rule validation system."""

import pytest
from neuroglia.validation.business_rules import (
    BusinessRule,
    BusinessRuleValidator,
    ValidationResult,
    ValidationError,
    PropertyRule,
    ConditionalRule,
    CompositeRule,
    rule,
    conditional_rule,
    when,
)
from neuroglia.validation.exceptions import (
    BusinessRuleViolationException,
    ConditionalValidationException,
    CompositeValidationException,
)


# Test entities
class User:
    def __init__(self, name: str, email: str, age: int, is_active: bool = True):
        self.name = name
        self.email = email
        self.age = age
        self.is_active = is_active


class TestValidationError:
    def test_validation_error_creation(self):
        error = ValidationError("Test message", "test_field", "test_code")
        assert error.message == "Test message"
        assert error.field == "test_field"
        assert error.code == "test_code"
        assert error.context is None

    def test_validation_error_with_context(self):
        context = {"additional": "info"}
        error = ValidationError("Test message", context=context)
        assert error.context == context


class TestValidationResult:
    def test_empty_validation_result_is_valid(self):
        result = ValidationResult([])
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validation_result_with_errors_is_invalid(self):
        errors = [ValidationError("Error 1"), ValidationError("Error 2")]
        result = ValidationResult(errors)
        assert not result.is_valid
        assert len(result.errors) == 2

    def test_add_error(self):
        result = ValidationResult([])
        result.add_error("Test error", "test_field", "test_code")

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].message == "Test error"
        assert result.errors[0].field == "test_field"
        assert result.errors[0].code == "test_code"

    def test_combine_results(self):
        result1 = ValidationResult([ValidationError("Error 1")])
        result2 = ValidationResult([ValidationError("Error 2")])

        combined = result1.combine(result2)
        assert len(combined.errors) == 2
        assert not combined.is_valid

    def test_get_field_errors(self):
        result = ValidationResult(
            [
                ValidationError("Error 1", "field1"),
                ValidationError("Error 2", "field1"),
                ValidationError("Error 3", "field2"),
                ValidationError("Error 4"),  # No field
            ]
        )

        field_errors = result.get_field_errors()
        assert len(field_errors["field1"]) == 2
        assert len(field_errors["field2"]) == 1
        assert len(field_errors["general"]) == 1


class TestPropertyRule:
    def test_property_rule_satisfied(self):
        rule = PropertyRule(
            "name_required",
            lambda user: user.name,
            lambda name: name is not None and len(name) > 0,
            "name",
        )

        user = User("John", "john@example.com", 25)
        assert rule.is_satisfied_by(user)

        result = rule.validate(user)
        assert result.is_valid

    def test_property_rule_violated(self):
        rule = PropertyRule(
            "name_required",
            lambda user: user.name,
            lambda name: name is not None and len(name) > 0,
            "name",
            "Name is required",
        )

        user = User("", "john@example.com", 25)
        assert not rule.is_satisfied_by(user)

        result = rule.validate(user)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "name"
        assert result.errors[0].message == "Name is required"

    def test_property_rule_exception_handling(self):
        rule = PropertyRule(
            "invalid_property",
            lambda user: user.nonexistent_property,
            lambda value: value is not None,
        )

        user = User("John", "john@example.com", 25)
        assert not rule.is_satisfied_by(user)


class TestConditionalRule:
    def test_conditional_rule_condition_not_met(self):
        inner_rule = rule("name_required", lambda user: len(user.name) > 0)
        conditional = ConditionalRule(
            "active_user_name_required", lambda user: user.is_active, inner_rule, "user is active"
        )

        user = User("", "john@example.com", 25, is_active=False)
        assert conditional.is_satisfied_by(user)  # Rule doesn't apply

        result = conditional.validate(user)
        assert result.is_valid

    def test_conditional_rule_condition_met_and_satisfied(self):
        inner_rule = rule("name_required", lambda user: len(user.name) > 0)
        conditional = ConditionalRule(
            "active_user_name_required", lambda user: user.is_active, inner_rule, "user is active"
        )

        user = User("John", "john@example.com", 25, is_active=True)
        assert conditional.is_satisfied_by(user)

        result = conditional.validate(user)
        assert result.is_valid

    def test_conditional_rule_condition_met_and_violated(self):
        inner_rule = rule("name_required", lambda user: len(user.name) > 0)
        conditional = ConditionalRule(
            "active_user_name_required", lambda user: user.is_active, inner_rule, "user is active"
        )

        user = User("", "john@example.com", 25, is_active=True)
        assert not conditional.is_satisfied_by(user)

        result = conditional.validate(user)
        assert not result.is_valid
        assert result.errors[0].context["condition"] == "user is active"


class TestCompositeRule:
    def test_composite_rule_and_all_satisfied(self):
        rule1 = rule("name_required", lambda user: len(user.name) > 0)
        rule2 = rule("email_required", lambda user: len(user.email) > 0)
        composite = CompositeRule("user_required_fields", [rule1, rule2], "AND")

        user = User("John", "john@example.com", 25)
        assert composite.is_satisfied_by(user)

        result = composite.validate(user)
        assert result.is_valid

    def test_composite_rule_and_some_violated(self):
        rule1 = rule("name_required", lambda user: len(user.name) > 0)
        rule2 = rule("email_required", lambda user: len(user.email) > 0)
        composite = CompositeRule("user_required_fields", [rule1, rule2], "AND")

        user = User("", "john@example.com", 25)
        assert not composite.is_satisfied_by(user)

        result = composite.validate(user)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_composite_rule_or_one_satisfied(self):
        rule1 = rule("name_required", lambda user: len(user.name) > 0)
        rule2 = rule("email_required", lambda user: len(user.email) > 0)
        composite = CompositeRule("user_has_identity", [rule1, rule2], "OR")

        user = User("", "john@example.com", 25)
        assert composite.is_satisfied_by(user)

        result = composite.validate(user)
        assert result.is_valid

    def test_composite_rule_or_none_satisfied(self):
        rule1 = rule("name_required", lambda user: len(user.name) > 0)
        rule2 = rule("email_required", lambda user: len(user.email) > 0)
        composite = CompositeRule("user_has_identity", [rule1, rule2], "OR")

        user = User("", "", 25)
        assert not composite.is_satisfied_by(user)

        result = composite.validate(user)
        assert not result.is_valid
        assert len(result.errors) == 2


class TestBusinessRuleValidator:
    def test_validator_with_no_rules(self):
        validator = BusinessRuleValidator()
        user = User("John", "john@example.com", 25)

        result = validator.validate(user)
        assert result.is_valid

    def test_validator_with_passing_rules(self):
        validator = BusinessRuleValidator()
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))
        validator.add_rule(rule("email_required", lambda user: len(user.email) > 0))

        user = User("John", "john@example.com", 25)
        result = validator.validate(user)
        assert result.is_valid

    def test_validator_with_failing_rules(self):
        validator = BusinessRuleValidator()
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))
        validator.add_rule(rule("email_required", lambda user: len(user.email) > 0))

        user = User("", "", 25)
        result = validator.validate(user)
        assert not result.is_valid
        assert len(result.errors) == 2

    def test_validate_and_throw_success(self):
        validator = BusinessRuleValidator()
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))

        user = User("John", "john@example.com", 25)
        # Should not raise exception
        validator.validate_and_throw(user)

    def test_validate_and_throw_single_error(self):
        validator = BusinessRuleValidator()
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))

        user = User("", "john@example.com", 25)
        with pytest.raises(BusinessRuleViolationException):
            validator.validate_and_throw(user)

    def test_validate_and_throw_multiple_errors(self):
        validator = BusinessRuleValidator()
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))
        validator.add_rule(rule("email_required", lambda user: len(user.email) > 0))

        user = User("", "", 25)
        with pytest.raises(CompositeValidationException):
            validator.validate_and_throw(user)


class TestConvenienceFunctions:
    def test_rule_function(self):
        user_rule = rule("name_required", lambda user: len(user.name) > 0)

        user = User("John", "john@example.com", 25)
        assert user_rule.is_satisfied_by(user)

        empty_user = User("", "john@example.com", 25)
        assert not user_rule.is_satisfied_by(empty_user)

    def test_conditional_rule_function(self):
        conditional = conditional_rule(
            "active_user_name_required",
            lambda user: user.is_active,
            lambda user: len(user.name) > 0,
            "user is active",
        )

        # Inactive user with empty name - rule doesn't apply
        inactive_user = User("", "john@example.com", 25, is_active=False)
        assert conditional.is_satisfied_by(inactive_user)

        # Active user with name - rule applies and is satisfied
        active_user = User("John", "john@example.com", 25, is_active=True)
        assert conditional.is_satisfied_by(active_user)

        # Active user without name - rule applies and is violated
        active_empty_user = User("", "john@example.com", 25, is_active=True)
        assert not conditional.is_satisfied_by(active_empty_user)

    def test_when_decorator_function(self):
        base_rule = rule("name_required", lambda user: len(user.name) > 0)
        conditional = when(lambda user: user.is_active, "user is active")(base_rule)

        # Test same scenarios as conditional_rule_function
        inactive_user = User("", "john@example.com", 25, is_active=False)
        assert conditional.is_satisfied_by(inactive_user)

        active_user = User("John", "john@example.com", 25, is_active=True)
        assert conditional.is_satisfied_by(active_user)

        active_empty_user = User("", "john@example.com", 25, is_active=True)
        assert not conditional.is_satisfied_by(active_empty_user)


class TestBusinessRuleIntegration:
    def test_complex_validation_scenario(self):
        """Test a complex validation scenario with multiple rule types."""
        validator = BusinessRuleValidator()

        # Simple rules
        validator.add_rule(rule("name_required", lambda user: len(user.name) > 0))
        validator.add_rule(rule("valid_age", lambda user: user.age >= 18))

        # Conditional rule - email required only for active users
        validator.add_rule(
            conditional_rule(
                "active_user_email_required",
                lambda user: user.is_active,
                lambda user: len(user.email) > 0,
                "user is active",
            )
        )

        # Composite rule - either name or email must be valid
        name_rule = rule("has_name", lambda user: len(user.name) > 2)
        email_rule = rule("has_email", lambda user: "@" in user.email)
        validator.add_rule(CompositeRule("identity_check", [name_rule, email_rule], "OR"))

        # Test valid user
        valid_user = User("John Doe", "john@example.com", 25, is_active=True)
        result = validator.validate(valid_user)
        assert result.is_valid

        # Test user with multiple violations
        invalid_user = User("Jo", "invalid-email", 16, is_active=True)
        result = validator.validate(invalid_user)
        assert not result.is_valid
        assert len(result.errors) >= 2  # Age and email issues
