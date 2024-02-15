
import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_to
from samples.openbank.integration.models.bank import BankTransactionDto


class BankTransactionTypeV1(Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    INTEREST = 'INTEREST'


@map_to(BankTransactionDto)
class BankTransactionV1(Entity[str]):

    def __init__(self, type: BankTransactionTypeV1, amount: Decimal, from_account_id: Optional[str], to_account_id: Optional[str], communication: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.created_at = datetime.datetime.now()
        self.type = type
        self.amount = amount
        self.from_account_id = from_account_id
        self.to_account_id = to_account_id
        self.communication = communication

    type: BankTransactionTypeV1

    amount: Decimal

    from_account_id: Optional[str]

    to_account_id: Optional[str]

    communication: Optional[str] = None
