"""Get Lab Instance Query Handler.

This handler processes queries to retrieve lab instance resources,
following CQRS patterns adapted for Resource Oriented Architecture.
"""

import logging
from typing import Optional

from application.queries.get_lab_instance_query import GetLabInstanceQuery
from integration.models.lab_instance_dto import LabInstanceDto
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import QueryHandler

log = logging.getLogger(__name__)


class GetLabInstanceQueryHandler(QueryHandler[GetLabInstanceQuery, Optional[LabInstanceDto]]):
    """Handler for retrieving lab instance request resources."""

    def __init__(self, service_provider: ServiceProviderBase, resource_repository: LabInstanceResourceRepository, mapper: Mapper):
        super().__init__(service_provider)
        self.resource_repository = resource_repository
        self.mapper = mapper

    async def handle_async(self, query: GetLabInstanceQuery) -> Optional[LabInstanceDto]:
        """Handle the get lab instance query."""

        try:
            log.debug(f"Retrieving lab instance: {query.resource_id}")

            # Get the resource from repository
            resource = await self.resource_repository.get_async(query.resource_id)

            if resource is None:
                log.debug(f"Lab instance not found: {query.resource_id}")
                return None

            # Map to DTO for response
            result_dto = self.mapper.map(resource, LabInstanceDto)

            log.debug(f"Lab instance retrieved successfully: {query.resource_id}")
            return result_dto

        except Exception as e:
            log.error(f"Failed to retrieve lab instance {query.resource_id}: {e}")
            raise
