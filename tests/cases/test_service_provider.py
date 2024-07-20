from neuroglia.dependency_injection.service_provider import ServiceProviderBase, ServiceCollection
from tests.services import FileLogger, LoggerBase, NullLogger, PrintLogger
import pytest


class TestServiceProvider:

    def test_build_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, singleton=FileLogger())
        services.add_singleton(LoggerBase, implementation_factory=self._build_null_logger)

        # act
        service_provider = services.build()

        # assert
        assert service_provider is not None, 'service_provider is none'

    def test_get_service_should_work(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_singleton(LoggerBase, implementation_type)
        service_provider = services.build()

        # act
        logger = service_provider.get_service(LoggerBase)

        # assert
        assert logger is not None, 'logger is none'
        assert isinstance(logger, implementation_type), f"logger is not of expected type '{implementation_type.__name__}'"

    def test_get_unregistered_service_should_work(self):
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # act
        logger = service_provider.get_service(LoggerBase)

        # assert
        assert logger is None, 'logger is not none'

    def test_get_required_service_should_work(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_singleton(LoggerBase, implementation_type)
        service_provider = services.build()

        # act
        logger = service_provider.get_required_service(LoggerBase)

        # assert
        assert logger is not None, 'logger is none'
        assert isinstance(logger, implementation_type), f"logger is not of expected type '{implementation_type.__name__}'"

    def test_get_required_unregistered_service_should_raise_error(self):
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # assert
        with pytest.raises(Exception):
            service_provider.get_required_service(LoggerBase)()

    def test_get_scoped_service_from_root_should_raise_error(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_scoped(LoggerBase, implementation_type)
        service_provider = services.build()

        # assert
        with pytest.raises(Exception):
            service_provider.get_required_service(LoggerBase)()

    def test_get_services_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, singleton=FileLogger())
        services.add_singleton(LoggerBase, implementation_factory=self._build_null_logger)
        service_provider = services.build()

        # act
        loggers = service_provider.get_services(LoggerBase)

        # assert
        assert len(loggers) == 3, f'expected 3 loggers, got {len(loggers)}'

    def test_create_scope_should_work(self):
        pass

    def test_get_scoped_service_should_work(self):
        pass

    def _build_null_logger(self, provider: ServiceProviderBase) -> NullLogger: return NullLogger()
