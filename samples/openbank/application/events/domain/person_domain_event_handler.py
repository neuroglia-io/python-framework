from multipledispatch import dispatch
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation.mediator import DomainEventHandler
from samples.openbank.domain.models.person import Person, PersonRegisteredDomainEventV1
from samples.openbank.integration.models import PersonDto

class PersonDomainEventHandler(DomainEventHandler[PersonRegisteredDomainEventV1]):
    
    def __init__(self, write_models: Repository[Person, str], read_models: Repository[PersonDto, str]):
        self.write_models = write_models
        self.read_models = read_models        

    write_models: Repository[Person, str]
    
    read_models: Repository[PersonDto, str]
   
    @dispatch(PersonRegisteredDomainEventV1)
    async def handle_async(self, e: PersonRegisteredDomainEventV1) -> None:
        pass