from pymongo import MongoClient
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository, MongoRepositoryOptions
from neuroglia.eventing.cloud_events.abstractions import CloudEventBus, CloudEventConsumer
from neuroglia.hosting.abstractions import HostedServiceBase
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, RequestHandler
from samples.openbank.api.controllers import AccountsController
from samples.openbank.application.queries import GetByIdQueryHandler
from samples.openbank.integration.models import BankAccountDto


connection_string = 'mongodb://localhost:27017'

builder = WebApplicationBuilder()

builder.services.add_singleton(MongoClient, singleton=MongoClient(connection_string))
#---------------
#todo: instead, add a helper method: we dont want to add 4 services for every single repository injected
builder.services.add_singleton(MongoRepositoryOptions[BankAccountDto, str], singleton= MongoRepositoryOptions[BankAccountDto, str]('openbank'))
builder.services.add_singleton(Repository[BankAccountDto, str], MongoRepository[BankAccountDto, str])
builder.services.add_singleton(QueryableRepository[BankAccountDto, str], implementation_factory= lambda provider: provider.get_required_service(Repository[BankAccountDto, str]))
#---------------
builder.services.add_singleton(Mapper)
builder.services.add_singleton(Mediator)
builder.services.add_singleton(CloudEventBus)
builder.services.add_singleton(HostedServiceBase, CloudEventConsumer)
builder.services.add_transient(RequestHandler, GetByIdQueryHandler[BankAccountDto, str]) #todo: should not be registering that manually, but should be done thanks to reflection (like for add_controllers)

builder.add_controllers([AccountsController.__module__])

app = builder.build()

#todo: add cloud event middleware here
app.use_controllers()

app.run()