from multipledispatch import dispatch
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation.mediator import DomainEventHandler
from samples.openbank.domain.models.bank_account import BankAccount, BankAccountCreatedDomainEventV1, BankAccountTransactionRecordedDomainEventV1
from samples.openbank.integration.models import BankAccountDto

class BankAccountDomainEventHandler(DomainEventHandler[BankAccountCreatedDomainEventV1 | BankAccountTransactionRecordedDomainEventV1]):
    
    def __init__(self, write_models: Repository[BankAccount, str], read_models: Repository[BankAccountDto, str]):
        self.write_models = write_models
        self.read_models = read_models        

    write_models: Repository[BankAccount, str]
    
    read_models: Repository[BankAccountDto, str]
   
    @dispatch(BankAccountCreatedDomainEventV1)
    async def handle_async(self, e: BankAccountCreatedDomainEventV1) -> None:
        pass
    
    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    async def handle_async(self, e: BankAccountTransactionRecordedDomainEventV1) -> None:
        pass