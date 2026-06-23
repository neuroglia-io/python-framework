import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, cast

from pydantic import Field
from pydantic_settings import BaseSettings

from neuroglia.dependency_injection.service_provider import (
    ServiceCollection,
    ServiceProviderBase,
    ServiceScopeBase,
)


class HostBase(ABC):
    """Defines the fundamentals of an program's abstraction"""

    services: ServiceProviderBase

    @abstractmethod
    async def start_async(self):
        """Starts the program"""
        raise NotImplementedError()

    @abstractmethod
    async def stop_async(self):
        """Attempts to gracefully stop the program"""
        raise NotImplementedError()

    def run(self):
        """Runs the program"""
        try:
            asyncio.get_running_loop()
            asyncio.ensure_future(self.start_async())
        except RuntimeError:
            asyncio.run(self.start_async())

    @abstractmethod
    def dispose(self):
        """Disposes of the program's resources"""
        raise NotImplementedError()


class HostedService:
    """Defines the fundamentals of a service managed by the host"""

    async def start_async(self):
        """Starts the service"""

    async def stop_async(self):
        """Attempts to gracefully stop the service"""


class HostApplicationLifetime:
    """Represents a service used to manage (and notify about) the application's lifetime events"""

    on_application_started: list[Callable[[], None]] = list[Callable[[], None]]()
    """ Gets a list containing the callbacks, if any, to invoke when the application has started """

    on_application_stopping: list[Callable[[], None]] = list[Callable[[], None]]()
    """ Gets a list containing the callbacks, if any, to invoke when the application is stopping """

    on_application_stopped: list[Callable[[], None]] = list[Callable[[], None]]()
    """ Gets a list containing the callbacks, if any, to invoke when the application has been stopped """

    def stop_application(self):
        """Stops the application"""

    @asynccontextmanager
    async def _run_async(self, app: HostBase):
        await asyncio.gather(*[handler() for handler in self.on_application_started])
        yield
        await asyncio.gather(*[handler() for handler in self.on_application_stopping])
        await app.stop_async()
        await asyncio.gather(*[handler() for handler in self.on_application_stopped])


class Host(HostBase):
    """Represents the default implementation of the HostBase class"""

    def __init__(self, services: ServiceProviderBase):
        self.services = services

    async def start_async(self):
        hosted_services = [cast(HostedService, service) for service in self.services.get_services(HostedService)]
        start_tasks = [hosted_service.start_async() for hosted_service in hosted_services]
        await asyncio.gather(*start_tasks)

    async def stop_async(self):
        hosted_services = [cast(HostedService, service) for service in self.services.get_services(HostedService)]
        stop_tasks = [hosted_service.stop_async() for hosted_service in hosted_services]
        await asyncio.gather(*stop_tasks)

    def dispose(self):
        if isinstance(self.services, ServiceScopeBase):
            self.services.dispose()


class ApplicationSettings(BaseSettings):
    """
    Base application settings with optional cloud events configuration.

    Cloud events fields are optional and only required when using event-driven features.
    For simple CQRS applications, these can be left as defaults.

    Environment variables are automatically parsed:
    - CONNECTION_STRINGS: JSON string, e.g., '{"mongo": "mongodb://localhost:27017"}'
    - CLOUD_EVENT_SINK: URL string
    - etc.
    """

    consumer_group: Optional[str] = None
    """Consumer group name for event processing. Optional - only needed for event-driven apps."""

    connection_strings: dict[str, str] = Field(default_factory=dict)
    """Database and service connection strings. Can be empty for in-memory testing."""

    cloud_event_sink: Optional[str] = None
    """Cloud event sink URL. Optional - only needed when publishing events."""

    cloud_event_source: Optional[str] = None
    """Cloud event source identifier. Optional - only needed when publishing events."""

    cloud_event_type_prefix: str = ""
    """Prefix for cloud event types. Defaults to empty string."""

    cloud_event_retry_attempts: int = 5
    """Number of retry attempts for cloud event publishing."""

    cloud_event_retry_delay: float = 1.0
    """Delay between cloud event retry attempts in seconds."""


# Note: ApplicationSettingsWithObservability is defined in observability/settings.py
# to avoid circular import issues. Import it from there when needed.


class ApplicationBuilderBase:
    """Defines the fundamentals of a service used to build applications"""

    def __init__(self):
        self.services.try_add_singleton(HostApplicationLifetime)

    settings: ApplicationSettings = ApplicationSettings()

    services: ServiceCollection = ServiceCollection()

    @abstractmethod
    def build(self) -> HostBase:
        """Builds the application's host"""
        raise NotImplementedError()


class ApplicationBuilder(ApplicationBuilderBase):
    """Represents the default implementation of the ApplicationBuilderBase class"""

    def __init__(self):
        super().__init__()

    @contextmanager
    def build(self) -> HostBase:
        try:
            service_provider = self.services.build()
            host = Host(service_provider)
            yield host
        finally:
            host.dispose()
