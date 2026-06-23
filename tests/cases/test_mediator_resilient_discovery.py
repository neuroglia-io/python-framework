"""
Comprehensive tests for Mediator's resilient handler discovery functionality.

This test suite validates the Mediator.configure() method's ability to gracefully handle
package import failures while still discovering handlers from individual modules.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from neuroglia.data.abstractions import DomainEvent
from neuroglia.hosting import WebApplicationBuilder
from neuroglia.mediation import Command, OperationResult, Query
from neuroglia.mediation.mediator import (
    CommandHandler,
    DomainEventHandler,
    Mediator,
    QueryHandler,
)


# Test Command and Handler for testing
class TestCommand(Command[OperationResult]):
    def __init__(self, value: str):
        self.value = value


class TestCommandHandler(CommandHandler[TestCommand, OperationResult]):
    async def handle_async(self, request: TestCommand) -> OperationResult:
        return self.ok(f"Processed: {request.value}")


# Test Query and Handler for testing
class TestQuery(Query[OperationResult[str]]):
    def __init__(self, query: str):
        self.query = query


class TestQueryHandler(QueryHandler[TestQuery, OperationResult[str]]):
    async def handle_async(self, request: TestQuery) -> OperationResult[str]:
        return self.ok(f"Query result: {request.query}")


# Test Event and Handler for testing
class TestDomainEvent(DomainEvent):
    def __init__(self, event_data: str):
        super().__init__("test-aggregate-id")
        self.event_data = event_data


class TestDomainEventHandler(DomainEventHandler[TestDomainEvent]):
    async def handle_async(self, notification: TestDomainEvent):
        pass


class TestResilientMediatorDiscovery:
    """Test suite for resilient handler discovery functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.builder = WebApplicationBuilder()
        self.temp_dir: str = ""

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def create_test_package_structure(self, with_failing_init=True):
        """Create a temporary package structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        base_path = Path(self.temp_dir)

        # Create package structure
        package_path = base_path / "test_app" / "handlers"
        package_path.mkdir(parents=True)

        # Create __init__.py with optional import failure
        init_content = ""
        if with_failing_init:
            init_content = """
# This import will fail and should trigger fallback discovery
from .non_existent_module import NonExistentClass

# Valid exports that won't be reached due to import failure
from .test_command_handler import TestCommandHandler
from .test_query_handler import TestQueryHandler
"""
        else:
            init_content = """
# Valid __init__.py that imports successfully
from .test_command_handler import TestCommandHandler
from .test_query_handler import TestQueryHandler
"""

        (package_path / "__init__.py").write_text(init_content)

        # Create valid handler modules
        command_handler_content = """
from neuroglia.mediation import CommandHandler, Command, OperationResult

class TestCommand(Command[OperationResult]):
    def __init__(self, value: str):
        self.value = value

class TestCommandHandler(CommandHandler[TestCommand, OperationResult]):
    async def handle_async(self, request: TestCommand) -> OperationResult:
        return self.ok(f"Processed: {request.value}")
"""

        query_handler_content = """
from neuroglia.mediation import QueryHandler, Query, OperationResult

class TestQuery(Query[OperationResult[str]]):
    def __init__(self, query: str):
        self.query = query

class TestQueryHandler(QueryHandler[TestQuery, OperationResult[str]]):
    async def handle_async(self, request: TestQuery) -> OperationResult[str]:
        return self.ok(f"Query result: {request.query}")
"""

        (package_path / "test_command_handler.py").write_text(command_handler_content)
        (package_path / "test_query_handler.py").write_text(query_handler_content)

        return str(base_path)

    @pytest.mark.asyncio
    async def test_successful_package_import(self):
        """Test normal package import when __init__.py is valid."""
        with patch("sys.path") as mock_path:
            # Create test structure without failing __init__.py
            base_path = self.create_test_package_structure(with_failing_init=False)
            mock_path.insert(0, base_path)

            with patch("neuroglia.mediation.mediator.ModuleLoader.load") as mock_load:
                # Mock successful module loading
                mock_module = MagicMock()
                mock_module.__name__ = "test_app.handlers"
                mock_load.return_value = mock_module

                with patch("neuroglia.mediation.mediator.TypeFinder.get_types") as mock_get_types:
                    # Mock finding test handlers
                    mock_get_types.side_effect = [
                        [TestCommandHandler],  # Command handlers
                        [TestQueryHandler],  # Query handlers
                        [],  # Domain event handlers
                        [],  # Integration event handlers
                    ]

                    # Test the configuration
                    result = Mediator.configure(self.builder, ["test_app.handlers"])

                    # Verify results
                    assert result is self.builder
                    mock_load.assert_called_once_with("test_app.handlers")
                    assert mock_get_types.call_count == 4

    @pytest.mark.asyncio
    async def test_package_import_failure_with_successful_fallback(self):
        """Test fallback discovery when package import fails."""
        with patch("sys.path") as mock_path:
            base_path = self.create_test_package_structure(with_failing_init=True)
            mock_path.insert(0, base_path)

            with patch("neuroglia.mediation.mediator.ModuleLoader.load") as mock_load:
                # Mock package import failure, but successful submodule imports
                def mock_load_side_effect(module_name):
                    if module_name == "test_app.handlers":
                        raise ImportError("cannot import name 'NonExistentClass'")
                    elif "test_command_handler" in module_name:
                        mock_module = MagicMock()
                        mock_module.__name__ = module_name
                        return mock_module
                    elif "test_query_handler" in module_name:
                        mock_module = MagicMock()
                        mock_module.__name__ = module_name
                        return mock_module
                    else:
                        raise ImportError(f"No module named '{module_name}'")

                mock_load.side_effect = mock_load_side_effect

                with patch.object(Mediator, "_discover_submodules") as mock_discover:
                    mock_discover.return_value = [
                        "test_app.handlers.test_command_handler",
                        "test_app.handlers.test_query_handler",
                    ]

                    with patch("neuroglia.mediation.mediator.TypeFinder.get_types") as mock_get_types:
                        # Mock finding handlers in individual modules
                        mock_get_types.side_effect = [
                            [TestCommandHandler],
                            [],
                            [],
                            [],  # First submodule
                            [TestQueryHandler],
                            [],
                            [],
                            [],  # Second submodule
                        ]

                        # Test the configuration
                        result = Mediator.configure(self.builder, ["test_app.handlers"])

                        # Verify fallback was triggered
                        assert result is self.builder
                        mock_discover.assert_called_once_with("test_app.handlers")
                        assert mock_load.call_count >= 3  # Original attempt + 2 submodules

    @pytest.mark.asyncio
    async def test_discover_submodules_functionality(self):
        """Test the _discover_submodules helper method."""
        self.create_test_package_structure()

        # Test with 'src' directory structure
        src_path = Path(self.temp_dir) / "src"
        src_path.mkdir()
        shutil.move(str(Path(self.temp_dir) / "test_app"), str(src_path / "test_app"))

        with patch("neuroglia.mediation.mediator.Path") as mock_path_class:
            # Mock Path behavior to point to our test structure
            def mock_path_constructor(path_str):
                if path_str == "src":
                    return src_path
                elif path_str == ".":
                    return Path(self.temp_dir)
                elif path_str == "app":
                    return Path(self.temp_dir) / "nonexistent"
                else:
                    return Path(path_str)

            mock_path_class.side_effect = mock_path_constructor

            # Test submodule discovery
            submodules = Mediator._discover_submodules("test_app.handlers")

            # Verify discovered modules
            expected_modules = [
                "test_app.handlers.test_command_handler",
                "test_app.handlers.test_query_handler",
            ]
            assert len(submodules) == 2
            for expected in expected_modules:
                assert expected in submodules

    @pytest.mark.asyncio
    async def test_register_handlers_from_module(self):
        """Test the _register_handlers_from_module helper method."""
        mock_module = MagicMock()
        mock_module.__name__ = "test_module"

        with patch("neuroglia.mediation.mediator.TypeFinder.get_types") as mock_get_types:
            # Mock finding different types of handlers
            mock_get_types.side_effect = [
                [TestCommandHandler],  # Command handlers
                [TestQueryHandler],  # Query handlers
                [TestDomainEventHandler],  # Domain event handlers
                [],  # Integration event handlers
            ]

            # Test handler registration
            handlers_count = Mediator._register_handlers_from_module(self.builder, mock_module, "test_module")

            # Verify results
            assert handlers_count == 3
            assert mock_get_types.call_count == 4

    @pytest.mark.asyncio
    async def test_complete_failure_scenario(self):
        """Test scenario where both package and individual module imports fail."""
        with patch("neuroglia.mediation.mediator.ModuleLoader.load") as mock_load:
            # Mock all imports failing
            mock_load.side_effect = ImportError("Complete import failure")

            with patch.object(Mediator, "_discover_submodules") as mock_discover:
                mock_discover.return_value = ["test.module1", "test.module2"]

                # Test configuration with complete failure
                result = Mediator.configure(self.builder, ["test.failing_package"])

                # Should still return the builder and add singleton
                assert result is self.builder
                mock_discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure_packages(self):
        """Test scenario with multiple packages where some succeed and others fail."""
        with patch("neuroglia.mediation.mediator.ModuleLoader.load") as mock_load:

            def mixed_load_behavior(module_name):
                if module_name == "working.package":
                    mock_module = MagicMock()
                    mock_module.__name__ = module_name
                    return mock_module
                else:
                    raise ImportError(f"Failed to import {module_name}")

            mock_load.side_effect = mixed_load_behavior

            with patch("neuroglia.mediation.mediator.TypeFinder.get_types") as mock_get_types:
                mock_get_types.side_effect = [
                    [TestCommandHandler],
                    [],
                    [],
                    [],  # Working package handlers
                ]

                with patch.object(Mediator, "_discover_submodules") as mock_discover:
                    mock_discover.return_value = []  # No submodules found

                    # Test with mixed packages
                    result = Mediator.configure(self.builder, ["working.package", "failing.package"])

                    # Should handle both scenarios
                    assert result is self.builder
                    assert mock_load.call_count >= 2

    @pytest.mark.asyncio
    async def test_logging_behavior(self, caplog):
        """Test that appropriate logging messages are generated."""
        with caplog.at_level(logging.DEBUG):
            with patch("neuroglia.mediation.mediator.ModuleLoader.load") as mock_load:
                mock_load.side_effect = ImportError("Test import failure")

                with patch.object(Mediator, "_discover_submodules") as mock_discover:
                    mock_discover.return_value = []

                    # Test configuration
                    Mediator.configure(self.builder, ["test.package"])

                    # Verify logging
                    assert "Package import failed" in caplog.text
                    assert "Attempting fallback" in caplog.text

    @pytest.mark.asyncio
    async def test_empty_modules_list(self):
        """Test configuration with empty modules list."""
        result = Mediator.configure(self.builder, [])

        # Should still work and add singleton
        assert result is self.builder
        # Verify Mediator singleton was added (would need to check services collection)

    @pytest.mark.asyncio
    async def test_submodule_discovery_edge_cases(self):
        """Test edge cases in submodule discovery."""
        # Test with non-existent package
        submodules = Mediator._discover_submodules("completely.non.existent.package")
        assert submodules == []

        # Test with package name that doesn't translate to valid path
        submodules = Mediator._discover_submodules("invalid/path/name")
        assert submodules == []
