from abc import ABC, abstractclassmethod
from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import CommandHandler, DomainEventHandler
from neuroglia.data.infrastructure.abstractions import Repository
from tests.data import UserCreatedDomainEventV1, UserDto, GreetCommand


class LoggerBase(ABC):

    @abstractclassmethod
    def log(text: str):
        raise NotImplementedError()


class PrintLogger(LoggerBase):

    def log(text: str):
        print(text)


class FileLogger(LoggerBase):

    def log(text: str):
        with open('example.txt', 'a') as file:
            file.write(f'{text}\n')


class NullLogger(LoggerBase):

    def log(text: str):
        pass


class GreetCommandHandler(CommandHandler[GreetCommand, OperationResult[str]]):

    async def handle_async(self, command: GreetCommand) -> OperationResult[str]:
        result = OperationResult[str]('OK', 200)
        result.data = "Hello, world!"
        return result


class UserCreatedDomainEventV1Handler(DomainEventHandler[UserCreatedDomainEventV1]):

    def __init__(self, users: Repository[UserDto, str]):
        self.users = users

    users: Repository[UserDto, str]

    async def handle_async(self, e: UserCreatedDomainEventV1):
        await self.users.add_async(UserDto(e.aggregate_id, e.name, e.email))
