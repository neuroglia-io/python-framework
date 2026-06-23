"""
Unit tests for OperationResult helper methods in RequestHandler.

Tests all HTTP status code helper methods to ensure they create
properly formatted OperationResult instances with correct status codes,
titles, and detail messages.
"""

from dataclasses import dataclass

import pytest

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


# Test command for handler instantiation
@dataclass
class TestCommand(Command[OperationResult[str]]):
    """Test command for OperationResult helper method testing."""

    value: str = "test"


class TestCommandHandler(CommandHandler[TestCommand, OperationResult[str]]):
    """Test handler for verifying OperationResult helper methods."""

    async def handle_async(self, command: TestCommand) -> OperationResult[str]:
        return self.ok("test")


class TestOperationResultHelpers:
    """Test suite for OperationResult helper methods."""

    @pytest.fixture
    def handler(self):
        """Create a test handler instance."""
        return TestCommandHandler()

    # Success response tests (2xx)

    def test_ok_with_data(self, handler):
        """Test ok() method with data payload."""
        result = handler.ok(data="Success message")

        assert result.is_success
        assert result.status_code == 200
        assert result.title == "OK"
        assert result.data == "Success message"
        assert result.error_message is None

    def test_ok_without_data(self, handler):
        """Test ok() method without data payload."""
        result = handler.ok()

        assert result.is_success
        assert result.status_code == 200
        assert result.title == "OK"
        assert result.data is None

    def test_created_with_data(self, handler):
        """Test created() method with data payload."""
        result = handler.created(data={"id": "123", "name": "New Resource"})

        assert result.is_success
        assert result.status_code == 201
        assert result.title == "Created"
        assert result.data == {"id": "123", "name": "New Resource"}
        assert result.error_message is None

    def test_created_without_data(self, handler):
        """Test created() method without data payload."""
        result = handler.created()

        assert result.is_success
        assert result.status_code == 201
        assert result.title == "Created"
        assert result.data is None

    def test_accepted_with_data(self, handler):
        """Test accepted() method for async operations."""
        result = handler.accepted(data={"job_id": "async-123", "status": "processing"})

        assert result.is_success
        assert result.status_code == 202
        assert result.title == "Accepted"
        assert result.data == {"job_id": "async-123", "status": "processing"}
        assert result.error_message is None

    def test_accepted_without_data(self, handler):
        """Test accepted() method without data."""
        result = handler.accepted()

        assert result.is_success
        assert result.status_code == 202
        assert result.title == "Accepted"
        assert result.data is None

    def test_no_content(self, handler):
        """Test no_content() method for successful operations with no response body."""
        result = handler.no_content()

        assert result.is_success
        assert result.status_code == 204
        assert result.title == "No Content"
        assert result.data is None
        assert result.error_message is None

    # Client error response tests (4xx)

    def test_bad_request(self, handler):
        """Test bad_request() method for validation errors."""
        result = handler.bad_request("Invalid email format")

        assert not result.is_success
        assert result.status_code == 400
        assert result.title == "Bad Request"
        assert result.error_message == "Invalid email format"
        assert result.data is None
        assert "Bad%20Request" in result.type

    def test_unauthorized_with_custom_message(self, handler):
        """Test unauthorized() method with custom message."""
        result = handler.unauthorized("Invalid JWT token")

        assert not result.is_success
        assert result.status_code == 401
        assert result.title == "Unauthorized"
        assert result.error_message == "Invalid JWT token"
        assert result.data is None

    def test_unauthorized_with_default_message(self, handler):
        """Test unauthorized() method with default message."""
        result = handler.unauthorized()

        assert not result.is_success
        assert result.status_code == 401
        assert result.title == "Unauthorized"
        assert result.error_message == "Authentication required"

    def test_forbidden_with_custom_message(self, handler):
        """Test forbidden() method with custom message."""
        result = handler.forbidden("Insufficient permissions to access this resource")

        assert not result.is_success
        assert result.status_code == 403
        assert result.title == "Forbidden"
        assert result.error_message == "Insufficient permissions to access this resource"
        assert result.data is None

    def test_forbidden_with_default_message(self, handler):
        """Test forbidden() method with default message."""
        result = handler.forbidden()

        assert not result.is_success
        assert result.status_code == 403
        assert result.title == "Forbidden"
        assert result.error_message == "Access denied"

    def test_not_found(self, handler):
        """Test not_found() method for missing entities."""

        class User:
            pass

        result = handler.not_found(User, "user-123", "id")

        assert not result.is_success
        assert result.status_code == 404
        assert result.title == "Not Found"
        assert "User" in result.error_message
        assert "user-123" in result.error_message
        assert result.data is None

    def test_conflict(self, handler):
        """Test conflict() method for concurrent update conflicts."""
        result = handler.conflict("Order was modified by another process. " "Expected version 3, actual version 5. Please reload and retry.")

        assert not result.is_success
        assert result.status_code == 409
        assert result.title == "Conflict"
        assert "Expected version 3" in result.error_message
        assert "actual version 5" in result.error_message
        assert result.data is None

    def test_unprocessable_entity(self, handler):
        """Test unprocessable_entity() method for semantic validation errors."""
        result = handler.unprocessable_entity("Cannot create order: Customer has exceeded credit limit")

        assert not result.is_success
        assert result.status_code == 422
        assert result.title == "Unprocessable Entity"
        assert result.error_message == "Cannot create order: Customer has exceeded credit limit"
        assert result.data is None

    # Server error response tests (5xx)

    def test_internal_server_error_with_custom_message(self, handler):
        """Test internal_server_error() method with custom message."""
        result = handler.internal_server_error("Database connection failed")

        assert not result.is_success
        assert result.status_code == 500
        assert result.title == "Internal Server Error"
        assert result.error_message == "Database connection failed"
        assert result.data is None

    def test_internal_server_error_with_default_message(self, handler):
        """Test internal_server_error() method with default message."""
        result = handler.internal_server_error()

        assert not result.is_success
        assert result.status_code == 500
        assert result.title == "Internal Server Error"
        assert result.error_message == "An internal error occurred"

    def test_service_unavailable_with_custom_message(self, handler):
        """Test service_unavailable() method with custom message."""
        result = handler.service_unavailable("Payment gateway is down for maintenance")

        assert not result.is_success
        assert result.status_code == 503
        assert result.title == "Service Unavailable"
        assert result.error_message == "Payment gateway is down for maintenance"
        assert result.data is None

    def test_service_unavailable_with_default_message(self, handler):
        """Test service_unavailable() method with default message."""
        result = handler.service_unavailable()

        assert not result.is_success
        assert result.status_code == 503
        assert result.title == "Service Unavailable"
        assert result.error_message == "Service temporarily unavailable"

    # Integration tests

    def test_status_code_ranges(self, handler):
        """Test that status codes are correctly categorized as success/error."""
        # Success range (2xx)
        assert handler.ok().is_success
        assert handler.created().is_success
        assert handler.accepted().is_success
        assert handler.no_content().is_success

        # Client error range (4xx)
        assert not handler.bad_request("error").is_success
        assert not handler.unauthorized().is_success
        assert not handler.forbidden().is_success

        class TestEntity:
            pass

        assert not handler.not_found(TestEntity, "123").is_success
        assert not handler.conflict("conflict").is_success
        assert not handler.unprocessable_entity("error").is_success

        # Server error range (5xx)
        assert not handler.internal_server_error().is_success
        assert not handler.service_unavailable().is_success

    def test_error_results_have_no_data(self, handler):
        """Test that all error results have None data payload."""
        # All error responses should have no data
        assert handler.bad_request("error").data is None
        assert handler.unauthorized().data is None
        assert handler.forbidden().data is None

        class TestEntity:
            pass

        assert handler.not_found(TestEntity, "123").data is None
        assert handler.conflict("error").data is None
        assert handler.unprocessable_entity("error").data is None
        assert handler.internal_server_error().data is None
        assert handler.service_unavailable().data is None

    def test_success_results_have_proper_type_urls(self, handler):
        """Test that all results have proper RFC 7807 type URLs."""
        # Error results should have type URLs
        assert handler.bad_request("error").type is not None
        assert "http" in handler.bad_request("error").type.lower()

        class TestEntity:
            pass

        assert handler.not_found(TestEntity, "123").type is not None
        assert handler.conflict("error").type is not None
        assert handler.internal_server_error("error").type is not None


class TestOperationResultHelpersUsagePatterns:
    """Test real-world usage patterns of OperationResult helper methods."""

    @pytest.fixture
    def handler(self):
        """Create a test handler instance."""
        return TestCommandHandler()

    @pytest.mark.asyncio
    async def test_validation_pattern(self, handler):
        """Test common validation pattern with bad_request."""
        email = ""

        if not email:
            result = handler.bad_request("Email is required")
            assert not result.is_success
            assert result.status_code == 400
            assert "Email is required" in result.error_message

    @pytest.mark.asyncio
    async def test_authorization_pattern(self, handler):
        """Test authorization check pattern with forbidden."""
        user_role = "viewer"
        required_role = "admin"

        if user_role != required_role:
            result = handler.forbidden(f"Requires '{required_role}' role, but user has '{user_role}' role")
            assert not result.is_success
            assert result.status_code == 403
            assert "admin" in result.error_message

    @pytest.mark.asyncio
    async def test_async_operation_pattern(self, handler):
        """Test async operation pattern with accepted."""
        job_id = "async-job-123"

        result = handler.accepted({"job_id": job_id, "status": "queued", "check_url": f"/jobs/{job_id}"})

        assert result.is_success
        assert result.status_code == 202
        assert result.data["job_id"] == job_id
        assert result.data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_delete_operation_pattern(self, handler):
        """Test delete operation pattern with no_content."""
        # Simulate successful deletion
        result = handler.no_content()

        assert result.is_success
        assert result.status_code == 204
        assert result.data is None
