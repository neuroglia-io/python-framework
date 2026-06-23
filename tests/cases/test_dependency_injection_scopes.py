"""
Comprehensive tests for the dependency injection service lifecycle and scoping.
"""
import pytest
from neuroglia.dependency_injection import ServiceCollection


# Test service classes
class IRepository:
    """Interface for repository"""
    def get_data(self) -> str:
        raise NotImplementedError()


class DatabaseRepository(IRepository):
    """Database repository implementation"""
    def __init__(self):
        self.instance_id = id(self)
    
    def get_data(self) -> str:
        return f"data_from_db_{self.instance_id}"


class IEmailService:
    """Interface for email service"""
    def send_email(self, to: str) -> str:
        raise NotImplementedError()


class EmailService(IEmailService):
    """Email service implementation"""
    def __init__(self, repository: IRepository):
        self.repository = repository
        self.instance_id = id(self)
    
    def send_email(self, to: str) -> str:
        return f"email_sent_to_{to}_by_{self.instance_id}_with_{self.repository.get_data()}"


class IUserService:
    """Interface for user service"""
    def create_user(self, name: str) -> str:
        raise NotImplementedError()


class UserService(IUserService):
    """User service implementation"""
    def __init__(self, repository: IRepository, email_service: IEmailService):
        self.repository = repository
        self.email_service = email_service
        self.instance_id = id(self)
    
    def create_user(self, name: str) -> str:
        data = self.repository.get_data()
        email_result = self.email_service.send_email(f"{name}@test.com")
        return f"user_{name}_created_{self.instance_id}_with_{data}_and_{email_result}"


class TestDependencyInjectionScopes:
    """Test suite for dependency injection service lifecycle and scoping"""

    def setup_method(self):
        """Setup for each test"""
        self.services = ServiceCollection()

    def test_singleton_lifetime(self):
        """Test that singleton services return the same instance"""
        # Register singleton service
        self.services.add_singleton(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Get service multiple times
        repo1 = provider.get_service(IRepository)
        repo2 = provider.get_service(IRepository)
        repo3 = provider.get_required_service(IRepository)
        
        # All should be the same instance
        assert repo1 is repo2
        assert repo2 is repo3
        assert isinstance(repo1, DatabaseRepository)

    def test_transient_lifetime(self):
        """Test that transient services return new instances each time"""
        # Register transient service
        self.services.add_transient(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Get service multiple times
        repo1 = provider.get_service(IRepository)
        repo2 = provider.get_service(IRepository)
        repo3 = provider.get_required_service(IRepository)
        
        # All should be different instances
        assert repo1 is not repo2
        assert repo2 is not repo3
        assert repo1 is not repo3
        assert all(isinstance(repo, DatabaseRepository) for repo in [repo1, repo2, repo3])

    def test_scoped_lifetime_within_single_scope(self):
        """Test that scoped services return the same instance within a scope"""
        # Register scoped service
        self.services.add_scoped(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Create a scope
        scope = provider.create_scope()
        scoped_provider = scope.get_service_provider()
        
        # Get service multiple times within the same scope
        repo1 = scoped_provider.get_service(IRepository)
        repo2 = scoped_provider.get_service(IRepository)
        repo3 = scoped_provider.get_required_service(IRepository)
        
        # All should be the same instance within the scope
        assert repo1 is repo2
        assert repo2 is repo3
        assert isinstance(repo1, DatabaseRepository)
        
        # Cleanup
        scope.dispose()

    def test_scoped_lifetime_across_different_scopes(self):
        """Test that scoped services return different instances across different scopes"""
        # Register scoped service
        self.services.add_scoped(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Create two different scopes
        scope1 = provider.create_scope()
        scope2 = provider.create_scope()
        
        provider1 = scope1.get_service_provider()
        provider2 = scope2.get_service_provider()
        
        # Get services from different scopes
        repo1 = provider1.get_service(IRepository)
        repo2 = provider2.get_service(IRepository)
        
        # Should be different instances across scopes
        assert repo1 is not repo2
        assert isinstance(repo1, DatabaseRepository)
        assert isinstance(repo2, DatabaseRepository)
        
        # Cleanup
        scope1.dispose()
        scope2.dispose()

    def test_mixed_lifetimes_dependency_injection(self):
        """Test complex dependency injection with mixed lifetimes"""
        # Register services with different lifetimes
        self.services.add_singleton(IRepository, DatabaseRepository)  # Singleton
        self.services.add_scoped(IEmailService, EmailService)          # Scoped
        self.services.add_transient(IUserService, UserService)         # Transient
        
        provider = self.services.build()
        
        # Create scope
        scope = provider.create_scope()
        scoped_provider = scope.get_service_provider()
        
        # Get services multiple times
        user_service1 = scoped_provider.get_service(IUserService)
        user_service2 = scoped_provider.get_service(IUserService)
        
        # UserService should be different (transient)
        assert user_service1 is not user_service2
        
        # But their dependencies should follow their lifetime rules:
        # Repository should be same (singleton)
        assert user_service1.repository is user_service2.repository
        
        # EmailService should be same within scope (scoped)
        assert user_service1.email_service is user_service2.email_service
        
        # Repository in EmailService should be same as in UserService (singleton)
        assert user_service1.email_service.repository is user_service1.repository
        
        # Test functionality
        result1 = user_service1.create_user("Alice")
        result2 = user_service2.create_user("Bob")
        
        assert "Alice" in result1
        assert "Bob" in result2
        
        # Cleanup
        scope.dispose()

    def test_scope_isolation(self):
        """Test that different scopes are properly isolated"""
        # Register scoped services
        self.services.add_scoped(IRepository, DatabaseRepository)
        self.services.add_scoped(IEmailService, EmailService)
        provider = self.services.build()
        
        # Create two scopes
        scope1 = provider.create_scope()
        scope2 = provider.create_scope()
        
        provider1 = scope1.get_service_provider()
        provider2 = scope2.get_service_provider()
        
        # Get services from both scopes
        email1a = provider1.get_service(IEmailService)
        email1b = provider1.get_service(IEmailService)  # Same scope
        email2 = provider2.get_service(IEmailService)   # Different scope
        
        # Services within same scope should be same
        assert email1a is email1b
        
        # Services across different scopes should be different
        assert email1a is not email2
        
        # Dependencies should also be scoped correctly
        assert email1a.repository is not email2.repository
        
        # Cleanup
        scope1.dispose()
        scope2.dispose()

    def test_scope_disposal_cleanup(self):
        """Test that scope disposal properly cleans up resources"""
        # Register scoped service
        self.services.add_scoped(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Create scope and get service
        scope = provider.create_scope()
        scoped_provider = scope.get_service_provider()
        repo = scoped_provider.get_service(IRepository)
        
        assert repo is not None
        
        # Dispose scope
        scope.dispose()
        
        # Create new scope and get service - should be different instance
        scope2 = provider.create_scope()
        scoped_provider2 = scope2.get_service_provider()
        repo2 = scoped_provider2.get_service(IRepository)
        
        assert repo is not repo2
        
        # Cleanup
        scope2.dispose()

    def test_cannot_resolve_scoped_from_root(self):
        """Test that scoped services cannot be resolved directly from root provider"""
        # Register scoped service
        self.services.add_scoped(IRepository, DatabaseRepository)
        provider = self.services.build()
        
        # Trying to get scoped service from root should raise exception
        with pytest.raises(Exception) as exc_info:
            provider.get_service(IRepository)
        
        assert "scoped service" in str(exc_info.value).lower()

    def test_service_registration_types(self):
        """Test different service registration patterns"""
        # Test various registration patterns
        self.services.add_singleton(IRepository, DatabaseRepository)
        self.services.add_transient(str, implementation_factory=lambda sp: "factory_created")
        self.services.add_scoped(int, singleton=None, implementation_factory=lambda sp: 42)
        
        provider = self.services.build()
        scope = provider.create_scope()
        scoped_provider = scope.get_service_provider()
        
        # Test singleton registration
        repo = provider.get_service(IRepository)
        assert isinstance(repo, DatabaseRepository)
        
        # Test transient factory
        str1 = provider.get_service(str)
        str2 = provider.get_service(str)
        assert str1 == "factory_created"
        assert str2 == "factory_created" 
        # Note: These might be the same string object due to Python string interning,
        # but they were created by separate factory calls
        
        # Test scoped factory
        int1 = scoped_provider.get_service(int)
        int2 = scoped_provider.get_service(int)
        assert int1 == 42
        assert int2 == 42
        assert int1 is int2  # Should be same instance within scope
        
        # Cleanup
        scope.dispose()

    def test_try_add_methods_prevent_duplicates(self):
        """Test that try_add_* methods prevent duplicate registrations"""
        # First registration should succeed
        self.services.try_add_singleton(IRepository, DatabaseRepository)
        assert len(self.services) == 1
        
        # Second registration should be ignored
        self.services.try_add_singleton(IRepository, DatabaseRepository)
        assert len(self.services) == 1  # Still only one registration
        
        # But regular add should create duplicate
        self.services.add_singleton(IRepository, DatabaseRepository)
        assert len(self.services) == 2  # Now we have two