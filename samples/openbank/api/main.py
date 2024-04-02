from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.eventing.cloud_events.infrastructure import  CloudEventIngestor, CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublisher
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer


database_name = "openbank"
application_module = "samples.openbank.application"

builder = WebApplicationBuilder()

Mapper.configure(builder, [application_module])
Mediator.configure(builder, [application_module])
CloudEventIngestor.configure(builder, ["samples.openbank.integration.models"]) #replace application_module with name of module(s) defining cloud events to handle
CloudEventPublisher.configure(builder)
ESEventStore.configure(builder, EventStoreOptions(database_name))
DataAccessLayer.WriteModel.configure(builder, [ "samples.openbank.domain.models" ], lambda builder_, entity_type, key_type: EventSourcingRepository.configure(builder_, entity_type, key_type))
DataAccessLayer.ReadModel.configure(builder, [ "samples.openbank.integration.models" ], lambda builder_, entity_type, key_type: MongoRepository.configure(builder_, entity_type, key_type, database_name))
JsonSerializer.configure(builder)
builder.add_controllers(["samples.openbank.api.controllers"])

app = builder.build()

#app.add_middleware(ExceptionHandlingMiddleware, service_provider=app.services)
app.add_middleware(CloudEventMiddleware, service_provider=app.services)
app.use_controllers()

app.run()