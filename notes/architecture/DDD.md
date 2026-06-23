Of course. Here is a sample implementation showing how to persist a `Pizza` `AggregateRoot` into MongoDB using a dedicated repository and a command handler, while still respecting the Unit of Work concept.

For MongoDB, the **Unit of Work** is often managed at the level of a single aggregate. Since an aggregate is a consistency boundary, saving its entire state in one atomic operation (like `insert_one` or `replace_one`) fulfills the pattern's goal.

We'll use the `motor` library, the official `asyncio` driver for MongoDB.

---

### \#\# 1. The Domain Model (Unchanged)

First, our `Pizza` `AggregateRoot` remains completely ignorant of how it's being stored. This is a core principle of DDD and Clean Architecture.

```python
# In your domain layer
import uuid

class Pizza(AggregateRoot[str]):
    def __init__(self, name: str, id: str = None):
        super().__init__(id or str(uuid.uuid4()))
        self.name = name
        self.toppings = []
        self.is_baked = False

    def add_topping(self, topping: str):
        if self.is_baked:
            raise DomainException("Cannot add toppings to a baked pizza!")
        self.toppings.append(topping)
```

---

### \#\# 2. The MongoDB Repository Implementation

This is where we connect our domain model to the database. The repository's job is to handle the mapping between the Python `Pizza` object and a MongoDB document.

Notice we now have an `update_async` method. Unlike a traditional ORM that tracks changes automatically, with a document database, it's often more explicit to tell the repository to save the current state of the aggregate.

```python
# In your infrastructure layer
from motor.motor_asyncio import AsyncIOMotorCollection
from your_domain import Pizza
from your_application import IPizzaRepository # Abstract interface

class PizzaMongodbRepository(IPizzaRepository):

    def __init__(self, collection: AsyncIOMotorCollection):
        # The MongoDB collection is injected.
        self._collection = collection

    def _to_document(self, pizza: Pizza) -> dict:
        """Maps the Pizza object to a MongoDB document."""
        return {
            "_id": pizza.id,
            "name": pizza.name,
            "toppings": pizza.toppings,
            "is_baked": pizza.is_baked
        }

    def _from_document(self, doc: dict) -> Pizza:
        """Maps a MongoDB document back to a Pizza object."""
        pizza = Pizza(name=doc["name"], id=doc["_id"])
        pizza.toppings = doc["toppings"]
        pizza.is_baked = doc["is_baked"]
        return pizza

    async def get_by_id_async(self, id: str) -> Pizza | None:
        doc = await self._collection.find_one({"_id": id})
        return self._from_document(doc) if doc else None

    async def add_async(self, pizza: Pizza) -> None:
        """Adds a new pizza. This is an atomic operation."""
        doc = self._to_document(pizza)
        await self._collection.insert_one(doc)

    async def update_async(self, pizza: Pizza) -> None:
        """
        Updates an existing pizza. This is the key method for saving changes.
        replace_one is atomic, ensuring the entire aggregate state is saved consistently.
        """
        doc = self._to_document(pizza)
        await self._collection.replace_one({"_id": pizza.id}, doc)
```

---

### \#\# 3. The Command Handler Implementation

Now, let's see how a command handler uses this repository. The handler orchestrates the workflow: **get the aggregate, execute domain logic, and save the new state**.

Here's a handler for creating a new pizza.

#### Example 1: Creating a New Pizza

```python
# In your application layer
from neuroglia.mapping import Mapper
from neuroglia.mediation import CommandHandler

class CreatePizzaCommand:
    """A DTO representing the command to create a pizza."""
    name: str

class CreatePizzaCommandHandler(CommandHandler[CreatePizzaCommand, str]):

    def __init__(self, mapper: Mapper, pizzas: IPizzaRepository):
        self._mapper = mapper
        self._pizzas = pizzas

    async def handle(self, command: CreatePizzaCommand) -> str:
        # 1. Create a new aggregate instance
        pizza = Pizza(name=command.name)

        # 2. Add the new aggregate to the repository
        await self._pizzas.add_async(pizza)

        # 3. Return the ID of the newly created pizza
        return pizza.id
```

#### Example 2: Modifying an Existing Pizza

This example demonstrates the full "Unit of Work" cycle for a single aggregate.

```python
# In your application layer
class AddToppingToPizzaCommand:
    """A DTO representing the command to add a topping."""
    pizza_id: str
    topping: str

class AddToppingToPizzaCommandHandler(CommandHandler[AddToppingToPizzaCommand, None]):

    def __init__(self, pizzas: IPizzaRepository):
        self._pizzas = pizzas

    async def handle(self, command: AddToppingToPizzaCommand) -> None:
        # 1. Retrieve the aggregate from persistence
        pizza = await self._pizzas.get_by_id_async(command.pizza_id)
        if not pizza:
            raise NotFoundException(f"Pizza with id '{command.pizza_id}' not found")

        # 2. Execute the domain logic on the aggregate
        pizza.add_topping(command.topping)

        # 3. Persist the new state of the aggregate
        # The update_async call atomically saves the entire changed object.
        await self._pizzas.update_async(pizza)
```

Excellent question. In the state-based persistence model we just illustrated, the handling of **aggregate state** and **domain events** is explicitly separated. They have distinct roles and are managed at different stages of the process.

Here’s a clear breakdown:

---

### \#\# 1. How Aggregate State is Handled

The aggregate's state is its set of current properties (`name`, `toppings`, `is_baked`, etc.). In this model, the state is treated like a **snapshot**.

- **In-Memory**: While your command handler is running, the state exists **within the `Pizza` object instance**. When you call `pizza.add_topping("pepperoni")`, you are directly modifying the `toppings` list on that Python object. This is where your business logic operates and enforces its rules.
- **In Persistence (Database)**: The state is saved to the MongoDB collection as a **single document representing the final, current state** of the aggregate. The `PizzaMongodbRepository`'s `_to_document` method creates this snapshot. The database doesn't know _how_ the pizza got its toppings; it only knows what toppings it currently has.

Think of it as taking a **photograph**. You capture the final pose, not the series of movements that led to it.

---

### \#\# 2. How Domain Events are Handled

In a state-based model, domain events are not used to build the aggregate's state. Instead, they serve a different, crucial purpose: they are **notifications of side-effects** used to communicate that something important happened. They are the primary way to trigger downstream logic in other parts of your system _without creating tight coupling_.

Here’s the lifecycle of a domain event in this scenario:

#### Step 1: The Aggregate Raises the Event

The `AggregateRoot` is still responsible for creating events. You would modify your domain model to raise an event whenever its state changes in a way that other parts of the system might care about.

```python
# In your domain layer

# Define the event as a simple data class
@dataclass
class ToppingAddedToPizza(DomainEvent):
    pizza_id: str
    topping_name: str

class Pizza(AggregateRoot[str]):
    # ... (init and other methods) ...

    def add_topping(self, topping: str):
        if self.is_baked:
            raise DomainException("Cannot add toppings to a baked pizza!")
        self.toppings.append(topping)

        # Create and "raise" the event. The base AggregateRoot collects it.
        self._raise_event(ToppingAddedToPizza(
            pizza_id=self.id,
            topping_name=topping
        ))
```

#### Step 2: The Handler and Dispatcher Process the Event

The events are collected within the `Pizza` instance but are not persisted with its state. They are processed _after_ the main transaction succeeds. This ensures you don't announce an event for a change that ultimately failed to save.

Your command handler would be slightly modified, or more commonly, this logic would be handled by a **domain event dispatcher** in your application's pipeline/middleware.

Here’s how the handler would look with explicit dispatching:

```python
# In your application layer
class AddToppingToPizzaCommandHandler(CommandHandler[AddToppingToPizzaCommand, None]):

    def __init__(self, pizzas: IPizzaRepository, mediator: Mediator): # Inject a mediator/dispatcher
        self._pizzas = pizzas
        self._mediator = mediator

    async def handle(self, command: AddToppingToPizzaCommand) -> None:
        # 1. Retrieve the aggregate
        pizza = await self._pizzas.get_by_id_async(command.pizza_id)

        # 2. Execute domain logic (this raises the event internally)
        pizza.add_topping(command.topping)

        # 3. Persist the new state of the aggregate
        await self._pizzas.update_async(pizza)

        # 4. AFTER successful persistence, dispatch the collected events
        for event in pizza.domain_events:
            await self._mediator.publish_async(event)
```

---

### \#\# Summary: State vs. Events

| Aspect             | State-Based Persistence (This Example)                         | Event Sourcing                                                         |
| :----------------- | :------------------------------------------------------------- | :--------------------------------------------------------------------- |
| **Primary Goal**   | Persist the **current state** of the aggregate.                | Persist the **full history** of changes as a sequence of events.       |
| **Role of State**  | It's the **source of truth**. Stored as a document/row.        | It's a **transient projection**. Rebuilt by replaying events.          |
| **Role of Events** | **Side-effects**. Notifications for other parts of the system. | They are the **source of truth**. The primary artifact that is stored. |
| **Analogy**        | Saving a **photograph**.                                       | Recording a **video**.                                                 |

====

is there a way to automatically dispatch domain events for when a request completed?

i'd like to add a middleware in neuroglia to handle that automatically, scanning for any AggregateRoot object in the request context (like finding "pizza" object as an AggregateRoot) and calling publishing all events automatically?

====

Yes, absolutely. What you're describing is a best practice for implementing clean architecture and is a perfect use case for a middleware in `neuroglia-python`'s mediation pipeline.

You can create a "Unit of Work" object that is scoped to a single request. This object's job is to track any aggregates that are loaded or created during the request. Then, a middleware can use this object after the handler has completed to automatically collect and dispatch all domain events.

This approach is powerful because it completely decouples your command handlers from the event dispatching logic. The handlers don't need to know about the mediator or the dispatching process at all.

Here’s how you can implement it step-by-step.

---

### \#\# Step 1: Create a Unit of Work and an Event Collector

First, define a service that will be responsible for tracking aggregates. We can call it `UnitOfWork`. This object will live for the duration of a single request.

```python
# In your application/infrastructure layer

from typing import Iterable
from neuroglia.dependency_injection import Scoped
from your_domain import AggregateRoot, DomainEvent

@Scoped() # This tells the DI container to create one instance per request
class UnitOfWork:
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

---

### \#\# Step 2: Modify Your Repository to Use the Unit of Work

Next, update your repository to notify the `UnitOfWork` whenever it loads or adds an aggregate.

```python
# In your infrastructure layer
from motor.motor_asyncio import AsyncIOMotorCollection

class PizzaMongodbRepository(IPizzaRepository):
    def __init__(self, collection: AsyncIOMotorCollection, uow: UnitOfWork):
        # Inject the request-scoped Unit of Work
        self._collection = collection
        self._uow = uow

    async def get_by_id_async(self, id: str) -> Pizza | None:
        doc = await self._collection.find_one({"_id": id})
        if not doc:
            return None
        pizza = self._from_document(doc)
        # Track the loaded aggregate
        self._uow.track(pizza)
        return pizza

    async def add_async(self, pizza: Pizza) -> None:
        doc = self._to_document(pizza)
        await self._collection.insert_one(doc)
        # Track the new aggregate
        self._uow.track(pizza)

    # ... update_async and other methods ...
```

---

### \#\# Step 3: Create the Domain Event Dispatching Middleware 🚀

This is the core component you asked for. This middleware will be placed in the mediation pipeline. It executes the next handler in the chain and, upon its successful completion, uses the `UnitOfWork` to dispatch any pending events.

```python
# In your application/infrastructure layer
from neuroglia.mediation.middleware import Middleware
from neuroglia.mediation import Mediator, Request

class DomainEventDispatchingMiddleware(Middleware):
    def __init__(self, uow: UnitOfWork, mediator: Mediator):
        self._uow = uow
        self._mediator = mediator

    async def handle(self, request: Request, next: callable):
        # 1. Let the command handler run first
        result = await next(request)

        # 2. After the handler succeeds, get all pending events
        events_to_dispatch = list(self._uow.pending_domain_events)

        # 3. Dispatch each event using the mediator
        for event in events_to_dispatch:
            await self._mediator.publish_async(event)

        return result
```

---

### \#\# Step 4: Update Your Command Handler (to be simpler\!)

Now, your command handler becomes beautifully simple. It no longer needs to know about the mediator or the event dispatching process. It just focuses on its core responsibility.

```python
# In your application layer
class AddToppingToPizzaCommandHandler(CommandHandler[AddToppingToPizzaCommand, None]):
    def __init__(self, pizzas: IPizzaRepository):
        self._pizzas = pizzas

    async def handle(self, command: AddToppingToPizzaCommand) -> None:
        # 1. Retrieve the aggregate (the repo tracks it with the UoW)
        pizza = await self._pizzas.get_by_id_async(command.pizza_id)
        if not pizza:
            raise NotFoundException(...)

        # 2. Execute domain logic (this raises events internally)
        pizza.add_topping(command.topping)

        # 3. Persist the new state
        await self._pizzas.update_async(pizza)

        # That's it! No event dispatching code here.
```

By wiring up the `UnitOfWork` and the `DomainEventDispatchingMiddleware` in your application's dependency injection container, you create a robust, automatic, and clean system for handling domain events.
