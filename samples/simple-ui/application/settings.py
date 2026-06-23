"""Application settings and configuration."""

import logging
import os
import sys
from dataclasses import dataclass


@dataclass
class AppSettings:
    """Application settings with Keycloak integration."""

    # Application
    app_name: str = "Simple UI"
    app_version: str = "1.0.0"
    debug: bool = True

    # JWT Settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Keycloak Settings
    keycloak_server_url: str = os.getenv("KEYCLOAK_SERVER_URL", "http://keycloak:8080")
    keycloak_realm: str = os.getenv("KEYCLOAK_REALM", "pyneuro")
    keycloak_client_id: str = os.getenv("KEYCLOAK_CLIENT_ID", "simple-ui-app")
    keycloak_client_secret: str | None = os.getenv("KEYCLOAK_CLIENT_SECRET")


# Global settings instance
app_settings = AppSettings()


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure root logger
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)])

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
