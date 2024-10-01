from uuid import uuid4
from pymongo import MongoClient
import pytest
from neuroglia.data.infrastructure.abstractions import FlexibleRepository, Repository
from neuroglia.data.infrastructure.mongo.mongo_repository import FlexibleMongoRepository, MongoRepositoryOptions
from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProvider
from neuroglia.serialization.json import JsonSerializer
from neuroglia.serialization.abstractions import Serializer, TextSerializer

from tests.data import UserDto


class TestFlexibleMongoRepository:
    """A "FlexibleRepository enables user to set the MongoDB Database name
    as well as the Collection name for all operations.
    """
    _mongo_database_name = 'placeholder'
    _service_provider: ServiceProvider
    _mongo_client: MongoClient
    _repository: FlexibleRepository[UserDto, str]

    @pytest.mark.asyncio
    async def test_add_should_work(self):
        # arrange
        self._setup()
        testcollection = "mytestusers"
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        user = UserDto(user_id, user_name, user_email)

        # act
        await self._repository.set_database("mytestdb")
        await self._repository.add_by_collection_name_async(testcollection, user)
        result = await self._repository.get_by_collection_name_async(testcollection, user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == user_name, f"expected id '{user_name}', got '{result.name}' instead"
        assert result.email == user_email, f"expected id '{user_email}', got '{result.email}' instead"

        # clean
        await self._teardown()

    @pytest.mark.asyncio
    async def test_contains_should_work(self):
        # arrange
        self._setup()
        testcollection = "mytestusers"
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.set_database("mytestdb")
        await self._repository.add_by_collection_name_async(testcollection, user)

        # act
        exists = await self._repository.contains_by_collection_name_async(testcollection, user.id)

        # assert
        assert exists, f"failed to find the user with the specified id '{user.id}'"

    @pytest.mark.asyncio
    async def test_get_should_work(self):
        # arrange
        self._setup()
        testcollection = "mytestusers"
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.add_by_collection_name_async(testcollection, user)

        # act
        result = await self._repository.get_by_collection_name_async(testcollection, user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"

        # clean
        await self._teardown()

    @pytest.mark.asyncio
    async def test_update_should_work(self):
        # arrange
        self._setup()
        testcollection = "mytestusers"
        user_id = str(uuid4())
        user = UserDto(user_id, 'John Doe', 'john.doe@email.com')
        await self._repository.add_by_collection_name_async(testcollection, user)
        updated_user_name = "Jane Doe"
        updated_user_email = "jane.doe@email.com"
        user.name = updated_user_name
        user.email = updated_user_email

        # act
        await self._repository.update_by_collection_name_async(testcollection, user)
        result = await self._repository.get_by_collection_name_async(testcollection, user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == updated_user_name, f"expected id '{updated_user_name}', got '{result.name}' instead"
        assert result.email == updated_user_email, f"expected id '{updated_user_email}', got '{result.email}' instead"

        # clean
        await self._teardown()

    @pytest.mark.asyncio
    async def test_remove_should_work(self):
        # arrange
        self._setup()
        testcollection = "mytestusers"
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.add_by_collection_name_async(testcollection, user)

        # act
        await self._repository.remove_by_collection_name_async(testcollection, user.id)
        result = await self._repository.get_async(user.id)

        # assert
        assert result is None, f"expected None, got removed user"

        # clean
        await self._teardown()

    def _setup(self) -> None:
        self._service_provider = TestFlexibleMongoRepository._build_services()
        self._mongo_client = self._service_provider.get_required_service(MongoClient)
        self._repository = self._service_provider.get_required_service(FlexibleRepository[UserDto, str])

    @staticmethod
    def _build_services() -> ServiceProvider:
        connection_string = 'mongodb://localhost:27099'
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        services.add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        services.add_singleton(MongoRepositoryOptions[UserDto, str], singleton=MongoRepositoryOptions[UserDto, str](TestFlexibleMongoRepository._mongo_database_name))
        services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
        services.add_singleton(Repository[UserDto, str], FlexibleMongoRepository[UserDto, str])
        services.add_singleton(FlexibleRepository[UserDto, str], implementation_factory=lambda provider: provider.get_required_service(Repository[UserDto, str]))
        return services.build()

    async def _teardown(self):
        db_name = await self._repository.get_database()
        self._mongo_client.drop_database(db_name)
        self._service_provider.dispose()
