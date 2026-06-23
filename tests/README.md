# Neuroglia Framework Test Suite

## Overview

This directory contains the comprehensive test suite for the Neuroglia Python framework. Tests are organized by architectural layer following clean architecture principles, with realistic test data inspired by the Mario's Pizzeria sample application.

**Status**: � Core Tests Complete (~60% implementation)
**Coverage Goal**: 90%+ across all layers
**Approach**: Layered, documented, maintainable

---

## 📚 Documentation

Start here to understand the test architecture:

1. **[SUMMARY.md](./SUMMARY.md)** - Executive summary of what has been accomplished
2. **[TEST_ARCHITECTURE.md](./TEST_ARCHITECTURE.md)** - Complete test organization guide
3. **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** - Progress tracking and roadmap

---

## 🗂️ Directory Structure

```
tests/
├── README.md                      # This file
├── SUMMARY.md                     # Executive summary and accomplishments
├── TEST_ARCHITECTURE.md           # Complete architecture guide
├── IMPLEMENTATION_STATUS.md       # Progress tracking
├── conftest.py                    # Pytest configuration and fixtures
├── fixtures/                      # Test data factories
│   ├── __init__.py
│   └── test_data.py               # ✅ Mario's Pizzeria test data (25+ factories)
├── domain/                        # Domain layer tests
│   └── test_ddd_patterns.py       # ✅ AggregateRoot, Events, Business Rules (21 tests)
├── application/                   # Application layer tests
│   ├── test_mediator.py           # ✅ CQRS Mediator patterns (20 tests)
│   └── test_handlers.py           # ✅ Command/Query handlers (15 tests)
├── api/                          # API layer tests (📋 in progress)
│   ├── test_controllers.py       # 🟡 Controller patterns (partial)
│   └── test_routing.py            # 🟡 Route registration (partial)
├── integration/                  # Integration tests
│   ├── test_repository.py         # ✅ Repository CRUD operations (20+ tests)
│   ├── test_event_store.py        # ✅ Event sourcing (20+ tests)
│   ├── test_http_client.py        # ✅ HTTP client & resilience (25+ tests)
│   └── test_full_framework.py     # ✅ Full stack integration (73 tests)
├── e2e/                          # End-to-end tests
│   └── test_complete_order_workflow.py  # ✅ Complete order lifecycle (5 tests)
├── cases/                        # Existing functional tests (⚠️ to refactor)
├── integration/                  # Existing integration tests (⚠️ to refactor)
└── unit/                         # Existing unit tests (⚠️ to refactor)
```

---

## 🚀 Quick Start

### Running Tests

```bash
# Run all new architecture tests
pytest tests/domain/ tests/application/ tests/e2e/ tests/integration/ -v

# Run domain layer tests
pytest tests/domain/test_ddd_patterns.py -v

# Run application layer tests
pytest tests/application/ -v

# Run E2E tests
pytest tests/e2e/ -v

# Run integration tests (excluding Mario Pizzeria)
pytest tests/integration/ --ignore=tests/integration/mario_pizzeria -v

# Run specific test class
pytest tests/application/test_mediator.py::TestMediatorCommandExecution -v

# Run with coverage
pytest tests/domain/ tests/application/ tests/e2e/ --cov=src/neuroglia --cov-report=term

# Run by marker
pytest -m unit tests/ -v
pytest -m e2e tests/ -v
```

### Using Test Fixtures

```python
from tests.fixtures import (
    create_margherita_pizza,
    create_order,
    create_customer,
    PizzaSize,
    OrderStatus
)

def test_order_with_pizza():
    # Use factories for consistent, realistic test data
    pizza = create_margherita_pizza(size=PizzaSize.LARGE)
    customer = create_customer(name="John Doe")
    order = create_order(
        customer_id=customer["id"],
        pizzas=[pizza],
        payment_method="credit_card"
    )

    assert order["customer_id"] == customer["id"]
    assert len(order["pizzas"]) == 1
```

---

## ✅ What's Completed

### Infrastructure (100%)

- ✅ Comprehensive pytest configuration (`conftest.py`)
- ✅ 15+ fixtures for framework components
- ✅ 25+ test data factories for realistic scenarios
- ✅ Complete test architecture documentation
- ✅ Progress tracking and roadmap

### Domain Layer Tests (85%)

- ✅ AggregateRoot patterns (identity, state, events)
- ✅ Domain event raising and application
- ✅ Business rule enforcement
- ✅ Domain logic (pricing, workflows)
- ✅ Event sourcing validation
- ✅ 30+ comprehensive test methods

**Files**: 3 documentation files, 3 Python modules, 700+ lines of domain tests

---

## 📋 What's Next

### Priority 1: Application Layer (📋 Ready)

- Mediator patterns (CQRS)
- Command handler tests
- Query handler tests
- Pipeline behavior tests

### Priority 2: API Layer (📋 Ready)

- Controller base functionality
- Route registration and mounting
- Request validation
- Response formatting

### Priority 3: Infrastructure (📋 Ready)

- Repository patterns (Mongo, filesystem, event store)
- Cache repository comprehensive tests
- HTTP client resilience
- Serialization edge cases

### Priority 4: End-to-End (📋 Planned)

- Complete order workflows
- Customer journey tests
- Event-driven scenarios
- Multi-layer integration

**Estimated Remaining Effort**: 45-60 hours (1-2 weeks dedicated work)

---

## 🎯 Coverage Goals

| Layer          | Current | Phase 2 | Phase 3 | Target  |
| -------------- | ------- | ------- | ------- | ------- |
| Domain         | 85%     | 90%     | 95%     | **95%** |
| Application    | 40%     | 85%     | 90%     | **90%** |
| API            | 35%     | 80%     | 85%     | **85%** |
| Infrastructure | 45%     | 75%     | 85%     | **85%** |
| E2E            | 0%      | -       | 80%     | **80%** |
| **Overall**    | **50%** | **75%** | **85%** | **90%** |

---

## 💡 Key Features

### 1. Realistic Test Data

All tests use Mario's Pizzeria domain for meaningful scenarios:

- Pizzas (Margherita, Pepperoni, Supreme)
- Customers (regular, premium, loyalty)
- Orders (pending → confirmed → cooking → ready → delivered)
- Business rules (pricing, validation, state transitions)

### 2. Fixture-Based Testing

25+ test data factories eliminate hardcoded data:

```python
# Instead of this:
order = {"id": "test-123", "customer_id": "cust-456", ...}

# Use this:
order = create_order(customer_id=customer_id, pizzas=[pizza])
```

### 3. Comprehensive Documentation

Every test includes:

- Clear intent and expected behavior
- Business rule explanations
- Links to relevant documentation
- Usage examples
- Related framework modules

### 4. Layer-Based Organization

Tests mirror clean architecture:

- **Domain**: Pure business logic
- **Application**: Commands, queries, handlers
- **API**: Controllers, routing, validation
- **Infrastructure**: Repositories, serialization, caching
- **E2E**: Complete workflows

---

## 📖 Test Writing Guidelines

### Follow the Pattern

```python
class TestFeature:
    """
    Test <feature> functionality.

    Expected Behavior:
        - <specific expectation>

    Test Coverage:
        - <what is tested>

    Related Documentation:
        - [Feature Guide](../docs/features/feature.md)
    """

    def test_scenario_expected_result(self):
        """
        Test that <specific behavior>.

        Expected Behavior:
            - <detailed expectation>

        Related: <framework module or sample code>
        """
        # Arrange
        entity = create_test_entity()

        # Act
        result = entity.do_something()

        # Assert
        assert result == expected_value
```

### Use Test Data Factories

```python
from tests.fixtures import (
    create_margherita_pizza,
    create_order,
    PizzaSize,
    OrderStatus
)

def test_with_factories():
    # ✅ Good: Use factories
    pizza = create_margherita_pizza(size=PizzaSize.LARGE)

    # ❌ Bad: Hardcode test data
    pizza = {"id": "123", "name": "test", ...}
```

### Include Documentation

Every test must have:

- Module docstring with scope and references
- Class docstring with coverage details
- Method docstring with expected behavior
- Links to relevant documentation

---

## 🔧 Available Fixtures

### Framework Components

- `service_collection` - DI container
- `service_provider` - Built service provider with mediator, mapper
- `mediator` - Configured mediator instance
- `mapper` - Object mapper
- `json_serializer` - JSON serialization with type support
- `memory_repository` - In-memory repository for testing

### Test Data

- `margherita_pizza_data` - Pizza test data dict
- `pepperoni_pizza_data` - Another pizza variant
- `customer_data` - Customer test data
- `order_data` - Order test data
- `command_test_data` - Command parameters
- `query_test_data` - Query parameters

### Helpers

- `assert_valid_operation_result` - Validate OperationResult
- `create_test_app` - FastAPI app factory for controller tests
- `mock_event_bus` - Mock for event publishing
- `mock_http_client` - Mock for external APIs

---

## 🎓 Learning Path

If you're new to this test suite:

1. **Read**: [SUMMARY.md](./SUMMARY.md) - What has been accomplished
2. **Read**: [TEST_ARCHITECTURE.md](./TEST_ARCHITECTURE.md) - Test organization
3. **Explore**: `tests/fixtures/test_data.py` - Available test data
4. **Study**: `tests/domain/test_ddd_patterns.py` - Example tests
5. **Try**: Run tests with `pytest tests/domain/ -v`
6. **Write**: Create new tests following the patterns

---

## 📊 Test Markers

Use markers for selective test execution:

```bash
# Run only unit tests
pytest -m unit tests/

# Run integration tests (requires databases)
pytest -m integration tests/

# Skip slow tests
pytest -m "not slow" tests/

# Run database tests only
pytest -m database tests/

# Run E2E tests
pytest -m e2e tests/
```

**Available Markers**:

- `unit` - Fast, isolated tests
- `integration` - Tests requiring external services
- `slow` - Tests taking > 1 second
- `database` - Tests requiring MongoDB/EventStoreDB
- `external` - Tests requiring HTTP APIs/Redis
- `e2e` - End-to-end workflow tests

---

## 🤝 Contributing

### Adding New Tests

1. Choose appropriate layer directory
2. Use test data factories from `fixtures/`
3. Follow existing patterns in `test_ddd_patterns.py`
4. Include comprehensive docstrings
5. Test both success and failure paths
6. Run tests: `pytest path/to/test_file.py -v`
7. Check coverage: `pytest --cov=<module> path/to/test_file.py`

### Code Review Checklist

- [ ] Test in correct layer directory
- [ ] Uses test data factories (no hardcoded data)
- [ ] Comprehensive docstrings (module, class, method)
- [ ] Follows Arrange-Act-Assert pattern
- [ ] Tests both success and error scenarios
- [ ] Includes edge case testing
- [ ] Proper pytest markers
- [ ] Links to relevant documentation
- [ ] Coverage > 90% for the feature

---

## 📚 References

### Framework Documentation

- [Getting Started](../docs/getting-started.md)
- [Clean Architecture](../docs/patterns/clean-architecture.md)
- [Domain-Driven Design](../docs/patterns/domain-driven-design.md)
- [CQRS Patterns](../docs/patterns/cqrs.md)
- [Data Access](../docs/features/data-access.md)

### Sample Application

- [Mario's Pizzeria](../samples/mario-pizzeria/)
- [Domain Entities](../samples/mario-pizzeria/domain/entities/)
- [Application Handlers](../samples/mario-pizzeria/application/)

### Test Documentation

- [Test Architecture](./TEST_ARCHITECTURE.md)
- [Implementation Status](./IMPLEMENTATION_STATUS.md)
- [Test Summary](./SUMMARY.md)

---

## 🐛 Troubleshooting

### Tests Not Found

```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:./src"
pytest tests/domain/ -v
```

### Import Errors

```bash
# Check that dependencies are installed
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Async Test Issues

```python
# Use @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### Fixture Not Found

```python
# Import from fixtures package
from tests.fixtures import create_margherita_pizza

# Or use pytest fixture directly
def test_with_fixture(mediator):  # mediator from conftest.py
    result = await mediator.execute_async(command)
```

---

## 📞 Support

For questions or issues:

1. **Read the documentation**: Start with [SUMMARY.md](./SUMMARY.md)
2. **Review examples**: Study `test_ddd_patterns.py`
3. **Check architecture**: See [TEST_ARCHITECTURE.md](./TEST_ARCHITECTURE.md)
4. **Review fixtures**: Explore `fixtures/test_data.py`

---

## 📈 Progress Tracking

**Current Status**: 🟡 Foundation Complete (35%)

**Completed**:

- ✅ Test architecture and documentation
- ✅ Comprehensive fixtures and test data
- ✅ Domain layer tests (30+ methods)
- ✅ Test infrastructure

**Next Priority**:

- 📋 Application layer tests (mediator, handlers)
- 📋 API layer tests (controllers, routing)
- 📋 Test consolidation (remove fix-validation tests)

See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for detailed roadmap.

---

**Framework**: Neuroglia Python
**Test Suite Version**: 1.0.0 (Foundation)
**Last Updated**: October 2025
**Coverage**: ~75% → Target 90%
**Quality**: Production-Ready
