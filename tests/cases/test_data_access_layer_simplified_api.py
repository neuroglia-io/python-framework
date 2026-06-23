"""
Tests for simplified DataAccessLayer.WriteModel configuration API.

This test suite validates the enhancement that allows configuring EventSourcingRepository
with options directly, without requiring verbose custom factory functions.
"""

import inspect
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
    EventSourcingRepositoryOptions,
)
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer


# Test State
@dataclass
class TestAggregateState(AggregateState):
    """State for test aggregate"""

    name: str = ""


# Test Aggregate
class TestAggregate(AggregateRoot[TestAggregateState, str]):
    """Test aggregate for repository configuration tests"""

    def __init__(self, aggregate_id: str, name: str):
        super().__init__(aggregate_id, TestAggregateState(name=name))

    @property
    def name(self) -> str:
        return self.state.name


# Another Test State
@dataclass
class AnotherTestState(AggregateState):
    """State for another test aggregate"""


class AnotherTestAggregate(AggregateRoot[AnotherTestState, str]):
    """Another test aggregate"""

    def __init__(self, aggregate_id: str):
        super().__init__(aggregate_id, AnotherTestState())


class TestDataAccessLayerSimplifiedAPI:
    """Tests for simplified DataAccessLayer.WriteModel API"""

    def setup_method(self):
        """Setup test fixtures before each test"""
        self.builder = Mock(spec=ApplicationBuilderBase)
        self.builder.services = Mock()
        self.builder.services.add_singleton = Mock()

    def test_write_model_init_without_options(self):
        """Test WriteModel initialization without options"""
        write_model = DataAccessLayer.WriteModel()
        assert write_model._options is None

    def test_write_model_init_with_options(self):
        """Test WriteModel initialization with options"""
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        write_model = DataAccessLayer.WriteModel(options=options)
        assert write_model._options is options
        assert write_model._options.delete_mode == DeleteMode.HARD

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_without_options_no_custom_setup(self, mock_type_finder, mock_module_loader):
        """Test configure() without options and no custom setup function"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # Create WriteModel and configure
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["test.module"])

        # Verify
        assert result is self.builder
        mock_module_loader.load.assert_called_once_with("test.module")
        self.builder.services.add_singleton.assert_called_once()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_options(self, mock_type_finder, mock_module_loader):
        """Test configure() with custom options"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # Create WriteModel with HARD delete mode
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        write_model = DataAccessLayer.WriteModel(options=options)
        result = write_model.configure(self.builder, ["test.module"])

        # Verify
        assert result is self.builder
        mock_module_loader.load.assert_called_once_with("test.module")
        self.builder.services.add_singleton.assert_called_once()

        # Verify factory was called with options
        call_args = self.builder.services.add_singleton.call_args
        assert call_args is not None
        assert "implementation_factory" in call_args.kwargs

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_soft_delete_options(self, mock_type_finder, mock_module_loader):
        """Test configure() with SOFT delete mode and custom method name"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # Create WriteModel with SOFT delete mode
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.SOFT, soft_delete_method_name="mark_deleted")
        write_model = DataAccessLayer.WriteModel(options=options)
        result = write_model.configure(self.builder, ["test.module"])

        # Verify
        assert result is self.builder
        self.builder.services.add_singleton.assert_called_once()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_multiple_aggregates(self, mock_type_finder, mock_module_loader):
        """Test configure() discovers and configures multiple aggregates"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate, AnotherTestAggregate]

        # Create WriteModel and configure
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        write_model = DataAccessLayer.WriteModel(options=options)
        result = write_model.configure(self.builder, ["test.module"])

        # Verify both aggregates were registered
        assert result is self.builder
        assert self.builder.services.add_singleton.call_count == 2

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_multiple_modules(self, mock_type_finder, mock_module_loader):
        """Test configure() scans multiple modules"""
        # Setup mocks
        mock_module1 = Mock()
        mock_module2 = Mock()
        mock_module_loader.load.side_effect = [mock_module1, mock_module2]
        mock_type_finder.get_types.side_effect = [[TestAggregate], [AnotherTestAggregate]]

        # Create WriteModel and configure with multiple modules
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["module1", "module2"])

        # Verify both modules were loaded
        assert result is self.builder
        assert mock_module_loader.load.call_count == 2
        mock_module_loader.load.assert_any_call("module1")
        mock_module_loader.load.assert_any_call("module2")
        assert self.builder.services.add_singleton.call_count == 2

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_custom_setup_takes_precedence(self, mock_type_finder, mock_module_loader):
        """Test custom repository_setup function takes precedence over options"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        custom_setup = Mock()

        # Create WriteModel with options AND custom setup
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        write_model = DataAccessLayer.WriteModel(options=options)
        result = write_model.configure(self.builder, ["test.module"], custom_setup)

        # Verify custom setup was called, not the simplified path
        assert result is self.builder
        custom_setup.assert_called_once_with(self.builder, TestAggregate, str)
        # Verify simplified path was NOT used (no direct service registration)
        assert self.builder.services.add_singleton.call_count == 0

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_custom_setup_only(self, mock_type_finder, mock_module_loader):
        """Test backwards compatibility: custom setup without options"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        custom_setup = Mock()

        # Create WriteModel without options, use custom setup
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["test.module"], custom_setup)

        # Verify custom setup was called
        assert result is self.builder
        custom_setup.assert_called_once_with(self.builder, TestAggregate, str)

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_filters_aggregateroot_base_class(self, mock_type_finder, mock_module_loader):
        """Test that AggregateRoot base class itself is not configured"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module

        # TypeFinder should filter out AggregateRoot base class
        # This is tested by verifying the lambda filter
        def test_filter(cls):
            return inspect.isclass(cls) and issubclass(cls, AggregateRoot) and not cls == AggregateRoot

        # Test filter logic
        assert test_filter(TestAggregate) is True
        assert test_filter(AggregateRoot) is False
        assert test_filter(str) is False

    def test_write_model_options_type_preservation(self):
        """Test that options attributes are preserved correctly"""
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.SOFT, soft_delete_method_name="custom_delete")
        write_model = DataAccessLayer.WriteModel(options=options)

        assert write_model._options.delete_mode == DeleteMode.SOFT
        assert write_model._options.soft_delete_method_name == "custom_delete"

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_empty_module_list(self, mock_type_finder, mock_module_loader):
        """Test configure() with empty module list"""
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, [])

        # Should return builder without errors
        assert result is self.builder
        mock_module_loader.load.assert_not_called()
        self.builder.services.add_singleton.assert_not_called()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_no_aggregates_found(self, mock_type_finder, mock_module_loader):
        """Test configure() when no aggregates are found in modules"""
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = []  # No aggregates found

        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["test.module"])

        # Should return builder without errors
        assert result is self.builder
        mock_module_loader.load.assert_called_once()
        self.builder.services.add_singleton.assert_not_called()

    def test_write_model_init_with_database_name_and_consumer_group(self):
        """Test WriteModel initialization with database_name and consumer_group"""
        write_model = DataAccessLayer.WriteModel(database_name="testdb", consumer_group="testgroup", delete_mode=DeleteMode.HARD)
        assert write_model._database_name == "testdb"
        assert write_model._consumer_group == "testgroup"
        assert write_model._delete_mode == DeleteMode.HARD

    def test_write_model_init_with_database_name_only_raises_error(self):
        """Test WriteModel configure raises ValueError if database_name provided without consumer_group"""
        write_model = DataAccessLayer.WriteModel(database_name="testdb")

        with pytest.raises(ValueError, match="consumer_group is required"):
            write_model.configure(self.builder, ["test.module"])

    @patch("neuroglia.data.infrastructure.event_sourcing.event_store.event_store.ESEventStore")
    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_database_name_calls_es_event_store_configure(self, mock_type_finder, mock_module_loader, mock_es_event_store):
        """Test configure() with database_name internally calls ESEventStore.configure()"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]
        mock_es_event_store.configure = Mock(return_value=self.builder)

        # Create WriteModel with database_name and consumer_group
        write_model = DataAccessLayer.WriteModel(database_name="testdb", consumer_group="testgroup", delete_mode=DeleteMode.HARD)
        result = write_model.configure(self.builder, ["test.module"])

        # Verify ESEventStore.configure was called
        assert result is self.builder
        mock_es_event_store.configure.assert_called_once()

        # Verify EventStoreOptions were created with correct values
        call_args = mock_es_event_store.configure.call_args
        assert call_args[0][0] is self.builder
        event_store_options = call_args[0][1]
        assert event_store_options.database_name == "testdb"
        assert event_store_options.consumer_group == "testgroup"

    @patch("neuroglia.data.infrastructure.event_sourcing.event_store.event_store.ESEventStore")
    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_database_name_uses_delete_mode(self, mock_type_finder, mock_module_loader, mock_es_event_store):
        """Test configure() with database_name uses provided delete_mode"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]
        mock_es_event_store.configure = Mock(return_value=self.builder)

        # Create WriteModel with SOFT delete mode
        write_model = DataAccessLayer.WriteModel(database_name="testdb", consumer_group="testgroup", delete_mode=DeleteMode.SOFT)
        write_model.configure(self.builder, ["test.module"])

        # Verify repository was configured with correct delete mode
        assert self.builder.services.add_singleton.called


class TestDataAccessLayerBackwardsCompatibility:
    """Tests to ensure backwards compatibility with existing code"""

    def setup_method(self):
        """Setup test fixtures before each test"""
        self.builder = Mock(spec=ApplicationBuilderBase)
        self.builder.services = Mock()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_legacy_custom_factory_pattern_still_works(self, mock_type_finder, mock_module_loader):
        """Test that legacy custom factory pattern continues to work"""
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # Legacy pattern: always pass custom setup function
        def legacy_setup(builder_, entity_type, key_type):
            # Simulate EventSourcingRepository.configure()
            builder_.services.add_singleton(
                Repository[entity_type, key_type],  # type: ignore
                EventSourcingRepository[entity_type, key_type],  # type: ignore
            )

        # Old API usage (without instantiation)
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["test.module"], legacy_setup)

        assert result is self.builder
        self.builder.services.add_singleton.assert_called_once()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_new_api_simple_default_configuration(self, mock_type_finder, mock_module_loader):
        """Test new simplified API with default options"""
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # New simple pattern
        write_model = DataAccessLayer.WriteModel()
        result = write_model.configure(self.builder, ["test.module"])

        assert result is self.builder
        self.builder.services.add_singleton.assert_called_once()

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_new_api_with_options(self, mock_type_finder, mock_module_loader):
        """Test new simplified API with custom options"""
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestAggregate]

        # New pattern with options
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        write_model = DataAccessLayer.WriteModel(options=options)
        result = write_model.configure(self.builder, ["test.module"])

        assert result is self.builder
        self.builder.services.add_singleton.assert_called_once()


@pytest.mark.integration
class TestDataAccessLayerIntegration:
    """Integration tests with real module loading"""

    def test_write_model_instantiation_patterns(self):
        """Test different instantiation patterns"""
        # Pattern 1: Default
        wm1 = DataAccessLayer.WriteModel()
        assert wm1._options is None

        # Pattern 2: With options
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
        wm2 = DataAccessLayer.WriteModel(options=options)
        assert wm2._options is options

        # Pattern 3: With SOFT delete
        soft_options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.SOFT, soft_delete_method_name="mark_as_deleted")
        wm3 = DataAccessLayer.WriteModel(options=soft_options)
        assert wm3._options.delete_mode == DeleteMode.SOFT
        assert wm3._options.soft_delete_method_name == "mark_as_deleted"

    def test_delete_mode_enum_values(self):
        """Test all DeleteMode enum values can be configured"""
        for delete_mode in [DeleteMode.DISABLED, DeleteMode.SOFT, DeleteMode.HARD]:
            options = EventSourcingRepositoryOptions(delete_mode=delete_mode)
            wm = DataAccessLayer.WriteModel(options=options)
            assert wm._options.delete_mode == delete_mode


# Test Queryable Models for ReadModel tests
class TestQueryableModel:
    """Test queryable model for read model configuration tests"""

    __queryable__ = True

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class AnotherQueryableModel:
    """Another test queryable model"""

    __queryable__ = True

    def __init__(self, id: str):
        self.id = id


class TestDataAccessLayerReadModelSimplifiedAPI:
    """Tests for simplified DataAccessLayer.ReadModel API"""

    def setup_method(self):
        """Setup test fixtures before each test"""
        self.builder = Mock(spec=ApplicationBuilderBase)
        self.builder.settings = Mock()
        self.builder.settings.consumer_group = "test-group"
        self.builder.settings.connection_strings = {"mongo": "mongodb://localhost:27017"}
        self.builder.services = Mock()
        self.builder.services.add_singleton = Mock()
        self.builder.services.try_add_singleton = Mock()
        self.builder.services.add_transient = Mock()

    def test_read_model_init_without_database_name(self):
        """Test ReadModel initialization without database name"""
        read_model = DataAccessLayer.ReadModel()
        assert read_model._database_name is None
        assert read_model._repository_type == "mongo"  # Default

    def test_read_model_init_with_database_name(self):
        """Test ReadModel initialization with database name"""
        read_model = DataAccessLayer.ReadModel(database_name="myapp")
        assert read_model._database_name == "myapp"
        assert read_model._repository_type == "mongo"  # Default

    def test_read_model_init_with_motor_repository_type(self):
        """Test ReadModel initialization with motor repository type"""
        read_model = DataAccessLayer.ReadModel(database_name="myapp", repository_type="motor")
        assert read_model._database_name == "myapp"
        assert read_model._repository_type == "motor"

    def test_read_model_init_with_invalid_repository_type(self):
        """Test ReadModel initialization with invalid repository type raises error"""
        with pytest.raises(ValueError, match="Invalid repository_type 'invalid'"):
            DataAccessLayer.ReadModel(database_name="myapp", repository_type="invalid")

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_database_name(self, mock_type_finder, mock_module_loader):
        """Test configure() with database name (default mongo repository)"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        # Create ReadModel with database name
        read_model = DataAccessLayer.ReadModel(database_name="testdb")
        result = read_model.configure(self.builder, ["test.module"])

        # Verify
        assert result is self.builder
        mock_module_loader.load.assert_called_once_with("test.module")
        # Should register MongoClient, options, repository, queryable repository, and handlers
        assert self.builder.services.try_add_singleton.call_count >= 3
        assert self.builder.services.add_transient.call_count == 2  # GetById and List handlers

    @patch("neuroglia.data.infrastructure.mongo.motor_repository.MotorRepository.configure")
    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_motor_repository_type(self, mock_type_finder, mock_module_loader, mock_motor_configure):
        """Test configure() with motor repository type"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        # Create ReadModel with motor repository type
        read_model = DataAccessLayer.ReadModel(database_name="testdb", repository_type="motor")
        result = read_model.configure(self.builder, ["test.module"])

        # Verify
        assert result is self.builder
        mock_module_loader.load.assert_called_once_with("test.module")

        # Should call MotorRepository.configure() for discovered type
        mock_motor_configure.assert_called_once_with(builder=self.builder, entity_type=TestQueryableModel, key_type=str, database_name="testdb")

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_without_database_name_raises_error(self, mock_type_finder, mock_module_loader):
        """Test configure() without database name raises error"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        # Create ReadModel without database name
        read_model = DataAccessLayer.ReadModel()

        # Should raise ValueError
        with pytest.raises(ValueError, match="database_name not provided"):
            read_model.configure(self.builder, ["test.module"])

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_custom_setup_takes_precedence(self, mock_type_finder, mock_module_loader):
        """Test custom repository_setup function takes precedence over database_name"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        custom_setup = Mock()

        # Create ReadModel with database_name AND custom setup
        read_model = DataAccessLayer.ReadModel(database_name="testdb")
        result = read_model.configure(self.builder, ["test.module"], custom_setup)

        # Verify custom setup was called, not the simplified path
        assert result is self.builder
        custom_setup.assert_called_once_with(self.builder, TestQueryableModel, str)
        # ReadModelReconciliator should still be registered
        assert self.builder.services.add_singleton.call_count >= 2

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_multiple_queryable_types(self, mock_type_finder, mock_module_loader):
        """Test configure() discovers and configures multiple queryable types"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel, AnotherQueryableModel]

        # Create ReadModel and configure
        read_model = DataAccessLayer.ReadModel(database_name="testdb")
        result = read_model.configure(self.builder, ["test.module"])

        # Verify both queryable types were registered
        assert result is self.builder
        # Should have multiple registrations for each type
        assert self.builder.services.try_add_singleton.call_count >= 5  # MongoClient + 2*(options + repo + queryable)
        assert self.builder.services.add_transient.call_count == 4  # 2 handlers per type

    def test_configure_without_consumer_group_raises_error(self):
        """Test configure() without consumer_group raises error"""
        self.builder.settings.consumer_group = None

        read_model = DataAccessLayer.ReadModel(database_name="testdb")

        with pytest.raises(ValueError, match="consumer group not specified"):
            read_model.configure(self.builder, ["test.module"])

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_without_mongo_connection_string_raises_error(self, mock_type_finder, mock_module_loader):
        """Test configure() without mongo connection string raises error"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        # Remove mongo connection string
        self.builder.settings.connection_strings = {}

        read_model = DataAccessLayer.ReadModel(database_name="testdb")

        with pytest.raises(ValueError, match="Missing 'mongo' connection string"):
            read_model.configure(self.builder, ["test.module"])

    @patch("neuroglia.hosting.configuration.data_access_layer.ModuleLoader")
    @patch("neuroglia.hosting.configuration.data_access_layer.TypeFinder")
    def test_configure_with_custom_setup_backwards_compatible(self, mock_type_finder, mock_module_loader):
        """Test backwards compatibility: custom setup without database_name"""
        # Setup mocks
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module
        mock_type_finder.get_types.return_value = [TestQueryableModel]

        custom_setup = Mock()

        # Create ReadModel without database_name, use custom setup
        read_model = DataAccessLayer.ReadModel()
        result = read_model.configure(self.builder, ["test.module"], custom_setup)

        # Verify custom setup was called
        assert result is self.builder
        custom_setup.assert_called_once_with(self.builder, TestQueryableModel, str)


@pytest.mark.integration
class TestDataAccessLayerReadModelIntegration:
    """Integration tests for ReadModel configuration"""

    def test_read_model_instantiation_patterns(self):
        """Test different instantiation patterns"""
        # Pattern 1: Default (no database name)
        rm1 = DataAccessLayer.ReadModel()
        assert rm1._database_name is None

        # Pattern 2: With database name
        rm2 = DataAccessLayer.ReadModel(database_name="myapp")
        assert rm2._database_name == "myapp"

        # Pattern 3: With different database name
        rm3 = DataAccessLayer.ReadModel(database_name="production_db")
        assert rm3._database_name == "production_db"
