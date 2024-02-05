from neuroglia.eventing.cloud_events.decorators import cloudevent
from dataclasses import dataclass
from datetime import date
from neuroglia.integration.models import IntegrationEvent
from samples.openbank.domain.models.address import Address
from samples.openbank.integration.person_gender import PersonGender


@cloudevent("io.openbank.test.requested.v1")
@dataclass
class PersonRegisteredIntegrationEvent(IntegrationEvent[str]):

    created_at: str

    aggregate_id: str

    first_name: str

    last_name: str

    nationality: str

    date_of_birth: date
