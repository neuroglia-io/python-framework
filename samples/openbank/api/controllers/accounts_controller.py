from classy_fastapi.decorators import get
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator 
from neuroglia.mvc.controller_base import ControllerBase
from samples.openbank.application.queries.generic import GetByIdQuery
from samples.openbank.integration.models import BankAccountDto


class AccountsController(ControllerBase):
    
    def __init__(self, service_provider : ServiceProviderBase, mapper : Mapper, mediator : Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @get("/byid/{id}", response_model=BankAccountDto, responses=ControllerBase.error_responses)
    async def get_bank_account_by_id(self, id: str) -> BankAccountDto:
        ''' Gets the bank account with the specified id '''
        return self.process(await self.mediator.execute_async(GetByIdQuery[BankAccountDto, str](id)))