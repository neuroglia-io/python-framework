from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus, CloudEventIngestor, CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_ingestor import CloudEventIngestionOptions
from neuroglia.hosting.abstractions import HostedServiceBase
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from samples.openbank.domain.models.bank_account import BankAccount
from samples.openbank.integration.models import BankAccountDto


application_module = "samples.openbank.application"

builder = WebApplicationBuilder()

ESEventStore.configure(builder, EventStoreOptions("openbank"))

EventSourcingRepository.configure(builder, BankAccount, str)
MongoRepository.configure(builder, BankAccountDto, str, "openbank")

Mapper.configure(builder, [application_module])
Mediator.configure(builder, [application_module])
CloudEventIngestor.configure(builder, [application_module])

builder.add_controllers([application_module])

app = builder.build()

app.add_middleware(CloudEventMiddleware, service_provider=app.services) #todo: add cloud event middleware here
app.use_controllers()

app.run()