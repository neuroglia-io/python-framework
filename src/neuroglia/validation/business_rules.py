"""
Business rule validation system for the Neuroglia framework.

This module provides a fluent API for defining and validating business rules,
enabling complex domain logic validation with clear, readable rule definitions.
Business rules can be simple property validations or complex multi-entity
business invariants.

For detailed information about business rule validation, see:
https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
"""
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from .exceptions import BusinessRuleViolationException

T = TypeVar("T")


@dataclass
class ValidationError:
    """
    Represents a single validation error with context.

    Provides structured error information including field names, error codes,
    and contextual information for comprehensive error reporting.

    For detailed information about validation patterns, see:
    https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
    """

    message: str
    field: Optional[str] = None
    code: Optional[str] = None
    context: Optional[dict[str, Any]] = None


@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation with comprehensive error reporting.

    Aggregates multiple validation errors and provides methods for checking
    validation success and accessing detailed error information.

    For detailed information about validation results, see:
    https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
    """

    errors: list[ValidationError]

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def add_error(
        self,
        message: str,
        field: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a validation error to the result."""
        self.errors.append(ValidationError(message, field, code, context))

    def combine(self, other: "ValidationResult") -> "ValidationResult":
        """Combine this result with another validation result."""
        combined_errors = self.errors + other.errors
        return ValidationResult(combined_errors)

    def get_field_errors(self) -> dict[str, list[str]]:
        """Get errors grouped by field name."""
        field_errors: dict[str, list[str]] = {}
        for error in self.errors:
            field_name = error.field or "general"
            if field_name not in field_errors:
                field_errors[field_name] = []
            field_errors[field_name].append(error.message)
        return field_errors


class BusinessRule(ABC, Generic[T]):
    """
    Abstract base class for business rules with fluent validation API.

    Business rules encapsulate domain logic and can be applied to entities
    or value objects to ensure business invariants are maintained. This class
    provides a foundation for implementing complex domain validation logic.

    For detailed information about business rule validation, see:
    https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
    """

    def __init__(self, name: str, message: Optional[str] = None):
        self.name = name
        self.message = message or f"Business rule '{name}' violated"

    @abstractmethod
    def is_satisfied_by(self, entity: T) -> bool:
        """Check if the entity satisfies this business rule."""

    def validate(self, entity: T) -> ValidationResult:
        """Validate the entity against this rule and return detailed results."""
        result = ValidationResult([])

        if not self.is_satisfied_by(entity):
            result.add_error(message=self.message, code=f"business_rule_{self.name.lower().replace(' ', '_')}")

        return result


class PropertyRule(BusinessRule[T]):
    """Business rule that validates a specific property of an entity.

    This rule extracts a property value using a provided function and
    validates it against a predicate function.
    """

    def __init__(
        self,
        name: str,
        property_getter: Callable[[T], Any],
        predicate: Callable[[Any], bool],
        field_name: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__(name, message)
        self.property_getter = property_getter
        self.predicate = predicate
        self.field_name = field_name

    def is_satisfied_by(self, entity: T) -> bool:
        """Check if the property value satisfies the predicate."""
        try:
            value = self.property_getter(entity)
            return self.predicate(value)
        except Exception:
            return False

    def validate(self, entity: T) -> ValidationResult:
        """Validate with field-specific error reporting."""
        result = ValidationResult([])

        if not self.is_satisfied_by(entity):
            result.add_error(
                message=self.message,
                field=self.field_name,
                code=f"business_rule_{self.name.lower().replace(' ', '_')}",
            )

        return result


class ConditionalRule(BusinessRule[T]):
    """Business rule that only applies when a condition is met.

    This rule first checks a condition, and only validates the main rule
    if the condition is satisfied.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[T], bool],
        rule: BusinessRule[T],
        condition_description: Optional[str] = None,
    ):
        super().__init__(name)
        self.condition = condition
        self.rule = rule
        self.condition_description = condition_description or "condition met"

    def is_satisfied_by(self, entity: T) -> bool:
        """Check condition first, then validate rule if condition is met."""
        if not self.condition(entity):
            return True  # Rule doesn't apply, so it's satisfied
        return self.rule.is_satisfied_by(entity)

    def validate(self, entity: T) -> ValidationResult:
        """Validate with conditional context."""
        if not self.condition(entity):
            return ValidationResult([])  # Rule doesn't apply

        result = self.rule.validate(entity)

        # Add conditional context to errors
        for error in result.errors:
            if error.context is None:
                error.context = {}
            error.context["condition"] = self.condition_description

        return result


class CompositeRule(BusinessRule[T]):
    """Business rule that combines multiple rules with logical operators.

    Supports AND and OR operations on multiple business rules.
    """

    def __init__(self, name: str, rules: list[BusinessRule[T]], operator: str = "AND"):
        super().__init__(name)
        self.rules = rules
        self.operator = operator.upper()

        if self.operator not in ["AND", "OR"]:
            raise ValueError("Operator must be 'AND' or 'OR'")

    def is_satisfied_by(self, entity: T) -> bool:
        """Apply logical operator to all contained rules."""
        if self.operator == "AND":
            return all(rule.is_satisfied_by(entity) for rule in self.rules)
        else:  # OR
            return any(rule.is_satisfied_by(entity) for rule in self.rules)

    def validate(self, entity: T) -> ValidationResult:
        """Validate all rules and combine results based on operator."""
        results = [rule.validate(entity) for rule in self.rules]

        if self.operator == "AND":
            # For AND, combine all errors
            combined = ValidationResult([])
            for result in results:
                combined = combined.combine(result)
            return combined
        else:  # OR
            # For OR, return empty result if any rule passed
            if any(result.is_valid for result in results):
                return ValidationResult([])

            # All rules failed, combine all errors
            combined = ValidationResult([])
            for result in results:
                combined = combined.combine(result)
            return combined


class BusinessRuleValidator:
    """
    Provides fluent API for composing and executing business rule validations.

    Enables chaining multiple business rules together and executing them
    with comprehensive error collection and reporting.

    For detailed information about business rule composition, see:
    https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
    """

    def __init__(self):
        self.rules: list[BusinessRule] = []

    def add_rule(self, rule: BusinessRule) -> "BusinessRuleValidator":
        """Add a business rule to the validator (fluent interface)."""
        self.rules.append(rule)
        return self

    def validate(self, entity: Any) -> ValidationResult:
        """Validate entity against all registered rules."""
        combined_result = ValidationResult([])

        for rule in self.rules:
            result = rule.validate(entity)
            combined_result = combined_result.combine(result)

        return combined_result

    def validate_and_throw(self, entity: Any) -> None:
        """Validate entity and raise exception if validation fails."""
        result = self.validate(entity)

        if not result.is_valid:
            # Create appropriate exception based on error types
            errors = []
            for error in result.errors:
                if error.context and "condition" in error.context:
                    from .exceptions import ConditionalValidationException

                    exc = ConditionalValidationException(
                        error.message,
                        error.context["condition"],
                        field=error.field,
                        code=error.code,
                    )
                else:
                    exc = BusinessRuleViolationException(
                        error.message,
                        error.code or "unknown_rule",
                        field=error.field,
                        code=error.code,
                    )
                errors.append(exc)

            if len(errors) == 1:
                raise errors[0]
            else:
                from .exceptions import CompositeValidationException

                raise CompositeValidationException(errors)


# Convenience functions for creating common business rules


def rule(name: str, predicate: Callable[[Any], bool], message: Optional[str] = None) -> BusinessRule[Any]:
    """Create a simple business rule from a predicate function.

    Args:
        name: Name of the rule for identification
        predicate: Function that returns True if rule is satisfied
        message: Optional custom error message

    Returns:
        BusinessRule instance
    """

    class SimpleRule(BusinessRule[Any]):
        def __init__(self, name: str, message: Optional[str] = None):
            super().__init__(name, message)
            self._predicate = predicate

        def is_satisfied_by(self, entity: Any) -> bool:
            return self._predicate(entity)

    return SimpleRule(name, message)


def conditional_rule(
    name: str,
    condition: Callable[[Any], bool],
    rule_predicate: Callable[[Any], bool],
    condition_description: Optional[str] = None,
    message: Optional[str] = None,
) -> ConditionalRule[Any]:
    """Create a conditional business rule.

    Args:
        name: Name of the rule
        condition: Function that determines if rule should be applied
        rule_predicate: Function that validates the actual rule
        condition_description: Description of the condition
        message: Optional custom error message

    Returns:
        ConditionalRule instance
    """
    inner_rule = rule(name, rule_predicate, message)
    return ConditionalRule(name, condition, inner_rule, condition_description)


def when(condition: Callable[[Any], bool], condition_description: Optional[str] = None) -> Callable[[BusinessRule[Any]], ConditionalRule[Any]]:
    """Decorator-style function for creating conditional rules.

    Usage:
        user_rule = when(lambda u: u.is_active, "user is active")(
            rule("has_email", lambda u: u.email is not None)
        )

    Args:
        condition: Function that determines if rule should be applied
        condition_description: Description of the condition

    Returns:
        Function that wraps a rule in a conditional rule
    """

    def wrapper(business_rule: BusinessRule[Any]) -> ConditionalRule[Any]:
        return ConditionalRule(f"conditional_{business_rule.name}", condition, business_rule, condition_description)

    return wrapper
