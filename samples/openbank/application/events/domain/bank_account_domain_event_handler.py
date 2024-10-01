from decimal import Decimal
from multipledispatch import dispatch

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.queries.generic import GetByIdQuery
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import DomainEventHandler, Mediator

from samples.openbank.application.events.domain_event_handler_base import DomainEventHandlerBase
from samples.openbank.domain.events.bank_transaction import BankAccountTransactionRecordedDomainEventV1
from samples.openbank.domain.models.bank_account import BankTransactionTypeV1, BankAccount
from samples.openbank.domain.events.bank_account import BankAccountCreatedDomainEventV1
from samples.openbank.integration.models.person import PersonDto
from samples.openbank.integration.models.bank import BankAccountDto


class BankAccountDomainEventHandler(DomainEventHandlerBase[BankAccount, BankAccountDto, str],
                                    DomainEventHandler[BankAccountCreatedDomainEventV1 | BankAccountTransactionRecordedDomainEventV1]):

    def __init__(self, mediator: Mediator, mapper: Mapper, write_models: Repository[BankAccount, str], read_models: Repository[BankAccountDto, str], cloud_event_bus: CloudEventBus, cloud_event_publishing_options: CloudEventPublishingOptions):
        super().__init__(mediator, mapper, write_models, read_models, cloud_event_bus, cloud_event_publishing_options)

    write_models: Repository[BankAccount, str]

    read_models: Repository[BankAccountDto, str]

    @dispatch(BankAccountCreatedDomainEventV1)
    async def handle_async(self, e: BankAccountCreatedDomainEventV1) -> None:
        owner: PersonDto = (await self.mediator.execute_async(GetByIdQuery[PersonDto, str](e.owner_id))).data
        bank_account = await self.get_or_create_read_model_async(e.aggregate_id)
        if not hasattr(bank_account, "balance"):
            bank_account.balance = Decimal(0)
        bank_account.balance = Decimal(0)
        bank_account.owner_id = owner.id
        bank_account.owner = f"{owner.first_name} {owner.last_name}"
        await self.read_models.update_async(bank_account)
        await self.publish_cloud_event_async(e)

    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    async def handle_async(self, e: BankAccountTransactionRecordedDomainEventV1) -> None:
        bank_account = await self.get_or_create_read_model_async(e.aggregate_id)
        if not hasattr(bank_account, "balance"):
            bank_account.balance = Decimal(0)
        if e.transaction.type == BankTransactionTypeV1.DEPOSIT.value or \
            e.transaction.type == BankTransactionTypeV1.INTEREST.value or \
                (e.transaction.type == BankTransactionTypeV1.TRANSFER.value and e.transaction.to_account_id == bank_account.id):
            bank_account.balance = Decimal(bank_account.balance) + Decimal(e.transaction.amount)
        else:
            bank_account.balance = str(Decimal(bank_account.balance) - Decimal(e.transaction.amount))
        await self.read_models.update_async(bank_account)
        await self.publish_cloud_event_async(e)
