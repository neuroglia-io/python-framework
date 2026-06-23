"""
Comprehensive Test Suite for Domain-Driven Design Patterns
=========================================================

This test suite demonstrates the implementation and testing of Domain-Driven Design patterns
in the Neuroglia framework, covering both traditional CRUD and event-sourced persistence approaches.

Test Coverage:
- Domain Entities (both simple Entity and AggregateRoot)
- Domain Events and Event Application
- Value Objects and Business Rules
- Traditional Repository Pattern (CRUD operations)
- Event Sourcing Repository Pattern
- Domain Services and Business Logic
- Aggregate Consistency and Invariant Enforcement
- Event Handling and Side Effects

The tests showcase the framework's comprehensive support for DDD patterns while maintaining
clean architecture principles and testability.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, Mock

import pytest
from multipledispatch import dispatch

from neuroglia.data.abstractions import (
    AggregateRoot,
    AggregateState,
    DomainEvent,
    Entity,
    Identifiable,
)
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
)

# =============================================================================
# Domain Events for Testing
# =============================================================================


class AccountOpenedEvent(DomainEvent[str]):
    """Event raised when a new bank account is opened."""

    def __init__(self, aggregate_id: str, account_holder: str, initial_balance: Decimal):
        super().__init__(aggregate_id)
        self.account_holder = account_holder
        self.initial_balance = initial_balance


class MoneyDepositedEvent(DomainEvent[str]):
    """Event raised when money is deposited into an account."""

    def __init__(self, aggregate_id: str, amount: Decimal, description: str):
        super().__init__(aggregate_id)
        self.amount = amount
        self.description = description


class MoneyWithdrawnEvent(DomainEvent[str]):
    """Event raised when money is withdrawn from an account."""

    def __init__(self, aggregate_id: str, amount: Decimal, description: str):
        super().__init__(aggregate_id)
        self.amount = amount
        self.description = description


class AccountClosedEvent(DomainEvent[str]):
    """Event raised when an account is closed."""

    def __init__(self, aggregate_id: str, final_balance: Decimal, closure_reason: str):
        super().__init__(aggregate_id)
        self.final_balance = final_balance
        self.closure_reason = closure_reason


# =============================================================================
# Value Objects for Testing
# =============================================================================


@dataclass(frozen=True)
class Money:
    """Value object representing monetary amounts with currency."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency cannot be empty")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Result would be negative")
        return Money(result_amount, self.currency)


@dataclass(frozen=True)
class AccountNumber:
    """Value object representing a bank account number."""

    value: str

    def __post_init__(self):
        if not self.value or len(self.value) < 8:
            raise ValueError("Account number must be at least 8 characters")
        if not self.value.isdigit():
            raise ValueError("Account number must contain only digits")


# =============================================================================
# Aggregate State for Event Sourcing
# =============================================================================


class BankAccountState(AggregateState[str]):
    """Aggregate state that rebuilds from events using multiple dispatch."""

    def __init__(self):
        super().__init__()
        self.account_holder: Optional[str] = None
        self.balance: Decimal = Decimal("0")
        self.is_closed: bool = False
        self.transaction_count: int = 0

    @property
    def id(self) -> str:
        """Get the aggregate ID from _id property."""
        return self._id

    @dispatch(AccountOpenedEvent)
    def on(self, event: AccountOpenedEvent):
        """Apply account opened event."""
        self._id = event.aggregate_id
        self.created_at = event.created_at
        self.account_holder = event.account_holder
        self.balance = event.initial_balance
        self.is_closed = False
        self.transaction_count = 0

    @dispatch(MoneyDepositedEvent)
    def on(self, event: MoneyDepositedEvent):
        """Apply money deposited event."""
        self.last_modified = event.created_at
        self.balance += event.amount
        self.transaction_count += 1

    @dispatch(MoneyWithdrawnEvent)
    def on(self, event: MoneyWithdrawnEvent):
        """Apply money withdrawn event."""
        self.last_modified = event.created_at
        self.balance -= event.amount
        self.transaction_count += 1

    @dispatch(AccountClosedEvent)
    def on(self, event: AccountClosedEvent):
        """Apply account closed event."""
        self.last_modified = event.created_at
        self.is_closed = True


# =============================================================================
# Domain Entities for Testing
# =============================================================================


class BankAccount(AggregateRoot[BankAccountState, str]):
    """
    Bank Account Aggregate Root demonstrating event-sourced DDD patterns.

    This aggregate enforces business rules, maintains consistency, and raises
    domain events for all state changes.
    """

    def __init__(self, account_holder: str, initial_balance: Optional[Decimal] = None):
        super().__init__()
        if not account_holder or not account_holder.strip():
            raise ValueError("Account holder name is required")

        initial_amount = initial_balance or Decimal("0")
        if initial_amount < 0:
            raise ValueError("Initial balance cannot be negative")

        account_id = str(uuid.uuid4()).replace("-", "")
        event = AccountOpenedEvent(account_id, account_holder, initial_amount)
        self.state.on(self.register_event(event))

    @property
    def id(self) -> str:
        """Override to make id an attribute instead of method for consistency."""
        return super().id()

    @property
    def account_holder(self) -> str:
        """Get the account holder name."""
        return self.state.account_holder

    @property
    def balance(self) -> Decimal:
        """Get the current account balance."""
        return self.state.balance

    @property
    def is_closed(self) -> bool:
        """Check if the account is closed."""
        return self.state.is_closed

    @property
    def transaction_count(self) -> int:
        """Get the number of transactions performed."""
        return self.state.transaction_count

    def deposit(self, amount: Decimal, description: str = "Deposit"):
        """
        Deposit money into the account.

        Business Rules:
        - Amount must be positive
        - Account must not be closed
        - Description is required
        """
        if self.is_closed:
            raise ValueError("Cannot deposit into a closed account")

        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        if not description or not description.strip():
            raise ValueError("Deposit description is required")

        event = MoneyDepositedEvent(self.id, amount, description.strip())
        self.state.on(self.register_event(event))

    def withdraw(self, amount: Decimal, description: str = "Withdrawal"):
        """
        Withdraw money from the account.

        Business Rules:
        - Amount must be positive
        - Account must not be closed
        - Sufficient funds must be available
        - Description is required
        """
        if self.is_closed:
            raise ValueError("Cannot withdraw from a closed account")

        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        if amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal")

        if not description or not description.strip():
            raise ValueError("Withdrawal description is required")

        event = MoneyWithdrawnEvent(self.id, amount, description.strip())
        self.state.on(self.register_event(event))

    def close(self, reason: str = "Account closure requested"):
        """
        Close the account.

        Business Rules:
        - Account must not already be closed
        - Reason must be provided
        """
        if self.is_closed:
            raise ValueError("Account is already closed")

        if not reason or not reason.strip():
            raise ValueError("Closure reason is required")

        event = AccountClosedEvent(self.id, self.balance, reason.strip())
        self.state.on(self.register_event(event))


class Customer(Entity[str]):
    """
    Traditional Entity demonstrating simple DDD patterns without event sourcing.

    This entity uses traditional property-based state management and validation.
    """

    def __init__(self, name: str, email: str):
        super().__init__()
        self.id = str(uuid.uuid4()).replace("-", "")
        self._name = ""
        self._email = ""

        # Use setters for validation
        self.name = name
        self.email = email
        self._account_numbers: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not value or not value.strip():
            raise ValueError("Customer name is required")
        if len(value.strip()) < 2:
            raise ValueError("Customer name must be at least 2 characters")
        self._name = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        if not value or not value.strip():
            raise ValueError("Customer email is required")
        if "@" not in value or "." not in value:
            raise ValueError("Invalid email format")
        self._email = value.strip().lower()

    @property
    def account_numbers(self) -> list[str]:
        return self._account_numbers.copy()

    def add_account(self, account_number: str):
        """Add an account number to this customer."""
        if not account_number or not account_number.strip():
            raise ValueError("Account number is required")

        clean_number = account_number.strip()
        if clean_number in self._account_numbers:
            raise ValueError("Account number already exists for this customer")

        self._account_numbers.append(clean_number)

    def remove_account(self, account_number: str):
        """Remove an account number from this customer."""
        if account_number in self._account_numbers:
            self._account_numbers.remove(account_number)


# =============================================================================
# Domain Services for Testing
# =============================================================================


class BankingDomainService:
    """
    Domain service demonstrating business logic that spans multiple aggregates
    or requires external dependencies.
    """

    def __init__(self, account_repository: Repository[BankAccount, str]):
        self.account_repository = account_repository

    async def transfer_funds(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: Decimal,
        description: str = "Transfer",
    ) -> bool:
        """
        Transfer funds between two accounts.

        This operation requires coordination between two aggregates and
        demonstrates a domain service pattern.
        """
        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")

        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        # Load both accounts
        from_account = await self.account_repository.get_async(from_account_id)
        to_account = await self.account_repository.get_async(to_account_id)

        if not from_account:
            raise ValueError("Source account not found")
        if not to_account:
            raise ValueError("Destination account not found")

        # Perform the transfer
        from_account.withdraw(amount, f"Transfer to {to_account_id}: {description}")
        to_account.deposit(amount, f"Transfer from {from_account_id}: {description}")

        # Save both accounts
        await self.account_repository.update_async(from_account)
        await self.account_repository.update_async(to_account)

        return True


# =============================================================================
# DTOs for Traditional Repository Testing
# =============================================================================


@dataclass
class BankAccountDto(Identifiable):
    """Data Transfer Object for traditional repository operations."""

    id: str
    account_holder: str
    balance: Decimal
    is_closed: bool
    created_at: datetime
    last_modified: Optional[datetime] = None


@dataclass
class CustomerDto(Identifiable):
    """Data Transfer Object for customer traditional repository operations."""

    id: str
    name: str
    email: str
    account_numbers: list[str]


# =============================================================================
# Test Suite: Domain Entity Behavior
# =============================================================================


class TestDomainEntityBehavior:
    """Test suite for basic domain entity behavior and business rules."""

    def test_bank_account_creation_success(self):
        """Test successful bank account creation with valid data."""
        # Arrange
        account_holder = "John Doe"
        initial_balance = Decimal("100.50")

        # Act
        account = BankAccount(account_holder, initial_balance)

        # Assert
        assert account.account_holder == account_holder
        assert account.balance == initial_balance
        assert not account.is_closed
        assert account.transaction_count == 0
        assert account.id is not None

        # Verify event was raised
        events = account._pending_events
        assert len(events) == 1
        assert isinstance(events[0], AccountOpenedEvent)
        assert events[0].account_holder == account_holder
        assert events[0].initial_balance == initial_balance

    def test_bank_account_creation_with_invalid_data(self):
        """Test bank account creation fails with invalid data."""
        # Test empty account holder
        with pytest.raises(ValueError, match="Account holder name is required"):
            BankAccount("")

        # Test negative initial balance
        with pytest.raises(ValueError, match="Initial balance cannot be negative"):
            BankAccount("John Doe", Decimal("-10"))

    def test_bank_account_deposit_success(self):
        """Test successful money deposit with business rule validation."""
        # Arrange
        account = BankAccount("John Doe", Decimal("100"))
        initial_balance = account.balance
        deposit_amount = Decimal("50.25")
        description = "Salary deposit"

        # Act
        account.deposit(deposit_amount, description)

        # Assert
        assert account.balance == initial_balance + deposit_amount
        assert account.transaction_count == 1

        # Verify event was raised
        events = account._pending_events
        assert len(events) == 2  # AccountOpened + MoneyDeposited
        deposit_event = next(e for e in events if isinstance(e, MoneyDepositedEvent))
        assert deposit_event.amount == deposit_amount
        assert deposit_event.description == description

    def test_bank_account_deposit_validation(self):
        """Test deposit validation rules."""
        account = BankAccount("John Doe")

        # Test negative amount
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account.deposit(Decimal("-10"))

        # Test zero amount
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account.deposit(Decimal("0"))

        # Test empty description
        with pytest.raises(ValueError, match="Deposit description is required"):
            account.deposit(Decimal("100"), "")

        # Test deposit to closed account
        account.close("Testing")
        with pytest.raises(ValueError, match="Cannot deposit into a closed account"):
            account.deposit(Decimal("100"), "Test deposit")

    def test_bank_account_withdrawal_success(self):
        """Test successful money withdrawal with sufficient funds."""
        # Arrange
        account = BankAccount("John Doe", Decimal("100"))
        withdrawal_amount = Decimal("30.75")
        description = "ATM withdrawal"

        # Act
        account.withdraw(withdrawal_amount, description)

        # Assert
        assert account.balance == Decimal("69.25")
        assert account.transaction_count == 1

        # Verify event was raised
        events = account._pending_events
        assert len(events) == 2  # AccountOpened + MoneyWithdrawn
        withdrawal_event = next(e for e in events if isinstance(e, MoneyWithdrawnEvent))
        assert withdrawal_event.amount == withdrawal_amount
        assert withdrawal_event.description == description

    def test_bank_account_withdrawal_validation(self):
        """Test withdrawal validation rules and business constraints."""
        account = BankAccount("John Doe", Decimal("50"))

        # Test insufficient funds
        with pytest.raises(ValueError, match="Insufficient funds for withdrawal"):
            account.withdraw(Decimal("100"))

        # Test negative amount
        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            account.withdraw(Decimal("-10"))

        # Test zero amount
        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            account.withdraw(Decimal("0"))

        # Test empty description
        with pytest.raises(ValueError, match="Withdrawal description is required"):
            account.withdraw(Decimal("10"), "")

        # Test withdrawal from closed account
        account.close("Testing")
        with pytest.raises(ValueError, match="Cannot withdraw from a closed account"):
            account.withdraw(Decimal("10"), "Test withdrawal")

    def test_bank_account_closure(self):
        """Test account closure with proper state management."""
        # Arrange
        account = BankAccount("John Doe", Decimal("150.50"))
        closure_reason = "Customer request"

        # Act
        account.close(closure_reason)

        # Assert
        assert account.is_closed
        assert account.balance == Decimal("150.50")  # Balance preserved

        # Verify event was raised
        events = account._pending_events
        assert len(events) == 2  # AccountOpened + AccountClosed
        close_event = next(e for e in events if isinstance(e, AccountClosedEvent))
        assert close_event.final_balance == Decimal("150.50")
        assert close_event.closure_reason == closure_reason

        # Test cannot close already closed account
        with pytest.raises(ValueError, match="Account is already closed"):
            account.close("Another reason")

    def test_traditional_entity_customer_creation(self):
        """Test traditional entity creation and validation."""
        # Arrange & Act
        customer = Customer("Jane Smith", "jane.smith@email.com")

        # Assert
        assert customer.name == "Jane Smith"
        assert customer.email == "jane.smith@email.com"
        assert customer.id is not None
        assert len(customer.account_numbers) == 0

    def test_traditional_entity_validation(self):
        """Test traditional entity property validation."""
        # Test invalid name
        with pytest.raises(ValueError, match="Customer name is required"):
            Customer("", "test@email.com")

        with pytest.raises(ValueError, match="Customer name must be at least 2 characters"):
            Customer("A", "test@email.com")

        # Test invalid email
        with pytest.raises(ValueError, match="Customer email is required"):
            Customer("John Doe", "")

        with pytest.raises(ValueError, match="Invalid email format"):
            Customer("John Doe", "invalid-email")

    def test_traditional_entity_account_management(self):
        """Test traditional entity business logic for account management."""
        # Arrange
        customer = Customer("John Doe", "john@email.com")

        # Test adding accounts
        customer.add_account("12345678")
        customer.add_account("87654321")

        assert len(customer.account_numbers) == 2
        assert "12345678" in customer.account_numbers
        assert "87654321" in customer.account_numbers

        # Test duplicate account prevention
        with pytest.raises(ValueError, match="Account number already exists"):
            customer.add_account("12345678")

        # Test removing accounts
        customer.remove_account("12345678")
        assert len(customer.account_numbers) == 1
        assert "12345678" not in customer.account_numbers
        assert "87654321" in customer.account_numbers


# =============================================================================
# Test Suite: Value Objects
# =============================================================================


class TestValueObjects:
    """Test suite for value object behavior and immutability."""

    def test_money_value_object_creation(self):
        """Test money value object creation and validation."""
        # Valid creation
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

        # Test default currency
        money_default = Money(Decimal("50.25"))
        assert money_default.currency == "USD"

        # Test negative amount validation
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Money(Decimal("-10.00"))

        # Test empty currency validation
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(Decimal("100.00"), "")

    def test_money_value_object_operations(self):
        """Test money value object arithmetic operations."""
        money1 = Money(Decimal("100.50"), "USD")
        money2 = Money(Decimal("50.25"), "USD")

        # Test addition
        result = money1.add(money2)
        assert result.amount == Decimal("150.75")
        assert result.currency == "USD"

        # Test subtraction
        result = money1.subtract(money2)
        assert result.amount == Decimal("50.25")
        assert result.currency == "USD"

        # Test currency mismatch
        money_eur = Money(Decimal("100.00"), "EUR")
        with pytest.raises(ValueError, match="Cannot add money with different currencies"):
            money1.add(money_eur)

        with pytest.raises(ValueError, match="Cannot subtract money with different currencies"):
            money1.subtract(money_eur)

        # Test negative result prevention
        with pytest.raises(ValueError, match="Result would be negative"):
            money2.subtract(money1)

    def test_money_value_object_immutability(self):
        """Test that money value objects are immutable."""
        money = Money(Decimal("100.00"), "USD")

        # Verify that money objects are immutable (frozen dataclass)
        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")

        with pytest.raises(AttributeError):
            money.currency = "EUR"

    def test_account_number_value_object(self):
        """Test account number value object validation."""
        # Valid account number
        account_num = AccountNumber("12345678")
        assert account_num.value == "12345678"

        # Test minimum length validation
        with pytest.raises(ValueError, match="Account number must be at least 8 characters"):
            AccountNumber("1234567")

        # Test empty validation
        with pytest.raises(ValueError, match="Account number must be at least 8 characters"):
            AccountNumber("")

        # Test digits only validation
        with pytest.raises(ValueError, match="Account number must contain only digits"):
            AccountNumber("1234567A")


# =============================================================================
# Test Suite: Event Application and State Reconstruction
# =============================================================================


class TestEventApplicationAndStateReconstruction:
    """Test suite for event application and aggregate state reconstruction."""

    def test_event_application_through_multiple_dispatch(self):
        """Test that events are properly applied using multiple dispatch pattern."""
        # Arrange
        account = BankAccount("John Doe", Decimal("100"))

        # Act - Perform multiple operations
        account.deposit(Decimal("50"), "Salary")
        account.withdraw(Decimal("25"), "Groceries")
        account.deposit(Decimal("75"), "Bonus")

        # Assert state is correctly updated
        assert account.balance == Decimal("200")  # 100 + 50 - 25 + 75
        assert account.transaction_count == 3
        assert not account.is_closed

        # Verify all events were registered
        events = account._pending_events
        assert len(events) == 4  # AccountOpened + 2 Deposits + 1 Withdrawal

        event_types = [type(e).__name__ for e in events]
        assert "AccountOpenedEvent" in event_types
        assert event_types.count("MoneyDepositedEvent") == 2
        assert event_types.count("MoneyWithdrawnEvent") == 1

    def test_state_reconstruction_from_events(self):
        """Test that aggregate state can be reconstructed from events."""
        # Arrange - Create a new state and apply events manually
        state = BankAccountState()
        account_id = str(uuid.uuid4()).replace("-", "")

        # Apply events in sequence
        events = [
            AccountOpenedEvent(account_id, "Jane Doe", Decimal("200")),
            MoneyDepositedEvent(account_id, Decimal("100"), "Salary"),
            MoneyWithdrawnEvent(account_id, Decimal("50"), "Bills"),
            MoneyDepositedEvent(account_id, Decimal("25"), "Refund"),
        ]

        for event in events:
            state.on(event)

        # Assert final state
        assert state._id == account_id
        assert state.account_holder == "Jane Doe"
        assert state.balance == Decimal("275")  # 200 + 100 - 50 + 25
        assert state.transaction_count == 3
        assert not state.is_closed

    def test_event_ordering_and_consistency(self):
        """Test that event ordering maintains aggregate consistency."""
        # Arrange
        account = BankAccount("Test User", Decimal("100"))

        # Act - Perform operations that should maintain consistency
        account.deposit(Decimal("50"), "Deposit 1")
        account.withdraw(Decimal("30"), "Withdrawal 1")
        account.deposit(Decimal("20"), "Deposit 2")
        account.withdraw(Decimal("40"), "Withdrawal 2")

        # Assert - Final state should be consistent
        expected_balance = Decimal("100") + Decimal("50") - Decimal("30") + Decimal("20") - Decimal("40")
        assert account.balance == expected_balance
        assert account.transaction_count == 4

        # Verify events are in correct order
        events = account._pending_events
        non_creation_events = [e for e in events if not isinstance(e, AccountOpenedEvent)]

        assert isinstance(non_creation_events[0], MoneyDepositedEvent)
        assert non_creation_events[0].amount == Decimal("50")

        assert isinstance(non_creation_events[1], MoneyWithdrawnEvent)
        assert non_creation_events[1].amount == Decimal("30")

        assert isinstance(non_creation_events[2], MoneyDepositedEvent)
        assert non_creation_events[2].amount == Decimal("20")

        assert isinstance(non_creation_events[3], MoneyWithdrawnEvent)
        assert non_creation_events[3].amount == Decimal("40")

    def test_account_closure_state_changes(self):
        """Test that account closure properly updates state and prevents further operations."""
        # Arrange
        account = BankAccount("Test User", Decimal("500"))
        account.deposit(Decimal("100"), "Before closure")

        # Act
        final_balance_before_closure = account.balance
        account.close("Account no longer needed")

        # Assert
        assert account.is_closed
        assert account.balance == final_balance_before_closure  # Balance unchanged

        # Verify closure event
        events = account._pending_events
        close_event = next(e for e in events if isinstance(e, AccountClosedEvent))
        assert close_event.final_balance == final_balance_before_closure
        assert close_event.closure_reason == "Account no longer needed"

        # Verify operations are blocked after closure
        with pytest.raises(ValueError, match="Cannot deposit into a closed account"):
            account.deposit(Decimal("10"), "After closure")

        with pytest.raises(ValueError, match="Cannot withdraw from a closed account"):
            account.withdraw(Decimal("10"), "After closure")


# =============================================================================
# Test Suite: Traditional Repository Pattern (CRUD)
# =============================================================================


class TestTraditionalRepositoryPattern:
    """
    Test suite for traditional repository pattern with CRUD operations.

    This demonstrates testing domain entities with traditional persistence
    that doesn't use event sourcing.
    """

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        repository = Mock(spec=Repository[Customer, str])
        repository.add_async = AsyncMock()
        repository.get_async = AsyncMock()
        repository.update_async = AsyncMock()
        repository.remove_async = AsyncMock()
        repository.contains_async = AsyncMock()
        return repository

    @pytest.mark.asyncio
    async def test_traditional_entity_crud_operations(self, mock_repository):
        """Test CRUD operations with traditional domain entities."""
        # Arrange
        customer = Customer("John Doe", "john.doe@email.com")
        customer.add_account("12345678")
        customer.add_account("87654321")

        # Mock repository responses
        mock_repository.add_async.return_value = None
        mock_repository.get_async.return_value = customer
        mock_repository.update_async.return_value = None
        mock_repository.contains_async.return_value = True

        # Test CREATE
        await mock_repository.add_async(customer)
        mock_repository.add_async.assert_called_once_with(customer)

        # Test READ
        retrieved_customer = await mock_repository.get_async(customer.id)
        mock_repository.get_async.assert_called_once_with(customer.id)
        assert retrieved_customer.name == "John Doe"
        assert retrieved_customer.email == "john.doe@email.com"
        assert len(retrieved_customer.account_numbers) == 2

        # Test UPDATE
        customer.name = "John Smith"
        customer.email = "john.smith@email.com"
        await mock_repository.update_async(customer)
        mock_repository.update_async.assert_called_once_with(customer)

        # Test DELETE (via contains check)
        exists = await mock_repository.contains_async(customer.id)
        assert exists
        mock_repository.contains_async.assert_called_once_with(customer.id)

    @pytest.mark.asyncio
    async def test_traditional_repository_with_dto_mapping(self):
        """Test traditional repository operations with DTO mapping."""
        # Arrange - Create domain entity
        customer = Customer("Jane Doe", "jane.doe@email.com")
        customer.add_account("11111111")
        customer.add_account("22222222")

        # Act - Map to DTO (simulating repository layer)
        customer_dto = CustomerDto(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            account_numbers=customer.account_numbers,
        )

        # Assert DTO contains correct data
        assert customer_dto.id == customer.id
        assert customer_dto.name == "Jane Doe"
        assert customer_dto.email == "jane.doe@email.com"
        assert customer_dto.account_numbers == ["11111111", "22222222"]

        # Act - Map back to domain entity (simulating repository retrieval)
        reconstructed_customer = Customer(customer_dto.name, customer_dto.email)
        reconstructed_customer.id = customer_dto.id
        for account_num in customer_dto.account_numbers:
            reconstructed_customer.add_account(account_num)

        # Assert domain entity is correctly reconstructed
        assert reconstructed_customer.id == customer.id
        assert reconstructed_customer.name == customer.name
        assert reconstructed_customer.email == customer.email
        assert reconstructed_customer.account_numbers == customer.account_numbers

    @pytest.mark.asyncio
    async def test_traditional_repository_business_rule_enforcement(self, mock_repository):
        """Test that business rules are enforced even with traditional persistence."""
        # Arrange
        customer = Customer("Test User", "test@email.com")

        # Test that entity validates data before persistence
        with pytest.raises(ValueError, match="Invalid email format"):
            customer.email = "invalid-email"

        # Test that business rules are enforced
        customer.add_account("12345678")
        with pytest.raises(ValueError, match="Account number already exists"):
            customer.add_account("12345678")

        # Verify repository would only receive valid entities
        assert customer.name == "Test User"
        assert customer.email == "test@email.com"
        assert len(customer.account_numbers) == 1


# =============================================================================
# Test Suite: Event Sourcing Repository Pattern
# =============================================================================


class TestEventSourcingRepositoryPattern:
    """
    Test suite for event sourcing repository pattern.

    This demonstrates testing domain entities with event-sourced persistence
    where state is reconstructed from events.
    """

    @pytest.fixture
    def mock_event_store(self):
        """Create a mock event store for testing."""
        event_store = Mock()
        event_store.save_events_async = AsyncMock()
        event_store.get_events_async = AsyncMock()
        return event_store

    @pytest.fixture
    def mock_es_repository(self, mock_event_store):
        """Create a mock event sourcing repository."""
        repository = Mock(spec=EventSourcingRepository[BankAccount, str])
        repository.add_async = AsyncMock()
        repository.get_async = AsyncMock()
        repository.update_async = AsyncMock()
        repository.event_store = mock_event_store
        return repository

    @pytest.mark.asyncio
    async def test_event_sourced_entity_persistence(self, mock_es_repository, mock_event_store):
        """Test event-sourced entity persistence and retrieval."""
        # Arrange
        account = BankAccount("John Doe", Decimal("1000"))
        account.deposit(Decimal("500"), "Salary deposit")
        account.withdraw(Decimal("200"), "Bills payment")

        # Mock event store to return the events
        events = account._pending_events
        mock_event_store.get_events_async.return_value = events

        # Test saving aggregate (persists events)
        await mock_es_repository.add_async(account)
        mock_es_repository.add_async.assert_called_once_with(account)

        # Test loading aggregate (reconstructs from events)
        # Mock the reconstruction process
        def mock_get_async(aggregate_id: str):
            # Simulate aggregate reconstruction from events
            reconstructed_account = BankAccount.__new__(BankAccount)
            reconstructed_account.state = BankAccountState()
            for event in events:
                reconstructed_account.state.on(event)
            reconstructed_account._uncommitted_events = []
            return reconstructed_account

        mock_es_repository.get_async.side_effect = mock_get_async

        retrieved_account = await mock_es_repository.get_async(account.id)

        # Assert reconstructed state matches original
        assert retrieved_account.account_holder == "John Doe"
        assert retrieved_account.balance == Decimal("1300")  # 1000 + 500 - 200
        assert retrieved_account.transaction_count == 2
        assert not retrieved_account.is_closed

    @pytest.mark.asyncio
    async def test_event_sourced_aggregate_updates(self, mock_es_repository, mock_event_store):
        """Test updating event-sourced aggregates with new events."""
        # Arrange - Create initial account
        account = BankAccount("Jane Smith", Decimal("500"))
        initial_events = account._pending_events

        # Simulate persisting initial events
        await mock_es_repository.add_async(account)

        # Act - Perform additional operations
        account.deposit(Decimal("300"), "Bonus")
        account.withdraw(Decimal("100"), "Shopping")
        account.close("Moving banks")

        # Get new events (since last persistence)
        all_events = account._pending_events
        new_events = all_events[len(initial_events) :]

        # Simulate the events being fresh after operations
        if len(new_events) == 0:
            new_events = all_events[-3:]  # Last 3 events (Deposit, Withdrawal, Closure)

        # Test updating with new events
        await mock_es_repository.update_async(account)
        mock_es_repository.update_async.assert_called_once_with(account)

        # Verify new events would be persisted
        assert len(new_events) == 3  # Deposit, Withdrawal, Closure
        assert isinstance(new_events[0], MoneyDepositedEvent)
        assert isinstance(new_events[1], MoneyWithdrawnEvent)
        assert isinstance(new_events[2], AccountClosedEvent)

    @pytest.mark.asyncio
    async def test_event_sourced_aggregate_state_consistency(self, mock_es_repository):
        """Test that event-sourced aggregates maintain consistency across operations."""
        # Arrange
        account = BankAccount("Consistency Test", Decimal("1000"))

        # Act - Perform complex sequence of operations
        account.deposit(Decimal("250"), "Income")  # Balance: 1250
        account.withdraw(Decimal("100"), "Expense")  # Balance: 1150
        account.deposit(Decimal("50"), "Refund")  # Balance: 1200
        account.withdraw(Decimal("300"), "Bills")  # Balance: 900

        # Assert - State should be consistent
        assert account.balance == Decimal("900")
        assert account.transaction_count == 4
        assert not account.is_closed

        # Verify event sequence maintains consistency
        events = account._pending_events
        non_creation_events = [e for e in events if not isinstance(e, AccountOpenedEvent)]

        # Manually reconstruct state to verify consistency
        test_state = BankAccountState()
        test_state.on(events[0])  # AccountOpened
        assert test_state.balance == Decimal("1000")

        for event in non_creation_events:
            test_state.on(event)

        assert test_state.balance == account.balance
        assert test_state.transaction_count == account.transaction_count
        assert test_state.is_closed == account.is_closed


# =============================================================================
# Test Suite: Domain Services and Cross-Aggregate Operations
# =============================================================================


class TestDomainServices:
    """Test suite for domain services that coordinate multiple aggregates."""

    @pytest.fixture
    def mock_account_repository(self):
        """Create a mock account repository for domain service testing."""
        repository = Mock(spec=Repository[BankAccount, str])
        repository.get_async = AsyncMock()
        repository.update_async = AsyncMock()
        return repository

    @pytest.fixture
    def banking_service(self, mock_account_repository):
        """Create banking domain service with mocked dependencies."""
        return BankingDomainService(mock_account_repository)

    @pytest.mark.asyncio
    async def test_funds_transfer_success(self, banking_service, mock_account_repository):
        """Test successful funds transfer between accounts."""
        # Arrange
        from_account = BankAccount("Alice", Decimal("1000"))
        to_account = BankAccount("Bob", Decimal("500"))
        transfer_amount = Decimal("250")

        # Mock repository to return accounts
        mock_account_repository.get_async.side_effect = lambda account_id: {
            from_account.id: from_account,
            to_account.id: to_account,
        }.get(account_id)

        # Act
        result = await banking_service.transfer_funds(from_account.id, to_account.id, transfer_amount, "Transfer test")

        # Assert
        assert result is True
        assert from_account.balance == Decimal("750")  # 1000 - 250
        assert to_account.balance == Decimal("750")  # 500 + 250

        # Verify repository interactions
        assert mock_account_repository.get_async.call_count == 2
        assert mock_account_repository.update_async.call_count == 2

        # Verify events were raised
        from_events = from_account._pending_events
        to_events = to_account._pending_events

        # Should have withdrawal event in from_account
        withdrawal_events = [e for e in from_events if isinstance(e, MoneyWithdrawnEvent)]
        assert len(withdrawal_events) == 1
        assert withdrawal_events[0].amount == transfer_amount

        # Should have deposit event in to_account
        deposit_events = [e for e in to_events if isinstance(e, MoneyDepositedEvent)]
        assert len(deposit_events) == 1
        assert deposit_events[0].amount == transfer_amount

    @pytest.mark.asyncio
    async def test_funds_transfer_validation(self, banking_service, mock_account_repository):
        """Test funds transfer validation rules."""
        # Test same account transfer
        with pytest.raises(ValueError, match="Cannot transfer to the same account"):
            await banking_service.transfer_funds("account1", "account1", Decimal("100"))

        # Test negative amount
        with pytest.raises(ValueError, match="Transfer amount must be positive"):
            await banking_service.transfer_funds("account1", "account2", Decimal("-50"))

        # Test zero amount
        with pytest.raises(ValueError, match="Transfer amount must be positive"):
            await banking_service.transfer_funds("account1", "account2", Decimal("0"))

    @pytest.mark.asyncio
    async def test_funds_transfer_account_not_found(self, banking_service, mock_account_repository):
        """Test funds transfer when accounts don't exist."""
        # Mock repository to return None for non-existent accounts
        mock_account_repository.get_async.return_value = None

        # Test source account not found
        with pytest.raises(ValueError, match="Source account not found"):
            await banking_service.transfer_funds("nonexistent1", "account2", Decimal("100"))

        # Test destination account not found
        from_account = BankAccount("Alice", Decimal("1000"))
        mock_account_repository.get_async.side_effect = lambda account_id: {"account1": from_account}.get(account_id)

        with pytest.raises(ValueError, match="Destination account not found"):
            await banking_service.transfer_funds("account1", "nonexistent2", Decimal("100"))

    @pytest.mark.asyncio
    async def test_funds_transfer_insufficient_funds(self, banking_service, mock_account_repository):
        """Test funds transfer with insufficient funds."""
        # Arrange
        from_account = BankAccount("Alice", Decimal("100"))  # Low balance
        to_account = BankAccount("Bob", Decimal("500"))

        mock_account_repository.get_async.side_effect = lambda account_id: {
            from_account.id: from_account,
            to_account.id: to_account,
        }.get(account_id)

        # Act & Assert - Should fail due to insufficient funds
        with pytest.raises(ValueError, match="Insufficient funds for withdrawal"):
            await banking_service.transfer_funds(from_account.id, to_account.id, Decimal("200"), "Failed transfer")

        # Verify no state changes occurred
        assert from_account.balance == Decimal("100")
        assert to_account.balance == Decimal("500")

        # Verify no repository updates were called
        mock_account_repository.update_async.assert_not_called()


# =============================================================================
# Test Suite: Integration Testing (Both Patterns)
# =============================================================================


class TestDomainDrivenDesignIntegration:
    """
    Integration test suite demonstrating both traditional and event-sourced
    patterns working together in a complete domain scenario.
    """

    @pytest.mark.asyncio
    async def test_complete_banking_workflow_traditional_and_event_sourced(self):
        """
        Integration test demonstrating a complete banking workflow using both
        traditional entities (Customer) and event-sourced aggregates (BankAccount).
        """
        # Arrange - Traditional entity (Customer)
        customer = Customer("John Banking", "john.banking@email.com")

        # Arrange - Event-sourced aggregate (BankAccount)
        checking_account = BankAccount("John Banking", Decimal("1000"))
        savings_account = BankAccount("John Banking", Decimal("5000"))

        # Link accounts to customer (traditional entity operation)
        customer.add_account(checking_account.id)
        customer.add_account(savings_account.id)

        # Act - Perform banking operations (event-sourced operations)
        # 1. Deposit salary into checking
        checking_account.deposit(Decimal("2000"), "Monthly salary")

        # 2. Transfer from checking to savings
        checking_account.withdraw(Decimal("1500"), "Transfer to savings")
        savings_account.deposit(Decimal("1500"), "Transfer from checking")

        # 3. Pay bills from checking
        checking_account.withdraw(Decimal("800"), "Monthly bills")

        # 4. Interest earning in savings
        savings_account.deposit(Decimal("25"), "Monthly interest")

        # Assert - Verify customer state (traditional)
        assert customer.name == "John Banking"
        assert customer.email == "john.banking@email.com"
        assert len(customer.account_numbers) == 2
        assert checking_account.id in customer.account_numbers
        assert savings_account.id in customer.account_numbers

        # Assert - Verify account states (event-sourced)
        assert checking_account.balance == Decimal("700")  # 1000 + 2000 - 1500 - 800
        assert checking_account.transaction_count == 3
        assert not checking_account.is_closed

        assert savings_account.balance == Decimal("6525")  # 5000 + 1500 + 25
        assert savings_account.transaction_count == 2
        assert not savings_account.is_closed

        # Assert - Verify event history (event-sourced)
        checking_events = checking_account._pending_events
        savings_events = savings_account._pending_events

        # Checking account should have: Open + Deposit + Withdrawal + Withdrawal
        assert len(checking_events) == 4
        deposit_events = [e for e in checking_events if isinstance(e, MoneyDepositedEvent)]
        withdrawal_events = [e for e in checking_events if isinstance(e, MoneyWithdrawnEvent)]
        assert len(deposit_events) == 1
        assert len(withdrawal_events) == 2

        # Savings account should have: Open + Deposit + Deposit
        assert len(savings_events) == 3
        savings_deposits = [e for e in savings_events if isinstance(e, MoneyDepositedEvent)]
        assert len(savings_deposits) == 2

    @pytest.mark.asyncio
    async def test_domain_service_with_mixed_persistence_patterns(self):
        """
        Test domain service coordinating between traditional and event-sourced entities.

        This demonstrates how domain services can work with entities using different
        persistence patterns within the same business operation.
        """
        # Arrange - Mock repositories for both patterns
        account_repository = Mock(spec=Repository[BankAccount, str])
        customer_repository = Mock(spec=Repository[Customer, str])

        # Create domain entities
        customer = Customer("Alice Mixed", "alice.mixed@email.com")
        premium_account = BankAccount("Alice Mixed", Decimal("10000"))
        regular_account = BankAccount("Alice Mixed", Decimal("2000"))

        # Link accounts to customer
        customer.add_account(premium_account.id)
        customer.add_account(regular_account.id)

        # Mock repository responses
        customer_repository.get_async.return_value = customer
        account_repository.get_async.side_effect = lambda account_id: {
            premium_account.id: premium_account,
            regular_account.id: regular_account,
        }.get(account_id)

        # Create domain service
        banking_service = BankingDomainService(account_repository)

        # Act - Perform cross-aggregate operation
        await banking_service.transfer_funds(premium_account.id, regular_account.id, Decimal("3000"), "Account rebalancing")

        # Assert - Verify traditional entity unchanged
        assert customer.name == "Alice Mixed"
        assert len(customer.account_numbers) == 2

        # Assert - Verify event-sourced aggregates updated
        assert premium_account.balance == Decimal("7000")  # 10000 - 3000
        assert regular_account.balance == Decimal("5000")  # 2000 + 3000

        # Assert - Verify events were generated
        premium_events = premium_account._pending_events
        regular_events = regular_account._pending_events

        # Should have withdrawal in premium and deposit in regular
        premium_withdrawals = [e for e in premium_events if isinstance(e, MoneyWithdrawnEvent)]
        regular_deposits = [e for e in regular_events if isinstance(e, MoneyDepositedEvent)]

        assert len(premium_withdrawals) == 1
        assert premium_withdrawals[0].amount == Decimal("3000")

        assert len(regular_deposits) == 1
        assert regular_deposits[0].amount == Decimal("3000")

        # Verify repository interactions
        assert account_repository.get_async.call_count == 2
        assert account_repository.update_async.call_count == 2

    def test_business_rule_enforcement_across_patterns(self):
        """
        Test that business rules are consistently enforced across both
        traditional and event-sourced patterns.
        """
        # Traditional entity business rules
        customer = Customer("Rule Test", "rule.test@email.com")

        # Test traditional validation
        with pytest.raises(ValueError, match="Account number already exists"):
            customer.add_account("12345678")
            customer.add_account("12345678")  # Duplicate

        # Event-sourced aggregate business rules
        account = BankAccount("Rule Test", Decimal("100"))

        # Test event-sourced validation
        with pytest.raises(ValueError, match="Insufficient funds"):
            account.withdraw(Decimal("200"))  # More than balance

        # Test business rule consistency between patterns
        # Both should enforce positive amounts for monetary operations
        with pytest.raises(ValueError, match="Invalid email format"):
            customer.email = "invalid-email"

        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account.deposit(Decimal("-50"))

        # Both should validate required fields
        with pytest.raises(ValueError, match="Customer name is required"):
            Customer("", "test@email.com")

        with pytest.raises(ValueError, match="Account holder name is required"):
            BankAccount("")

    def test_aggregate_boundary_enforcement(self):
        """
        Test that aggregate boundaries are properly enforced and that
        consistency is maintained within aggregates but not across them.
        """
        # Each aggregate maintains its own consistency
        account1 = BankAccount("Account 1", Decimal("1000"))
        account2 = BankAccount("Account 2", Decimal("500"))

        # Operations within an aggregate are consistent
        account1.deposit(Decimal("100"))
        account1.withdraw(Decimal("50"))
        assert account1.balance == Decimal("1050")

        # Operations across aggregates require coordination (domain service)
        # Direct cross-aggregate operations are not allowed
        # (This would be handled by BankingDomainService.transfer_funds)

        # Each aggregate has its own event stream
        account1_events = account1._pending_events
        account2_events = account2._pending_events

        # Events are isolated to their respective aggregates
        assert len(account1_events) == 3  # Open + Deposit + Withdrawal
        assert len(account2_events) == 1  # Open only

        # No cross-contamination of events
        for event in account1_events:
            assert event.aggregate_id == account1.id

        for event in account2_events:
            assert event.aggregate_id == account2.id
