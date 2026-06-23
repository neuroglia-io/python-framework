# Domain-Driven Design Pattern Test Suite

## Overview

This comprehensive test suite demonstrates the implementation and testing of Domain-Driven Design patterns in the Neuroglia framework, covering both **traditional CRUD** and **event-sourced persistence** approaches.

## Test Coverage Summary

### ✅ 32 Tests Passing - Complete Coverage

The test suite provides comprehensive coverage of DDD patterns and includes:

## 🎯 Test Categories

### 1. **Domain Entity Behavior** (10 tests)

- **Event-Sourced Aggregates**: `BankAccount` with business rules and event generation
- **Traditional Entities**: `Customer` with property validation and business logic
- **Business Rule Enforcement**: Comprehensive validation across all operations
- **State Management**: Both event-driven and property-based state handling

### 2. **Value Objects** (4 tests)

- **Immutable Value Objects**: `Money` and `AccountNumber` with validation
- **Arithmetic Operations**: Currency-aware money calculations
- **Validation Rules**: Type safety and business constraints
- **Immutability Enforcement**: Protection against state mutation

### 3. **Event Application & State Reconstruction** (4 tests)

- **Multiple Dispatch Pattern**: Event application using `@dispatch` decorators
- **State Reconstruction**: Building aggregate state from event streams
- **Event Ordering**: Maintaining consistency through ordered event application
- **Consistency Enforcement**: Aggregate invariants and business rules

### 4. **Traditional Repository Pattern** (3 tests)

- **CRUD Operations**: Create, Read, Update, Delete with traditional entities
- **DTO Mapping**: Domain entity to data transfer object transformations
- **Business Rule Preservation**: Validation enforcement at persistence boundaries
- **Mock Repository Testing**: Isolation of domain logic from infrastructure

### 5. **Event Sourcing Repository Pattern** (3 tests)

- **Event Stream Persistence**: Storing and retrieving events for aggregates
- **Aggregate Reconstruction**: Rebuilding domain objects from event history
- **Event Store Integration**: Working with event-sourced persistence mechanisms
- **State Consistency**: Ensuring aggregate state matches event stream

### 6. **Domain Services** (4 tests)

- **Cross-Aggregate Operations**: Coordinating between multiple aggregates
- **Transaction Coordination**: Managing consistency across aggregate boundaries
- **Business Logic Orchestration**: Complex workflows spanning multiple domains
- **Error Handling**: Comprehensive validation and exception management

### 7. **Integration Testing** (4 tests)

- **Mixed Persistence Patterns**: Traditional and event-sourced entities working together
- **End-to-End Workflows**: Complete business scenarios from start to finish
- **Aggregate Boundary Enforcement**: Ensuring proper separation of concerns
- **Business Rule Consistency**: Validation across different persistence approaches

## 🏗️ Architecture Patterns Demonstrated

### Event-Sourced Aggregates

```python
class BankAccount(AggregateRoot[BankAccountState, str]):
    """Event-sourced aggregate with business rules and event generation"""

    def deposit(self, amount: Decimal, description: str):
        # Business rule validation
        if self.is_closed:
            raise ValueError("Cannot deposit into a closed account")

        # Event generation
        event = MoneyDepositedEvent(self.id(), amount, description)
        self.state.on(self.register_event(event))
```

### Traditional Entities

```python
class Customer(Entity[str]):
    """Traditional entity with property validation"""

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        if "@" not in value:
            raise ValueError("Invalid email format")
        self._email = value.strip().lower()
```

### Multiple Dispatch Event Application

```python
class BankAccountState(AggregateState[str]):
    """State reconstruction using multiple dispatch"""

    @dispatch(MoneyDepositedEvent)
    def on(self, event: MoneyDepositedEvent):
        self.balance += event.amount
        self.transaction_count += 1

    @dispatch(MoneyWithdrawnEvent)
    def on(self, event: MoneyWithdrawnEvent):
        self.balance -= event.amount
        self.transaction_count += 1
```

### Domain Services

```python
class BankingDomainService:
    """Cross-aggregate business operations"""

    async def transfer_funds(self, from_account_id: str, to_account_id: str,
                           amount: Decimal) -> bool:
        # Load aggregates
        from_account = await self.account_repository.get_async(from_account_id)
        to_account = await self.account_repository.get_async(to_account_id)

        # Coordinate transaction
        from_account.withdraw(amount, f"Transfer to {to_account_id}")
        to_account.deposit(amount, f"Transfer from {from_account_id}")

        # Persist changes
        await self.account_repository.update_async(from_account)
        await self.account_repository.update_async(to_account)
```

## 🧪 Testing Strategies Covered

### 1. **Unit Testing**

- **Business Logic Isolation**: Testing domain rules without infrastructure
- **Mock Dependencies**: Using mocks for repositories and external services
- **Edge Case Coverage**: Boundary conditions and error scenarios
- **State Validation**: Ensuring correct state transitions

### 2. **Integration Testing**

- **End-to-End Workflows**: Complete business scenarios
- **Repository Integration**: Testing with actual persistence patterns
- **Cross-Aggregate Operations**: Domain services coordinating multiple entities
- **Mixed Pattern Integration**: Traditional and event-sourced entities together

### 3. **Behavior-Driven Testing**

- **Business Rule Validation**: Testing domain constraints and invariants
- **Event Sequence Testing**: Verifying correct event ordering and application
- **State Reconstruction**: Ensuring aggregates rebuild correctly from events
- **Consistency Enforcement**: Testing aggregate boundary protection

## 🎨 Key Testing Patterns

### Arrange-Act-Assert (AAA)

```python
def test_bank_account_deposit_success(self):
    # Arrange
    account = BankAccount("John Doe", Decimal('100'))
    deposit_amount = Decimal('50.25')

    # Act
    account.deposit(deposit_amount, "Salary deposit")

    # Assert
    assert account.balance == Decimal('150.25')
    assert len(account._pending_events) == 2  # Open + Deposit
```

### Mock Repository Pattern

```python
@pytest.fixture
def mock_repository(self):
    repository = Mock(spec=Repository[Customer, str])
    repository.add_async = AsyncMock()
    repository.get_async = AsyncMock()
    return repository
```

### Event Verification

```python
def test_event_generation(self):
    account = BankAccount("Test User", Decimal('100'))
    account.deposit(Decimal('50'), "Test deposit")

    events = account._pending_events
    deposit_event = next(e for e in events if isinstance(e, MoneyDepositedEvent))
    assert deposit_event.amount == Decimal('50')
    assert deposit_event.description == "Test deposit"
```

## 🚀 Running the Tests

```bash
# Run all DDD pattern tests
pytest tests/cases/test_domain_driven_design_patterns.py -v

# Run specific test categories
pytest tests/cases/test_domain_driven_design_patterns.py::TestDomainEntityBehavior -v
pytest tests/cases/test_domain_driven_design_patterns.py::TestEventSourcingRepositoryPattern -v
pytest tests/cases/test_domain_driven_design_patterns.py::TestDomainServices -v

# Run with coverage
pytest tests/cases/test_domain_driven_design_patterns.py --cov=neuroglia --cov-report=html
```

## 📚 Educational Value

This test suite serves as:

1. **Reference Implementation**: Complete examples of DDD patterns in Neuroglia
2. **Learning Resource**: Step-by-step progression from simple to complex patterns
3. **Testing Guide**: Best practices for testing domain-driven code
4. **Framework Documentation**: Real-world usage of Neuroglia's DDD abstractions
5. **Quality Assurance**: Comprehensive validation of business logic and patterns

## 🔗 Related Documentation

- [Domain-Driven Design Patterns](../docs/patterns/domain-driven-design.md)
- [Event Sourcing Guide](../docs/features/event-sourcing.md)
- [Repository Pattern](../docs/features/data-access.md)
- [Testing Best Practices](../docs/testing/best-practices.md)

---

**Note**: This test suite demonstrates both traditional CRUD and event-sourced persistence patterns,
showcasing how the Neuroglia framework supports multiple architectural approaches within the same application while maintaining clean domain-driven design principles.
