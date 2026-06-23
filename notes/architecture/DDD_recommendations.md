# Proposal: First-Class Support for State-Based Persistence and Automatic Domain Event Dispatching

---

### 1. Summary

This document proposes the introduction of a first-class, integrated mechanism to support **state-based persistence** for DDD `AggregateRoot` objects within the `neuroglia-python` framework. The core of this proposal is a new **`UnitOfWork` service** and a corresponding **`DomainEventDispatchingMiddleware`**. This combination will allow developers to use traditional persistence patterns (e.g., with MongoDB or SQLAlchemy) while automatically dispatching domain events after the primary business transaction has successfully completed, ensuring consistency and simplifying application logic.

---

### 2. Motivation

The Neuroglia framework provides excellent, in-depth support for advanced patterns like Event Sourcing, as detailed in the official documentation. However, Event Sourcing is a complex pattern with a steep learning curve that is not suitable for all projects.

A significant number of applications are built using a more traditional **state-based persistence** model, where the current state of an aggregate is stored directly in a database. Currently, developers who wish to use this common pattern with Neuroglia must manually implement the logic for dispatching domain events, often leading to repetitive code in command handlers and a potential for inconsistencies if not handled carefully.

By providing a built-in, automated solution, Neuroglia can:

- **Lower the barrier to entry** for developers new to DDD.
- **Broaden its appeal** to projects where Event Sourcing is overkill.
- **Enforce best practices** for transactional consistency between state persistence and event publication.
- **Simplify application handlers**, allowing them to focus purely on orchestrating domain logic.

---

### 3. Proposed Solution

The proposed solution consists of three core components that work together seamlessly with the existing dependency injection and mediation pipeline.

1. **`IUnitOfWork` Service**: A request-scoped service responsible for tracking all `AggregateRoot` instances that are loaded or created during a single business transaction (i.e., a single command execution).
2. **`DomainEventDispatchingMiddleware`**: A mediation middleware that sits in the pipeline. After the command handler successfully executes and the database transaction is committed, this middleware will query the `IUnitOfWork` service for all tracked aggregates, collect their pending domain events, and dispatch them via the `Mediator`.
3. **Repository Integration**: Repositories will be modified to accept an `IUnitOfWork` dependency. They will register each aggregate they load or create with the `IUnitOfWork`, making them available to the middleware.

This approach is fully aligned with the framework's commitment to **Clean Architecture**, as described at [https://bvandewe.github.io/pyneuro/patterns/clean-architecture/](https://bvandewe.github.io/pyneuro/patterns/clean-architecture/). The domain, application, and infrastructure layers remain perfectly decoupled.

---

### 4. Detailed Implementation Guide

The following code provides a concrete implementation plan for the proposed components.

#### 4.1. The Unit of Work Service

This service acts as the central tracker for aggregates within a request.

```python
# neuroglia/domain/infrastructure.py (or a new file)

from typing import Iterable
from neuroglia.dependency_injection import Scoped
from neuroglia.domain.models import AggregateRoot, DomainEvent

class IUnitOfWork:
    """Defines the interface for a Unit of Work that tracks aggregates."""
    def track(self, aggregate: AggregateRoot):
        raise NotImplementedError

    @property
    def pending_domain_events(self) -> Iterable[DomainEvent]:
        raise NotImplementedError

@Scoped(IUnitOfWork)
class UnitOfWork(IUnitOfWork):
    """A request-scoped implementation of the Unit of Work."""
    def __init__(self):
        self._tracked_aggregates: set[AggregateRoot] = set()

    def track(self, aggregate: AggregateRoot):
        """Adds an aggregate to be tracked by the Unit of Work."""
        self._tracked_aggregates.add(aggregate)

    @property
    def pending_domain_events(self) -> Iterable[DomainEvent]:
        """Collects all domain events from all tracked aggregates."""
        for aggregate in self._tracked_aggregates:
            yield from aggregate.domain_events
```

#### 4.2. The Domain Event Dispatching Middleware

This middleware orchestrates the event dispatching process.

```python
# neuroglia/mediation/middleware.py (or a new file)

from neuroglia.mediation import Mediator, Request
from neuroglia.mediation.middleware import Middleware
from ..domain.infrastructure import IUnitOfWork # Relative import

class DomainEventDispatchingMiddleware(Middleware):
    """
    A middleware that automatically dispatches domain events from aggregates
    tracked by the Unit of Work after a command has been handled.
    """
    def __init__(self, uow: IUnitOfWork, mediator: Mediator):
        self._uow = uow
        self._mediator = mediator

    async def handle(self, request: Request, next: callable):
        # 1. Allow the command handler and persistence logic to execute first.
        # If this fails, an exception will be thrown and the events will not be dispatched.
        result = await next(request)

        # 2. After successful completion, collect and dispatch events.
        events_to_dispatch = list(self._uow.pending_domain_events)

        if not events_to_dispatch:
            return result

        for event in events_to_dispatch:
            await self._mediator.publish_async(event)

        return result
```

#### 4.3. Example Repository Integration

Repositories become clients of the `IUnitOfWork` service.

```python
# In user's infrastructure code (as an example)
from motor.motor_asyncio import AsyncIOMotorCollection
from neuroglia.domain.infrastructure import IUnitOfWork

class PizzaMongodbRepository(IPizzaRepository):
    def __init__(self, collection: AsyncIOMotorCollection, uow: IUnitOfWork):
        self._collection = collection
        self._uow = uow

    async def get_by_id_async(self, id: str) -> Pizza | None:
        doc = await self._collection.find_one({"_id": id})
        if not doc: return None
        pizza = self._from_document(doc)
        self._uow.track(pizza)  # Track the loaded aggregate
        return pizza

    async def add_async(self, pizza: Pizza) -> None:
        # ... persistence logic ...
        self._uow.track(pizza)  # Track the new aggregate
```

---

### 5\. Wiring and Configuration

To make this feature easy to adopt, a new extension method for the service collection should be created. This provides a single point of configuration for the user.

```python
# neuroglia/dependency_injection/__init__.py (or similar)

from ..domain.infrastructure import IUnitOfWork, UnitOfWork
from ..mediation.middleware import DomainEventDispatchingMiddleware

class ServiceCollection:
    # ... existing methods ...

    def add_state_based_persistence(self):
        """
        Registers the necessary services for state-based persistence with
        automatic domain event dispatching.
        """
        self.try_add_scoped(IUnitOfWork, UnitOfWork)
        self.add_middleware(DomainEventDispatchingMiddleware)
        return self
```

A user would then simply call `services.add_state_based_persistence()` during their application setup.

---

### 6\. Alignment with Neuroglia's Philosophy

This proposal reinforces Neuroglia's commitment to the principles of **Domain-Driven Design** (see [https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/](https://www.google.com/search?q=https://bvandewe.github.io/pyneuro/patterns/domain-driven-design/)). By automating the dispatch of domain events, it allows the `AggregateRoot` to remain the true center of the domain model, responsible for its state and for announcing important changes, without coupling the application layer to the dispatching mechanism.

---

### 7\. Benefits

- **Simplicity**: Command handlers become simpler and more focused.
- **Consistency**: Guarantees that domain events are only dispatched after the primary transaction is successful.
- **Decoupling**: The application layer is fully decoupled from the event publication mechanism.
- **Accessibility**: Makes the framework more approachable for teams not ready for Event Sourcing.

---

### 8\. Conclusion

We believe that implementing first-class support for state-based persistence will make Neuroglia a more versatile and powerful framework for a wider range of Python developers. This proposal provides a clear, robust, and non-breaking path to achieving that goal, strengthening the framework's DDD capabilities while improving the developer experience.
