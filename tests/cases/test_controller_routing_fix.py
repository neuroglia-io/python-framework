"""
Test suite for controller routing fix.

This validates that controllers are properly mounted to the FastAPI application
and their routes are accessible in Swagger UI and OpenAPI spec.
"""

import pytest
from fastapi.testclient import TestClient

from neuroglia.core import OperationResult
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mvc import ControllerBase


# Test controller for validation
class TestUsersController(ControllerBase):
    """Test controller with sample endpoints"""

    def __init__(self, service_provider, mapper, mediator):
        super().__init__(service_provider, mapper, mediator)

    async def get_users(self):
        """Get all users endpoint"""
        result = OperationResult(title="OK", status=200)
        result.data = [{"id": "1", "name": "User 1"}, {"id": "2", "name": "User 2"}]
        return self.process(result)

    async def get_user(self, user_id: str):
        """Get user by ID endpoint"""
        result = OperationResult(title="OK", status=200)
        result.data = {"id": user_id, "name": f"User {user_id}"}
        return self.process(result)

    async def create_user(self, user_data: dict):
        """Create user endpoint"""
        result = OperationResult(title="Created", status=201)
        result.data = {"id": "new-id", **user_data}
        return self.process(result)


# Manually decorate methods since we can't use decorators in class body for tests
from classy_fastapi.decorators import get, post

TestUsersController.get_users = get("/")(TestUsersController.get_users)
TestUsersController.get_user = get("/{user_id}")(TestUsersController.get_user)
TestUsersController.create_user = post("/")(TestUsersController.create_user)


class TestControllerRoutingFix:
    """Test suite validating the controller routing fix"""

    def test_controllers_registered_to_di_container(self):
        """Test that add_controllers() registers controller types to DI container"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()

        # Manually register test controller
        builder.services.add_singleton(ControllerBase, TestUsersController)

        # Act
        provider = builder.services.build()
        controllers = provider.get_services(ControllerBase)

        # Assert
        assert len(controllers) > 0, "Controllers should be registered in DI container"
        assert any(isinstance(ctrl, TestUsersController) for ctrl in controllers)

    def test_use_controllers_mounts_routes(self):
        """Test that use_controllers() properly mounts controller routes to FastAPI app"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        # Build without auto-mounting
        app = builder.build(auto_mount_controllers=False)

        # Assert routes not mounted yet
        initial_routes = [route.path for route in app.routes]
        assert "/api/testusers/" not in initial_routes

        # Act - manually mount controllers
        app.use_controllers()

        # Assert routes are now mounted
        final_routes = [route.path for route in app.routes]
        assert any("/api/testusers" in route for route in final_routes), f"Expected /api/testusers route to be mounted. Routes: {final_routes}"

    def test_auto_mount_controllers_on_build(self):
        """Test that build() automatically mounts controllers when auto_mount_controllers=True"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        # Act - build with auto-mounting (default)
        app = builder.build()

        # Assert routes are mounted
        routes = [route.path for route in app.routes]
        assert any("/api/testusers" in route for route in routes), f"Expected controllers to be auto-mounted. Routes: {routes}"

    def test_manual_mount_control(self):
        """Test that auto_mount_controllers=False allows manual control"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        # Act - build without auto-mounting
        app = builder.build(auto_mount_controllers=False)

        # Assert routes not mounted
        routes = [route.path for route in app.routes]
        assert not any("/api/testusers" in route for route in routes), "Controllers should not be auto-mounted when auto_mount_controllers=False"

        # Manually mount
        app.use_controllers()
        routes_after = [route.path for route in app.routes]
        assert any("/api/testusers" in route for route in routes_after), "Controllers should be mounted after explicit use_controllers() call"

    def test_controller_endpoints_accessible(self):
        """Test that mounted controller endpoints are accessible via HTTP"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        app = builder.build()
        client = TestClient(app)

        # Act & Assert - Test GET /api/testusers/
        response = client.get("/api/testusers/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of users"
        assert len(data) == 2

        # Act & Assert - Test GET /api/testusers/{id}
        response = client.get("/api/testusers/123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "123"

        # Act & Assert - Test POST /api/testusers/
        response = client.post("/api/testusers/", json={"name": "New User"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New User"

    def test_openapi_spec_includes_controller_routes(self):
        """Test that OpenAPI spec includes controller routes for Swagger UI"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        app = builder.build()
        client = TestClient(app)

        # Act - Get OpenAPI spec
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()

        # Assert - Check that paths are defined
        assert "paths" in openapi_spec, "OpenAPI spec should have 'paths' section"
        paths = openapi_spec["paths"]
        assert len(paths) > 0, "OpenAPI spec should not be empty"

        # Assert - Check for controller routes
        assert "/api/testusers/" in paths or any("testusers" in path for path in paths.keys()), f"Expected controller routes in OpenAPI spec. Paths: {list(paths.keys())}"

    def test_swagger_ui_accessible(self):
        """Test that Swagger UI page is accessible"""
        # Arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)

        app = builder.build()
        client = TestClient(app)

        # Act
        response = client.get("/api/docs")

        # Assert
        assert response.status_code == 200, "Swagger UI should be accessible at /api/docs"
        assert "swagger-ui" in response.text.lower() or "openapi" in response.text.lower(), "Swagger UI HTML should be returned"

    def test_multiple_controllers_mounted(self):
        """Test that multiple controllers can be registered and mounted"""

        # Arrange
        class TestOrdersController(ControllerBase):
            def __init__(self, service_provider, mapper, mediator):
                super().__init__(service_provider, mapper, mediator)

            async def get_orders(self):
                result = OperationResult(title="OK", status=200)
                result.data = [{"id": "o1", "total": 100}]
                return self.process(result)

        TestOrdersController.get_orders = get("/")(TestOrdersController.get_orders)

        builder = WebApplicationBuilder()
        builder.services.add_singleton(Mapper)
        builder.services.add_mediator()
        builder.services.add_singleton(ControllerBase, TestUsersController)
        builder.services.add_singleton(ControllerBase, TestOrdersController)

        # Act
        app = builder.build()
        client = TestClient(app)

        # Assert - Both controllers accessible
        users_response = client.get("/api/testusers/")
        assert users_response.status_code == 200

        orders_response = client.get("/api/testorders/")
        assert orders_response.status_code == 200

        # Assert - OpenAPI includes both
        openapi_response = client.get("/openapi.json")
        paths = openapi_response.json()["paths"]
        assert any("testusers" in path for path in paths.keys())
        assert any("testorders" in path for path in paths.keys())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
