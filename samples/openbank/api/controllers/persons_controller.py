from classy_fastapi import post
from classy_fastapi.decorators import get
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator 
from neuroglia.mvc.controller_base import ControllerBase
from samples.openbank.application.commands.persons import RegisterPersonCommand
from samples.openbank.application.queries.generic import GetByIdQuery
from samples.openbank.integration.commands.persons import RegisterPersonCommandDto
from samples.openbank.integration.models import PersonDto


class PersonsController(ControllerBase):
    
    def __init__(self, service_provider : ServiceProviderBase, mapper : Mapper, mediator : Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/", response_model=PersonDto, status_code=201, responses=ControllerBase.error_responses)
    async def register_person(self, command : RegisterPersonCommandDto) -> PersonDto:
        ''' Registers a new person '''
        return self.process(await self.mediator.execute_async(self.mapper.map(command, RegisterPersonCommand)))

    @get("/byid/{id}", response_model=PersonDto, responses=ControllerBase.error_responses)
    async def get_person_by_id(self, id: str) -> PersonDto:
        ''' Gets the person with the specified id '''
        return self.process(await self.mediator.execute_async(GetByIdQuery[PersonDto, str](id)))