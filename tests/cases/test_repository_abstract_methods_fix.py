"""
Test suite to verify that the abstract method fixes for Repository implementations work correctly.

This test file validates the fixes for:
1. EventSourcingRepository - Implements _do_add_async, _do_update_async, _do_remove_async
2. MongoRepository - Implements _do_add_async, _do_update_async, _do_remove_async
3. Missing List import in queryable.py
4. Missing List import in mongo_repository.py
"""

from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
)
from neuroglia.data.infrastructure.mongo.mongo_repository import (
    MongoRepository,
    MongoRepositoryOptions,
)
from neuroglia.serialization.json import JsonSerializer


class TestAggregateState(AggregateState):
    """Test aggregate state for testing purposes"""

    def __init__(self, id: str, name: str):
        super().__init__()
        self.id = id
        self.name = name


class TestAggregate(AggregateRoot[TestAggregateState, str]):
    """Test aggregate for testing purposes"""

    def __init__(self, state: TestAggregateState):
        super().__init__(state)

    def id(self) -> str:
        return self.state.id

    def change_name(self, new_name: str):
        self.state.name = new_name
        event = TestAggregateChangedEvent(self.id(), new_name)
        self.raise_event(event)


class TestAggregateChangedEvent(DomainEvent):
    """Test domain event"""

    def __init__(self, aggregate_id: str, new_name: str):
        super().__init__()
        self.aggregate_id = aggregate_id
        self.new_name = new_name


class TestEntity:
    """Simple test entity for MongoDB tests"""

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class TestEventSourcingRepositoryInstantiation:
    """Test that EventSourcingRepository can be instantiated after fixes"""

    def test_can_instantiate_without_mediator(self):
        """Verify EventSourcingRepository can be created without mediator"""
        mock_eventstore = Mock()
        mock_aggregator = Mock()

        # This should not raise TypeError about abstract methods
        repo = EventSourcingRepository[TestAggregate, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            mediator=None,
        )

        assert repo is not None
        assert repo._eventstore == mock_eventstore
        assert repo._aggregator == mock_aggregator
        assert repo._mediator is None

    def test_can_instantiate_with_mediator(self):
        """Verify EventSourcingRepository can be created with mediator"""
        mock_eventstore = Mock()
        mock_aggregator = Mock()
        mock_mediator = Mock()

        # This should not raise TypeError about abstract methods
        repo = EventSourcingRepository[TestAggregate, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            mediator=mock_mediator,
        )

        assert repo is not None
        assert repo._mediator == mock_mediator

    def test_has_all_required_abstract_methods(self):
        """Verify EventSourcingRepository implements all required abstract methods"""
        mock_eventstore = Mock()
        mock_aggregator = Mock()

        repo = EventSourcingRepository[TestAggregate, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
        )

        # Check that all required methods exist
        assert hasattr(repo, "_do_add_async")
        assert callable(repo._do_add_async)
        assert hasattr(repo, "_do_update_async")
        assert callable(repo._do_update_async)
        assert hasattr(repo, "_do_remove_async")
        assert callable(repo._do_remove_async)

    @pytest.mark.asyncio
    async def test_do_remove_async_raises_not_implemented(self):
        """Verify _do_remove_async raises NotImplementedError as designed"""
        mock_eventstore = Mock()
        mock_aggregator = Mock()

        repo = EventSourcingRepository[TestAggregate, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
        )

        with pytest.raises(NotImplementedError, match="Event sourcing repositories do not support hard deletes"):
            await repo._do_remove_async("test-id")


class TestMongoRepositoryInstantiation:
    """Test that MongoRepository can be instantiated after fixes"""

    def test_can_instantiate_without_errors(self):
        """Verify MongoRepository can be created without abstract method errors"""
        mock_client = Mock()
        mock_serializer = Mock(spec=JsonSerializer)
        options = MongoRepositoryOptions[TestEntity, str](database_name="test_db")

        # This should not raise TypeError about abstract methods
        repo = MongoRepository[TestEntity, str](
            options=options,
            mongo_client=mock_client,
            serializer=mock_serializer,
        )

        assert repo is not None
        assert repo._options == options
        assert repo._mongo_client == mock_client
        assert repo._serializer == mock_serializer

    def test_has_all_required_abstract_methods(self):
        """Verify MongoRepository implements all required abstract methods"""
        mock_client = Mock()
        mock_serializer = Mock(spec=JsonSerializer)
        options = MongoRepositoryOptions[TestEntity, str](database_name="test_db")

        repo = MongoRepository[TestEntity, str](
            options=options,
            mongo_client=mock_client,
            serializer=mock_serializer,
        )

        # Check that all required methods exist
        assert hasattr(repo, "_do_add_async")
        assert callable(repo._do_add_async)
        assert hasattr(repo, "_do_update_async")
        assert callable(repo._do_update_async)
        assert hasattr(repo, "_do_remove_async")
        assert callable(repo._do_remove_async)


class TestListImportFixes:
    """Test that List import fixes work correctly"""

    def test_list_available_in_queryable_module(self):
        """Verify List is imported in queryable module"""
        from neuroglia.data import queryable

        # Verify List is available in the module
        assert hasattr(queryable, "List")
        assert queryable.List is List

    def test_list_available_in_mongo_repository_module(self):
        """Verify List is imported in mongo_repository module"""
        from neuroglia.data.infrastructure.mongo import mongo_repository

        # Verify List is available in the module
        assert hasattr(mongo_repository, "List")
        assert mongo_repository.List is List

    def test_queryable_to_list_uses_list_type(self):
        """Verify that Queryable.to_list() can reference List type"""
        from neuroglia.data.queryable import Queryable

        # This should not raise NameError: name 'List' is not defined
        # We're just checking the method exists and the type is referenced correctly
        assert hasattr(Queryable, "to_list")

    def test_mongo_query_provider_execute_uses_list_type(self):
        """Verify MongoQueryProvider.execute() can reference List type"""
        from neuroglia.data.infrastructure.mongo.mongo_repository import (
            MongoQueryProvider,
        )

        # This should not raise NameError: name 'List' is not defined
        # We're just checking the method exists and the type is referenced correctly
        assert hasattr(MongoQueryProvider, "execute")


class TestRepositoryTemplateMethodPattern:
    """Test that the Template Method Pattern works correctly after fixes"""

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_calls_do_methods(self):
        """Verify EventSourcingRepository properly implements template method pattern"""
        mock_eventstore = Mock()
        mock_eventstore.append_async = AsyncMock()
        mock_aggregator = Mock()

        repo = EventSourcingRepository[TestAggregate, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            mediator=None,
        )

        # Create test aggregate with pending events
        state = TestAggregateState(id="test-123", name="Test")
        aggregate = TestAggregate(state)
        aggregate.change_name("Updated")

        # Mock the _build_stream_id_for method
        with patch.object(repo, "_build_stream_id_for", return_value="test-stream-id"):
            # Call add_async (which should call _do_add_async internally)
            result = await repo.add_async(aggregate)

            # Verify the template method was called
            assert mock_eventstore.append_async.called
            assert result == aggregate
            assert len(aggregate._pending_events) == 0  # Events should be cleared

    @pytest.mark.asyncio
    async def test_mongo_repository_add_calls_do_method(self):
        """Verify MongoRepository add_async calls _do_add_async correctly"""
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()
        mock_collection.find_one = Mock(return_value=None)  # Entity doesn't exist
        mock_collection.insert_one = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_client.__getitem__ = Mock(return_value=mock_db)

        mock_serializer = Mock(spec=JsonSerializer)
        mock_serializer.serialize_to_text = Mock(return_value='{"id": "test-123", "name": "Test"}')
        mock_serializer.deserialize_from_text = Mock(return_value={"id": "test-123", "name": "Test"})

        options = MongoRepositoryOptions[TestEntity, str](database_name="test_db")

        repo = MongoRepository[TestEntity, str](
            options=options,
            mongo_client=mock_client,
            serializer=mock_serializer,
        )

        entity = TestEntity(id="test-123", name="Test")

        # Mock the __orig_class__ attribute for type resolution
        repo.__orig_class__ = Mock()
        repo.__orig_class__.__args__ = [TestEntity, str]

        # Call add_async (which should call _do_add_async internally)
        result = await repo.add_async(entity)

        # Verify the persistence happened
        assert mock_collection.insert_one.called
        assert result == entity


class TestNoRuntimePatches:
    """Verify that the fixes eliminate the need for runtime patches"""

    def test_event_sourcing_repository_no_abstract_methods_error(self):
        """Verify EventSourcingRepository doesn't have abstractmethods issues"""
        mock_eventstore = Mock()
        mock_aggregator = Mock()

        # This would raise TypeError if abstract methods weren't implemented
        try:
            repo = EventSourcingRepository[TestAggregate, str](
                eventstore=mock_eventstore,
                aggregator=mock_aggregator,
            )
            # Success - no exception raised
            assert True
        except TypeError as e:
            if "abstract methods" in str(e):
                pytest.fail(f"EventSourcingRepository still has abstract method issues: {e}")
            raise

    def test_mongo_repository_no_abstract_methods_error(self):
        """Verify MongoRepository doesn't have abstractmethods issues"""
        mock_client = Mock()
        mock_serializer = Mock(spec=JsonSerializer)
        options = MongoRepositoryOptions[TestEntity, str](database_name="test_db")

        # This would raise TypeError if abstract methods weren't implemented
        try:
            repo = MongoRepository[TestEntity, str](
                options=options,
                mongo_client=mock_client,
                serializer=mock_serializer,
            )
            # Success - no exception raised
            assert True
        except TypeError as e:
            if "abstract methods" in str(e):
                pytest.fail(f"MongoRepository still has abstract method issues: {e}")
            raise
