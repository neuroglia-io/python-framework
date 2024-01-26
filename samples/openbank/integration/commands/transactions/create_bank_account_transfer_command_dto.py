from decimal import Decimal
from pydantic import BaseModel
from typing import Optional


class CreateBankAccountTransferCommandDto(BaseModel):
    ''' Represents the command used to create a new bank account transfer '''    

    from_bank_account_id: str
    ''' Gets the id of the bank account to transfer the specified amount from '''
    
    to_bank_account_id: str
    ''' Gets the id of the bank account to transfer the specified amount to '''
    
    amount : Decimal
    ''' Gets the amount to transfer '''
    
    communication : Optional[str] = None
    ''' Gets the communication, if any, associated with the transfer to create '''
   