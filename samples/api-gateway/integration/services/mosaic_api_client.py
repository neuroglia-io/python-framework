import logging
import os
from pathlib import Path
import uuid
from typing import Any
from urllib.parse import urljoin

import httpx
from neuroglia.serialization.abstractions import Serializer, TextSerializer
from neuroglia.serialization.json import JsonSerializer
from neuroglia.hosting.abstractions import ApplicationBuilderBase

from application.exceptions import ApplicationException
from application.settings import app_settings
from integration.exceptions import IntegrationException
from integration.services.api_client import (
    OauthApiClient,
    OauthClientCredentialsAuthApiOptions,
)

log = logging.getLogger(__name__)


class MosaicApiClientOAuthOptions(OauthClientCredentialsAuthApiOptions):
    """
    Mosaic API Client OAuth Options
    """

    def __init__(self, client_id: str, client_secret: str, token_url: str, base_url: str):
        super().__init__(client_id=client_id, client_secret=client_secret, token_url=token_url, base_url=base_url)


class MosaicApiClientException(Exception):
    """Exception raised for errors in the MosaicApiClient."""


class MosaicApiClient(OauthApiClient):
    endpoints = {
        "pull_search_items": ("POST", "/api/search/items"),
        "export_items_by_module": ("POST", "/api/itembank/export/items/module/{moduleId}"),
        "get_file_by_id": ("GET", "/api/file/download/{fileId}"),
        "get_blueprint_by_id": ("GET", "/api/blueprint/{blueprintId}"),
        "get_blueprint_settings": ("GET", "/api/module/{moduleId}/blueprint_settings"),
        "get_formset_settings": ("GET", "/api/v1/formset/settings"),
        "get_package_list": ("GET", "/api/packages/getList"),
        "get_publish_history": ("GET", "/api/formset/{formsetId}/publishhistory"),
        "publish_formset_package": ("POST", "/api/v1/formset/publish"),
        "download_formset_package": ("GET", "/api/file/download/formset/package/{publishedRecordId}"),
    }

    def __init__(self, api_client_options: MosaicApiClientOAuthOptions, json_serializer: JsonSerializer):
        super().__init__(api_client_options=api_client_options, json_serializer=json_serializer, app_settings=app_settings)

    def set_base_url(self, base_url: str):
        self.base_url = str(base_url)

    def _call_api(self, method, endpoint, path_params=None, params=None, data=None, headers=None, timeout=30) -> Any:
        """
        Internal method to call the Mosaic API.

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The API endpoint to call.
            path_params (dict,optional): Path parameters for the request.
            params (dict, optional): Query parameters for the request.
            data (Any, optional): The data to send in the request body.
            headers (dict, optional): Additional headers to send with the request.

        Returns:
            Any: The response from the API call.

        Raises:
            MosaicSessionManagerApiClientException: If the API request fails.
        """
        req_id = str(uuid.uuid4())
        if not self.base_url:
            raise MosaicApiClientException(f"The base URL is not set.")

        if path_params is not None:
            endpoint = endpoint.format(**path_params)

        url = urljoin(self.base_url, endpoint)
        response = None
        try:
            log.debug(f"Req#{req_id}: Calling {method} {url} {params} type(data):{type(data)}")
            if data is not None:
                data = self.json_serializer.serialize_to_text(data)
                log.debug(f"Req#{req_id}: Serialized data: {data}")

            self.headers.update(self.refresh_authorization_header())
            match method:
                case "GET":
                    response = httpx.get(url, params=params, headers=self.headers)
                case "POST":
                    self.headers.update({"Accept": "application/json"})
                    response = httpx.post(url, params=params, data=data, headers=self.headers, timeout=timeout)
                case "PATCH":
                    response = httpx.patch(url, params=params, data=data, headers=self.headers)
                case "PUT":
                    response = httpx.put(url, params=params, data=data, headers=self.headers)
                case "DELETE":
                    response = httpx.delete(url, params=params, headers=self.headers)
                case _:
                    raise MosaicApiClientException(f"Unsupported HTTP method: {method}")

            if response:
                log.debug(f"Res#{req_id}: Response {response}")
                response.raise_for_status()

                # Check the Content-Type header
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    if response.text:
                        return response.json()
                else:
                    # Assuming it's a file download
                    return response

        except httpx.HTTPStatusError as e:
            raise MosaicApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(f"Req#{req_id}: HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}")
            else:
                log.debug(f"Req#{req_id}: NO RESPONSE")

    async def _call_api_async(self, method, endpoint, path_params=None, params=None, data=None, headers=None, timeout=10) -> Any:
        """
        TODO: Internal method to call the Mosaic API in Async mode

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The API endpoint to call.
            path_params (dict,optional): Path parameters for the request.
            params (dict, optional): Query parameters for the request.
            data (Any, optional): The data to send in the request body.
            headers (dict, optional): Additional headers to send with the request.

        Returns:
            Any: The response from the API call.

        Raises:
            MosaicSessionManagerApiClientException: If the API request fails.
        """
        req_id = str(uuid.uuid4())
        if not self.base_url:
            raise MosaicApiClientException(f"The base URL is not set.")

        if path_params is not None:
            endpoint = endpoint.format(**path_params)

        url = urljoin(self.base_url, endpoint)
        response = None
        try:
            log.debug(f"Req#{req_id}: Calling {method} {url} {params} type(data):{type(data)}")
            if data is not None:
                data = self.json_serializer.serialize_to_text(data)
                log.debug(f"Req#{req_id}: Serialized data: {data}")

            self.headers.update(self.refresh_authorization_header())
            match method:
                case "GET":
                    response = httpx.get(url, params=params, headers=self.headers)
                case "POST":
                    self.headers.update({"Accept": "application/json"})
                    response = httpx.post(url, params=params, data=data, headers=self.headers, timeout=timeout)
                case "PATCH":
                    response = httpx.patch(url, params=params, data=data, headers=self.headers)
                case "PUT":
                    response = httpx.put(url, params=params, data=data, headers=self.headers)
                case "DELETE":
                    response = httpx.delete(url, params=params, headers=self.headers)
                case _:
                    raise MosaicApiClientException(f"Unsupported HTTP method: {method}")

            if response:
                log.debug(f"Res#{req_id}: Response {response}")
                response.raise_for_status()

                # Check the Content-Type header
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    if response.text:
                        return response.json()
                else:
                    # Assuming it's a file download
                    return response

        except httpx.HTTPStatusError as e:
            raise MosaicApiClientException(f"API request failed: {e}") from e

        finally:
            if response:
                log.debug(f"Req#{req_id}: HTTP Status Code: {response.status_code}, Response Text: {response.text[:300]}")
            else:
                log.debug(f"Req#{req_id}: NO RESPONSE")

    # Pure API Wrappers
    def get_supported_packages(self):
        """
        Retrieves packages defined in Mosaic

        Returns list of Mosaic packages
        """
        try:
            response = self._call_api(method=self.endpoints["get_package_list"][0], endpoint=self.endpoints["get_package_list"][1])
            return response
        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to get_package_list: {ex}")
        return None

    def get_blueprint_by_id(self, blueprint_id: str) -> dict[str, Any]:
        """
        Retrieves Blueprint details by blueprint id

        Args:
        blueprintId - str, to be passed to path_params

        Returns a dict of the blueprint details:
        {
            "blueprintId": "string",
            "examId": "string",
            "id": "string",
            "nodes": [
                {
                "hierarchyLabel": "string",
                "id": "string",
                "level": 0,
                "nodes": [
                    null
                ],
                "parentNode": "string",
                "sequenceLabel": "string",
                "title": "string",
                "topicTitle": "string",
                "weight": 0
                }
            ],
            "revision": "string",
            "title": "string"
        }
        """
        path_params = {"blueprintId": blueprint_id}
        try:
            response = self._call_api(method=self.endpoints["get_blueprint_by_id"][0], endpoint=self.endpoints["get_blueprint_by_id"][1], path_params=path_params)
            if "nodes" in response:
                return response
            return {}
        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to get_blueprint_by_id({blueprint_id}): {ex}")
            raise IntegrationException(f"Error when trying to get_blueprint_by_id({blueprint_id}): {ex}")

    def get_blueprint_settings(self, module_id: str) -> dict[str, Any]:
        """
        Retrieves Blueprint settings for a given module

        Args:
        moduleId - str, to be passed to path_params

        Returns a dict of the blueprint setting.
        {
            "blueprintId": "string",
            "healthratio": 0,
            "isPoints": true,
            "itemStatusOrder": [
                {
                "healthStatusRef": true,
                "hidden": true,
                "itemStatus": "string"
                }
            ],
            "nodepoints": [
                {
                "nodeId": "string",
                "percentagePoints": 0,
                "points": 0
                }
            ],
            "totalScore": 0
        }
        """
        path_params = {"moduleId": module_id}
        try:
            response = self._call_api(method=self.endpoints["get_blueprint_settings"][0], endpoint=self.endpoints["get_blueprint_settings"][1], path_params=path_params)
            if "blueprintId" in response:
                return response
            return {}
        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to get_blueprint_settings: {ex}")
            raise IntegrationException(f"Error when trying to get_blueprint_settings: {ex}")

    def get_formset_settings(self, qualified_name: str) -> dict[str, Any]:
        """
        Retrieves formset settings for a given formset

        Args:
        formsetId - str, to be passed to path_params

        Returns a dict of the formset setting.

        """
        params = {"qualifiedName": qualified_name}
        try:
            response = self._call_api(method=self.endpoints["get_formset_settings"][0], endpoint=self.endpoints["get_formset_settings"][1], params=params)
            if not "formsetName" in response or not "recertQTISettings" in response:
                raise IntegrationException(f"get_formset_settings({qualified_name}) failed to return a valid response: {response}")
            return response
        except (IntegrationException, httpx.HTTPStatusError) as ex:
            log.error(f"Error when trying to get_formset_settings: {ex}")
            raise IntegrationException(f"Error when trying to get_formset_settings: {ex}")

    def get_formset_publishing_history(self, formset_id: str) -> list[Any]:
        """
        Get publishing history, given a Formset Id

        Args:
        formset_id - str,  to be passed to path_params

        Returns a list of published packages.
        """
        path_params = {"formsetId": formset_id}
        try:
            response = self._call_api(method=self.endpoints["get_publish_history"][0], endpoint=self.endpoints["get_publish_history"][1], path_params=path_params)
            if isinstance(response, list):
                return response
        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to get_publish_history: {ex}")
        return None

    def download_file_locally(self, fileId: str, full_local_file_name: str) -> bool:
        """
        Downloads the file with given fileId to provided local path.

        Args:
        fileId - str, required to pass to path_params
        local_file_path - Local path where the file needs to be downloaded.

        Return: True if the fileId was successfully downloaded locally, False otherwiser.
        """
        if " " in fileId:
            raise IntegrationException(f"Invalid fileId {fileId} !?")

        if not self._is_valid_path_and_not_existing_file(full_local_file_name):
            raise IntegrationException(f"Invalid Local file path {full_local_file_name} !?")

        path_params = {"fileId": fileId}
        try:
            response = self._call_api(method=self.endpoints["get_file_by_id"][0], endpoint=self.endpoints["get_file_by_id"][1], path_params=path_params)

            try:
                with open(full_local_file_name, "wb") as f:
                    f.write(response.content)
                log.info(f"Mosaic File {fileId} was successfully downloaded locally at {full_local_file_name}")
                return True

            except OSError as ex:
                log.error(f"Error writing file to {full_local_file_name}: {ex}")
                raise httpx.HTTPError(message=f"Error downloading file (write error): {ex}")

        except (httpx.HTTPError, httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as ex:
            log.error(f"Error when trying to get_file_by_id: {ex}")
            return False

    def download_formset_package_locally(self, published_record_id: str, full_local_file_name: str) -> bool:
        """
        Downloads a package with given publishedRecordId

        Args:
        published_record_id - str, the publishedRecordId to download.
        full_local_file_name: str The full local file_path where to download the package.

        Returns: True if the file was successfully downloaded.
        """
        path_params = {"publishedRecordId": published_record_id}
        try:
            response = self._call_api(method=self.endpoints["download_formset_package"][0], endpoint=self.endpoints["download_formset_package"][1], path_params=path_params)

            if "content" in dir(response):
                try:
                    with open(full_local_file_name, "wb") as f:
                        f.write(response.content)
                    log.info(f"File id {published_record_id} was successfully downloaded at {full_local_file_name}")
                except OSError as ex:
                    raise
            return True

        except (IntegrationException, httpx.HTTPStatusError, OSError) as ex:
            log.error(f"Error when trying to download_package: {ex}")
            raise IntegrationException(f"Error when trying to download_package: {ex}")

    def publish_formset_package(self, qualified_name: str, qti_id: str, layout_id: str) -> list[Any]:
        """
        Publish a formset in Mosaic.

        Args:
        formset_id - str,  to be passed to path_params
        qti_id - the QTI packageId
        layout_id - the Layout "QTI" id

        Returns a list of publish records generated for each package that was published.
        """
        params = {"qualifiedName": qualified_name}
        data = {"pkgLayouts": [{"layoutId": f"{layout_id}", "layoutName": "PVUE_Written", "pkgId": f"{qti_id}", "pkgName": "QTI", "langCode": "ENU"}]}
        try:
            response = self._call_api(method=self.endpoints["publish_formset_package"][0], endpoint=self.endpoints["publish_formset_package"][1], params=params, data=data)
            # TODO: Parse response!
            return response
        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to publish_formset_package: {ex}")
            raise IntegrationException(f"Error when trying to publish_formset_package: {ex}")

    # Custom Data Fetcher
    def get_all_items_of_formset(self, mosaic_ids: dict, all_items: bool = True, page_num: int = 0, page_size: int = 0, sort_asc: bool = True) -> list[Any]:
        """
        Retrieves all item(s) for an identified FormSet

        Args: data - Request body parameter in json format.

        Returns:  List of all item(s) matching
        """
        default_statuses = ["Draft", "Draft Completed", "Cog Comp Review", "Tech Review", "Grammar", "Field Test/SS", "Ready To Use", "Live", "Resting", "Retired", "Obsolete"]
        try:
            data_pull_search_items = {
                "allItems": all_items,
                "trackId": mosaic_ids["track_id"],
                "examId": mosaic_ids["exam_id"],
                "moduleId": mosaic_ids["module_id"],
                "filters": [
                    {"combinator": "and", "field": "Belongs to Formset", "values": [mosaic_ids["formset_id"]]},
                    {"combinator": "and", "field": "Item Status", "values": default_statuses},
                ],
                "pageNumber": page_num,
                "pageSize": page_size,
                "sortKey": "SHORTID",
                "sortOrder": "asc" if sort_asc else "desc",
            }
            response = self._call_api(method=self.endpoints["pull_search_items"][0], endpoint=self.endpoints["pull_search_items"][1], data=data_pull_search_items)

            if response and "resultItemIds" not in response:
                raise IntegrationException(f"pull_search_items returned no resultItemIds? input: {data_pull_search_items}")

            # TODO: return a specific Type!
            return response.get("resultItemIds", [])

        except httpx.HTTPStatusError as ex:
            log.error(f"Error when trying to pull_search_items: {ex}")
            raise IntegrationException(f"Error when trying to publish_formset_package: {ex}")

    def export_selected_items_by_module(self, module_id: str, item_ids: list[str]) -> str | None:
        """
        Export items related data from an Item Bank and returns the corresponding Mosaic URI.

        Args:
        module_id - str, required to pass to path_params
        item_ids: List[str] - The list of Item ID's to export.
        data - Request body parameter in json format.

        Returns:  The Mosaic URI for the exported file, if any.
        """
        path_params = {"moduleId": module_id}
        data_export_items_by_module = {"dataTypeChoices": ["default", "associations", "forms"], "itemIds": item_ids}
        try:
            response = self._call_api(method=self.endpoints["export_items_by_module"][0], endpoint=self.endpoints["export_items_by_module"][1], path_params=path_params, data=data_export_items_by_module)
            if "_links" not in response and "links" not in response:
                raise IntegrationException(f"no links was returned by Mosaic!?")

            if "_links" in response and len(response["_links"]):
                return response["_links"]["self"]["href"]
            elif "links" in response and len(response["links"]):
                return response["links"][0]["href"]

        except (httpx.HTTPStatusError, AttributeError, IndexError) as ex:
            log.error(f"Error when trying to export_items_by_module: {ex}")
        return None

    def get_package_layout_ids(self, package_name: str = "QTI", layout_name: str = "PVUE_Written") -> tuple[str, str]:
        """
        Retrieves the package ID and layout ID for the 'QTI' package with the 'PVUE_Written' layout.

        Returns:
            tuple (pkg_id, layout_id) : A tuple containing the package ID (str) and layout ID (str).
        """
        package_list = self.get_supported_packages()
        if not package_list:
            raise IntegrationException(f"Could not pull the list of packages from mosaic!?")

        pkg_id = ""
        layout_id = ""

        for pkg in package_list:
            if pkg["name"] == package_name:
                pkg_id = pkg.get("id", "")
                for layout in pkg.get("layouts", []):
                    if layout["name"] == layout_name:
                        layout_id = layout.get("id", "")
                        break
            if pkg_id and layout_id:
                break

        log.info(f"The package_name {package_name}.id={pkg_id}. Layout {layout_name}id={layout_id}")
        return pkg_id, layout_id

    def get_package_id_after_auto_publish(self, qualified_name) -> str:
        """
        Publishes a package in Mosaic for a given formset and retrieves
        the package ID.

        Args:
            formset_id (str): The ID of the formset for which to publish
            the package.

        Returns:
            str: The ID of the published package.
        """
        package_name = "QTI"
        layout_name = "PVUE_Written"
        qualified_name = qualified_name[:-2]
        log.info(f"Fetching the package {package_name} id and layout {layout_name} id for the formset {qualified_name}")
        qti_id, layout_id = self.get_package_layout_ids(package_name, layout_name)
        package = self.publish_formset_package(qualified_name=qualified_name, qti_id=qti_id, layout_id=layout_id)
        if package:
            package_id = package[0].get("id", "")
            log.info(f"Published the package for the formset id {qualified_name}" f"The package id is {package_id}")
            return package_id
        raise IntegrationException(f"Failed to get_package_id_from_publish_package({qualified_name}!?")

    def get_package_id_from_publish_history(self, formset_id: str):
        """
        Fetches the most recently published package ID from the publish
        history of a given formset.

        Args:
            formset_id (str): The ID of the formset for which to retrieve
            the publish history.

        Returns:
            str: The ID of the most recently published package.
        """
        # Fetch the recently published package from the package history.
        packages = self.get_formset_publishing_history(formset_id)
        package_id = None
        if packages != []:
            for package in packages:
                if package["layoutName"] == "PVUE_Written" and package["mosaicPkgName"] == "QTI":
                    package_id = package.get("id", "")
                    break

        if not package_id:
            raise ApplicationException(f"For the formset {formset_id}, couldnt find any QTI published package having PVUE Written Layout. Consider publishing the package before generating the report")

        log.info(f"Using the package that is already published." f"The package id is {package_id}")
        return package_id

    def get_package_file_path(self, package_id):
        """
        Downloads a package file from Mosaic to the local container
        and returns its file path.

        Args:
            package_id (str): The ID of the package to be downloaded.

        Returns:
            str: The local file path of the downloaded package.
        """
        # Download the package file from Mosaic to local container.
        log.info(f"Attempting to download the package file with id {package_id}")

        # local_file_path = self.local_fs_mgr.get_file_path(package_id)
        local_file_path = f"/app/tmp/{package_id}.zip"
        self.download_formset_package_locally(package_id, local_file_path)

        return local_file_path

    # Private/Utils functions
    def _is_valid_path_and_not_existing_file(self, filename: str) -> bool:
        """
        Checks if the provided filename represents a valid path with existing directories
        and the file itself doesn't exist in the last folder.

        Args:
            filename (str): The filename string to check.

        Returns:
            bool: True if the path is valid and the file doesn't exist, False otherwise.
        """
        if not filename:
            return False  # Empty filename is not valid

        # Split the filename to get the directory path and actual filename
        directory, filename = os.path.split(filename)

        # Check if the directory path exists
        if not os.path.exists(directory):
            return False  # Path doesn't exist

        # Check if the file exists (using join to ensure path construction)
        full_path = os.path.join(directory, filename)
        return not os.path.exists(full_path)

    @staticmethod
    def configure(builder: ApplicationBuilderBase):
        builder.services.try_add_singleton(JsonSerializer)
        builder.services.try_add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        builder.services.try_add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        builder.services.try_add_singleton(MosaicApiClientOAuthOptions, singleton=MosaicApiClientOAuthOptions(**builder.settings.mosaic_oauth_client))
