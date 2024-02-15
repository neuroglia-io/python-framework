from classy_fastapi import post
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from samples.openbank.application.commands.transactions import CreateBankAccountTransferCommand, CreateBankAccountDepositCommand
from samples.openbank.integration.commands.transactions import CreateBankAccountTransferCommandDto, CreateBankAccountDepositCommandDto
from samples.openbank.integration.models.bank import BankTransactionDto


class TransactionsController(ControllerBase):

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/transfer", response_model=BankTransactionDto, status_code=201, responses=ControllerBase.error_responses)
    async def create_transfer(self, command: CreateBankAccountTransferCommandDto) -> BankTransactionDto:
        ''' Creates a new transfer from a bank account to another '''
        return self.process(await self.mediator.execute_async(self.mapper.map(command, CreateBankAccountTransferCommand)))

    @post("/deposit", response_model=BankTransactionDto, status_code=201, responses=ControllerBase.error_responses)
    async def create_deposit(self, command: CreateBankAccountDepositCommandDto) -> BankTransactionDto:
        ''' Creates a new deposit to a bank account owned by the depositor'''
        return self.process(await self.mediator.execute_async(self.mapper.map(command, CreateBankAccountDepositCommand)))
