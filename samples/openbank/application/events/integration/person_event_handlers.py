from dataclasses import dataclass
from datetime import date

from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.integration.models import IntegrationEvent

from samples.openbank.domain.models.address import Address
from samples.openbank.integration.person_gender import PersonGender


@cloudevent("person.registered.v1")
@dataclass
class PersonRegisteredIntegrationEvent(IntegrationEvent[str]):

    created_at: str

    aggregate_id: str

    first_name: str

    last_name: str

    nationality: str

    date_of_birth: date

    address: Address

    gender: PersonGender
