import logging
from typing import Any, Optional

import httpx
from neuroglia.hosting.abstractions import ApplicationBuilderBase, ApplicationSettings
from neuroglia.serialization.json import JsonSerializer
from pydantic import BaseModel

from integration.services.api_client import (
    OAuthApiClientException,
    OauthClientCredentialsAuthApiOptions,
)
from integration.services.mozart_api_client import (
    MozartApiClient,
    MozartApiClientException,
)

log = logging.getLogger(__name__)


class CreateSessionCommandDto(BaseModel):
    """
    {
        "id": "string",
        "candidateId": "string",
        "lds": {
            "id": "string",
            "environment": "string"
        },
        "parts": [
            {
            "id": "string",
            "pod": {
                "id": "string",
                "devices": [
                    {}
                ]
            }
            }
        ]
    }
    """

    id: str
    candidateId: str
    lds: dict[str, str]
    parts: Optional[Any] = None


class MozartGenAiPromptApiClientException(MozartApiClientException):
    """Exception raised for errors in the MozartGenAiPromptApiClient."""


class MozartGenAiPromptAuthApiOptions(OauthClientCredentialsAuthApiOptions):
    """Configuration options for the Mozart GenAI Prompt Engine API client."""


class MozartGenAiPromptApiClient(MozartApiClient):
    """
    Asynchronous API client to interact with Mozart's GenAI Prompt Engine.

    Inherits from ApiClient and OauthAuthenticationClient to provide methods
    for managing Grading sessions in Mozart's system.

    Attributes:
        json_serializer (JsonSerializer): Serializer for JSON data.
        base_url (str): Base URL for the Mozart API.
        headers (Dict[str, str]): Headers to include in API requests.
        default_headers (Dict[str, str]): Default headers for API requests.
    """

    endpoints = {
        "create_session": ("POST", "/api/v1/sessions"),
        "get_session": ("GET", "/api/v1/sessions/{sessionId}"),
        "add_part": ("POST", "/api/v1/sessions/parts"),
        "grade_part": ("POST", "/api/v1/sessions/{sessionId}/parts/{partId}/grade"),
    }

    def __init__(self, api_client_options: MozartGenAiPromptAuthApiOptions, json_serializer: JsonSerializer, app_settings: ApplicationSettings):
        """
        Initializes the MozartGenAiPromptApiClient with the given options and serializer.

        Args:
            api_client_options (MozartApiClientOptions): Configuration options for the client.
            json_serializer (JsonSerializer): Serializer for JSON data.
        """
        super().__init__(api_client_options=api_client_options, json_serializer=json_serializer, app_settings=app_settings)

    async def is_online(self) -> bool:
        """
        Checks if the GenAI Prompt Engine API is online.

        Returns:
            bool: True if the API is online, False otherwise.
        """
        try:
            res, code = await self.call_api_async(method=self.endpoints["create_session"][0], endpoint=self.endpoints["create_session"][1], data={})
            return code == 400

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when checking if grading-engine is online: {ex}")
            return False

    async def create_session(self, create_session_command_dto: CreateSessionCommandDto) -> Any:
        """
        Creates a new GenAI Prompt Engine session.

        Args:
            mozart_session_id (str): The ID of the Mozart session.
            candidate_id (str): The ID of the candidate (min 3 chars).
            lds_environment_acronym (str): The acronym of the LDS environment.
            lds_session_id (str): The ID of the LDS session.

        Returns:
            Any: The response from the API call. TODO: Define the response type.
        """
        try:
            res, code = await self.call_api_async(method=self.endpoints["create_session"][0], endpoint=self.endpoints["create_session"][1], data=create_session_command_dto.model_dump())
            if code < 300:
                return res  # TODO: Define the response type.
            raise MozartApiClientException(f"{code}: {res}")

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to create_session: {ex}")
            raise MozartGenAiPromptApiClientException(f"Error when trying to create_session: {ex}")

    async def create_empty_session(self, mozart_session_id: str, candidate_id: str, lds_environment_acronym: LdsEnvironmentAcronym, lds_session_id: str) -> Any:
        """
        Creates a new empty GenAI Prompt Engine session that can get parts added to it.

        Args:
            mozart_session_id (str): The ID of the Mozart session.
            candidate_id (str): The ID of the candidate (min 3 chars).
            lds_environment_acronym (str): The acronym of the LDS environment.
            lds_session_id (str): The ID of the LDS session.

        Returns:
            Any: The response from the API call. TODO: Define the response type.
        """
        try:
            create_session_command = {
                "id": mozart_session_id,
                "candidateId": candidate_id,
                "lds": {
                    "environment": lds_environment_acronym.value,
                    "id": lds_session_id,
                },
            }
            res, code = await self.call_api_async(method=self.endpoints["create_session"][0], endpoint=self.endpoints["create_session"][1], data=create_session_command)
            if code < 300:
                return res  # TODO: Define the response type.
            raise MozartApiClientException(f"{code}: {res}")

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to create_session: {ex}")
            raise MozartGenAiPromptApiClientException(f"Error when trying to create_session: {ex}")

    async def get_session(self, mozart_session_id: str) -> Any:
        """
        Gets a GenAI Prompt Engine session.

        Args:
            mozart_session_id (str): The ID of the Mozart session.

        Returns:
            Any: The response from the API call. TODO: Define the response type.
        """
        try:
            res, code = await self.call_api_async(method=self.endpoints["get_session"][0], endpoint=self.endpoints["get_session"][1].format(sessionId=mozart_session_id))
            if code < 300:
                return res  # TODO: Define the response type.
            raise MozartApiClientException(f"{code}: {res}")

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to get_session: {ex}")
            raise MozartGenAiPromptApiClientException(f"Error when trying to get_session: {ex}")

    async def session_exists(self, mozart_session_id: str) -> bool:
        """
        Checks if a GenAI Prompt Engine session exists.

        Args:
            mozart_session_id (str): The ID of the Mozart session.

        Returns:
            bool: True if the session exists, False otherwise.
        """
        try:
            res = await self.get_session(mozart_session_id)
            return res is not None

        except MozartGenAiPromptApiClientException as ex:
            log.error(f"Error when trying to session_exists: {ex}")
            return False

    async def add_part(self, mozart_session_id: str, part_qualified_name: str, pod_descriptor: Optional[Any] = None) -> bool:
        """
        Adds a part to a GenAI Prompt Engine session.

        Args:
            mozart_session_id (str): The ID of the Mozart session.
            part_qualified_name (str): The qualified name of the part.
            pod_descriptor (Any): The descriptor of the pod. (id and devices list)

        Returns:
            Any: The response from the API call. TODO: Define the response type.
        """
        try:
            add_part_command = {
                "id": mozart_session_id,
                "part": {"id": part_qualified_name},
            }
            if pod_descriptor is not None:
                add_part_command["part"]["pod"] = pod_descriptor
            res, code = await self.call_api_async(method=self.endpoints["add_part"][0], endpoint=self.endpoints["add_part"][1], data=add_part_command)
            if code < 300:
                return True
            raise MozartApiClientException(f"{code}: {res}")

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to add_part: {ex}")
            raise MozartGenAiPromptApiClientException(f"Error when trying to add_part: {ex}")

    async def grade_part(self, mozart_session_id: str, part_qualified_name: str, recollect: Optional[bool] = True) -> bool:
        """
        Request the GenAI Prompt Engine to grade a part.

        Args:
            mozart_session_id (str): The ID of the Mozart session.
            part_qualified_name (str): The qualified name of the part.

        Returns:
            bool: True if the grading request was successful, False otherwise.
        """
        try:
            recollect_query_param = "true" if recollect else "false"
            res, code = await self.call_api_async(method=self.endpoints["grade_part"][0], endpoint=self.endpoints["grade_part"][1], path_params={"sessionId": mozart_session_id, "partId": part_qualified_name}, params={"recollect": recollect_query_param})
            if code == 202:
                return True
            raise MozartApiClientException(f"{code}: {res}")

        except (MozartApiClientException, OAuthApiClientException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to grade_part: {ex}")
            raise MozartGenAiPromptApiClientException(f"Error when trying to grade_part: {ex}")

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
        grading_engine_api_options = MozartGenAiPromptAuthApiOptions(**builder.settings.grading_engine_oauth_client.__dict__)
        builder.services.try_add_singleton(MozartGenAiPromptAuthApiOptions, singleton=grading_engine_api_options)
        builder.services.add_scoped(MozartGenAiPromptApiClient, MozartGenAiPromptApiClient)
        return builder
