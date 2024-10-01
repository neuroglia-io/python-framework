from datetime import date

from neuroglia.data.abstractions import DomainEvent
from neuroglia.mapping.mapper import map_to

from samples.openbank.domain.models import Address
from samples.openbank.integration import PersonGender
from samples.openbank.application.events.integration import PersonRegisteredIntegrationEvent


@map_to(PersonRegisteredIntegrationEvent)
class PersonRegisteredDomainEventV1(DomainEvent[str]):

    def __init__(self, aggregate_id: str, first_name: str, last_name: str, nationality: str, gender: PersonGender, date_of_birth: date, address: Address):
        super().__init__(aggregate_id)
        self.first_name = first_name
        self.last_name = last_name
        self.nationality = nationality
        self.gender = gender
        self.date_of_birth = date_of_birth
        self.address = address

    first_name: str

    last_name: str

    nationality: str

    gender: PersonGender

    date_of_birth: date

    address: Address
