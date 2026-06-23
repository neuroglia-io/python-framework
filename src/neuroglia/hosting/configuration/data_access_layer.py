import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from neuroglia.core import ModuleLoader, TypeFinder
from neuroglia.data.abstractions import AggregateRoot
from neuroglia.data.infrastructure.event_sourcing.read_model_reconciliator import (
    ReadModelConciliationOptions,
    ReadModelReconciliator,
)
from neuroglia.data.queries.generic import GetByIdQueryHandler, ListQueryHandler
from neuroglia.hosting.abstractions import ApplicationBuilderBase, HostedService
from neuroglia.mediation.mediator import RequestHandler

if TYPE_CHECKING:
    from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
        EventSourcingRepositoryOptions,
    )


class DataAccessLayer:
    class WriteModel:
        """Represents a helper class used to configure an application's Write Model DAL

        Supports two configuration patterns:
        1. Simplified: Pass database_name, consumer_group, and delete_mode to constructor
        2. Custom: Pass custom repository_setup function to configure()

        Examples:
            # Simple configuration with all required parameters
            from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode

            DataAccessLayer.WriteModel(
                database_name="myapp",
                consumer_group="myapp_group",
                delete_mode=DeleteMode.HARD
            ).configure(builder, ["domain.entities"])

            # Minimal configuration (uses default delete mode)
            DataAccessLayer.WriteModel(
                database_name="myapp",
                consumer_group="myapp_group"
            ).configure(builder, ["domain.entities"])

            # Legacy: With EventSourcingRepositoryOptions (backwards compatible)
            from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
                EventSourcingRepositoryOptions
            )

            DataAccessLayer.WriteModel(
                options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
            ).configure(builder, ["domain.entities"])

            # Custom factory (advanced, backwards compatible)
            def custom_setup(builder_, entity_type, key_type):
                # Custom configuration logic
                pass
            DataAccessLayer.WriteModel().configure(
                builder, ["domain.entities"], custom_setup
            )
        """

        def __init__(
            self,
            database_name: Optional[str] = None,
            consumer_group: Optional[str] = None,
            delete_mode: Optional["DeleteMode"] = None,
            options: Optional["EventSourcingRepositoryOptions"] = None,
        ):
            """Initialize WriteModel configuration

            Args:
                database_name: Database/stream prefix for event store (e.g., "myapp").
                              Internally creates EventStoreOptions and calls ESEventStore.configure().
                consumer_group: Consumer group name for event store subscriptions.
                delete_mode: Optional deletion strategy (DISABLED, SOFT, HARD).
                            If not provided, defaults to DISABLED.
                options: Legacy parameter for EventSourcingRepositoryOptions (backwards compatible).
                        If database_name is provided, this parameter is ignored.

            Example:
                ```python
                # Simplified configuration (recommended)
                DataAccessLayer.WriteModel(
                    database_name="myapp",
                    consumer_group="myapp_group",
                    delete_mode=DeleteMode.HARD
                ).configure(builder, ["domain.entities"])

                # Legacy (still supported)
                DataAccessLayer.WriteModel(
                    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
                ).configure(builder, ["domain.entities"])
                ```
            """
            self._database_name = database_name
            self._consumer_group = consumer_group
            self._delete_mode = delete_mode
            self._options = options

        def configure(self, builder: ApplicationBuilderBase, modules: list[str], repository_setup: Optional[Callable[[ApplicationBuilderBase, type, type], None]] = None) -> ApplicationBuilderBase:
            """Configures the application's Write Model DAL, scanning for aggregate root types within the specified modules

            Args:
                builder (ApplicationBuilderBase): the application builder to configure
                modules (List[str]): a list containing the names of the modules to scan for aggregate root types
                repository_setup (Optional[Callable[[ApplicationBuilderBase, Type, Type], None]]):
                    Optional custom function to setup repositories. If provided, takes precedence over options.
                    If not provided, uses simplified configuration with database_name/consumer_group or options.

            Returns:
                ApplicationBuilderBase: The configured builder

            Raises:
                ImportError: If EventSourcingRepository cannot be imported
                ValueError: If database_name is provided without consumer_group
            """
            # If custom setup provided, use it (backwards compatible)
            if repository_setup is not None:
                for module in [ModuleLoader.load(module_name) for module_name in modules]:
                    for aggregate_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and issubclass(cls, AggregateRoot) and not cls == AggregateRoot):
                        key_type = str  # todo: reflect from DTO base type
                        repository_setup(builder, aggregate_type, key_type)
                return builder

            # If database_name provided, configure event store and use simplified configuration
            if self._database_name is not None:
                if self._consumer_group is None:
                    raise ValueError("consumer_group is required when database_name is provided")

                # Configure ESEventStore
                from neuroglia.data.infrastructure.event_sourcing.abstractions import (
                    EventStoreOptions,
                )
                from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import (
                    ESEventStore,
                )

                event_store_options = EventStoreOptions(
                    database_name=self._database_name,
                    consumer_group=self._consumer_group,
                )
                ESEventStore.configure(builder, event_store_options)

            # Otherwise use simplified configuration with options or defaults
            return self._configure_with_options(builder, modules)

        def _configure_with_options(self, builder: ApplicationBuilderBase, modules: list[str]) -> ApplicationBuilderBase:
            """Configure repositories using simplified options pattern

            Args:
                builder: The application builder
                modules: List of module names to scan for aggregates

            Returns:
                The configured builder
            """
            from neuroglia.data.infrastructure.abstractions import Repository
            from neuroglia.data.infrastructure.event_sourcing.abstractions import (
                Aggregator,
                DeleteMode,
                EventStore,
            )
            from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
                EventSourcingRepository,
                EventSourcingRepositoryOptions,
            )
            from neuroglia.dependency_injection import ServiceProvider
            from neuroglia.mediation import Mediator

            # Determine delete mode to use
            delete_mode = self._delete_mode if self._delete_mode is not None else (self._options.delete_mode if self._options else DeleteMode.DISABLED)

            # Discover and configure each aggregate type
            for module in [ModuleLoader.load(module_name) for module_name in modules]:
                for aggregate_type in TypeFinder.get_types(
                    module,
                    lambda cls: inspect.isclass(cls) and issubclass(cls, AggregateRoot) and not cls == AggregateRoot,
                ):
                    key_type = str  # todo: reflect from DTO base type

                    # Create type-specific options
                    typed_options = EventSourcingRepositoryOptions[aggregate_type, key_type](  # type: ignore
                        delete_mode=delete_mode,
                        soft_delete_method_name=self._options.soft_delete_method_name if self._options else "mark_as_deleted",
                    )

                    # Create factory function with proper closure
                    def make_factory(et, kt, opts):
                        def repository_factory(sp: ServiceProvider):
                            return EventSourcingRepository[et, kt](  # type: ignore
                                eventstore=sp.get_required_service(EventStore),
                                aggregator=sp.get_required_service(Aggregator),
                                mediator=sp.get_service(Mediator),
                                options=opts,
                            )

                        return repository_factory

                    # Register repository with factory
                    builder.services.add_singleton(
                        Repository[aggregate_type, key_type],  # type: ignore
                        implementation_factory=make_factory(aggregate_type, key_type, typed_options),
                    )

            return builder

    class ReadModel:
        """Represents a helper class used to configure an application's Read Model DAL

        Supports three configuration patterns:
        1. Simplified Sync: Pass database_name with repository_type='mongo' (default)
        2. Simplified Async: Pass database_name with repository_type='motor' for FastAPI
        3. Custom: Pass custom repository_setup function to configure()

        Examples:
            # Simple synchronous configuration (default)
            DataAccessLayer.ReadModel(database_name="myapp").configure(
                builder, ["integration.models"]
            )

            # Async configuration with Motor for FastAPI
            DataAccessLayer.ReadModel(
                database_name="myapp",
                repository_type='motor'
            ).configure(builder, ["integration.models"])

            # With custom repository mappings
            DataAccessLayer.ReadModel(
                database_name="myapp",
                repository_type='motor',
                repository_mappings={
                    TaskDtoRepository: MotorTaskDtoRepository,
                }
            ).configure(builder, ["integration.models"])

            # Custom factory (advanced, backwards compatible)
            def custom_setup(builder_, entity_type, key_type):
                # Custom configuration logic
                pass
            DataAccessLayer.ReadModel().configure(
                builder, ["integration.models"], custom_setup
            )
        """

        def __init__(
            self,
            database_name: Optional[str] = None,
            repository_type: str = "mongo",
            repository_mappings: Optional[dict[type, type]] = None,
        ):
            """Initialize ReadModel configuration

            Args:
                database_name: Optional database name for MongoDB repositories.
                              If not provided, custom repository_setup must be used.
                repository_type: Type of repository to use ('mongo' or 'motor'). Defaults to 'mongo'.
                    - 'mongo': Use MongoRepository with PyMongo (synchronous driver)
                    - 'motor': Use MotorRepository with Motor (async driver for FastAPI)
                repository_mappings: Optional mapping of abstract repository interfaces
                                    to their concrete implementations. Allows single-line
                                    registration of custom domain repositories.
                    Example: {TaskDtoRepository: MotorTaskDtoRepository}

            Example:
                ```python
                # Simplified sync configuration
                DataAccessLayer.ReadModel(database_name="myapp").configure(...)

                # Async configuration with Motor
                DataAccessLayer.ReadModel(
                    database_name="myapp",
                    repository_type='motor'
                ).configure(...)

                # With custom repository implementations
                DataAccessLayer.ReadModel(
                    database_name="myapp",
                    repository_type='motor',
                    repository_mappings={
                        TaskDtoRepository: MotorTaskDtoRepository,
                        UserDtoRepository: MotorUserDtoRepository,
                    }
                ).configure(...)
                ```
            """
            self._database_name = database_name
            self._repository_type = repository_type
            self._repository_mappings = repository_mappings or {}

            # Validate repository_type
            if repository_type not in ("mongo", "motor"):
                raise ValueError(f"Invalid repository_type '{repository_type}'. " "Must be either 'mongo' (synchronous PyMongo) or 'motor' (async Motor)")

        def configure(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
            repository_setup: Optional[Callable[[ApplicationBuilderBase, type, type], None]] = None,
        ) -> ApplicationBuilderBase:
            """Configures the application's Read Model DAL, scanning for types marked with the 'queryable' decorator within the specified modules

            Args:
                builder (ApplicationBuilderBase): the application builder to configure
                modules (List[str]): a list containing the names of the modules to scan for types decorated with 'queryable'
                repository_setup (Optional[Callable[[ApplicationBuilderBase, Type, Type], None]]):
                    Optional custom function to setup repositories. If provided, takes precedence over database_name.
                    If not provided, uses simplified configuration with database_name.

            Returns:
                ApplicationBuilderBase: The configured builder

            Raises:
                ValueError: If consumer_group not specified in settings
                ValueError: If neither repository_setup nor database_name is provided
            """
            # Configure read model reconciliation
            self._configure_reconciliation(builder)

            # If custom setup provided, use it (backwards compatible)
            if repository_setup is not None:
                return self._configure_with_custom_setup(builder, modules, repository_setup)

            # Otherwise use simplified configuration with database_name
            return self._configure_with_database_name(builder, modules)

        def _configure_reconciliation(self, builder: ApplicationBuilderBase) -> None:
            """Configure read model reconciliation services

            Args:
                builder: The application builder

            Raises:
                ValueError: If consumer_group not specified in settings
            """
            consumer_group = builder.settings.consumer_group
            if not consumer_group:
                raise ValueError("Cannot configure Read Model DAL: consumer group not specified in application settings")
            builder.services.add_singleton(ReadModelConciliationOptions, singleton=ReadModelConciliationOptions(consumer_group))
            builder.services.add_singleton(HostedService, ReadModelReconciliator)

        def _configure_with_custom_setup(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
            repository_setup: Callable[[ApplicationBuilderBase, type, type], None],
        ) -> ApplicationBuilderBase:
            """Configure repositories using custom setup function (backwards compatible pattern)

            Args:
                builder: The application builder
                modules: List of module names to scan for queryable types
                repository_setup: Custom function to setup repositories

            Returns:
                The configured builder
            """
            for module in [ModuleLoader.load(module_name) for module_name in modules]:
                for queryable_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and hasattr(cls, "__queryable__")):
                    key_type = str  # todo: reflect from DTO base type
                    repository_setup(builder, queryable_type, key_type)
                    builder.services.add_transient(RequestHandler, GetByIdQueryHandler[queryable_type, key_type])  # type: ignore
                    builder.services.add_transient(RequestHandler, ListQueryHandler[queryable_type, key_type])  # type: ignore
            return builder

        def _configure_with_database_name(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
        ) -> ApplicationBuilderBase:
            """Configure repositories using simplified database_name pattern

            Args:
                builder: The application builder
                modules: List of module names to scan for queryable types

            Returns:
                The configured builder

            Raises:
                ValueError: If database_name was not provided
            """
            if not self._database_name:
                raise ValueError("Cannot configure Read Model with simplified API: " "database_name not provided. Either pass database_name to ReadModel() " "or use custom repository_setup function.")

            # Configure based on repository type
            if self._repository_type == "mongo":
                return self._configure_mongo_repositories(builder, modules)
            elif self._repository_type == "motor":
                return self._configure_motor_repositories(builder, modules)

            return builder

        def _configure_mongo_repositories(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
        ) -> ApplicationBuilderBase:
            """Configure synchronous MongoRepository instances

            Args:
                builder: The application builder
                modules: List of module names to scan for queryable types

            Returns:
                The configured builder

            Raises:
                ValueError: If mongo connection string is missing
            """
            from pymongo import MongoClient

            from neuroglia.data.infrastructure.abstractions import (
                QueryableRepository,
                Repository,
            )
            from neuroglia.data.infrastructure.mongo.mongo_repository import (
                MongoRepository,
                MongoRepositoryOptions,
            )
            from neuroglia.dependency_injection import ServiceProvider

            # Get MongoDB connection string
            connection_string_name = "mongo"
            connection_string = builder.settings.connection_strings.get(connection_string_name, None)
            if connection_string is None:
                raise ValueError(f"Missing '{connection_string_name}' connection string in application settings")

            # Register MongoClient singleton (shared across all repositories)
            builder.services.try_add_singleton(MongoClient, singleton=MongoClient(connection_string))

            # Discover and configure each queryable type
            for module in [ModuleLoader.load(module_name) for module_name in modules]:
                for queryable_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and hasattr(cls, "__queryable__")):
                    key_type = str  # todo: reflect from DTO base type

                    # Register options for this entity type
                    builder.services.try_add_singleton(
                        MongoRepositoryOptions[queryable_type, key_type],  # type: ignore
                        singleton=MongoRepositoryOptions[queryable_type, key_type](self._database_name),  # type: ignore
                    )

                    # Register repository
                    builder.services.try_add_singleton(
                        Repository[queryable_type, key_type],  # type: ignore
                        MongoRepository[queryable_type, key_type],  # type: ignore
                    )

                    # Register queryable repository alias
                    def make_queryable_factory(qt, kt):
                        def queryable_factory(provider: ServiceProvider):
                            return provider.get_required_service(Repository[qt, kt])  # type: ignore

                        return queryable_factory

                    builder.services.try_add_singleton(
                        QueryableRepository[queryable_type, key_type],  # type: ignore
                        implementation_factory=make_queryable_factory(queryable_type, key_type),
                    )

                    # Register query handlers
                    builder.services.add_transient(RequestHandler, GetByIdQueryHandler[queryable_type, key_type])  # type: ignore
                    builder.services.add_transient(RequestHandler, ListQueryHandler[queryable_type, key_type])  # type: ignore

            return builder

        def _configure_motor_repositories(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
        ) -> ApplicationBuilderBase:
            """Configure async MotorRepository instances

            Args:
                builder: The application builder
                modules: List of module names to scan for queryable types

            Returns:
                The configured builder

            Raises:
                ValueError: If mongo connection string is missing
            """
            from motor.motor_asyncio import AsyncIOMotorClient

            # Get MongoDB connection string
            connection_string_name = "mongo"
            connection_string = builder.settings.connection_strings.get(connection_string_name, None)
            if connection_string is None:
                raise ValueError(f"Missing '{connection_string_name}' connection string in application settings")

            # Register AsyncIOMotorClient singleton (shared across all repositories)
            builder.services.try_add_singleton(AsyncIOMotorClient, singleton=AsyncIOMotorClient(connection_string))

            # Discover and configure each queryable type
            self._register_motor_queryable_types(builder, modules)

            # Register custom repository mappings
            self._register_custom_repository_mappings(builder)

            return builder

        def _register_motor_queryable_types(
            self,
            builder: ApplicationBuilderBase,
            modules: list[str],
        ) -> None:
            """Register MotorRepository for each @queryable decorated type

            Args:
                builder: The application builder
                modules: List of module names to scan for queryable types
            """
            from motor.motor_asyncio import AsyncIOMotorClient

            from neuroglia.data.infrastructure.abstractions import (
                QueryableRepository,
                Repository,
            )
            from neuroglia.data.infrastructure.mongo.motor_repository import (
                MotorRepository,
            )
            from neuroglia.dependency_injection import ServiceProvider
            from neuroglia.mediation import Mediator
            from neuroglia.serialization.json import JsonSerializer

            for module in [ModuleLoader.load(module_name) for module_name in modules]:
                for entity_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and hasattr(cls, "__queryable__")):
                    key_type = str  # todo: reflect from DTO base type

                    # Determine collection name (default to lowercase entity name)
                    collection_name = entity_type.__name__.lower()
                    if collection_name.endswith("dto"):
                        collection_name = collection_name[:-3]

                    # Factory function to create MotorRepository instance
                    def make_motor_factory(et, kt, cn):
                        def motor_factory(provider: ServiceProvider):
                            # Attempt to resolve Mediator optionally (tests may skip registration)
                            mediator = provider.get_service(Mediator)
                            if mediator is None:
                                mediator = provider.get_required_service(Mediator)

                            return MotorRepository[et, kt](  # type: ignore
                                client=provider.get_required_service(AsyncIOMotorClient),
                                database_name=self._database_name,
                                collection_name=cn,
                                serializer=provider.get_required_service(JsonSerializer),
                                entity_type=et,
                                mediator=mediator,
                            )

                        return motor_factory

                    # Register MotorRepository (scoped for proper async context per request)
                    builder.services.try_add_scoped(
                        MotorRepository[entity_type, key_type],  # type: ignore
                        implementation_factory=make_motor_factory(entity_type, key_type, collection_name),
                    )

                    # Register Repository interface (handlers expect this)
                    def make_repository_factory(et, kt):
                        def repository_factory(provider: ServiceProvider):
                            return provider.get_required_service(MotorRepository[et, kt])  # type: ignore

                        return repository_factory

                    builder.services.try_add_scoped(
                        Repository[entity_type, key_type],  # type: ignore
                        implementation_factory=make_repository_factory(entity_type, key_type),
                    )

                    # Register QueryableRepository interface (for queryable support)
                    def make_queryable_factory(et, kt):
                        def queryable_factory(provider: ServiceProvider):
                            return provider.get_required_service(Repository[et, kt])  # type: ignore

                        return queryable_factory

                    builder.services.try_add_scoped(
                        QueryableRepository[entity_type, key_type],  # type: ignore
                        implementation_factory=make_queryable_factory(entity_type, key_type),
                    )

                    # Register query handlers (consistent with mongo)
                    builder.services.add_transient(RequestHandler, GetByIdQueryHandler[entity_type, key_type])  # type: ignore
                    builder.services.add_transient(RequestHandler, ListQueryHandler[entity_type, key_type])  # type: ignore

        def _register_custom_repository_mappings(self, builder: ApplicationBuilderBase) -> None:
            """Register custom domain repository implementations

            Uses factory functions to properly instantiate custom repositories,
            avoiding DI auto-construction issues with generic type parameters.

            Args:
                builder: The application builder
            """
            from motor.motor_asyncio import AsyncIOMotorClient

            from neuroglia.dependency_injection import ServiceProvider
            from neuroglia.mediation import Mediator
            from neuroglia.serialization.json import JsonSerializer

            for abstract_type, implementation_type in self._repository_mappings.items():

                def make_custom_repo_factory(impl_type):
                    def custom_repo_factory(provider: ServiceProvider):
                        # Get entity type from implementation's base classes
                        entity_type = None
                        collection_name = None

                        # Extract entity type from MotorRepository[TEntity, TKey] base
                        for base in getattr(impl_type, "__orig_bases__", []):
                            if hasattr(base, "__origin__") and base.__origin__.__name__ == "MotorRepository":
                                if hasattr(base, "__args__") and len(base.__args__) >= 1:
                                    entity_type = base.__args__[0]
                                    # Determine collection name
                                    collection_name = entity_type.__name__.lower()
                                    if collection_name.endswith("dto"):
                                        collection_name = collection_name[:-3]
                                    break

                        if entity_type is None:
                            raise ValueError(f"Could not determine entity type for {impl_type.__name__}. " f"Ensure it extends MotorRepository[TEntity, TKey]")

                        # Construct repository with proper dependencies
                        mediator = provider.get_service(Mediator)
                        if mediator is None:
                            mediator = provider.get_required_service(Mediator)

                        return impl_type(
                            client=provider.get_required_service(AsyncIOMotorClient),
                            database_name=self._database_name,
                            collection_name=collection_name,
                            serializer=provider.get_required_service(JsonSerializer),
                            entity_type=entity_type,
                            mediator=mediator,
                        )

                    return custom_repo_factory

                builder.services.add_scoped(abstract_type, implementation_factory=make_custom_repo_factory(implementation_type))
