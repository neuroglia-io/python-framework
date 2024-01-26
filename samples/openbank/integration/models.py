from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from neuroglia.data.abstractions import queryable
from neuroglia.eventing.cloud_events.decorators import cloudevent
from samples.openbank.integration import PersonGender


@dataclass
class AddressDto:
    
    street_name : str
    
    street_number: str
    
    zip_code: str
    
    city : str
    
    state: str
    
    country: str


@queryable
@dataclass
class PersonDto:
    
    id: str
    
    first_name : str
    
    last_name : str
    
    nationality: str
    
    gender : PersonGender
    
    date_of_birth: date
    
    address : AddressDto
    

@queryable
@dataclass
class BankAccountDto:
    
    id : str

    owner : str
    
    balance : Decimal
    

@queryable
@dataclass
class BankTransactionDto:
    
    pass

@cloudevent("test")
class MyCloudEvent:
    
    foo: str
    
    bar : str
    
    baz : str
