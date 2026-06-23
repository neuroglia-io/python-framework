from typing import Any

from pydantic import BaseModel, Field

flag = Field(description="Boolean Flag stating if the external dependency is available or not.")


class SelfHealthCheckResultDto(BaseModel):
    online: bool

    detail: str


class ExternalDependenciesHealthCheckResultDto(BaseModel):
    """Flags statings whether external dependencies are available."""

    identity_provider: bool = flag
    """Whether the IDP is reachable."""

    events_gateway: bool = flag
    """Whether the EventsGateway is reachable."""

    cache_db: bool = flag
    """Whether the CacheDB is reachable."""
