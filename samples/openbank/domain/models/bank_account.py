from decimal import Decimal
from typing import List
import uuid
from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_to
from samples.openbank.domain.events.bank_account import BankAccountCreatedDomainEventV1
from samples.openbank.domain.events.bank_transaction import BankAccountTransactionRecordedDomainEventV1
from samples.openbank.domain.models.person import Person
from samples.openbank.integration.models.bank import BankAccountDto
from samples.openbank.domain.models.bank_transaction import BankTransactionV1, BankTransactionTypeV1  # Splitting into a separate module vs BankAccount in order to avoid circular import in the application's domain_event_handler


@map_to(BankAccountDto)
class BankAccountStateV1(AggregateState[str]):

    def __init__(self):
        super().__init__()

    owner_id: str

    transactions: List[BankTransactionV1] = list[BankTransactionV1]()

    balance: Decimal

    overdraft_limit: Decimal

    @dispatch(BankAccountCreatedDomainEventV1)
    def on(self, e: BankAccountCreatedDomainEventV1):
        self.id = e.aggregate_id
        self.created_at = e.created_at
        self.owner_id = e.owner_id
        self.overdraft_limit = e.overdraft_limit

    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    def on(self, e: BankAccountTransactionRecordedDomainEventV1):
        self.last_modified = e.created_at
        self.transactions.append(e.transaction)
        self._compute_balance()

    def _compute_balance(self):
        # todo: use snapshots
        balance: Decimal = 0
        for transaction in self.transactions:
            if transaction.type == BankTransactionTypeV1.DEPOSIT.value or transaction.type == BankTransactionTypeV1.INTEREST.value or (transaction.type == BankTransactionTypeV1.TRANSFER.value and transaction.to_account_id == self.id):
                balance = Decimal(balance) + Decimal(transaction.amount)
            else:
                balance = Decimal(balance) - Decimal(transaction.amount)
        self.balance = balance


class BankAccount(AggregateRoot[BankAccountStateV1, str]):

    def __init__(self, owner: Person, overdraft_limit: Decimal = 0):
        super().__init__()
        self.state.on(self.register_event(BankAccountCreatedDomainEventV1(str(uuid.uuid4()).replace('-', ''), owner.id(), overdraft_limit)))

    def get_available_balance(self) -> Decimal:
        return Decimal(self.state.balance) + Decimal(self.state.overdraft_limit)

    def try_add_transaction(self, transaction: BankTransactionV1) -> bool:
        if transaction.type != BankTransactionTypeV1.DEPOSIT and transaction.type != BankTransactionTypeV1.INTEREST and not (transaction.type == BankTransactionTypeV1.TRANSFER and transaction.to_account_id == self.id()) and transaction.amount > self.get_available_balance():
            return False
        self.state.on(self.register_event(BankAccountTransactionRecordedDomainEventV1(self.id(), transaction)))
        return True
