"""
Comprehensive validation system for business rules, domain logic, and data integrity.

This module provides enterprise-grade validation capabilities including fluent business
rule APIs, conditional validation, property validators, and comprehensive error reporting.
Designed to integrate seamlessly with CQRS, domain-driven design, and clean architecture
patterns for maintaining data integrity and business invariants.

Key Components:
    - BusinessRule: Abstract base for domain business rules
    - ValidationResult: Comprehensive validation result aggregation
    - PropertyValidator: Field-level validation with fluent API
    - EntityValidator: Object-level validation and business invariants
    - Conditional Rules: Context-aware validation logic
    - Validation Decorators: Method parameter and return value validation

Features:
    - Fluent API for readable rule definitions
    - Conditional and composite validation rules
    - Field-level and entity-level validation
    - Comprehensive error reporting with context
    - Async validation support for repository checks
    - Integration with command and query handlers
    - Custom validator creation and composition

Examples:
    ```python
    from neuroglia.validation import BusinessRule, ValidationResult, rule, when

    # Simple business rule
    class MinimumAgeRule(BusinessRule[User]):
        def __init__(self, minimum_age: int = 18):
            super().__init__("minimum_age", f"User must be at least {minimum_age} years old")
            self.minimum_age = minimum_age

        def is_satisfied_by(self, user: User) -> bool:
            return user.age >= self.minimum_age

    # Validation in command handlers
    class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
        async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
            validation_result = await BusinessRuleValidator.validate_async([
                MinimumAgeRule()
            ], command)

            if not validation_result.is_valid:
                return self.bad_request(
                    "Validation failed",
                    validation_result.get_field_errors()
                )

            # Process valid command
            user = User(command.name, command.email, command.age)
            await self.user_repository.save_async(user)
            return self.ok(self.mapper.map(user, UserDto))
    ```

See Also:
    - Enhanced Model Validation: https://bvandewe.github.io/pyneuro/features/enhanced-model-validation/
    - Business Rules Guide: https://bvandewe.github.io/pyneuro/patterns/
    - CQRS Integration: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
"""

from .business_rules import BusinessRule, BusinessRuleValidator
from .business_rules import ValidationError as ValidationError
from .business_rules import ValidationResult, conditional_rule, rule, when
from .exceptions import (
    BusinessRuleViolationException,
    ConditionalValidationException,
    ValidationException,
)
from .validators import (
    CompositeValidator,
    EntityValidator,
    PropertyValidator,
    ValidatorBase,
    custom_validator,
    email_format,
    max_length,
    min_length,
    numeric_range,
    required,
    validate_with,
)

__all__ = [
    # Business Rules
    "BusinessRule",
    "BusinessRuleValidator",
    "ValidationResult",
    "ValidationError",
    "rule",
    "conditional_rule",
    "when",
    # Validators
    "ValidatorBase",
    "PropertyValidator",
    "EntityValidator",
    "CompositeValidator",
    "validate_with",
    "required",
    "min_length",
    "max_length",
    "email_format",
    "numeric_range",
    "custom_validator",
    # Exceptions
    "ValidationException",
    "BusinessRuleViolationException",
    "ConditionalValidationException",
]
