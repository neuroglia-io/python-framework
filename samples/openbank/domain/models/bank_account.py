from dataclasses import dataclass
import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid
from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent, Entity
from neuroglia.mapping.mapper import map_to
from samples.openbank.domain.models.person import Person
from samples.openbank.integration.models import BankAccountDto, BankTransactionDto


class BankTransactionTypeV1(Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    INTEREST = 'INTEREST'
    

@map_to(BankTransactionDto)
class BankTransactionV1(Entity[str]):
    
    def __init__(self, type : BankTransactionTypeV1, amount : Decimal, from_account_id : Optional[str], to_account_id : Optional[str], communication: Optional[str] = None):
        self.id = uuid.uuid4()
        self.created_at = datetime.datetime.now()
        self.type = type
        self.amount = amount
        self.from_account_id = from_account_id
        self.to_account_id = to_account_id
        self.communication = communication

    type : BankTransactionTypeV1
    
    amount : Decimal
    
    from_account_id : Optional[str]
    
    to_account_id: Optional[str]
    
    communication: Optional[str] = None
  

class BankAccountCreatedDomainEventV1(DomainEvent[str]):
    
    def __init__(self, aggregate_id: str, owner_id: str, overdraft_limit : Decimal):
        super().__init__(aggregate_id)
        self.owner_id = owner_id
        self.overdraft_limit = overdraft_limit

    owner_id : str
    
    overdraft_limit: Decimal
   

class BankAccountTransactionRecordedDomainEventV1(DomainEvent[str]):
    
    def __init__(self, aggregate_id: str, transaction : BankTransactionV1):
        super().__init__(aggregate_id)
        self.transaction = transaction
        
    type : BankTransactionTypeV1
    
    transaction : BankTransactionV1
    

@map_to(BankAccountDto)
class BankAccountStateV1(AggregateState[str]):
    
    def __init__(self):
        super().__init__()

    owner_id : str
    
    transactions : List[BankTransactionV1] = list[BankTransactionV1]()
    
    overdraft_limit : Decimal
    
    balance : Decimal
    
    @dispatch(BankAccountCreatedDomainEventV1)
    def on(self, e : BankAccountCreatedDomainEventV1):
        self.id = e.aggregate_id
        self.created_at = e.created_at
        self.owner_id = e.owner_id
        self.overdraft_limit = e.overdraft_limit
        self.balance = 100 #todo: replace
        
    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    def on(self, e : BankAccountTransactionRecordedDomainEventV1):
        self.last_modified = e.created_at
        self.transactions.append(e.transaction)
        self._compute_balance()
        
    def _compute_balance(self):
        balance : Decimal = 0
        for transaction in self.transactions:
            if transaction.type == BankTransactionTypeV1.DEPOSIT or transaction.type == BankTransactionTypeV1.INTEREST or (transaction.type == BankTransactionTypeV1.TRANSFER and transaction.to_account_id == self.id):
                balance = Decimal(balance) + Decimal(transaction.amount)
            else:
                balance = Decimal(balance) - Decimal(transaction.amount)
 

class BankAccount(AggregateRoot[BankAccountStateV1, str]):
    
    def __init__(self, owner : Person, overdraft_limit: Decimal = 0):
        super().__init__()
        self.state.on(self.register_event(BankAccountCreatedDomainEventV1(str(uuid.uuid4()).replace('-', ''), owner.id(), overdraft_limit)))
        
    def get_available_balance(self) -> Decimal: return Decimal(self.state.balance) + Decimal(self.state.overdraft_limit)

    def try_add_transaction(self, transaction : BankTransactionV1) -> bool:
        if transaction.type != BankTransactionTypeV1.DEPOSIT and transaction.type != BankTransactionTypeV1.INTEREST and not (transaction.type == BankTransactionTypeV1.TRANSFER and transaction.to_account_id == self.id()) and transaction.amount > self.get_available_balance(): return False
        self.state.on(self.register_event(BankAccountTransactionRecordedDomainEventV1(self.id(), transaction)))
        return True