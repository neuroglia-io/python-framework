from uuid import uuid4
from pymongo import MongoClient
import pytest
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository, MongoRepositoryOptions
from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProvider
from neuroglia.serialization.json import JsonSerializer
from neuroglia.serialization.abstractions import Serializer, TextSerializer

from tests.data import UserDto


class TestMongoRepository:

    _mongo_database_name = 'test'

    _service_provider: ServiceProvider
    _mongo_client: MongoClient
    _repository: QueryableRepository[UserDto, str]

    @pytest.mark.asyncio
    async def test_add_should_work(self):
        # arrange
        self._setup()
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        user = UserDto(user_id, user_name, user_email)

        # act
        await self._repository.add_async(user)
        result = await self._repository.get_async(user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == user_name, f"expected id '{user_name}', got '{result.name}' instead"
        assert result.email == user_email, f"expected id '{user_email}', got '{result.email}' instead"

        # clean
        self._teardown()

    @pytest.mark.asyncio
    async def test_contains_should_work(self):
        # arrange
        self._setup()
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.add_async(user)

        # act
        exists = await self._repository.contains_async(user.id)

        # assert
        assert exists, f"failed to find the user with the specified id '{user.id}'"

    @pytest.mark.asyncio
    async def test_get_should_work(self):
        # arrange
        self._setup()
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.add_async(user)

        # act
        result = await self._repository.get_async(user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"

        # clean
        self._teardown()

    @pytest.mark.asyncio
    async def test_update_should_work(self):
        # arrange
        self._setup()
        user_id = str(uuid4())
        user = UserDto(user_id, 'John Doe', 'john.doe@email.com')
        await self._repository.add_async(user)
        updated_user_name = "Jane Doe"
        updated_user_email = "jane.doe@email.com"
        user.name = updated_user_name
        user.email = updated_user_email

        # act
        await self._repository.update_async(user)
        result = await self._repository.get_async(user.id)

        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == updated_user_name, f"expected id '{updated_user_name}', got '{result.name}' instead"
        assert result.email == updated_user_email, f"expected id '{updated_user_email}', got '{result.email}' instead"

        # clean
        self._teardown()

    @pytest.mark.asyncio
    async def test_query_should_work(self):
        # arrange
        self._setup()
        prefix = 'fake'
        count = 10
        for i in range(count):
            await self._repository.add_async(UserDto(str(uuid4()), f'{prefix}_name_{i}', f'{prefix}_email_{i}'))

        # act
        query = await self._repository.query_async()
        query = query.where(lambda u: u.name.startswith('fake'))
        results = query.to_list()

        # assert
        assert len(results) == count, f"expected to match {count} items, matched '{len(results)}' instead"

        # clean
        self._teardown()

    @pytest.mark.asyncio
    async def test_remove_should_work(self):
        # arrange
        self._setup()
        user = UserDto(str(uuid4()), 'John Doe', 'john.doe@email.com')
        await self._repository.add_async(user)

        # act
        await self._repository.remove_async(user.id)
        result = await self._repository.get_async(user.id)

        # assert
        assert result is None, f"expected None, got removed user"

        # clean
        self._teardown()

    def _setup(self) -> None:
        self._service_provider = TestMongoRepository._build_services()
        self._mongo_client = self._service_provider.get_required_service(MongoClient)
        self._repository = self._service_provider.get_required_service(QueryableRepository[UserDto, str])

    @staticmethod
    def _build_services() -> ServiceProvider:
        connection_string = 'mongodb://localhost:27099'
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        services.add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        services.add_singleton(MongoRepositoryOptions[UserDto, str], singleton=MongoRepositoryOptions[UserDto, str](TestMongoRepository._mongo_database_name))
        services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
        services.add_singleton(Repository[UserDto, str], MongoRepository[UserDto, str])
        services.add_singleton(QueryableRepository[UserDto, str], implementation_factory=lambda provider: provider.get_required_service(Repository[UserDto, str]))
        return services.build()

    def _teardown(self):
        self._mongo_client.drop_database(TestMongoRepository._mongo_database_name)
        self._service_provider.dispose()
