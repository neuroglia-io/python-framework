from multipledispatch import dispatch
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping import Mapper
from neuroglia.mediation import DomainEventHandler, Mediator
from samples.openbank.application.events.domain_event_handler_base import DomainEventHandlerBase
from samples.openbank.domain.models.person import Person, PersonRegisteredDomainEventV1
from samples.openbank.integration.models import PersonDto


class PersonDomainEventHandler(DomainEventHandlerBase[Person, PersonDto, str],
                               DomainEventHandler[PersonRegisteredDomainEventV1]):

    def __init__(self, mediator: Mediator, mapper: Mapper, write_models: Repository[Person, str], read_models: Repository[PersonDto, str]):
        super().__init__(mediator, mapper, write_models, read_models)

    @dispatch(PersonRegisteredDomainEventV1)
    async def handle_async(self, e: PersonRegisteredDomainEventV1) -> None:
        await self.get_or_create_read_model_async(e.aggregate_id)
