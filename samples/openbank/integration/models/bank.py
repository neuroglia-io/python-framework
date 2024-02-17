from dataclasses import dataclass
from decimal import Decimal
from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class BankAccountDto(Identifiable):

    id: str

    owner_id: str

    owner: str

    balance: Decimal


@queryable
@dataclass
class BankTransactionDto:

    pass
