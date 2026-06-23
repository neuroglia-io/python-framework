from typing import Optional

from neuroglia.hosting.abstractions import ApplicationSettings
from pydantic import BaseModel, ConfigDict, computed_field

from integration.services.api_client import OauthClientCredentialsAuthApiOptions


class AiGatewaySettings(ApplicationSettings, BaseModel):
    model_config = ConfigDict(extra="allow")
    log_level: str = "INFO"
    local_dev: bool = False
    app_title: str = "Cisco Certs AI Gateway"
    app_version: str = "0.1.0"

    # OAuth2.0 Settings
    jwt_authority: str = "http://keycloak47/realms/mozart"
    jwt_signing_key: str = "copy-from-jwt-authority"
    jwt_audience: str = "ai-gateways"
    required_scope: str = "api"

    # SWAGERUI Settings
    oauth2_scheme: Optional[str] = None  # "client_credentials"  # "client_credentials" or "authorization_code" or None/missing
    swagger_ui_jwt_authority: str = "http://localhost:4780/realms/mozart"  # the URL where the local swaggerui can reach its local keycloak, e.g. http://localhost:8087
    swagger_ui_client_id: str = "ai-gateway"
    swagger_ui_client_secret: str = "somesecret"

    # Mosaic API_KEY Settings
    mosaic_api_keys: list[str] = ["key1", "key2"]

    # External Services Settings
    connection_strings: dict[str, str] = {"redis": "redis://redis47:6379"}
    redis_max_connections: int = 10
    background_job_store: dict[str, str | int] = {"redis_host": "redis47", "redis_port": 6379, "redis_db": 0}  # needs explicit host:port:db

    # Local file path
    tmp_path: str = "/tmp"

    # MinIO Oauth credentials
    s3_endpoint: str
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_secure: Optional[bool] = True
    s3_session_token: Optional[str] = None
    s3_region: Optional[str] = None
    s3_part_size: int = 10 * 1024 * 1024
    s3_expiration_delta_days: int = 7

    # GenAI API Settings
    gen_ai_prompt_oauth_client: str = "placeholder"

    # Mozart Oauth Client Credentials
    mozart_oauth_client: OauthClientCredentialsAuthApiOptions

    # Mosaic Oauth Client Credentials
    mosaic_oauth_client: OauthClientCredentialsAuthApiOptions

    @computed_field
    def jwt_authorization_url(self) -> str:
        return f"{self.jwt_authority}/protocol/openid-connect/auth"

    @computed_field
    def jwt_token_url(self) -> str:
        return f"{self.jwt_authority}/protocol/openid-connect/token"

    @computed_field
    def swagger_ui_authorization_url(self) -> str:
        return f"{self.swagger_ui_jwt_authority}/protocol/openid-connect/auth"

    @computed_field
    def swagger_ui_token_url(self) -> str:
        return f"{self.swagger_ui_jwt_authority}/protocol/openid-connect/token"


app_settings = AiGatewaySettings(_env_file=".env")
