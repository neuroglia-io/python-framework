from pathlib import Path

from application.settings import MarioPizzeriaApplicationSettings
from fastapi import FastAPI

# Get the path relative to the current file
OPENAPI_DESCRIPTION_FILENAME = Path(__file__).parent.parent / "description.md"


def set_oas_description(app: FastAPI, settings: MarioPizzeriaApplicationSettings):
    """Sets up OpenAPI/Swagger description and metadata from settings and description file.

    Args:
        app (FastAPI): The FastAPI application instance.
        settings (MarioPizzeriaApplicationSettings): The application settings instance.
    """

    # Load description from markdown file
    with open(OPENAPI_DESCRIPTION_FILENAME, "r") as description_file:
        description = description_file.read()

    # Update FastAPI app configuration
    app.title = settings.app_name
    app.version = settings.app_version
    app.description = description

    # Configure OAuth2 for Swagger UI
    # CRITICAL: Include authorizationUrl and tokenUrl so Swagger knows where to redirect
    app.swagger_ui_init_oauth = {
        "clientId": settings.swagger_ui_client_id,
        "appName": settings.app_name,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": settings.required_scope,  # Space-separated string is correct
        # These URLs tell Swagger UI where Keycloak is (browser-accessible)
        "authorizationUrl": settings.swagger_ui_authorization_url,
        "tokenUrl": settings.swagger_ui_token_url,
    }

    # Use OpenAPI 3.0.1 for compatibility
    app.openapi_version = "3.0.1"
