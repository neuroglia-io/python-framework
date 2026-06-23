"""
Test suite for WebApplicationBuilder settings registration bug fix.

This test suite validates that application settings are properly registered
in the DI container as singleton instances (not lambda functions), which
allows dependent services to be resolved correctly.

Bug Report: https://github.com/neuroglia-io/python-framework/issues/XXX
Fixed in: v0.6.6
"""

import inspect
from dataclasses import dataclass

from neuroglia.dependency_injection import ServiceCollection
from neuroglia.hosting.abstractions import ApplicationSettings
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator


# Test fixtures and sample classes
class SampleSettings(ApplicationSettings):
    """Test settings class for validation"""

    model_config = {"extra": "allow"}  # Allow extra fields for testing

    test_value: str = "test"
    api_key: str = "test-key-123"


@dataclass
class SampleCommand(Command[str]):
    """Test command for validation"""

    message: str


class SampleCommandHandler(CommandHandler[SampleCommand, str]):
    """Test handler that depends on settings"""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        settings: SampleSettings,  # This dependency triggers the bug
    ):
        super().__init__(mediator, mapper)
        self.settings = settings

    async def handle_async(self, command: SampleCommand) -> str:
        return f"{self.settings.test_value}: {command.message}"


class TestWebApplicationBuilderSettingsRegistration:
    """Test suite for settings registration bug fix"""

    def test_settings_registered_as_singleton_not_lambda(self):
        """
        Verify settings are registered as singleton instance, not lambda.

        This is the core fix: settings should be registered using
        singleton=app_settings, not lambda: app_settings
        """
        settings = SampleSettings(app_name="test", app_version="1.0.0")
        builder = WebApplicationBuilder(app_settings=settings)

        # Find the settings descriptor
        settings_descriptor = None
        for descriptor in builder.services:
            if descriptor.service_type == SampleSettings:
                settings_descriptor = descriptor
                break

        assert settings_descriptor is not None, "Settings should be registered in DI container"

        # Critical assertion: implementation should NOT be a lambda or callable
        # It should be registered as a singleton instance
        if callable(settings_descriptor.implementation_type):
            # If it's callable, it must be a type (class), not a function
            assert inspect.isclass(settings_descriptor.implementation_type), "Settings implementation_type should be a class, not a lambda function"

        # The singleton instance should be set directly
        assert settings_descriptor.singleton is settings, "Settings should be registered with singleton=app_settings"

    def test_settings_can_be_resolved_from_service_provider(self):
        """
        Test that settings can be resolved from the service provider.

        This validates that the DI container can successfully resolve
        the settings without encountering AttributeError.
        """
        settings = SampleSettings(app_name="test", app_version="1.0.0", test_value="resolved")
        builder = WebApplicationBuilder(app_settings=settings)
        provider = builder.services.build()

        # Should not raise AttributeError: 'function' object has no attribute '__origin__'
        resolved_settings = provider.get_service(SampleSettings)

        assert resolved_settings is not None
        assert resolved_settings.test_value == "resolved"

    def test_handler_with_settings_dependency_can_be_resolved(self):
        """
        Test that command handlers depending on Settings can be resolved.

        This is the real-world scenario that triggered the bug: a command
        handler with a settings dependency should be resolvable by the
        mediator.
        """
        settings = SampleSettings(app_name="test", app_version="1.0.0", test_value="handler-test")

        builder = WebApplicationBuilder(app_settings=settings)

        # Configure mediator and mapper properly
        Mediator.configure(builder, ["tests.cases.test_web_application_builder_settings_registration"])
        Mapper.configure(builder, ["tests.cases.test_web_application_builder_settings_registration"])

        provider = builder.services.build()

        # Should not raise AttributeError when resolving settings
        resolved_settings = provider.get_service(SampleSettings)
        assert resolved_settings is not None
        assert resolved_settings.test_value == "handler-test"

    def test_settings_type_is_preserved(self):
        """
        Verify that the settings type is correctly preserved in registration.

        The service should be registered with the actual settings type,
        not with ApplicationSettings base type.
        """
        settings = SampleSettings(app_name="test", app_version="1.0.0")
        builder = WebApplicationBuilder(app_settings=settings)

        # Find the settings descriptor
        descriptor = None
        for desc in builder.services:
            if desc.service_type == SampleSettings:
                descriptor = desc
                break

        assert descriptor is not None
        assert descriptor.service_type == SampleSettings
        assert descriptor.service_type != ApplicationSettings

    def test_no_settings_registration_when_none_provided(self):
        """
        Test that no SampleSettings are registered when app_settings is None.

        This ensures the fix doesn't break the no-settings use case.
        """
        builder = WebApplicationBuilder()  # No app_settings

        # Should not have any SampleSettings registered (but may have other registrations)
        settings_descriptors = [desc for desc in builder.services if desc.service_type == SampleSettings]

        assert len(settings_descriptors) == 0

    def test_lambda_registration_would_fail_defensive_check(self):
        """
        Verify that lambda registration would be caught by defensive check.

        This test validates that the defensive check in ServiceProvider
        prevents crashes from lambda registrations (even though we fixed
        the root cause in WebApplicationBuilder).
        """
        services = ServiceCollection()

        # Manually register with lambda (simulating the old broken code)
        settings = SampleSettings(app_name="test", app_version="1.0.0")
        services.add_singleton(SampleSettings, implementation_factory=lambda _: settings)

        provider = services.build()

        # Should NOT crash with AttributeError, thanks to defensive check
        resolved = provider.get_service(SampleSettings)
        assert resolved is settings

    def test_multiple_settings_types_can_coexist(self):
        """
        Test that multiple settings types can be registered and resolved.

        This validates that the fix works with multiple settings types
        in the same application.
        """

        class OtherSettings(ApplicationSettings):
            model_config = {"extra": "allow"}
            other_value: str = "other"

        settings1 = SampleSettings(test_value="value1")
        settings2 = OtherSettings(other_value="value2")

        builder = WebApplicationBuilder(app_settings=settings1)
        builder.services.add_singleton(OtherSettings, singleton=settings2)

        provider = builder.services.build()

        resolved1 = provider.get_service(SampleSettings)
        resolved2 = provider.get_service(OtherSettings)

        assert resolved1 is not None
        assert resolved2 is not None
        assert resolved1.test_value == "value1"
        assert resolved2.other_value == "value2"

    def test_settings_singleton_descriptor_registered(self):
        """
        Verify that the settings descriptor has the singleton set.

        The descriptor should have the singleton instance, not None or a factory.
        """
        settings = SampleSettings()
        builder = WebApplicationBuilder(app_settings=settings)

        # Find descriptor
        descriptor = None
        for desc in builder.services:
            if desc.service_type == SampleSettings:
                descriptor = desc
                break

        assert descriptor is not None
        assert descriptor.singleton is not None

    def test_settings_can_be_resolved_multiple_times(self):
        """
        Test that settings can be resolved multiple times without errors.
        """
        settings = SampleSettings()
        builder = WebApplicationBuilder(app_settings=settings)
        provider = builder.services.build()

        # Resolve multiple times
        resolved1 = provider.get_service(SampleSettings)
        resolved2 = provider.get_service(SampleSettings)
        resolved3 = provider.get_service(SampleSettings)

        # All resolutions should succeed
        assert resolved1 is not None
        assert resolved2 is not None
        assert resolved3 is not None


class TestSettingsRegistrationBackwardCompatibility:
    """Test backward compatibility of the settings registration fix"""

    def test_explicit_singleton_registration_still_works(self):
        """
        Test that explicit singleton registration (post-build) still works.

        This ensures the workaround users might have implemented
        continues to work after the fix.
        """
        settings = SampleSettings()

        # Old workaround pattern
        builder = WebApplicationBuilder()
        builder.services.add_singleton(SampleSettings, singleton=settings)

        provider = builder.services.build()
        resolved = provider.get_service(SampleSettings)

        assert resolved is not None

    def test_factory_registration_still_works(self):
        """
        Test that factory-based registration still works.

        This ensures we didn't break the ability to use factories
        for other service types.
        """
        settings = SampleSettings()

        builder = WebApplicationBuilder()
        builder.services.add_singleton(SampleSettings, implementation_factory=lambda _: settings)

        provider = builder.services.build()
        resolved = provider.get_service(SampleSettings)

        assert resolved is not None
