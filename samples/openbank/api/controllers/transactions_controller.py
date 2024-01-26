from classy_fastapi import post
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator 
from neuroglia.mvc.controller_base import ControllerBase
from samples.openbank.application.commands.transactions import CreateBankAccountTransferCommand
from samples.openbank.integration.commands.transactions import CreateBankAccountTransferCommandDto
from samples.openbank.integration.models import BankTransactionDto


class TransactionsController(ControllerBase):
    
    def __init__(self, service_provider : ServiceProviderBase, mapper : Mapper, mediator : Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/", response_model=BankTransactionDto, status_code=201, responses=ControllerBase.error_responses)
    async def create_bank_account(self, command : CreateBankAccountTransferCommandDto) -> BankTransactionDto:
        ''' Creates a new bank account '''
        return self.process(await self.mediator.execute_async(self.mapper.map(command, CreateBankAccountTransferCommand)))