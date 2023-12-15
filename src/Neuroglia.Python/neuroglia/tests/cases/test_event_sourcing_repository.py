from neuroglia.infrastructure.event_sourcing.abstractions import Aggregator
from neuroglia.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository, EventSourcingRepositoryOptions
from neuroglia.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.tests.data.user import User, UserCreatedDomainEventV1

def test_add_should_work():
    eventstore = ESEventStore()
    aggregator = Aggregator()
    repository = EventSourcingRepository[UserCreatedDomainEventV1, str](EventSourcingRepositoryOptions[User, str](), eventstore, aggregator)
    aggregate = User('John Doe', 'john.doe@email.com')
    repository.add(aggregate)
    aggregate = repository.get(aggregate.id())