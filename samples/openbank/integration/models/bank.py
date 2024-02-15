from dataclasses import dataclass
from decimal import Decimal
from neuroglia.data.abstractions import queryable


@queryable
@dataclass
class BankAccountDto:

    id: str

    owner_id: str

    owner: str

    balance: Decimal


@queryable
@dataclass
class BankTransactionDto:

    pass
