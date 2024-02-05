from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.eventing.cloud_events.infrastructure import CloudEventIngestor, CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublisher, ManagedHttpClient
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from neuroglia.hosting.web import ExceptionHandlingMiddleware, WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, RequestHandler
from neuroglia.serialization.json import JsonSerializer
from samples.openbank.application.queries.account_by_owner import AccountsByOwnerQueryHandler


database_name = "openbank"
application_module = "samples.openbank.application"

builder = WebApplicationBuilder()

Mapper.configure(builder, [application_module])
Mediator.configure(builder, [application_module, "samples.openbank.application.queries"])
builder.services.add_transient(RequestHandler, AccountsByOwnerQueryHandler)  # todo: remove when mediator is fixed
builder.services.try_add_singleton(ManagedHttpClient)

CloudEventIngestor.configure(builder, ["samples.openbank.application.events.integration.score_report_event_handler"])
CloudEventPublisher.configure(builder)
ESEventStore.configure(builder, EventStoreOptions(database_name))
DataAccessLayer.WriteModel.configure(builder, ["samples.openbank.domain.models"], lambda builder_, entity_type, key_type: EventSourcingRepository.configure(builder_, entity_type, key_type))
DataAccessLayer.ReadModel.configure(builder, ["samples.openbank.integration.models", "samples.openbank.application.events.integration.score_report_event_handler"], lambda builder_, entity_type, key_type: MongoRepository.configure(builder_, entity_type, key_type, database_name))
JsonSerializer.configure(builder)
builder.add_controllers(["samples.openbank.api.controllers"])

app = builder.build()

# app.add_middleware(ExceptionHandlingMiddleware, service_provider=app.services)
app.add_middleware(CloudEventMiddleware, service_provider=app.services)
app.use_controllers()

app.run()
