from uuid import uuid4
from pymongo import MongoClient
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository, MongoRepositoryOptions
from neuroglia.dependency_injection.service_provider import ServiceCollection
from tests.data import UserDto


class TestMongoRepository:
    
    def test_add_should_work(self):
        # arrange
        connection_string = 'mongodb://localhost:27017'
        services = ServiceCollection()
        services.add_singleton(MongoRepositoryOptions[UserDto, str], singleton= MongoRepositoryOptions[UserDto, str]('test-database'))
        services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
        services.add_singleton(Repository[UserDto, str], MongoRepository[UserDto, str])
        services.add_singleton(QueryableRepository[UserDto, str], implementation_factory= lambda provider: provider.get_required_service(Repository[UserDto, str]))
        service_provider = services.build()
        repository : QueryableRepository[UserDto, str] = service_provider.get_required_service(QueryableRepository[UserDto, str])
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        user = UserDto(user_id, user_name, user_email)

        # act
        repository.add(user)
        result = repository.get(user.id)
        
        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == user_name, f"expected id '{user_name}', got '{result.name}' instead"
        assert result.email == user_email, f"expected id '{user_email}', got '{result.email}' instead"
        
    def test_update_should_work(self):
        # arrange
        connection_string = 'mongodb://localhost:27017'
        services = ServiceCollection()
        services.add_singleton(MongoRepositoryOptions[UserDto, str], singleton= MongoRepositoryOptions[UserDto, str]('test-database'))
        services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
        services.add_singleton(Repository[UserDto, str], MongoRepository[UserDto, str])
        services.add_singleton(QueryableRepository[UserDto, str], implementation_factory= lambda provider: provider.get_required_service(Repository[UserDto, str]))
        service_provider = services.build()
        repository : QueryableRepository[UserDto, str] = service_provider.get_required_service(QueryableRepository[UserDto, str])
        user_id = str(uuid4())
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        user = UserDto(user_id, user_name, user_email)
        repository.add(user)
        updated_user_name = "Jane Doe"
        updated_user_email = "jane.doe@email.com"
        user.name = updated_user_name
        user.email = updated_user_email
        
        # act
        repository.update(user)
        result = repository.get(user.id)
        
        # assert
        assert result is not None, f"failed to find the user with the specified id '{user.id}'"
        assert result.id == user_id, f"expected id '{user_id}', got '{result.id}' instead"
        assert result.name == updated_user_name, f"expected id '{updated_user_name}', got '{result.name}' instead"
        assert result.email == updated_user_email, f"expected id '{updated_user_email}', got '{result.email}' instead"
        
    def test_remove_should_work(self):
        # arrange
        connection_string = 'mongodb://localhost:27017'
        services = ServiceCollection()
        services.add_singleton(MongoRepositoryOptions[UserDto, str], singleton= MongoRepositoryOptions[UserDto, str]('test-database'))
        services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
        services.add_singleton(Repository[UserDto, str], MongoRepository[UserDto, str])
        services.add_singleton(QueryableRepository[UserDto, str], implementation_factory= lambda provider: provider.get_required_service(Repository[UserDto, str]))
        service_provider = services.build()
        repository : QueryableRepository[UserDto, str] = service_provider.get_required_service(QueryableRepository[UserDto, str])
        user_id = str(uuid4())
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        user = UserDto(user_id, user_name, user_email)
        repository.add(user)
        
        # act
        repository.remove(user.id)
        result = repository.get(user.id)
        
        # assert
        assert result is None, f"expected None, got removed user"