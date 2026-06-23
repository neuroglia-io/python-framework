from neuroglia.hosting.web import WebHostBase

from application.settings import DesktopControllerSettings

OPENAPI_DESCRIPTION_FILENAME = "/app/src/api/description.md"


def set_oas_description(app: WebHostBase, settings: DesktopControllerSettings):
    with open(OPENAPI_DESCRIPTION_FILENAME, "r") as description_file:
        description = description_file.read()
        app.description = description
    app.title = "Cisco Certs pyApp"
    app.swagger_ui_init_oauth = {
        "clientId": settings.swagger_ui_client_id,
        "appName": settings.app_title,
        "clientSecret": settings.swagger_ui_client_secret,
        "usePkceWithAuthorizationCodeGrant": True,
        "authorizationUrl": settings.swagger_ui_authorization_url,
        "tokenUrl": settings.swagger_ui_token_url,
        "scopes": [settings.required_scope],
    }
    app.setup()
