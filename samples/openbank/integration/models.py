from dataclasses import dataclass
from decimal import Decimal

@dataclass
class BankAccountDto:
    
    id : str

    owner : str
    
    balance : Decimal