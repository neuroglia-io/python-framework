from uuid import uuid4
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.memory.memory_repository import MemoryRepository
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mediation.mediator import Mediator, NotificationHandler, RequestHandler
from tests.data import GreetCommand, UserCreatedDomainEventV1, UserDto
from tests.services import GreetCommandHandler, UserCreatedDomainEventV1Handler


class TestMediator:

    def test_execute_request_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_singleton(RequestHandler, GreetCommandHandler)
        service_provider = services.build()
        mediator : Mediator = service_provider.get_service(Mediator)
        greetings = 'Hello, world!'
        command = GreetCommand(greetings= greetings)
        
        # act
        result = mediator.execute(command)
        
        # assert
        assert result is not None, 'result is none'
        assert result.status is 200, f"expected status '200', got '{result.status}'"
        assert result.data == greetings, f"expected greetings '{greetings}', got '{result.data}'"
        
    def test_publish_notification_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_singleton(Repository[UserDto, str], singleton = MemoryRepository[UserDto, str]())
        services.add_singleton(NotificationHandler, UserCreatedDomainEventV1Handler)
        service_provider = services.build()
        mediator : Mediator = service_provider.get_service(Mediator)
        repository : Repository[UserDto, str] = service_provider.get_service(Repository[UserDto, str])
        user_id = str(uuid4())
        user_name = 'John Doe'
        user_email = 'john.doe@email.com'
        e = UserCreatedDomainEventV1(user_id, user_name, user_email)
        
        # act
        mediator.publish(e)
        user = repository.get(user_id)
        
        # assert
        assert user is not None, 'user is None'
        assert user.id == user_id, f"expected user id to be '{user_id}', but found '{user.id}'"
        assert user.name == user_name, f"expected user name to be '{user_name}', but found '{user.name}'"
        assert user.email == user_email, f"expected user id to be '{user_email}', but found '{user.email}'"