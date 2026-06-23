import logging

from neuroglia.hosting.abstractions import ApplicationSettings
from neuroglia.serialization.json import JsonSerializer

from integration.services.api_client import (
    OauthApiClient,
    OauthClientCredentialsAuthApiOptions,
)

log = logging.getLogger(__name__)


class MozartApiClientException(Exception):
    """Exception raised for errors in the MozartApiClient."""


class MozartApiClientOptions(OauthClientCredentialsAuthApiOptions):
    pass


class MozartApiClient(OauthApiClient):
    """
    Synchronous and Asynchronous API client to interact with Mozart's Session-manager.

    Inherits from OauthApiClient to provide methods for managing sessions in Mozart's system.

    Attributes:
        json_serializer (JsonSerializer): Serializer for JSON data.
        api_client_options (OauthClientCredentialsAuthenticationOptions): The ClientCredentials options
    """

    endpoints = {
        "get_widget_by_id": ("GET", "/widget-manager/api/widgets/byid/{widget_aggregate_id}"),
        "set_widget_state": ("PUT", "/widget-manager/api/widgets"),
    }

    def __init__(self, api_client_options: MozartApiClientOptions, json_serializer: JsonSerializer, app_settings: ApplicationSettings):
        """
        Initializes the MozartApiClient with the given options and serializer.

        Args:
            api_client_options (OauthClientCredentialsAuthApiOptions): Configuration options for the client.
            json_serializer (JsonSerializer): Serializer for JSON data.
        """
        super().__init__(api_client_options=api_client_options, json_serializer=json_serializer, app_settings=app_settings)
