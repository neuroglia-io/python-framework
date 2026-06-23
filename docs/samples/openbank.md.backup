# 🏦 OpenBank Sample Application

OpenBank is a comprehensive sample application that demonstrates advanced Neuroglia features including event sourcing, CQRS, domain-driven design, and event-driven architecture. It simulates a simple banking system with persons and accounts.

## 🎯 Overview

The OpenBank sample showcases:

- **Event Sourcing**: Complete event-sourced domain with event store
- **CQRS**: Separate command and query models
- **Domain-Driven Design**: Rich domain models with business rules
- **Event-Driven Architecture**: Domain events and integration events
- **Clean Architecture**: Clear separation of layers
- **Repository Pattern**: Both write (event sourcing) and read (MongoDB) repositories

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │  PersonsController │  │ AccountsController │  │  Other APIs  │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Application Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │    Commands     │  │     Queries     │  │     Events     │   │
│  │   Handlers      │  │    Handlers     │  │   Handlers     │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Domain Layer                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │     Person      │  │     Account     │  │    Address     │   │
│  │   Aggregate     │  │   Aggregate     │  │ Value Object   │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  Integration Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │ Event Store     │  │   MongoDB       │  │  API Clients   │   │
│  │ Repository      │  │  Repository     │  │                │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Git (to clone the repository)

### Quick Start

The fastest way to run OpenBank is using the provided CLI tool:

```bash
# Clone the repository (if not already done)
git clone https://github.com/bvandewe/pyneuro.git
cd pyneuro

# Start OpenBank (automatically starts shared infrastructure)
./openbank start

# Wait for services to be ready (~30 seconds)
./openbank status
```

### Access the Services

Once running, access:

- **API Documentation**: [http://localhost:8899/api/docs](http://localhost:8899/api/docs)
- **EventStoreDB UI**: [http://localhost:2113](http://localhost:2113) (admin/changeit)
- **MongoDB Express**: [http://localhost:8081](http://localhost:8081)
- **Keycloak**: [http://localhost:8090](http://localhost:8090) (admin/admin)
- **Event Player**: [http://localhost:8085](http://localhost:8085)
- **Grafana**: [http://localhost:3001](http://localhost:3001)

### CLI Commands

The OpenBank CLI tool provides convenient management:

```bash
# Start OpenBank and dependencies
./openbank start

# Stop OpenBank (keeps infrastructure running)
./openbank stop

# View logs
./openbank logs

# Follow logs in real-time
./openbank logs -f

# Check service status
./openbank status

# Restart OpenBank
./openbank restart

# Clean up containers and volumes
./openbank clean

# Reset everything (including data)
./openbank reset
```

### Development Mode

For development with hot-reload:

```bash
# Start in development mode with Poetry
poetry install
poetry run python samples/openbank/api/main.py
```

### Authentication

OpenBank uses Keycloak for authentication in the `pyneuro` realm:

- **Realm**: `pyneuro`
- **Client**: `openbank-app`
- **Test Users**:
  - Admin: `admin` / `admin123`
  - Customer: `customer` / `customer123`

## 📁 Project Structure

```text
samples/openbank/
├── api/
│   ├── main.py                     # Application entry point
│   └── controllers/
│       ├── persons_controller.py   # Person management API
│       └── accounts_controller.py  # Account management API
├── application/
│   ├── commands/
│   │   ├── persons/
│   │   │   └── register_person_command.py
│   │   └── accounts/
│   │       ├── open_account_command.py
│   │       └── deposit_command.py
│   ├── queries/
│   │   ├── person_by_id.py
│   │   └── account_by_owner.py
│   └── events/
│       ├── integration/
│       │   └── person_registered_handler.py
│       └── domain/
├── domain/
│   └── models/
│       ├── person.py               # Person aggregate
│       ├── account.py              # Account aggregate
│       └── address.py              # Address value object
└── integration/
    ├── models/                     # DTOs and read models
    │   ├── person.py
    │   └── account.py
    └── commands/                   # API command DTOs
        └── persons/
            └── register_person_command_dto.py
```

## 🏛️ Domain Models

### Person Aggregate

The Person aggregate manages person registration and personal information:

```python
from dataclasses import dataclass
from datetime import date
from neuroglia.data.abstractions import AggregateRoot
from samples.openbank.integration import PersonGender

@dataclass
class PersonState:
    """Person aggregate state"""
    id: str = None
    first_name: str = None
    last_name: str = None
    nationality: str = None
    gender: PersonGender = None
    date_of_birth: date = None
    address: Address = None

class Person(AggregateRoot[str]):
    """Person aggregate root"""

    def __init__(self, id: str = None):
        super().__init__(id)
        self.state = PersonState()

    def register(self, first_name: str, last_name: str, nationality: str,
                gender: PersonGender, date_of_birth: date, address: Address):
        """Register a new person"""

        # Validate business rules
        if not first_name or not last_name:
            raise ValueError("First name and last name are required")

        if date_of_birth >= date.today():
            raise ValueError("Date of birth must be in the past")

        # Raise domain event
        self.apply(PersonRegisteredEvent(
            person_id=self.id,
            first_name=first_name,
            last_name=last_name,
            nationality=nationality,
            gender=gender,
            date_of_birth=date_of_birth,
            address=address
        ))

    def update_address(self, new_address: Address):
        """Update person's address"""
        self.apply(PersonAddressUpdatedEvent(
            person_id=self.id,
            old_address=self.state.address,
            new_address=new_address
        ))

    # Event handlers
    def on_person_registered(self, event: PersonRegisteredEvent):
        """Handle person registered event"""
        self.state.id = event.person_id
        self.state.first_name = event.first_name
        self.state.last_name = event.last_name
        self.state.nationality = event.nationality
        self.state.gender = event.gender
        self.state.date_of_birth = event.date_of_birth
        self.state.address = event.address

    def on_person_address_updated(self, event: PersonAddressUpdatedEvent):
        """Handle address updated event"""
        self.state.address = event.new_address
```

### Account Aggregate

The Account aggregate manages banking accounts and transactions:

```python
from decimal import Decimal
from neuroglia.data.abstractions import AggregateRoot

@dataclass
class AccountState:
    """Account aggregate state"""
    id: str = None
    owner_id: str = None
    account_number: str = None
    balance: Decimal = Decimal('0.00')
    currency: str = 'USD'
    is_active: bool = True

class Account(AggregateRoot[str]):
    """Account aggregate root"""

    def __init__(self, id: str = None):
        super().__init__(id)
        self.state = AccountState()

    def open(self, owner_id: str, account_number: str, initial_deposit: Decimal = None):
        """Open a new account"""

        # Validate business rules
        if not owner_id:
            raise ValueError("Owner ID is required")

        if not account_number:
            raise ValueError("Account number is required")

        if initial_deposit and initial_deposit < Decimal('0'):
            raise ValueError("Initial deposit cannot be negative")

        # Raise domain event
        self.apply(AccountOpenedEvent(
            account_id=self.id,
            owner_id=owner_id,
            account_number=account_number,
            initial_deposit=initial_deposit or Decimal('0.00')
        ))

    def deposit(self, amount: Decimal, description: str = None):
        """Deposit money to the account"""

        # Validate business rules
        if amount <= Decimal('0'):
            raise ValueError("Deposit amount must be positive")

        if not self.state.is_active:
            raise ValueError("Cannot deposit to inactive account")

        # Raise domain event
        self.apply(MoneyDepositedEvent(
            account_id=self.id,
            amount=amount,
            description=description,
            balance_after=self.state.balance + amount
        ))

    def withdraw(self, amount: Decimal, description: str = None):
        """Withdraw money from the account"""

        # Validate business rules
        if amount <= Decimal('0'):
            raise ValueError("Withdrawal amount must be positive")

        if not self.state.is_active:
            raise ValueError("Cannot withdraw from inactive account")

        if self.state.balance < amount:
            raise ValueError("Insufficient funds")

        # Raise domain event
        self.apply(MoneyWithdrawnEvent(
            account_id=self.id,
            amount=amount,
            description=description,
            balance_after=self.state.balance - amount
        ))

    # Event handlers
    def on_account_opened(self, event: AccountOpenedEvent):
        """Handle account opened event"""
        self.state.id = event.account_id
        self.state.owner_id = event.owner_id
        self.state.account_number = event.account_number
        self.state.balance = event.initial_deposit

    def on_money_deposited(self, event: MoneyDepositedEvent):
        """Handle money deposited event"""
        self.state.balance = event.balance_after

    def on_money_withdrawn(self, event: MoneyWithdrawnEvent):
        """Handle money withdrawn event"""
        self.state.balance = event.balance_after
```

## 💼 Application Layer

### Command Handlers

Command handlers execute business operations:

```python
from neuroglia.mediation.mediator import CommandHandler
from neuroglia.data.infrastructure.abstractions import Repository

class RegisterPersonCommandHandler(CommandHandler[RegisterPersonCommand, OperationResult[PersonDto]]):
    """Handles person registration commands"""

    def __init__(self,
                 mapper: Mapper,
                 person_repository: Repository[Person, str]):
        self.mapper = mapper
        self.person_repository = person_repository

    async def handle_async(self, command: RegisterPersonCommand) -> OperationResult[PersonDto]:
        try:
            # Create new person aggregate
            person = Person(str(uuid.uuid4()))

            # Execute business operation
            person.register(
                first_name=command.first_name,
                last_name=command.last_name,
                nationality=command.nationality,
                gender=command.gender,
                date_of_birth=command.date_of_birth,
                address=command.address
            )

            # Save to event store
            saved_person = await self.person_repository.add_async(person)

            # Map to DTO and return
            person_dto = self.mapper.map(saved_person.state, PersonDto)
            return self.created(person_dto)

        except ValueError as ex:
            return self.bad_request(str(ex))
        except Exception as ex:
            return self.internal_error(f"Failed to register person: {ex}")

class DepositCommandHandler(CommandHandler[DepositCommand, OperationResult[AccountDto]]):
    """Handles money deposit commands"""

    def __init__(self,
                 mapper: Mapper,
                 account_repository: Repository[Account, str]):
        self.mapper = mapper
        self.account_repository = account_repository

    async def handle_async(self, command: DepositCommand) -> OperationResult[AccountDto]:
        try:
            # Load account from event store
            account = await self.account_repository.get_by_id_async(command.account_id)
            if account is None:
                return self.not_found("Account not found")

            # Execute business operation
            account.deposit(command.amount, command.description)

            # Save changes
            await self.account_repository.update_async(account)

            # Map to DTO and return
            account_dto = self.mapper.map(account.state, AccountDto)
            return self.ok(account_dto)

        except ValueError as ex:
            return self.bad_request(str(ex))
        except Exception as ex:
            return self.internal_error(f"Failed to deposit money: {ex}")
```

### Query Handlers

Query handlers retrieve data for read operations:

```python
class GetPersonByIdQueryHandler(QueryHandler[GetPersonByIdQuery, OperationResult[PersonDto]]):
    """Handles person lookup queries"""

    def __init__(self,
                 mapper: Mapper,
                 person_repository: Repository[PersonDto, str]):  # Read model repository
        self.mapper = mapper
        self.person_repository = person_repository

    async def handle_async(self, query: GetPersonByIdQuery) -> OperationResult[PersonDto]:
        person = await self.person_repository.get_by_id_async(query.person_id)

        if person is None:
            return self.not_found(f"Person with ID {query.person_id} not found")

        return self.ok(person)

class GetAccountsByOwnerQueryHandler(QueryHandler[GetAccountsByOwnerQuery, OperationResult[List[AccountDto]]]):
    """Handles account lookup by owner queries"""

    def __init__(self, account_repository: Repository[AccountDto, str]):
        self.account_repository = account_repository

    async def handle_async(self, query: GetAccountsByOwnerQuery) -> OperationResult[List[AccountDto]]:
        accounts = await self.account_repository.find_by_criteria_async(
            {"owner_id": query.owner_id}
        )
        return self.ok(accounts)
```

## 📡 Event Handling

### Domain Events

Domain events represent business events within aggregates:

```python
@dataclass
class PersonRegisteredEvent(DomainEvent):
    """Event raised when a person is registered"""
    person_id: str
    first_name: str
    last_name: str
    nationality: str
    gender: PersonGender
    date_of_birth: date
    address: Address

@dataclass
class AccountOpenedEvent(DomainEvent):
    """Event raised when an account is opened"""
    account_id: str
    owner_id: str
    account_number: str
    initial_deposit: Decimal

@dataclass
class MoneyDepositedEvent(DomainEvent):
    """Event raised when money is deposited"""
    account_id: str
    amount: Decimal
    description: str
    balance_after: Decimal
```

### Integration Events

Integration events handle cross-bounded-context communication:

```python
class PersonRegisteredIntegrationEventHandler(EventHandler[PersonRegisteredEvent]):
    """Handles person registered events for integration purposes"""

    def __init__(self,
                 cloud_event_publisher: CloudEventPublisher,
                 mapper: Mapper):
        self.cloud_event_publisher = cloud_event_publisher
        self.mapper = mapper

    async def handle_async(self, event: PersonRegisteredEvent):
        # Create integration event
        integration_event = PersonRegisteredIntegrationEvent(
            person_id=event.person_id,
            email=event.email,
            full_name=f"{event.first_name} {event.last_name}",
            timestamp=datetime.utcnow()
        )

        # Publish as CloudEvent
        await self.cloud_event_publisher.publish_async(
            event_type="person.registered.v1",
            data=integration_event,
            source="openbank.persons"
        )
```

## 🗄️ Data Access

### Event Sourcing Repository

The write model uses event sourcing:

```python
# Configuration in main.py
from neuroglia.data.infrastructure.event_sourcing import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store import ESEventStore

# Configure Event Store
ESEventStore.configure(builder, EventStoreOptions(database_name, consumer_group))

# Configure event sourcing repositories
DataAccessLayer.WriteModel.configure(
    builder,
    ["samples.openbank.domain.models"],
    lambda builder_, entity_type, key_type: EventSourcingRepository.configure(
        builder_, entity_type, key_type
    )
)
```

### Read Model Repository

The read model uses MongoDB:

```python
# Configuration in main.py
from neuroglia.data.infrastructure.mongo import MongoRepository

# Configure MongoDB repositories
DataAccessLayer.ReadModel.configure(
    builder,
    ["samples.openbank.integration.models", "samples.openbank.application.events"],
    lambda builder_, entity_type, key_type: MongoRepository.configure(
        builder_, entity_type, key_type, database_name
    )
)
```

## 🌐 API Layer

### Controllers

Controllers expose the domain through REST APIs:

```python
class PersonsController(ControllerBase):
    """Persons management API"""

    @post("/", response_model=PersonDto, status_code=201)
    async def register_person(self, command: RegisterPersonCommandDto) -> PersonDto:
        """Register a new person"""
        # Map DTO to domain command
        domain_command = self.mapper.map(command, RegisterPersonCommand)

        # Execute through mediator
        result = await self.mediator.execute_async(domain_command)

        # Process and return result
        return self.process(result)

    @get("/", response_model=List[PersonDto])
    async def list_persons(self) -> List[PersonDto]:
        """List all registered persons"""
        query = ListPersonsQuery()
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{person_id}", response_model=PersonDto)
    async def get_person_by_id(self, person_id: str) -> PersonDto:
        """Get person by ID"""
        query = GetPersonByIdQuery(person_id=person_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

class AccountsController(ControllerBase):
    """Accounts management API"""

    @post("/", response_model=AccountDto, status_code=201)
    async def open_account(self, command: OpenAccountCommandDto) -> AccountDto:
        """Open a new account"""
        domain_command = self.mapper.map(command, OpenAccountCommand)
        result = await self.mediator.execute_async(domain_command)
        return self.process(result)

    @post("/{account_id}/deposit", response_model=AccountDto)
    async def deposit(self, account_id: str, command: DepositCommandDto) -> AccountDto:
        """Deposit money to account"""
        domain_command = self.mapper.map(command, DepositCommand)
        domain_command.account_id = account_id
        result = await self.mediator.execute_async(domain_command)
        return self.process(result)

    @get("/by-owner/{owner_id}", response_model=List[AccountDto])
    async def get_accounts_by_owner(self, owner_id: str) -> List[AccountDto]:
        """Get all accounts for a person"""
        query = GetAccountsByOwnerQuery(owner_id=owner_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)
```

## 🧪 Testing

### Unit Tests

Test domain logic in isolation:

```python
def test_person_registration():
    # Arrange
    person = Person("test-id")
    address = Address("123 Main St", "Anytown", "12345", "USA")

    # Act
    person.register(
        first_name="John",
        last_name="Doe",
        nationality="US",
        gender=PersonGender.MALE,
        date_of_birth=date(1990, 1, 1),
        address=address
    )

    # Assert
    assert person.state.first_name == "John"
    assert person.state.last_name == "Doe"
    assert len(person.uncommitted_events) == 1
    assert isinstance(person.uncommitted_events[0], PersonRegisteredEvent)

def test_account_deposit():
    # Arrange
    account = Account("test-account")
    account.open("owner-id", "123456789", Decimal('100.00'))

    # Act
    account.deposit(Decimal('50.00'), "Test deposit")

    # Assert
    assert account.state.balance == Decimal('150.00')
    assert len(account.uncommitted_events) == 2  # Open + Deposit
```

### Integration Tests

Test the complete flow:

```python
@pytest.mark.asyncio
async def test_person_registration_flow():
    # Arrange
    client = TestClient(app)
    person_data = {
        "first_name": "John",
        "last_name": "Doe",
        "nationality": "US",
        "gender": "MALE",
        "date_of_birth": "1990-01-01",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "postal_code": "12345",
            "country": "USA"
        }
    }

    # Act
    response = client.post("/api/v1/persons", json=person_data)

    # Assert
    assert response.status_code == 201
    person = response.json()
    assert person["first_name"] == "John"
    assert person["last_name"] == "Doe"

    # Verify person can be retrieved
    get_response = client.get(f"/api/v1/persons/{person['id']}")
    assert get_response.status_code == 200
```

## 🚀 Running the Sample

### Using the CLI Tool (Recommended)

The easiest way to run OpenBank:

```bash
# Start OpenBank and all dependencies
./openbank start

# Check status
./openbank status

# View logs
./openbank logs -f

# Stop the application
./openbank stop
```

### Manual Startup

For development or troubleshooting:

```bash
# Start shared infrastructure first
cd deployment/docker-compose
docker-compose -f docker-compose.shared.yml up -d

# Start OpenBank-specific services
docker-compose -f docker-compose.openbank.yml up -d

# Or run locally with Poetry
cd /path/to/pyneuro
poetry install
poetry run python samples/openbank/api/main.py
```

### Example API Calls

**Register a Person**:

```bash
curl -X POST "http://localhost:8899/api/v1/persons" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "nationality": "US",
    "gender": "MALE",
    "date_of_birth": "1990-01-01",
    "address": {
      "street": "123 Main St",
      "city": "Anytown",
      "postal_code": "12345",
      "country": "USA"
    }
  }'
```

**Open an Account**:

```bash
curl -X POST "http://localhost:8899/api/v1/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "PERSON_ID_FROM_ABOVE",
    "account_number": "123456789",
    "initial_deposit": 1000.00
  }'
```

**Deposit Money**:

```bash
curl -X POST "http://localhost:8899/api/v1/accounts/ACCOUNT_ID/deposit" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 500.00,
    "description": "Salary deposit"
  }'
```

## 📋 Key Learnings

The OpenBank sample demonstrates:

1. **Event Sourcing**: How to store state as a sequence of events
2. **CQRS**: Separation of write and read models
3. **Domain-Driven Design**: Rich domain models with business rules
4. **Clean Architecture**: Clear separation of concerns
5. **Event-Driven Architecture**: How events enable loose coupling
6. **Repository Pattern**: Abstract data access for different storage types
7. **Integration Events**: Cross-bounded-context communication

## 🔗 Related Documentation

- [Getting Started](../getting-started.md) - Basic Neuroglia concepts
- [Event Sourcing](../patterns/event-sourcing.md) - Event sourcing patterns
- [CQRS & Mediation](../patterns/cqrs.md) - Command and query patterns
- [Event Handling](../features/event-handling.md) - Event-driven architecture
- [Source Code Naming Conventions](../references/source_code_naming_convention.md) - Naming patterns used throughout this sample
