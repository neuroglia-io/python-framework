from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.eventing.cloud_events.infrastructure import  CloudEventIngestor, CloudEventMiddleware
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from samples.openbank.domain.models.bank_account import BankAccount
from samples.openbank.integration.models import BankAccountDto

database_name = "openbank"
application_module = "samples.openbank.application"

builder = WebApplicationBuilder()

ESEventStore.configure(builder, EventStoreOptions(database_name))
EventSourcingRepository.configure(builder, BankAccount, str)
MongoRepository.configure(builder, BankAccountDto, str, database_name)

Mapper.configure(builder, [application_module])
Mediator.configure(builder, [application_module])
CloudEventIngestor.configure(builder, [application_module])

builder.add_controllers(["samples.openbank.api.controllers"])

app = builder.build()

app.add_middleware(CloudEventMiddleware, service_provider=app.services)
app.use_controllers()

app.run()