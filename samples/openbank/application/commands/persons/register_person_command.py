from dataclasses import dataclass
from datetime import date
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import map_from
from neuroglia.mediation.mediator import CommandHandler
from samples.openbank.domain.models import Address, Person
from samples.openbank.integration import PersonGender
from samples.openbank.integration.commands.persons import RegisterPersonCommandDto
from samples.openbank.integration.models.person import PersonDto


@map_from(RegisterPersonCommandDto)
@dataclass
class RegisterPersonCommand:
    ''' Represents the command used to register a new person '''

    first_name: str

    last_name: str

    nationality: str

    gender: PersonGender

    date_of_birth: date

    address: Address


class RegisterPersonCommandHandler(CommandHandler[RegisterPersonCommand, OperationResult[PersonDto]]):
    ''' Represents the service used to handle RegisterPersonCommands '''

    def __init__(self, mapper: Mapper, repository: Repository[Person, str]):
        self.mapper = mapper
        self.repository = repository

    mapper: Mapper

    repository: Repository[Person, str]

    async def handle_async(self, request: RegisterPersonCommand) -> OperationResult[PersonDto]:
        person = await self.repository.add_async(Person(request.first_name, request.last_name, request.nationality, request.gender, request.date_of_birth, request.address))
        return self.created(self.mapper.map(person.state, PersonDto))
