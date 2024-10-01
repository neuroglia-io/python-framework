from neuroglia.data.abstractions import DomainEvent
from neuroglia.mapping.mapper import map_to
from samples.openbank.application.events.integration.bank_account_event_handlers import BankAccountTransactionRecordedIntegrationEventV1
from samples.openbank.domain.models.bank_transaction import BankTransactionV1, BankTransactionTypeV1  # Splitting into a separate module vs BankAccount in order to avoid circular import in the application's domain_event_handler


@map_to(BankAccountTransactionRecordedIntegrationEventV1)
class BankAccountTransactionRecordedDomainEventV1(DomainEvent[str]):

    def __init__(self, aggregate_id: str, transaction: BankTransactionV1):
        super().__init__(aggregate_id)
        self.transaction = transaction

    type: BankTransactionTypeV1

    transaction: BankTransactionV1
