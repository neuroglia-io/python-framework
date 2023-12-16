import threading
from neuroglia.infrastructure.event_sourcing.abstractions import Aggregator, EventRecord, EventStoreOptions
from neuroglia.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository, EventSourcingRepositoryOptions
from neuroglia.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.tests.data.user import User, UserCreatedDomainEventV1
from rx import operators as ops
def on_event_recorded(e : EventRecord):
    
    pass

def test_add_should_work():
    eventstore_options = EventStoreOptions(database_name='test')
    eventstore = ESEventStore(eventstore_options)
    aggregator = Aggregator()
    repository = EventSourcingRepository[User, str](eventstore_options, eventstore, aggregator)
    aggregate = User('John Doe', 'john.doe@email.com')
    observable = eventstore.observe(f'user-{aggregate.id()}').subscribe(on_event_recorded)    

    repository.add(aggregate)
    aggregate = repository.get(aggregate.id())
    aggregate.set_email('john.doe@gmail.com')
    aggregate = repository.update(aggregate)
    
test_add_should_work()

print('hello')