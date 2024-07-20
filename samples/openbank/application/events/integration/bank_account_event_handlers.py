from neuroglia.eventing.cloud_events.decorators import cloudevent
from dataclasses import dataclass
from decimal import Decimal

from neuroglia.integration.models import IntegrationEvent
from samples.openbank.domain.models import BankTransactionTypeV1, BankTransactionV1


@cloudevent("bank_account.created.v1")
@dataclass
class BankAccountCreatedIntegrationEventV1(IntegrationEvent[str]):

    created_at: str

    aggregate_id: str

    owner_id: str

    overdraft_limit: Decimal

    balance: Decimal


@cloudevent("bank_account.transaction.recorded.v1")
@dataclass
class BankAccountTransactionRecordedIntegrationEventV1(IntegrationEvent[str]):

    created_at: str

    aggregate_id: str

    type: BankTransactionTypeV1

    transaction: BankTransactionV1
