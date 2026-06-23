"""System Status API Controller.

Provides system health and monitoring endpoints for the lab resource manager.
"""

from datetime import datetime
from typing import Any

from application.services.lab_instance_scheduler_service import (
    LabInstanceSchedulerService,
)
from classy_fastapi.decorators import get
from domain.resources.lab_instance_request import LabInstancePhase
from fastapi import HTTPException
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase


class StatusController(ControllerBase):
    """Controller for system status and monitoring."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/health")
    async def get_health(self) -> dict[str, Any]:
        """Get basic health status."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "service": "lab-resource-manager", "version": "1.0.0"}

    @get("/status")
    async def get_system_status(self) -> dict[str, Any]:
        """Get detailed system status."""
        try:
            # Get repository from service provider
            repository = self.service_provider.get_service(LabInstanceResourceRepository)

            # Collect statistics
            stats = {}
            for phase in LabInstancePhase:
                count = await repository.count_by_phase_async(phase)
                stats[f"instances_{phase.value.lower()}"] = count

            # Get scheduler service statistics if available
            try:
                scheduler = self.service_provider.get_service(LabInstanceSchedulerService)
                scheduler_stats = await scheduler.get_service_statistics_async()
                stats.update({"scheduler": scheduler_stats})
            except Exception:
                stats["scheduler"] = {"status": "unavailable"}

            return {"status": "operational", "timestamp": datetime.utcnow().isoformat(), "statistics": stats, "uptime_seconds": 0}  # Would track actual uptime

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

    @get("/metrics")
    async def get_metrics(self) -> dict[str, Any]:
        """Get system metrics in a format suitable for monitoring tools."""
        try:
            repository = self.service_provider.get_service(LabInstanceResourceRepository)

            metrics = {"lab_instances_total": 0, "lab_instances_by_phase": {}, "timestamp": datetime.utcnow().isoformat()}

            total_count = 0
            for phase in LabInstancePhase:
                count = await repository.count_by_phase_async(phase)
                metrics["lab_instances_by_phase"][phase.value.lower()] = count
                total_count += count

            metrics["lab_instances_total"] = total_count

            return metrics

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

    @get("/ready")
    async def get_readiness(self) -> dict[str, Any]:
        """Get readiness status for Kubernetes readiness probe."""
        try:
            # Check if essential services are available
            repository = self.service_provider.get_service(LabInstanceResourceRepository)

            # Simple connectivity test
            await repository.count_by_phase_async(LabInstancePhase.PENDING)

            return {"status": "ready", "timestamp": datetime.utcnow().isoformat(), "checks": {"repository": "ok"}}

        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
