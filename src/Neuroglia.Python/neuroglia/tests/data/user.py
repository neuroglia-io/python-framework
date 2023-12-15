from typing import Optional
import uuid
from neuroglia.data.abstractions import DomainEvent, AggregateRoot, AggregateState

class UserCreatedDomainEventV1(DomainEvent[str]):

    def __init__(self, aggregate_id: str, name: str, email: str):
        super().__init__(aggregate_id)
        self.name = name
        self.email = email        

    name: str
    
    email: str
        

class UserStateV1(AggregateState[str]):
  
    name: str
    
    email: str
    
    def on(self, e : UserCreatedDomainEventV1):
        self._id = e.aggregate_id
        self.created_at = e.created_at
        self.name = e.name
        self.email = e.email
       

class User(AggregateRoot[UserStateV1, str]):

    def __init__(self, name : str, email: Optional[str] = None):
        super().__init__()
        self.state.on(self.register_event(UserCreatedDomainEventV1(str(uuid.uuid4()).replace('-', ''), name, email)))