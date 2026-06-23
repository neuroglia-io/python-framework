# 🏦 OpenBank - Event Sourcing & CQRS Banking System

OpenBank is a comprehensive sample application demonstrating **Event Sourcing**, **CQRS**, **Domain-Driven Design**, and **Event-Driven Architecture** patterns using the Neuroglia framework. It simulates a complete banking system with persons, accounts, and transactions.

## 🎯 Overview

**What You'll Learn:**

- **Event Sourcing**: Store all state changes as immutable events
- **CQRS**: Complete separation of write and read models
- **DDD**: Rich domain models with complex business rules
- **Event-Driven Architecture**: Domain and integration events
- **Read Model Projections**: Eventual consistency patterns
- **Snapshots**: Performance optimization for aggregates
- **KurrentDB Integration**: Modern event store usage

**Use Cases:**

- Financial systems requiring complete audit trails
- Applications needing time-travel debugging
- Systems with complex business rules and domain logic
- Microservices requiring eventual consistency

## 🏗️ Architecture Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Client["💻 API Clients<br/>(REST, CLI, UI)"]
    end

    subgraph "API Layer"
        Controllers["🌐 Controllers<br/>(PersonsController,<br/>AccountsController,<br/>TransactionsController)"]
    end

    subgraph "Application Layer"
        Mediator["🎭 Mediator"]
        Commands["📝 Commands<br/>(RegisterPerson,<br/>CreateBankAccount,<br/>CreateDeposit)"]
        Queries["🔍 Queries<br/>(GetPerson,<br/>GetAccountsByOwner)"]
        CommandHandlers["⚙️ Command Handlers<br/>(Write Operations)"]
        QueryHandlers["🔎 Query Handlers<br/>(Read Operations)"]
        EventHandlers["📡 Event Handlers<br/>(Domain & Integration)"]
    end

    subgraph "Domain Layer"
        Aggregates["🏛️ Aggregates<br/>(Person, BankAccount)"]
        DomainEvents["⚡ Domain Events<br/>(PersonRegistered,<br/>AccountCreated,<br/>TransactionRecorded)"]
        BusinessRules["📋 Business Rules<br/>(Balance checks,<br/>Overdraft limits)"]
    end

    subgraph "Infrastructure Layer - Write Side"
        EventSourcingRepo["📦 Event Sourcing<br/>Repository"]
        EventStore["🗄️ KurrentDB<br/>(EventStoreDB)<br/>Event Streams"]
    end

    subgraph "Infrastructure Layer - Read Side"
        ReadModelRepo["📚 Read Model<br/>Repository"]
        MongoDB["🍃 MongoDB<br/>Read Models<br/>(Optimized Queries)"]
    end

    subgraph "Integration"
        CloudEventBus["☁️ CloudEvent Bus"]
        CloudEventPublisher["📤 CloudEvent<br/>Publisher"]
    end

    Client -->|HTTP Requests| Controllers
    Controllers -->|Dispatch| Mediator

    Mediator -->|Commands| CommandHandlers
    Mediator -->|Queries| QueryHandlers

    CommandHandlers -->|Load/Save| Aggregates
    QueryHandlers -->|Query| ReadModelRepo

    Aggregates -->|Raise| DomainEvents
    Aggregates -->|Enforce| BusinessRules

    CommandHandlers -->|Persist Events| EventSourcingRepo
    EventSourcingRepo -->|Append Events| EventStore

    EventStore -->|Subscribe| EventHandlers
    EventHandlers -->|Project| ReadModelRepo
    ReadModelRepo -->|Store| MongoDB

    EventHandlers -->|Publish| CloudEventPublisher
    CloudEventPublisher -->|Integration Events| CloudEventBus

    style Aggregates fill:#ffe0b2
    style EventStore fill:#c8e6c9
    style MongoDB fill:#bbdefb
    style CloudEventBus fill:#f8bbd0
```

### CQRS Separation

OpenBank implements complete CQRS with separate write and read models:

```mermaid
graph LR
    subgraph "Write Side (Commands)"
        direction TB
        WriteAPI["📝 Write API<br/>Commands"]
        WriteHandlers["⚙️ Command<br/>Handlers"]
        Aggregates["🏛️ Domain<br/>Aggregates"]
        EventStore["🗄️ KurrentDB<br/>Event Store"]

        WriteAPI --> WriteHandlers
        WriteHandlers --> Aggregates
        Aggregates -->|Events| EventStore
    end

    subgraph "Event Processing"
        EventStream["📡 Event Stream"]
        EventHandlers["🔄 Event<br/>Handlers"]

        EventStore -->|Subscribe| EventStream
        EventStream --> EventHandlers
    end

    subgraph "Read Side (Queries)"
        direction TB
        ReadAPI["🔍 Read API<br/>Queries"]
        QueryHandlers["🔎 Query<br/>Handlers"]
        ReadModels["📚 Read Models<br/>(Denormalized)"]
        MongoDB["🍃 MongoDB"]

        ReadAPI --> QueryHandlers
        QueryHandlers --> ReadModels
        ReadModels --> MongoDB
    end

    EventHandlers -->|Project| ReadModels

    style WriteAPI fill:#ffccbc
    style ReadAPI fill:#c8e6c9
    style EventStream fill:#fff9c4
```

**Key Principles:**

- **Write Model**: Optimized for transactional consistency and business rules
- **Read Model**: Optimized for query performance and reporting
- **Eventual Consistency**: Read models are updated asynchronously
- **Event-Driven Sync**: Events bridge the write and read sides

## 📊 Complete Data Flow

### Command Execution Flow

This diagram shows the complete journey of a command from API to persistence:

```mermaid
sequenceDiagram
    participant Client as 👤 Client
    participant API as 🌐 Controller
    participant Mediator as 🎭 Mediator
    participant Handler as ⚙️ Command<br/>Handler
    participant Aggregate as 🏛️ Aggregate<br/>(BankAccount)
    participant Repo as 📦 Event Sourcing<br/>Repository
    participant EventStore as 🗄️ KurrentDB<br/>Event Store
    participant EventBus as 📡 Event Bus

    Note over Client,EventBus: 1. Command Execution (Write Side)

    Client->>+API: POST /accounts/{id}/deposit<br/>{amount: 500, description: "Salary"}
    API->>API: Map DTO to Command
    API->>+Mediator: CreateDepositCommand

    Mediator->>+Handler: Handle CreateDepositCommand

    Note over Handler,Aggregate: 2. Load Aggregate from Event Store

    Handler->>+Repo: get_by_id_async(account_id)
    Repo->>+EventStore: Read event stream<br/>"bank-account-{id}"
    EventStore-->>-Repo: Event stream<br/>[AccountCreated,<br/>Transaction1, Transaction2...]

    Repo->>Repo: Reconstitute aggregate<br/>by replaying events
    Repo-->>-Handler: BankAccount aggregate<br/>(current state)

    Note over Handler,Aggregate: 3. Execute Business Logic

    Handler->>+Aggregate: try_add_transaction(transaction)
    Aggregate->>Aggregate: Check business rules:<br/>- Amount > 0<br/>- Sufficient balance<br/>- Overdraft limit

    alt Business Rules Pass
        Aggregate->>Aggregate: Raise domain event:<br/>TransactionRecorded
        Aggregate-->>-Handler: Success (event raised)
    else Business Rules Fail
        Aggregate-->>Handler: Failure (insufficient funds)
    end

    Note over Handler,EventStore: 4. Persist Events

    Handler->>+Repo: update_async(aggregate)
    Repo->>Repo: Get uncommitted events<br/>from aggregate
    Repo->>+EventStore: Append events to stream<br/>"bank-account-{id}"
    EventStore->>EventStore: Optimistic concurrency check<br/>(expected version)
    EventStore-->>-Repo: Events persisted<br/>(new version)
    Repo-->>-Handler: Success

    Note over Handler,EventBus: 5. Publish Domain Events

    Handler->>+EventBus: Publish domain events
    EventBus-->>-Handler: Published

    Handler-->>-Mediator: OperationResult<br/>(Success)
    Mediator-->>-API: Result
    API->>API: Map to DTO
    API-->>-Client: 200 OK<br/>{id, balance, transaction}

    Note over EventBus: 6. Event Handlers Process (Async)

    EventBus->>EventHandlers: TransactionRecorded event
    Note right of EventHandlers: See Read Model<br/>Reconciliation diagram
```

### Read Model Reconciliation Flow

This shows how domain events are projected into read models:

```mermaid
sequenceDiagram
    participant EventStore as 🗄️ KurrentDB<br/>Event Store
    participant Subscription as 📡 Event<br/>Subscription
    participant EventHandler as 🔄 Domain Event<br/>Handler
    participant Mediator as 🎭 Mediator
    participant WriteRepo as 📦 Write Model<br/>Repository
    participant ReadRepo as 📚 Read Model<br/>Repository
    participant MongoDB as 🍃 MongoDB
    participant CloudEvents as ☁️ CloudEvent<br/>Publisher

    Note over EventStore,CloudEvents: Read Model Synchronization (Async)

    EventStore->>+Subscription: New event appended<br/>TransactionRecorded
    Subscription->>Subscription: Deserialize event
    Subscription->>+EventHandler: handle_async(event)

    Note over EventHandler,MongoDB: 1. Load Current Read Model

    EventHandler->>+ReadRepo: get_by_id_async(account_id)
    ReadRepo->>+MongoDB: Find document<br/>{id: account_id}

    alt Read Model Exists
        MongoDB-->>-ReadRepo: BankAccountDto<br/>(current read model)
        ReadRepo-->>EventHandler: Existing read model
    else Read Model Missing
        MongoDB-->>ReadRepo: null
        ReadRepo-->>-EventHandler: null

        Note over EventHandler: 2. Reconstruct from Write Model

        EventHandler->>+Mediator: GetByIdQuery(account_id)
        Mediator->>+WriteRepo: get_by_id_async(account_id)
        WriteRepo->>EventStore: Read event stream
        EventStore-->>WriteRepo: Event stream
        WriteRepo->>WriteRepo: Reconstitute aggregate
        WriteRepo-->>-Mediator: BankAccount aggregate
        Mediator-->>-EventHandler: Aggregate state

        EventHandler->>EventHandler: Map aggregate to<br/>read model DTO
    end

    Note over EventHandler,MongoDB: 3. Apply Event to Read Model

    EventHandler->>EventHandler: Update read model<br/>based on event type:<br/>- DEPOSIT: balance += amount<br/>- WITHDRAWAL: balance -= amount<br/>- TRANSFER: check direction

    EventHandler->>+ReadRepo: update_async(read_model)
    ReadRepo->>+MongoDB: Update document<br/>{id, balance, owner, ...}
    MongoDB-->>-ReadRepo: Updated
    ReadRepo-->>-EventHandler: Success

    Note over EventHandler,CloudEvents: 4. Publish Integration Event

    EventHandler->>+CloudEvents: Publish TransactionRecorded<br/>as CloudEvent
    CloudEvents->>CloudEvents: Wrap as CloudEvent:<br/>- type: "bank.transaction.v1"<br/>- source: "openbank"<br/>- data: event payload
    CloudEvents-->>-EventHandler: Published to bus

    EventHandler-->>-Subscription: Processed
    Subscription-->>-EventStore: Acknowledge

    Note over EventStore,CloudEvents: Read Model Now Consistent with Write Model
```

### Query Execution Flow

```mermaid
sequenceDiagram
    participant Client as 👤 Client
    participant API as 🌐 Controller
    participant Mediator as 🎭 Mediator
    participant QueryHandler as 🔎 Query<br/>Handler
    participant ReadRepo as 📚 Read Model<br/>Repository
    participant MongoDB as 🍃 MongoDB

    Note over Client,MongoDB: Query Execution (Read Side - Optimized)

    Client->>+API: GET /accounts/by-owner/{owner_id}
    API->>API: Create Query<br/>GetAccountsByOwnerQuery
    API->>+Mediator: Execute query

    Mediator->>+QueryHandler: handle_async(query)

    Note over QueryHandler,MongoDB: Query Optimized Read Model

    QueryHandler->>+ReadRepo: find_by_criteria_async<br/>({owner_id: "{id}"})
    ReadRepo->>+MongoDB: db.bank_accounts.find<br/>({owner_id: "{id}"})

    Note over MongoDB: Indexed query on<br/>denormalized data<br/>(no joins needed)

    MongoDB-->>-ReadRepo: [BankAccountDto,<br/>BankAccountDto, ...]
    ReadRepo-->>-QueryHandler: List of accounts

    QueryHandler->>QueryHandler: Apply business filters<br/>(if any)
    QueryHandler-->>-Mediator: OperationResult<br/>(List[AccountDto])

    Mediator-->>-API: Result
    API->>API: Map to API DTOs
    API-->>-Client: 200 OK<br/>[{id, balance, owner}, ...]

    Note over Client,MongoDB: Fast query without<br/>replaying events
```

## 🔄 Read Model Reconciliation Patterns

### Projection Strategy

OpenBank implements a **continuous projection** pattern where domain events are projected into read models in real-time:

```python
class BankAccountDomainEventHandler(DomainEventHandler):
    """Projects domain events into read models."""

    def __init__(self,
                 mediator: Mediator,
                 mapper: Mapper,
                 write_models: Repository[BankAccount, str],
                 read_models: Repository[BankAccountDto, str],
                 cloud_event_bus: CloudEventBus):
        super().__init__()
        self.mediator = mediator
        self.mapper = mapper
        self.write_models = write_models
        self.read_models = read_models
        self.cloud_event_bus = cloud_event_bus

    @dispatch(BankAccountCreatedDomainEventV1)
    async def handle_async(self, event: BankAccountCreatedDomainEventV1) -> None:
        """Project account creation into read model."""

        # Get owner information (from another read model)
        owner: PersonDto = (await self.mediator.execute_async(
            GetByIdQuery[PersonDto, str](event.owner_id)
        )).data

        # Get or create read model
        bank_account = await self.get_or_create_read_model_async(event.aggregate_id)

        # Project event data
        bank_account.id = event.aggregate_id
        bank_account.owner_id = owner.id
        bank_account.owner = f"{owner.first_name} {owner.last_name}"
        bank_account.balance = Decimal(0)
        bank_account.overdraft_limit = event.overdraft_limit
        bank_account.created_at = event.created_at

        # Save to read model store
        await self.read_models.update_async(bank_account)

        # Publish integration event
        await self.publish_cloud_event_async(event)

    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    async def handle_async(self, event: BankAccountTransactionRecordedDomainEventV1) -> None:
        """Project transaction into read model balance."""

        # Load current read model
        bank_account = await self.get_or_create_read_model_async(event.aggregate_id)

        if not hasattr(bank_account, "balance"):
            bank_account.balance = Decimal(0)

        # Apply balance change based on transaction type
        transaction = event.transaction
        current_balance = Decimal(bank_account.balance)

        if transaction.type == BankTransactionTypeV1.DEPOSIT.value:
            bank_account.balance = current_balance + Decimal(transaction.amount)
        elif transaction.type == BankTransactionTypeV1.WITHDRAWAL.value:
            bank_account.balance = current_balance - Decimal(transaction.amount)
        elif transaction.type == BankTransactionTypeV1.TRANSFER.value:
            if transaction.to_account_id == bank_account.id:
                # Incoming transfer
                bank_account.balance = current_balance + Decimal(transaction.amount)
            else:
                # Outgoing transfer
                bank_account.balance = current_balance - Decimal(transaction.amount)
        elif transaction.type == BankTransactionTypeV1.INTEREST.value:
            bank_account.balance = current_balance + Decimal(transaction.amount)

        bank_account.last_modified = event.created_at

        # Update read model
        await self.read_models.update_async(bank_account)

        # Publish integration event
        await self.publish_cloud_event_async(event)
```

### Eventual Consistency Handling

**Key Concepts:**

1. **Write-Read Lag**: Small delay between command execution and read model update
2. **Idempotency**: Event handlers must handle duplicate events safely
3. **Ordering**: Events processed in order per aggregate stream
4. **Retry Logic**: Failed projections are retried automatically

**Consistency Guarantees:**

```mermaid
graph TB
    subgraph "Consistency Model"
        WriteModel["📝 Write Model<br/>(Immediate Consistency)"]
        EventStore["🗄️ Event Store<br/>(Source of Truth)"]
        ReadModel["📚 Read Model<br/>(Eventual Consistency)"]

        WriteModel -->|"Sync<br/>(Transactional)"| EventStore
        EventStore -->|"Async<br/>(Subscription)"| ReadModel
    end

    subgraph "Guarantees"
        StrongConsist["✅ Strong Consistency<br/>within Aggregate"]
        EventualConsist["⏰ Eventual Consistency<br/>across Aggregates"]
    end

    WriteModel -.->|Provides| StrongConsist
    ReadModel -.->|Provides| EventualConsist

    style WriteModel fill:#ffccbc
    style ReadModel fill:#c8e6c9
    style EventStore fill:#fff9c4
```

### Error Recovery Patterns

**1. Missing Read Model Recovery:**

```python
async def get_or_create_read_model_async(self, aggregate_id: str) -> BankAccountDto:
    """Get read model or reconstruct from event stream."""

    # Try to get existing read model
    read_model = await self.read_models.get_by_id_async(aggregate_id)

    if read_model:
        return read_model

    # Read model missing - reconstruct from write model
    logger.warning(f"Read model missing for {aggregate_id}, reconstructing...")

    # Load aggregate from event store
    aggregate = await self.write_models.get_by_id_async(aggregate_id)

    if not aggregate:
        raise ValueError(f"Aggregate {aggregate_id} not found in event store")

    # Map aggregate state to read model
    read_model = self.mapper.map(aggregate.state, BankAccountDto)
    read_model.id = aggregate_id

    # Save reconstructed read model
    await self.read_models.add_async(read_model)

    logger.info(f"Read model reconstructed for {aggregate_id}")
    return read_model
```

**2. Event Processing Failure Handling:**

```python
async def handle_async(self, event: DomainEvent) -> None:
    """Handle event with retry logic."""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Process event
            await self._process_event(event)
            return  # Success

        except TemporaryError as e:
            retry_count += 1
            if retry_count >= max_retries:
                # Log to dead letter queue
                await self.dead_letter_queue.send_async(event, str(e))
                logger.error(f"Failed to process event after {max_retries} retries: {e}")
                raise

            # Exponential backoff
            wait_time = 2 ** retry_count
            await asyncio.sleep(wait_time)
            logger.warning(f"Retrying event processing (attempt {retry_count}): {e}")

        except PermanentError as e:
            # Don't retry, log and skip
            logger.error(f"Permanent error processing event: {e}")
            await self.dead_letter_queue.send_async(event, str(e))
            return
```

## 📸 Snapshot Strategy

### Why Snapshots?

As aggregates accumulate many events, replaying all events becomes expensive. **Snapshots** are periodic "checkpoints" of aggregate state:

```mermaid
graph LR
    subgraph "Without Snapshots"
        Events1["Event 1<br/>(Created)"]
        Events2["Event 2"]
        Events3["Event 3"]
        EventsN["Event ...<br/>Event 1000"]
        ReplayAll["⏱️ Replay All<br/>1000 Events"]

        Events1 --> Events2
        Events2 --> Events3
        Events3 --> EventsN
        EventsN --> ReplayAll
    end

    subgraph "With Snapshots"
        Snapshot["📸 Snapshot<br/>(State at Event 900)"]
        RecentEvents["Event 901<br/>Event 902<br/>...<br/>Event 1000"]
        QuickReplay["⚡ Replay Only<br/>100 Events"]

        Snapshot --> RecentEvents
        RecentEvents --> QuickReplay
    end

    style ReplayAll fill:#ffccbc
    style QuickReplay fill:#c8e6c9
```

**When to Use Snapshots:**

✅ Aggregates with many events (>100)
✅ Frequently accessed aggregates
✅ Complex state reconstruction logic
✅ Performance-critical operations

### Implementing Snapshots

**1. Snapshot Storage in KurrentDB:**

```python
from decimal import Decimal
from neuroglia.data.abstractions import AggregateState

class BankAccountStateV1(AggregateState[str]):
    """Snapshotable aggregate state."""

    owner_id: str
    transactions: List[BankTransactionV1] = []
    balance: Decimal
    overdraft_limit: Decimal

    def _compute_balance(self):
        """Compute balance from all transactions.

        Note: This is expensive with many transactions.
        Snapshots avoid recomputing for every load.
        """
        balance = Decimal(0)
        for transaction in self.transactions:
            if transaction.type == BankTransactionTypeV1.DEPOSIT.value:
                balance += Decimal(transaction.amount)
            elif transaction.type == BankTransactionTypeV1.WITHDRAWAL.value:
                balance -= Decimal(transaction.amount)
            # ... handle other transaction types
        self.balance = balance
```

**2. Snapshot Configuration:**

```python
from neuroglia.data.infrastructure.event_sourcing import EventSourcingRepository

class SnapshotConfiguration:
    """Configure snapshot behavior."""

    # Take snapshot every N events
    SNAPSHOT_INTERVAL = 100

    # Keep last N snapshots
    MAX_SNAPSHOTS = 10

    @staticmethod
    def should_create_snapshot(version: int) -> bool:
        """Determine if snapshot should be created."""
        return version > 0 and version % SnapshotConfiguration.SNAPSHOT_INTERVAL == 0

# In repository implementation
class EventSourcingRepository(Repository[TAggregateRoot, TKey]):

    async def get_by_id_async(self, aggregate_id: TKey) -> TAggregateRoot:
        """Load aggregate with snapshot optimization."""

        # Try to load latest snapshot
        snapshot = await self.event_store.load_snapshot_async(aggregate_id)

        if snapshot:
            # Start from snapshot version
            aggregate = self._create_aggregate_from_snapshot(snapshot)
            from_version = snapshot.version
        else:
            # Start from beginning
            aggregate = self._create_new_aggregate(aggregate_id)
            from_version = 0

        # Load events after snapshot
        events = await self.event_store.load_events_async(
            aggregate_id,
            from_version=from_version
        )

        # Replay events
        for event in events:
            aggregate.state.on(event)

        return aggregate

    async def update_async(self, aggregate: TAggregateRoot) -> None:
        """Save aggregate with snapshot creation."""

        # Get uncommitted events
        events = aggregate.get_uncommitted_events()

        # Append events to stream
        await self.event_store.append_events_async(
            aggregate.id,
            events,
            expected_version=aggregate.version
        )

        # Check if snapshot should be created
        new_version = aggregate.version + len(events)
        if SnapshotConfiguration.should_create_snapshot(new_version):
            await self._create_snapshot_async(aggregate, new_version)

        aggregate.clear_uncommitted_events()

    async def _create_snapshot_async(self, aggregate: TAggregateRoot, version: int) -> None:
        """Create and save snapshot."""
        snapshot = {
            "aggregate_id": aggregate.id,
            "aggregate_type": type(aggregate).__name__,
            "version": version,
            "state": self._serialize_state(aggregate.state),
            "timestamp": datetime.utcnow()
        }

        await self.event_store.save_snapshot_async(snapshot)
        logger.info(f"Snapshot created for {aggregate.id} at version {version}")
```

**3. Snapshot Storage in KurrentDB:**

KurrentDB (EventStoreDB) stores snapshots in special streams:

```python
# Snapshot stream naming convention
def get_snapshot_stream_name(aggregate_id: str) -> str:
    return f"$snapshot-{aggregate_id}"

# Save snapshot
async def save_snapshot_async(self, snapshot: dict) -> None:
    """Save snapshot to EventStoreDB."""
    stream_name = get_snapshot_stream_name(snapshot["aggregate_id"])

    event_data = {
        "type": "snapshot",
        "data": snapshot
    }

    # Append to snapshot stream
    await self.client.append_to_stream(
        stream_name=stream_name,
        events=[event_data]
    )

# Load snapshot
async def load_snapshot_async(self, aggregate_id: str) -> Optional[dict]:
    """Load latest snapshot from EventStoreDB."""
    stream_name = get_snapshot_stream_name(aggregate_id)

    try:
        # Read last event from snapshot stream
        result = await self.client.read_stream(
            stream_name=stream_name,
            direction="backwards",
            count=1
        )

        if result:
            return result[0].data
    except StreamNotFoundError:
        return None

    return None
```

### Performance Comparison

```mermaid
graph TB
    subgraph "Performance Metrics"
        NoSnapshot["❌ No Snapshot<br/>1000 events<br/>Load Time: 850ms"]
        WithSnapshot["✅ With Snapshot<br/>100 events after snapshot<br/>Load Time: 95ms"]
        Improvement["🚀 89% Faster"]
    end

    NoSnapshot -.->|"Optimize with"| WithSnapshot
    WithSnapshot -.->|"Results in"| Improvement

    style NoSnapshot fill:#ffccbc
    style WithSnapshot fill:#c8e6c9
    style Improvement fill:#fff9c4
```

## 🔌 KurrentDB (EventStoreDB) Integration

### Connection and Configuration

OpenBank uses **KurrentDB** (the new name for EventStoreDB) for event storage:

```python
from neuroglia.data.infrastructure.event_sourcing.event_store import ESEventStore
from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions

# Configuration
database_name = "openbank"
consumer_group = "openbank-projections"

# Configure in application builder
ESEventStore.configure(builder, EventStoreOptions(database_name, consumer_group))
```

### Connection Pattern

Reference: [KurrentDB Python Client Getting Started](https://docs.kurrent.io/clients/python/v1.0/getting-started.html)

```python
from esdbclient import EventStoreDBClient, NewEvent, StreamState

class KurrentDBConnection:
    """Connection manager for KurrentDB."""

    def __init__(self, connection_string: str):
        self.client = EventStoreDBClient(uri=connection_string)

    async def connect_async(self) -> None:
        """Establish connection to KurrentDB."""
        # Connection string format:
        # esdb://admin:changeit@localhost:2113?tls=false

        try:
            # Verify connection
            await self.client.read_stream("$stats-127.0.0.1:2113", direction="backwards", count=1)
            logger.info("Connected to KurrentDB")
        except Exception as e:
            logger.error(f"Failed to connect to KurrentDB: {e}")
            raise
```

### Stream Naming Conventions

OpenBank follows consistent stream naming:

```python
class StreamNamingConvention:
    """Standard stream naming for OpenBank."""

    @staticmethod
    def aggregate_stream(aggregate_type: str, aggregate_id: str) -> str:
        """Get stream name for aggregate.

        Examples:
            - bank-account-550e8400e29b41d4a716446655440000
            - person-7c9e6679e58a43d9a1eb84c0a65c3f91
        """
        return f"{aggregate_type.lower()}-{aggregate_id}"

    @staticmethod
    def category_stream(aggregate_type: str) -> str:
        """Get category stream name.

        Examples:
            - $ce-bank-account (all bank account streams)
            - $ce-person (all person streams)
        """
        return f"$ce-{aggregate_type.lower()}"

    @staticmethod
    def event_type_stream(event_type: str) -> str:
        """Get event type stream.

        Examples:
            - $et-BankAccountCreated
            - $et-TransactionRecorded
        """
        return f"$et-{event_type}"
```

### Event Serialization

```python
from dataclasses import asdict
import json
from typing import Any
from neuroglia.serialization.json import JsonSerializer

class EventSerializer:
    """Serialize/deserialize events for KurrentDB."""

    def __init__(self, json_serializer: JsonSerializer):
        self.json_serializer = json_serializer

    def serialize_event(self, event: DomainEvent) -> dict:
        """Serialize domain event to JSON."""
        return {
            "event_type": type(event).__name__,
            "data": self.json_serializer.serialize(event),
            "metadata": {
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "timestamp": event.created_at.isoformat(),
                "correlation_id": event.correlation_id,
                "causation_id": event.causation_id
            }
        }

    def deserialize_event(self, event_data: dict) -> DomainEvent:
        """Deserialize event from JSON."""
        event_type = event_data["event_type"]
        event_class = self._get_event_class(event_type)

        return self.json_serializer.deserialize(
            event_data["data"],
            event_class
        )

    def _get_event_class(self, event_type: str) -> type:
        """Get event class by name."""
        # Use TypeFinder to locate event class
        from neuroglia.core import TypeFinder
        return TypeFinder.find_type(event_type)
```

### Subscription Patterns

**1. Catch-Up Subscription (Read Models):**

```python
class ReadModelProjection:
    """Subscribe to all events for read model projection."""

    async def start_projection_async(self):
        """Start catch-up subscription from beginning."""

        # Subscribe to $all stream (all events)
        async for event in self.client.subscribe_to_all(
            from_end=False,  # Start from beginning
            filter_include=["BankAccount", "Person"],  # Filter event types
            consumer_group="openbank-projections"
        ):
            await self._handle_event_async(event)

    async def _handle_event_async(self, event):
        """Project event into read model."""
        domain_event = self.serializer.deserialize_event(event)

        # Dispatch to appropriate handler
        await self.event_dispatcher.dispatch_async(domain_event)
```

**2. Persistent Subscription (Competing Consumers):**

```python
async def create_persistent_subscription():
    """Create persistent subscription for competing consumers."""

    await client.create_subscription_to_stream(
        group_name="openbank-projections",
        stream_name="$ce-bank-account",
        settings={
            "resolve_link_tos": True,
            "max_retry_count": 10,
            "message_timeout": 30
        }
    )

async def consume_subscription():
    """Consume from persistent subscription."""

    async for event in client.read_subscription_to_stream(
        group_name="openbank-projections",
        stream_name="$ce-bank-account"
    ):
        try:
            await process_event_async(event)
            await client.ack(event)  # Acknowledge processing
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            await client.nack(event, action="retry")  # Retry later
```

### Optimistic Concurrency

```python
async def append_events_with_concurrency_check(
    stream_name: str,
    events: List[DomainEvent],
    expected_version: int
) -> None:
    """Append events with optimistic concurrency check."""

    try:
        # Append with expected version check
        result = await client.append_to_stream(
            stream_name=stream_name,
            events=[serialize_event(e) for e in events],
            current_version=expected_version  # Concurrency check
        )

        logger.info(f"Appended {len(events)} events to {stream_name}")
        return result.next_expected_version

    except WrongExpectedVersionError as e:
        # Another process modified the stream
        logger.warning(f"Concurrency conflict on {stream_name}: {e}")
        raise ConcurrencyException(
            f"Stream {stream_name} was modified by another process"
        )
```

## 🚀 Getting Started

### Quick Start with CLI

```bash
# Start OpenBank and dependencies
./openbank start

# Check status
./openbank status

# View logs
./openbank logs -f

# Access services
# - API: http://localhost:8899/api/docs
# - KurrentDB UI: http://localhost:2113 (admin/changeit)
# - MongoDB Express: http://localhost:8081
```

### Example Workflow

**1. Register a Person:**

```bash
curl -X POST "http://localhost:8899/api/v1/persons" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Smith",
    "date_of_birth": "1990-05-15",
    "nationality": "US",
    "gender": "FEMALE"
  }'
```

**2. Create Bank Account:**

```bash
curl -X POST "http://localhost:8899/api/v1/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "{PERSON_ID_FROM_ABOVE}",
    "overdraft_limit": 500.00
  }'
```

**3. Make Deposit:**

```bash
curl -X POST "http://localhost:8899/api/v1/transactions/deposit" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "{ACCOUNT_ID}",
    "amount": 1000.00,
    "description": "Initial deposit"
  }'
```

**4. View Account Balance:**

```bash
curl "http://localhost:8899/api/v1/accounts/{ACCOUNT_ID}"
```

### Viewing Events in KurrentDB

Access KurrentDB UI at `http://localhost:2113`:

1. Navigate to **Stream Browser**
2. Find stream: `bank-account-{account_id}`
3. View event history:
   - `BankAccountCreatedDomainEventV1`
   - `BankAccountTransactionRecordedDomainEventV1`
   - etc.

## 📚 Key Learnings

### Event Sourcing Benefits

✅ **Complete Audit Trail**: Every state change is recorded
✅ **Time Travel**: Reconstruct state at any point in time
✅ **Event Replay**: Fix bugs by replaying events with corrected logic
✅ **Business Intelligence**: Analyze business events for insights
✅ **Debugging**: Full history of what happened and when

### CQRS Benefits

✅ **Optimized Read Models**: Denormalized for query performance
✅ **Scalability**: Read and write sides scale independently
✅ **Flexibility**: Multiple read models for different use cases
✅ **Performance**: No joins or complex queries on read side

### DDD Benefits

✅ **Business Logic in Domain**: Close to ubiquitous language
✅ **Rich Aggregates**: Encapsulate business rules
✅ **Event-Driven**: Natural fit for business processes
✅ **Testability**: Domain logic independent of infrastructure

## 🔗 Related Documentation

- **[Event Sourcing Pattern](../patterns/event-sourcing.md)** - Detailed event sourcing concepts
- **[CQRS Pattern](../patterns/cqrs.md)** - Command Query Responsibility Segregation
- **[Domain-Driven Design](../patterns/domain-driven-design.md)** - DDD principles and aggregates
- **[Repository Pattern](../patterns/repository.md)** - Data access abstraction
- **[Getting Started](../getting-started.md)** - Basic Neuroglia setup

## 💡 Production Considerations

### Monitoring and Observability

- **Event Store Metrics**: Monitor stream lengths, subscription lag
- **Read Model Lag**: Track delay between write and read models
- **Projection Errors**: Alert on failed event processing
- **Snapshot Performance**: Monitor snapshot creation and usage

### Scaling Strategies

- **Horizontal Scaling**: Multiple read model projections with competing consumers
- **Sharding**: Partition aggregates by ID ranges
- **Caching**: Cache frequently accessed read models
- **Snapshot Tuning**: Adjust snapshot intervals based on load

### Data Management

- **Event Stream Archiving**: Archive old events to cold storage
- **Read Model Rebuilding**: Capability to rebuild read models from events
- **Backup Strategy**: Backup both event store and read models
- **GDPR Compliance**: Handle right-to-be-forgotten with event encryption

---

**OpenBank demonstrates production-ready event sourcing and CQRS patterns that can be adapted for your own domain!**
