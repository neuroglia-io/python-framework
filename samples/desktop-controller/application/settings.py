from typing import Optional

from neuroglia.hosting.abstractions import ApplicationSettings
from pydantic import BaseModel, ConfigDict, computed_field


class DesktopControllerSettings(ApplicationSettings, BaseModel):
    model_config: ConfigDict = ConfigDict(extra="allow")
    log_level: str = "INFO"
    local_dev: bool = False
    app_title: str = "Desktop Controller"
    required_scope: str = "api"
    jwt_authority: str = "http://keycloak97/auth/realms/mozart"  # https://sj-keycloak.ccie.cisco.com/auth/realms/mozart
    jwt_signing_key: str = "copy-from-jwt-authority"
    jwt_audience: str = "desktops"
    oauth2_scheme: Optional[str] = None  # "client_credentials"  # "client_credentials" or "authorization_code" or None/missing
    swagger_ui_jwt_authority: str = "http://localhost:9780/auth/realms/mozart"  # the URL where the local swaggerui can reach its local keycloak, e.g. http://localhost:8087
    swagger_ui_client_id: str = "desktop-controller"
    swagger_ui_client_secret: str = "somesecret"
    docker_host_user_name: str = "sys-admin"
    docker_host_host_name: str = "host.docker.internal"  # macos:host.docker.internal ubuntu:{IP_address_or_DNS_name}
    remotefs_base_folder: str = "/tmp"
    userinfo_filename: str = "userinfo.json"
    hostinfo_filename: str = "hostinfo.json"

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


app_settings = DesktopControllerSettings(_env_file=".env")
