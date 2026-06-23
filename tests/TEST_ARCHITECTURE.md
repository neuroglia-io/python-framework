# Test Architecture for Neuroglia Framework

## Overview

This document defines the comprehensive test organization for the Neuroglia framework and sample applications. Tests are organized by architectural layer with clear separation of concerns and progressive complexity from unit tests to end-to-end integration tests.

## Test Organization Principles

### 1. Layered Test Structure

Tests mirror the framework's clean architecture layers:

- **Domain Layer Tests**: Pure business logic, entities, value objects, domain events
- **Application Layer Tests**: Commands, queries, handlers, services, pipeline behaviors
- **API Layer Tests**: Controllers, routing, request/response handling, DTOs
- **Integration Layer Tests**: Repositories, external services, serialization, caching
- **End-to-End Tests**: Complete workflows across all layers

### 2. Test Classification

- **Unit Tests** (`tests/unit/`): Test individual components in isolation with mocked dependencies
- **Integration Tests** (`tests/integration/`): Test component interactions with real dependencies (databases, services)
- **Functional Tests** (`tests/cases/`): Test specific framework features and capabilities
- **End-to-End Tests** (`tests/e2e/`): Test complete user scenarios across all layers

### 3. Test Data Strategy

- Use **Mario's Pizzeria domain** as primary test data source for framework tests
- Create **realistic, business-meaningful test scenarios** (orders, customers, pizzas, kitchen operations)
- Maintain **test data factories** in fixtures for consistency
- Separate **state from behavior** following aggregate pattern

## Framework Test Structure (`./tests/`)

```
tests/
├── conftest.py                    # Global fixtures and configuration
├── TEST_ARCHITECTURE.md          # This document
├── fixtures/                      # Shared test data and factories
│   ├── __init__.py
│   ├── domain_fixtures.py         # Entities, value objects, events
│   ├── application_fixtures.py    # Commands, queries, handlers
│   ├── integration_fixtures.py    # Repositories, services
│   └── test_data.py              # Mario's Pizzeria test data
├── unit/                          # Isolated component tests
│   ├── test_dependency_injection.py
│   ├── test_mediation.py
│   ├── test_mapping.py
│   ├── test_serialization.py
│   └── test_validation.py
├── integration/                   # Component interaction tests
│   ├── test_repository_patterns.py
│   ├── test_event_sourcing.py
│   ├── test_cache_integration.py
│   └── test_http_client_integration.py
├── domain/                        # Domain layer tests
│   ├── test_aggregate_root.py
│   ├── test_entities.py
│   ├── test_value_objects.py
│   └── test_domain_events.py
├── application/                   # Application layer tests
│   ├── test_mediator.py
│   ├── test_command_handlers.py
│   ├── test_query_handlers.py
│   └── test_pipeline_behaviors.py
├── api/                          # API layer tests
│   ├── test_controllers.py
│   ├── test_routing.py
│   └── test_request_validation.py
├── infrastructure/               # Infrastructure tests
│   ├── test_mongo_repository.py
│   ├── test_filesystem_repository.py
│   ├── test_event_store.py
│   └── test_cache_repository.py
└── e2e/                          # End-to-end tests
    ├── test_complete_order_workflow.py
    ├── test_customer_journey.py
    └── test_event_driven_scenarios.py
```

## Sample Application Test Structure (`samples/mario-pizzeria/tests/`)

```
samples/mario-pizzeria/tests/
├── conftest.py                    # Sample-specific fixtures
├── __init__.py
├── domain/                        # Domain tests
│   ├── test_pizza_entity.py
│   ├── test_order_entity.py
│   ├── test_customer_entity.py
│   ├── test_kitchen_entity.py
│   └── test_business_rules.py
├── application/                   # Application tests
│   ├── commands/
│   │   ├── test_place_order_handler.py
│   │   ├── test_update_order_status_handler.py
│   │   └── test_pizza_management_handlers.py
│   ├── queries/
│   │   ├── test_order_queries.py
│   │   ├── test_menu_queries.py
│   │   └── test_kitchen_queries.py
│   └── test_event_handlers.py
├── api/                          # API tests
│   ├── test_orders_controller.py
│   ├── test_menu_controller.py
│   ├── test_kitchen_controller.py
│   ├── test_auth_controller.py
│   └── test_profile_controller.py
├── integration/                  # Integration tests
│   ├── test_order_repository.py
│   ├── test_customer_repository.py
│   ├── test_payment_service.py
│   └── test_event_publishing.py
└── e2e/                          # End-to-end tests
    ├── test_complete_order_flow.py
    ├── test_kitchen_workflow.py
    └── test_delivery_workflow.py
```

## Test Naming Conventions

### Test Files

- `test_<feature>.py` - Feature-specific tests
- `test_<entity>_<action>.py` - Entity action tests
- `test_<layer>_<component>.py` - Layer component tests

### Test Classes

- `Test<ClassName>` - Matches the class being tested
- `Test<Feature>` - Feature test suite
- `Test<Scenario>Workflow` - End-to-end scenario tests

### Test Methods

- `test_<method>_<scenario>` - Unit tests
- `test_<action>_<expected_outcome>` - Behavior tests
- `test_<scenario>_raises_<exception>` - Error cases
- `test_<workflow>_end_to_end` - E2E tests

## Test Documentation Requirements

Every test must include comprehensive docstrings with:

```python
"""
<One-line test intent>

<Detailed explanation of what is being tested and why>

Expected Behavior:
    - <Specific expected outcome 1>
    - <Specific expected outcome 2>

Test Coverage:
    - <Component/method being tested>
    - <Scenario being validated>

Related Documentation:
    - [Feature Guide](../docs/features/feature.md)
    - [Pattern Guide](../docs/patterns/pattern.md)

References:
    - Framework Module: neuroglia.<module>.<class>
    - Sample Implementation: samples/mario-pizzeria/<layer>/<file>
"""
```

## Test Data Principles

### Use Realistic Business Scenarios

❌ **Bad**: Generic test data

```python
entity = SomeEntity("test_id", "test_value", 123)
```

✅ **Good**: Mario's Pizzeria-inspired test data

```python
pizza = Pizza(
    name="Margherita",
    base_price=Decimal("12.99"),
    size=PizzaSize.MEDIUM,
    toppings=["mozzarella", "basil", "tomato"]
)
```

### Test Data Factories

Use fixtures and factories for consistent test data:

```python
@pytest.fixture
def margherita_pizza():
    """Create a standard Margherita pizza for testing"""
    return create_pizza(
        name="Margherita",
        base_price=Decimal("12.99"),
        size=PizzaSize.MEDIUM
    )

@pytest.fixture
def typical_order(margherita_pizza):
    """Create a typical customer order"""
    return create_order(
        customer_name="John Doe",
        pizzas=[margherita_pizza],
        address="123 Main St"
    )
```

## Tests to Remove/Refactor

The following tests validate bug fixes rather than functionality and should be refactored:

1. `test_enum_serialization_fix.py` → Merge into `test_serialization.py`
2. `test_controller_routing_fix.py` → Merge into `test_routing.py`
3. `test_cache_repository_pattern_search_fix.py` → Merge into `test_cache_repository.py`
4. `test_type_variable_substitution.py` → Merge into `test_dependency_injection.py`
5. `test_string_annotation_error_handling.py` → Merge into `test_service_provider.py`

These tests contain valuable validation logic that should be preserved as functional tests, not fix-specific tests.

## Coverage Requirements

- **Minimum Coverage**: 90% for all production code
- **Domain Layer**: 95%+ (critical business logic)
- **Application Layer**: 90%+ (command/query handlers)
- **API Layer**: 85%+ (controllers and routing)
- **Integration Layer**: 85%+ (repositories and services)

## Test Execution Strategy

### Local Development

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -m integration -v

# Run with coverage
pytest --cov=src/neuroglia --cov-report=html --cov-report=term
```

### CI/CD Pipeline

```bash
# Fast feedback (unit + functional tests)
pytest tests/unit/ tests/domain/ tests/application/ -v

# Full validation (includes integration and E2E)
pytest tests/ -v --cov=src/neuroglia --cov-report=xml
```

## Best Practices

### 1. Test Isolation

- Each test must be independent
- No shared mutable state between tests
- Use fixtures for setup/teardown

### 2. Arrange-Act-Assert Pattern

```python
def test_pizza_calculates_total_price():
    # Arrange
    pizza = Pizza("Margherita", Decimal("12.99"), PizzaSize.MEDIUM)
    pizza.add_topping("extra_cheese")

    # Act
    total = pizza.total_price

    # Assert
    assert total == Decimal("14.49")  # base + topping
```

### 3. Test Meaningful Scenarios

Focus on business value, not implementation details

### 4. Mock External Dependencies

Use mocks for external services, real implementations for framework components

### 5. Comprehensive Error Testing

Test both success and failure paths, including edge cases

## References

- [Neuroglia Documentation](../docs/)
- [Testing Best Practices](../docs/guides/testing-setup.md)
- [Clean Architecture](../docs/patterns/clean-architecture.md)
- [Mario's Pizzeria Sample](../samples/mario-pizzeria/)
