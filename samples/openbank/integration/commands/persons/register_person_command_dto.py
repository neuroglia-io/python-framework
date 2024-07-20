from datetime import date
from pydantic import BaseModel
from samples.openbank.integration import PersonGender
from samples.openbank.integration.models.person import AddressDto


class RegisterPersonCommandDto(BaseModel):
    ''' Represents the command used to register a new person '''

    first_name: str

    last_name: str

    nationality: str

    gender: PersonGender

    date_of_birth: date

    address: AddressDto
