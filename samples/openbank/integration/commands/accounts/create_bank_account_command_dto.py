from pydantic import BaseModel


class CreateBankAccountCommandDto(BaseModel):
    ''' Represents the command used to create a new bank account '''
    
    owner_id: str
    ''' Gets the id of the owner of the bank account to create '''