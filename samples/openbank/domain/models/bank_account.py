from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid
from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent, Entity
from samples.openbank.domain.models.person import Person


class BankTransactionTypeV1(Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    INTEREST = 'INTEREST'
    

@dataclass
class BankTransactionV1(Entity[str]):
    
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
        
    @dispatch(BankAccountTransactionRecordedDomainEventV1)
    def on(self, e : BankAccountTransactionRecordedDomainEventV1):
        self.last_modified = e.created_at
        self.transactions.append(e.transaction)
        self.compute_balance()
        
    def _compute_balance(self):
        balance : Decimal = 0
        for transaction in self.transactions:
            if transaction.type == BankTransactionTypeV1.DEPOSIT or transaction.type == BankTransactionTypeV1.INTEREST:
                balance = balance + transaction.amount
            else:
                balance = balance - transaction.amount
 

class BankAccount(AggregateRoot[BankAccountStateV1, str]):
    
    def __init__(self, owner : Person, overdraft_limit: Decimal = 0):
        super().__init__()
        self.state.on(self.register_event(BankAccountCreatedDomainEventV1(str(uuid.uuid4()).replace('-', ''), owner.id, overdraft_limit)))
        
    def get_available_balance(self) -> Decimal: return self.state.balance + self.state.overdraft_limit

    def try_add_transaction(self, transaction : BankTransactionV1) -> bool:
        if transaction.type != BankTransactionTypeV1.DEPOSIT and transaction.type != BankTransactionTypeV1.INTEREST and transaction.amount > self.get_available_balance(): return False
        self.state.on(self.register_event(BankAccountTransactionRecordedDomainEventV1(self.id, transaction)))
        return True