"""Tests for MotorRepository configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

from neuroglia.data.infrastructure.mongo.motor_repository import MotorRepository
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer


@dataclass
class DummyEntity:
    """Simple entity used for configuration tests."""

    id: str
    name: str


class DomainRepositoryInterface:  # pragma: no cover - marker interface
    """Marker interface representing a domain-level repository."""

    async def list_entities(self) -> list[DummyEntity]:
        raise NotImplementedError


class CustomMotorRepository(MotorRepository[DummyEntity, str]):  # type: ignore[type-var]
    """Custom repository implementation with domain-specific methods."""

    async def get_by_name_async(self, name: str) -> list[DummyEntity]:
        """Custom query method for testing."""
        return await self.find_async({"name": name})


class NotARepository:
    """Class that does not extend MotorRepository - for validation tests."""


@pytest.fixture
def builder_mock() -> Mock:
    """Create an application builder mock compatible with configure()."""

    builder = Mock()
    builder.settings = Mock()
    builder.settings.connection_strings = {"mongo": "mongodb://localhost:27017"}
    builder.services = Mock()
    builder.services.try_add_singleton = Mock()
    builder.services.add_scoped = Mock()
    return builder


def _get_registered_service_types(builder: Mock) -> list[object]:
    """Extract service types registered via add_scoped for assertions."""

    return [call.args[0] for call in builder.services.add_scoped.call_args_list]


class TestMotorRepositoryConfigure:
    """Validate MotorRepository.configure registration behavior."""

    def test_registers_domain_repository_interface(self, builder_mock: Mock) -> None:
        """Ensure domain-level repository types are resolved to MotorRepository."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            result = MotorRepository.configure(
                builder_mock,
                entity_type=DummyEntity,
                key_type=str,
                database_name="test_db",
                domain_repository_type=DomainRepositoryInterface,
            )

        assert result is builder_mock
        builder_mock.services.try_add_singleton.assert_called_once()
        registered_types = _get_registered_service_types(builder_mock)
        assert DomainRepositoryInterface in registered_types
        assert builder_mock.services.add_scoped.call_count == 3

    def test_skips_domain_registration_when_not_provided(self, builder_mock: Mock) -> None:
        """Verify default behavior when no domain interface is specified."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            MotorRepository.configure(
                builder_mock,
                entity_type=DummyEntity,
                key_type=str,
                database_name="test_db",
            )

        builder_mock.services.try_add_singleton.assert_called_once()
        registered_types = _get_registered_service_types(builder_mock)
        assert DomainRepositoryInterface not in registered_types
        assert builder_mock.services.add_scoped.call_count == 2

    def test_factory_resolves_mediator_when_optional_lookup_fails(self, builder_mock: Mock) -> None:
        """Ensure mediator falls back to required service resolution when not optional."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            MotorRepository.configure(
                builder_mock,
                entity_type=DummyEntity,
                key_type=str,
                database_name="test_db",
            )

        repo_factory = builder_mock.services.add_scoped.call_args_list[0].kwargs["implementation_factory"]

        mediator_instance = Mock(spec=Mediator)
        serializer_instance = Mock(spec=JsonSerializer)
        motor_client_instance = Mock(name="AsyncIOMotorClientInstance")

        def get_required(service_type):
            if service_type is motor_client or getattr(service_type, "__name__", "") == "AsyncIOMotorClient":
                return motor_client_instance
            if service_type is JsonSerializer:
                return serializer_instance
            if service_type is Mediator:
                return mediator_instance
            raise AssertionError(f"Unexpected service request: {service_type}")

        service_provider = Mock()
        service_provider.get_service.return_value = None
        service_provider.get_required_service.side_effect = get_required

        repository = repo_factory(service_provider)

        service_provider.get_service.assert_called_once_with(Mediator)
        service_provider.get_required_service.assert_any_call(Mediator)
        assert repository._mediator is mediator_instance

    def test_configure_with_custom_implementation_type(self, builder_mock: Mock) -> None:
        """Test that custom repository implementation is used when implementation_type provided."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            result = MotorRepository.configure(
                builder_mock,
                entity_type=DummyEntity,
                key_type=str,
                database_name="test_db",
                domain_repository_type=DomainRepositoryInterface,
                implementation_type=CustomMotorRepository,
            )

        assert result is builder_mock
        builder_mock.services.try_add_singleton.assert_called_once()

        # Get the factory function
        repo_factory = builder_mock.services.add_scoped.call_args_list[0].kwargs["implementation_factory"]

        # Mock service provider
        mediator_instance = Mock(spec=Mediator)
        serializer_instance = Mock(spec=JsonSerializer)
        motor_client_instance = Mock(name="AsyncIOMotorClientInstance")

        def get_required(service_type):
            if service_type is motor_client or getattr(service_type, "__name__", "") == "AsyncIOMotorClient":
                return motor_client_instance
            if service_type is JsonSerializer:
                return serializer_instance
            if service_type is Mediator:
                return mediator_instance
            raise AssertionError(f"Unexpected service request: {service_type}")

        service_provider = Mock()
        service_provider.get_service.return_value = None
        service_provider.get_required_service.side_effect = get_required

        # Create repository using factory
        repository = repo_factory(service_provider)

        # Should be CustomMotorRepository instance
        assert isinstance(repository, CustomMotorRepository)
        assert hasattr(repository, "get_by_name_async")

    def test_configure_with_invalid_implementation_type(self, builder_mock: Mock) -> None:
        """Test that invalid implementation_type raises ValueError."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            with pytest.raises(ValueError, match="must extend MotorRepository"):
                MotorRepository.configure(
                    builder_mock,
                    entity_type=DummyEntity,
                    key_type=str,
                    database_name="test_db",
                    domain_repository_type=DomainRepositoryInterface,
                    implementation_type=NotARepository,
                )

    def test_configure_without_implementation_type_uses_base(self, builder_mock: Mock) -> None:
        """Test fallback to base MotorRepository when no implementation_type provided."""

        with patch("neuroglia.data.infrastructure.mongo.motor_repository.AsyncIOMotorClient") as motor_client:
            motor_client.return_value = Mock()

            MotorRepository.configure(
                builder_mock,
                entity_type=DummyEntity,
                key_type=str,
                database_name="test_db",
                domain_repository_type=DomainRepositoryInterface,
            )

        # Get the factory function
        repo_factory = builder_mock.services.add_scoped.call_args_list[0].kwargs["implementation_factory"]

        # Mock service provider
        mediator_instance = Mock(spec=Mediator)
        serializer_instance = Mock(spec=JsonSerializer)
        motor_client_instance = Mock(name="AsyncIOMotorClientInstance")

        def get_required(service_type):
            if service_type is motor_client or getattr(service_type, "__name__", "") == "AsyncIOMotorClient":
                return motor_client_instance
            if service_type is JsonSerializer:
                return serializer_instance
            if service_type is Mediator:
                return mediator_instance
            raise AssertionError(f"Unexpected service request: {service_type}")

        service_provider = Mock()
        service_provider.get_service.return_value = None
        service_provider.get_required_service.side_effect = get_required

        # Create repository using factory
        repository = repo_factory(service_provider)

        # Should be base MotorRepository instance, not CustomMotorRepository
        assert isinstance(repository, MotorRepository)
        assert type(repository).__name__ == "MotorRepository"
        assert not hasattr(repository, "get_by_name_async")
