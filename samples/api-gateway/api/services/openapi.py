from neuroglia.hosting.web import WebHostBase

from application.settings import AiGatewaySettings

OPENAPI_DESCRIPTION_FILENAME = "/app/src/api/description.md"


def set_oas_description(app: WebHostBase, settings: AiGatewaySettings):
    with open(OPENAPI_DESCRIPTION_FILENAME, "r") as description_file:
        description = description_file.read()
        app.description = description
    app.title = settings.app_title
    app.version = settings.app_version
    # app.contact = settings.app_contact
    app.swagger_ui_init_oauth = {
        "clientId": settings.swagger_ui_client_id,
        "appName": settings.app_title,
        "clientSecret": settings.swagger_ui_client_secret,
        "usePkceWithAuthorizationCodeGrant": True,
        "authorizationUrl": settings.swagger_ui_authorization_url,
        "tokenUrl": settings.swagger_ui_token_url,
        "scopes": [settings.required_scope],
    }
    # The default version(3.1) is not supported by Current version of Synapse workflows. TBR once this is fixed.
    app.openapi_version = "3.0.1"
    app.setup()
