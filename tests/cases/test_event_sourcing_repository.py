import pytest
from neuroglia.data.infrastructure.event_sourcing.abstractions import Aggregator, EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from tests.data import User


class TestEventSourcingRepository:

    @pytest.mark.asyncio
    async def test_add_should_work(self):
        # arrange
        eventstore_options = EventStoreOptions(database_name='test')
        eventstore = ESEventStore(eventstore_options)
        aggregator = Aggregator()
        repository = EventSourcingRepository[User, str](eventstore_options, eventstore, aggregator)
        aggregate = User('John Doe', 'john.doe@email.com')
        observable = await eventstore.observe_async(f'user-{aggregate.id()}').subscribe(on_event_recorded)    

        # act
        await repository.add_async(aggregate)
        aggregate = await repository.get_async(aggregate.id())
        aggregate.set_email('john.doe@gmail.com')
        aggregate = await repository.update_async(aggregate)
        
        # assert