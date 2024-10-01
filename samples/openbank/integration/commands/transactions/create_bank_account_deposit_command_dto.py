from decimal import Decimal
from pydantic import BaseModel
from typing import Optional


class CreateBankAccountDepositCommandDto(BaseModel):
    ''' Represents the command used to create a new bank account deposit'''

    depositor_id: str
    ''' Gets the id of the person who deposit the cash'''

    to_bank_account_id: str
    ''' Gets the id of the bank account where the deposit is made'''

    amount: Decimal
    ''' Gets the amount to deposit '''

    communication: Optional[str] = None
    ''' Gets the communication, if any, associated with the deposit to create '''
