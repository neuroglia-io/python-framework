"""Application settings and configuration"""

from typing import Optional

from pydantic import computed_field
from pydantic_settings import SettingsConfigDict

from neuroglia.observability.settings import ApplicationSettingsWithObservability


class MarioPizzeriaApplicationSettings(ApplicationSettingsWithObservability):
    """Application configuration for Mario's Pizzeria with integrated observability

    Key URL Concepts:
    - Internal URLs (keycloak_*): Used by backend services running in Docker network
    - External URLs (swagger_ui_*): Used by browser/Swagger UI for OAuth2 flows

    Observability Features:
    - Comprehensive three pillars: metrics, tracing, logging
    - Standard endpoints: /health, /ready, /metrics
    - Health checks for MongoDB and Keycloak dependencies
    """

    # Application Identity (used by observability)
    service_name: str = "mario-pizzeria"
    service_version: str = "1.0.0"
    deployment_environment: str = "development"

    # Application Configuration
    app_name: str = "Mario's Pizzeria"
    debug: bool = True
    log_level: str = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    local_dev: bool = True  # True = development mode with localhost URLs for browser
    app_url: str = "http://localhost:8080"  # External URL where the app is accessible (Docker port mapping)

    # Session (for UI app)
    session_secret_key: str = "change-me-in-production-please-use-strong-key-32-chars-min"
    session_max_age: int = 3600  # 1 hour

    # Redis Session Store Configuration
    redis_enabled: bool = True  # Enable Redis session storage (falls back to in-memory if unavailable)
    redis_url: str = "redis://redis:6379/0"  # Redis connection URL
    redis_key_prefix: str = "mario_session:"  # Prefix for session keys
    session_timeout_hours: int = 24  # Session timeout in hours

    # Keycloak Configuration (Internal Docker network URLs - used by backend)
    keycloak_server_url: str = "http://keycloak:8080"  # Internal Docker network
    keycloak_realm: str = "pyneuro"
    keycloak_client_id: str = "mario-app"
    keycloak_client_secret: str = "mario-secret-123"

    # JWT Validation (Backend token validation)
    jwt_signing_key: str = ""  # RSA public key - auto-discovered from Keycloak if empty
    jwt_audience: str = "mario-app"  # Expected audience claim in JWT (must match client_id)
    jwt_algorithm: str = "HS256"  # JWT algorithm (HS256 for legacy, RS256 for Keycloak)
    jwt_secret_key: str = "mario-secret-key-change-in-production"  # Secret for HS256 (legacy)

    # JWT Validation Options (for RS256 tokens from Keycloak)
    verify_audience: bool = True  # Verify audience claim in JWT
    expected_audience: str = "mario-app"  # Expected audience (same as jwt_audience)
    verify_issuer: bool = False  # Verify issuer claim in JWT
    expected_issuer: str = ""  # Expected issuer URL (e.g., http://keycloak:8080/realms/pyneuro)

    # Token Refresh (for session-based auth with refresh tokens)
    refresh_auto_leeway_seconds: int = 300  # Auto-refresh when token expires in less than 5 minutes

    required_scope: str = "openid profile email"  # Required OAuth2 scopes

    # OAuth2 Scheme Type
    oauth2_scheme: Optional[str] = "authorization_code"  # "client_credentials" or "authorization_code"

    # CloudEvent Publishing Configuration inherited from ApplicationSettingsWithObservability
    # Reads from CLOUD_EVENT_SINK, CLOUD_EVENT_SOURCE, CLOUD_EVENT_TYPE_PREFIX environment variables

    # Swagger UI OAuth Configuration (External URLs - used by browser)
    swagger_ui_client_id: str = "mario-app"  # Must match keycloak_client_id
    swagger_ui_client_secret: str = ""  # Leave empty for public clients

    # Observability Configuration (Three Pillars)
    observability_enabled: bool = True
    observability_metrics_enabled: bool = True
    observability_tracing_enabled: bool = True
    observability_logging_enabled: bool = False  # Disable for local development (as its very resource intensive)

    # Standard Endpoints
    observability_health_endpoint: bool = True
    observability_metrics_endpoint: bool = True
    observability_ready_endpoint: bool = True

    # Health Check Dependencies
    observability_health_checks: list[str] = ["mongodb", "keycloak"]

    # OpenTelemetry Configuration
    otel_endpoint: str = "http://otel-collector:4317"  # Docker network endpoint
    otel_console_export: bool = False  # Enable for debugging

    # Database Connection Strings (overrides base class default)
    connection_strings: dict[str, str] = {
        "mongo": "mongodb://root:neuroglia123@mongodb:27017/mario_pizzeria?authSource=admin",
    }

    # Computed Fields - Auto-generate URLs from base configuration
    @computed_field
    @property
    def jwt_authority(self) -> str:
        """Internal Keycloak authority URL (for backend token validation)"""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

    @computed_field
    def jwt_authorization_url(self) -> str:
        """Internal OAuth2 authorization URL"""
        return f"{self.jwt_authority}/protocol/openid-connect/auth"

    @computed_field
    def jwt_token_url(self) -> str:
        """Internal OAuth2 token URL"""
        return f"{self.jwt_authority}/protocol/openid-connect/token"

    @computed_field
    def swagger_ui_jwt_authority(self) -> str:
        """External Keycloak authority URL (for browser/Swagger UI)"""
        if self.local_dev:
            # Development: Browser connects to localhost:8090 (Keycloak Docker port mapping)
            return f"http://localhost:8090/realms/{self.keycloak_realm}"
        else:
            # Production: Browser connects to public Keycloak URL
            return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

    @computed_field
    def swagger_ui_authorization_url(self) -> str:
        """External OAuth2 authorization URL (for browser)"""
        return f"{self.swagger_ui_jwt_authority}/protocol/openid-connect/auth"

    @computed_field
    def swagger_ui_token_url(self) -> str:
        """External OAuth2 token URL (for browser)"""
        return f"{self.swagger_ui_jwt_authority}/protocol/openid-connect/token"

    @computed_field
    def app_version(self) -> str:
        """Application version (alias for service_version for backward compatibility)"""
        return self.service_version

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )


app_settings = MarioPizzeriaApplicationSettings()
