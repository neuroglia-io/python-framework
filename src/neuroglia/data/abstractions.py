from abc import ABC
from datetime import datetime, timezone
from typing import Generic, TypeVar

TKey = TypeVar("TKey")
""" Represents the generic argument used to specify the type of key to use """


class Identifiable(Generic[TKey], ABC):
    """
    Defines the abstraction for objects that can be uniquely identified within the domain.

    This fundamental abstraction provides the foundation for all entities, aggregates, and value objects
    that require unique identification in domain-driven design patterns.

    Type Parameters:
        TKey: The type of the unique identifier (str, int, UUID, etc.)

    Attributes:
        id (TKey): The unique identifier for this object

    Examples:
        ```python
        from uuid import UUID, uuid4

        class User(Identifiable[UUID]):
            def __init__(self, name: str):
                self.id = uuid4()
                self.name = name

        class Product(Identifiable[str]):
            def __init__(self, sku: str, name: str):
                self.id = sku
                self.name = name
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Domain-Driven Design: https://bvandewe.github.io/pyneuro/patterns/
    """

    id: TKey
    """ Gets the object's unique identifier """


TEntity = TypeVar("TEntity", bound=Identifiable)
""" Represents the generic argument used to specify the type of entity to use """


class Entity(Generic[TKey], Identifiable[TKey], ABC):
    """Represents the abstract class inherited by all entities in the application"""

    def __init__(self) -> None:
        super().__init__()
        # Initialize created_at only if not already set (e.g., during deserialization)
        # Use timezone-aware UTC timestamp for consistency
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    created_at: datetime
    """ Gets the date and time the entity has been created at """

    last_modified: datetime
    """ Gets the date and time the entity was last modified at, if any """


class VersionedState(ABC):
    """
    Represents an abstraction for state objects that maintain version tracking.

    This abstraction is essential for implementing optimistic concurrency control, event sourcing,
    and temporal state management patterns in domain-driven applications.

    Attributes:
        state_version (int): The version number of this state, used for conflict detection and ordering

    Examples:
        ```python
        class CustomerState(VersionedState):
            def __init__(self, name: str, email: str):
                super().__init__()
                self.name = name
                self.email = email

        # Version tracking in action
        state = CustomerState("John", "john@example.com")
        assert state.state_version == 0

        # After updates, version should increment
        state.state_version += 1
        assert state.state_version == 1
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Event Sourcing Guide: https://bvandewe.github.io/pyneuro/patterns/event-sourcing/
    """

    def __init__(self):
        self.state_version = 0

    state_version: int = 0
    """ Gets the state's version """


class AggregateState(Generic[TKey], Identifiable[TKey], VersionedState, ABC):
    """
    Represents an abstraction for aggregate root state management with enhanced tracking capabilities.

    This abstraction combines unique identification, version tracking, and temporal metadata
    to provide comprehensive state management for domain aggregates in event-driven architectures.

    Type Parameters:
        TKey: The type of the unique identifier for the aggregate

    Attributes:
        id (TKey): The unique identifier of the aggregate this state belongs to
        created_at (datetime): The timestamp when the aggregate was created
        last_modified (datetime): The timestamp of the last modification, if any

    Examples:
        ```python
        from uuid import UUID, uuid4

        class OrderState(AggregateState[UUID]):
            def __init__(self, customer_id: str, items: List[OrderItem]):
                super().__init__()
                self.id = uuid4()
                self.customer_id = customer_id
                self.items = items
                self.total_amount = sum(item.price * item.quantity for item in items)

        # State with full tracking
        order_state = OrderState("cust123", [OrderItem("prod1", 2, 10.0)])
        assert order_state.state_version == 0
        assert order_state.created_at is not None
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Domain-Driven Design: https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/
        - Event Sourcing Guide: https://bvandewe.github.io/pyneuro/patterns/event-sourcing/
    """

    def __init__(self):
        super().__init__()
        # Initialize timestamp tracking fields only if not already set (e.g., during deserialization)
        # Use timezone-aware UTC timestamps for consistency across the application
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if not hasattr(self, "last_modified") or self.last_modified is None:
            self.last_modified = self.created_at

    id: TKey
    """ Gets the id of the aggregate the state belongs to """

    created_at: datetime
    """ Gets the date and time the aggregate has been created at """

    last_modified: datetime
    """ Gets the date and time, if any, the aggregate was last modified at """


TState = TypeVar("TState", bound=AggregateState)
""" Represents the generic argument used to specify the state of an aggregate root """


class DomainEvent(Generic[TKey], ABC):
    """Represents the base class inherited by all domain events"""

    def __init__(self, aggregate_id: TKey):
        """Initializes a new domain event"""
        self.created_at = datetime.now()
        self.aggregate_id = aggregate_id

    created_at: datetime
    """ Gets the date and time the domain event has been created at """

    aggregate_id: TKey
    """ Gets the id of the aggregate that has produced the domain event """

    aggregate_version: int
    """ Gets the version of the aggregate's state, after reducing the domain event """


TEvent = TypeVar("TEvent", bound=DomainEvent)
""" Represents the generic argument used to specify the state of an aggregate root """


class AggregateRoot(Generic[TState, TKey], Entity[TKey], ABC):
    """
    Represents the abstraction for aggregate roots in domain-driven design.

    This abstraction encapsulates business logic, maintains consistency boundaries,
    and orchestrates domain events for complex business operations. Aggregate roots
    are the only entry points for modifying aggregate data and ensuring business rules.

    Type Parameters:
        TState: The type of the aggregate's state object
        TKey: The type of the unique identifier for the aggregate

    Attributes:
        state (TState): The current state of the aggregate
        _pending_events (List[DomainEvent]): Domain events pending persistence

    Examples:
        ```python
        class OrderAggregate(AggregateRoot[OrderState, UUID]):
            def __init__(self, customer_id: str):
                super().__init__()
                self.state = OrderState(customer_id)
                self.register_event(OrderCreatedEvent(self.id, customer_id))

            def add_item(self, product_id: str, quantity: int, price: Decimal):
                # Business logic here
                if quantity <= 0:
                    raise ValueError("Quantity must be positive")

                item = OrderItem(product_id, quantity, price)
                self.state.items.append(item)
                self.register_event(ItemAddedEvent(self.id, product_id, quantity))

        class Task(AggregateRoot[TaskState, str]):
            def assign(self, *, user_id: str) -> None:
                self.state.assignee_id = user_id
                self.register_event(TaskAssigned(self.id, user_id))
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Domain-Driven Design: https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/
        - Event Sourcing Guide: https://bvandewe.github.io/pyneuro/patterns/event-sourcing/
    """

    _pending_events: list[DomainEvent]
    """ Gets a list containing all domain events pending persistence """

    def __init__(self) -> None:
        """Initializes a new aggregate root"""
        state_type = self._get_state_type()
        self.state = object.__new__(state_type)
        state_type.__init__(self.state)
        self._pending_events = list[DomainEvent]()

    def id(self):  # type: ignore[override]
        """Gets the aggregate root's id"""
        return self.state.id

    state: TState
    """ Gets the aggregate root's state """

    def register_event(self, e: TEvent) -> TEvent:
        """Registers the specified domain event"""
        if not hasattr(self, "_pending_events"):
            self._pending_events = list[DomainEvent]()
        self._pending_events.append(e)
        e.aggregate_version = self.state.state_version + len(self._pending_events)
        return e

    def clear_pending_events(self):
        """Clears all pending domain events"""
        self._pending_events.clear()

    @property
    def domain_events(self) -> list[DomainEvent]:
        """
        Gets the list of domain events pending persistence.

        This property provides compatibility with the state-based persistence model
        while maintaining backward compatibility with existing event-sourcing patterns.
        It returns the same events as get_uncommitted_events() method.

        Returns:
            List of domain events raised by this aggregate that haven't been persisted

        Examples:
            ```python
            # State-based persistence usage
            user = User.create("john@example.com", "John Doe")
            events = user.domain_events  # [UserCreatedEvent]

            # Register with UnitOfWork for automatic dispatching
            unit_of_work.register_aggregate(user)

            # Events will be collected and dispatched by middleware
            ```
        """
        return self._pending_events.copy()

    def get_uncommitted_events(self) -> list[DomainEvent]:
        """
        Gets all uncommitted domain events for event sourcing compatibility.

        This method maintains compatibility with existing event-sourced aggregates
        while also supporting the new state-based persistence model through the
        domain_events property.

        Returns:
            List of uncommitted domain events
        """
        return self._pending_events.copy()

    @classmethod
    def _get_state_type(cls):
        """Resolves the state type declared for the aggregate root."""
        orig_bases = getattr(cls, "__orig_bases__", None)
        if orig_bases:
            base = orig_bases[0]
            if hasattr(base, "__args__") and base.__args__:
                return base.__args__[0]
        raise TypeError(f"{cls.__name__} must specify an AggregateState generic argument")


TAggregate = TypeVar("TAggregate", bound=AggregateRoot)
""" Represents the generic argument used to specify an aggregate root type """


def queryable(cls):
    """
    Decorator that marks a class as queryable for advanced query capabilities.

    This decorator enables classes to participate in LINQ-style query operations
    and advanced filtering patterns provided by the framework's query infrastructure.

    Args:
        cls: The class to mark as queryable

    Returns:
        The decorated class with queryable metadata

    Examples:
        ```python
        @queryable
        class Product:
            def __init__(self, name: str, price: Decimal, category: str):
                self.name = name
                self.price = price
                self.category = category

        # Now Product can be used with advanced querying
        products = repository.query(Product).where(lambda p: p.price > 10.0).to_list()
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
    """
    cls.__queryable__ = True
    return cls
