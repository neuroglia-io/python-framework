from neuroglia.mapping.mapper import MappingProfile
from samples.openbank.domain.models.bank_account import BankAccount
from samples.openbank.integration.models import BankAccountDto

class Profile(MappingProfile):
    ''' Represents the application's mapping profile '''
    
    def __init__(self):
        super().__init__()
        
        self.create_map(BankAccount, BankAccountDto)