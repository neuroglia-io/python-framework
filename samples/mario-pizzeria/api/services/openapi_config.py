"""OpenAPI/Swagger configuration service for API documentation."""
import logging
from collections.abc import Iterable
from typing import Any, cast

from application.settings import Settings
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant, SecurityRequirement
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.routing import Mount

log = logging.getLogger(__name__)


def configure_mounted_apps_openapi_prefix(app: FastAPI) -> None:
    """Annotate mounted sub-apps with their mount path for OpenAPI path rendering.

    This function iterates over all mounted sub-apps in the root application and
    sets the `openapi_path_prefix` attribute on each sub-app's state. This prefix
    is used by the OpenAPI schema generation to render full URLs in Swagger UI.

    Args:
        app: Root FastAPI application with mounted sub-apps
    """
    for route in app.routes:
        if isinstance(route, Mount) and hasattr(route, "app") and route.app is not None:
            mount_path = route.path or ""
            # Normalize to leading slash, but treat root mount as empty prefix
            if mount_path and not mount_path.startswith("/"):
                mount_path = f"/{mount_path}"
            normalized_prefix = mount_path.rstrip("/") if mount_path not in ("", "/") else ""
            log.debug(f"Mounted sub-app '{route}' at '{normalized_prefix}'")
            route.app.state.openapi_path_prefix = normalized_prefix  # type: ignore[attr-defined]


def _resolve_mount_prefix(app: FastAPI) -> str:
    """Return the normalized mount prefix ('' when mounted at root)."""
    prefix = getattr(app.state, "openapi_path_prefix", "")
    if not prefix:
        return ""
    normalized = prefix if prefix.startswith("/") else f"/{prefix}"
    normalized = normalized.rstrip("/")
    return normalized


# Custom setup function for API sub-app OpenAPI configuration
def configure_api_openapi(app: FastAPI, settings: Settings) -> None:
    """Configure OpenAPI security schemes for the API sub-app."""
    OpenAPIConfigService.configure_security_schemes(app, settings)
    OpenAPIConfigService.configure_swagger_ui(app, settings)


class OpenAPIConfigService:
    """Service to configure OpenAPI schema with security schemes for Swagger UI."""

    @staticmethod
    def configure_security_schemes(
        app: FastAPI,
        settings: Settings,
    ) -> None:
        """Configure OpenAPI security schemes for authentication in Swagger UI.

        Adds OAuth2 Authorization Code flow for browser-based authentication
        via Keycloak. Users click "Authorize" in Swagger UI, login via Keycloak,
        and the access token is automatically included in API requests.

        The client_id is automatically populated from settings.KEYCLOAK_CLIENT_ID,
        while client_secret is left empty for users to provide if needed.

        Args:
            app: FastAPI application instance
            settings: Application settings with Keycloak configuration
        """

        def custom_openapi() -> dict[str, Any]:
            """Generate custom OpenAPI schema with security configurations."""
            if app.openapi_schema:
                return app.openapi_schema

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )

            prefix = _resolve_mount_prefix(app)
            if prefix:
                openapi_schema["servers"] = [{"url": prefix}]

            # Add security scheme for OAuth2 Authorization Code Flow
            if "components" not in openapi_schema:
                openapi_schema["components"] = {}
            if "securitySchemes" not in openapi_schema["components"]:
                openapi_schema["components"]["securitySchemes"] = {}

            openapi_schema["components"]["securitySchemes"]["oauth2"] = {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/auth",
                        "tokenUrl": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
                        "scopes": {
                            "openid": "OpenID Connect",
                            "profile": "User profile",
                            "email": "Email address",
                            "roles": "User roles",
                        },
                    }
                },
            }

            # Tracking the missing security metadata back to FastAPI’s dependency tree:
            # the bearer scheme lives inside the nested dependant that get_current_user
            # pulls in, so the APIRoute itself exposed none.

            # Recursively walk every dependant tree and map FastAPI routes to their
            # declared security requirements. This ensures Swagger only attaches Authorization
            # headers when the underlying route actually depends on security schemes.
            def _collect_security_requirements(
                dependant: Dependant,
            ) -> list[SecurityRequirement]:
                stack: list[Dependant] = [dependant]
                visited: set[int] = set()
                collected: list[SecurityRequirement] = []
                while stack:
                    current = stack.pop()
                    identifier = id(current)
                    if identifier in visited:
                        continue
                    visited.add(identifier)
                    current_requirements: Iterable[SecurityRequirement] = getattr(current, "security_requirements", []) or []
                    collected.extend(current_requirements)
                    stack.extend(getattr(current, "dependencies", []) or [])
                return collected

            def _resolve_scheme_name(security_scheme: Any) -> str | None:
                name = getattr(security_scheme, "scheme_name", None)
                if name:
                    return cast(str, name)
                model = getattr(security_scheme, "model", None)
                model_name = getattr(model, "name", None)
                if model_name:
                    return cast(str, model_name)
                return None

            operations_security: dict[tuple[str, str], list[dict[str, list[str]]]] = {}
            for route in app.routes:
                if not isinstance(route, APIRoute):
                    continue
                dependant = getattr(route, "dependant", None)
                if not isinstance(dependant, Dependant):
                    continue
                security_requirements = _collect_security_requirements(dependant)
                if not security_requirements:
                    continue

                dedup: dict[tuple[str, tuple[str, ...]], dict[str, list[str]]] = {}
                for requirement in security_requirements:
                    security_scheme = getattr(requirement, "security_scheme", None)
                    scheme_name = _resolve_scheme_name(security_scheme)
                    scopes = list(getattr(requirement, "scopes", []) or [])
                    if scheme_name:
                        key = (scheme_name, tuple(scopes))
                        if key not in dedup:
                            dedup[key] = {scheme_name: scopes}
                requirement_dicts = list(dedup.values())
                if not requirement_dicts:
                    continue
                for method in route.methods or []:
                    method_lower = method.lower()
                    if method_lower in {"head", "options"}:
                        continue
                    operations_security[(route.path_format, method_lower)] = requirement_dicts

            paths = openapi_schema.get("paths", {})
            http_methods = {
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
                "trace",
            }
            for route_path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue
                for method, operation in path_item.items():
                    if method not in http_methods or not isinstance(operation, dict):
                        continue
                    security_entry = operations_security.get((route_path, method))
                    if security_entry:
                        operation["security"] = security_entry
                    elif "security" in operation:
                        operation.pop("security")

            # Set client_id in Swagger UI
            if "swagger-ui-parameters" not in openapi_schema:
                openapi_schema["swagger-ui-parameters"] = {}
            swagger_client_id = getattr(settings, "keycloak_public_client_id", "") or getattr(settings, "keycloak_client_id", "")
            if swagger_client_id:
                openapi_schema["swagger-ui-parameters"]["client_id"] = swagger_client_id

            app.openapi_schema = openapi_schema
            return app.openapi_schema

        app.openapi = custom_openapi  # type: ignore

    @staticmethod
    def configure_swagger_ui(app: FastAPI, settings: Settings) -> None:
        """Configure Swagger UI with OAuth2 client credentials.

        This sets up the Swagger UI initOAuth parameters to pre-fill
        the client_id in the authorization dialog.

        Args:
            app: FastAPI application instance
            settings: Application settings with Keycloak configuration
        """
        # Override swagger_ui_init_oauth to provide client_id
        # Prefer public browser client if configured (avoids confidential secret exposure)
        public_client_id = cast(str, getattr(settings, "keycloak_public_client_id", ""))
        confidential_client_id = cast(str, getattr(settings, "keycloak_client_id", ""))
        client_secret = cast(str, getattr(settings, "keycloak_client_secret", ""))

        chosen_client_id = public_client_id or confidential_client_id

        # Configure OAuth init; pass clientSecret only if using confidential client
        init_oauth: dict[str, Any] = {
            "clientId": chosen_client_id,
            "usePkceWithAuthorizationCodeGrant": True,
        }
        if chosen_client_id == confidential_client_id and client_secret:
            init_oauth["clientSecret"] = client_secret

        app.swagger_ui_init_oauth = init_oauth

        # Persist tokens across doc reloads and highlight server prefix in the UI
        existing_params = getattr(app, "swagger_ui_parameters", None)
        if not isinstance(existing_params, dict):
            existing_params = {}
        app.swagger_ui_parameters = {
            **existing_params,
            "persistAuthorization": True,
            # Ensure requests get Authorization header when flow completes
            # FastAPI's Swagger UI auto-injects once token is stored; we just keep it.
        }
