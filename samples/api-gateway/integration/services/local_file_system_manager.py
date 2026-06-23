import base64
import json
import logging
import os
from pathlib import Path
import shutil
import typing
import zipfile

from neuroglia.hosting.abstractions import ApplicationBuilderBase
from pydantic import BaseModel

from integration.exceptions import IntegrationException
import httpx

log = logging.getLogger(__name__)


class LocalFileSystemManagerSettings(BaseModel):
    tmp_path: str


class LocalFileSystemManager:
    def __init__(self, settings: LocalFileSystemManagerSettings):
        self.tmp_path = settings.tmp_path

    def try_create_folder(self, path) -> bool:
        """
        Creates a folder at the specified path if it doesn't already exist.

        Args:
            path (str): The path of the folder to create.

        Raises:
            Exception: If folder creation fails.

        """
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as e:
                logging.error(f"Couldnt create the folder: {e}")
                raise IntegrationException(f"Couldnt create the folder: {e}")
        return os.path.exists(path)

    def get_file_path(self, file_name) -> str:
        """
        Retrieves the file path within the temporary directory.

        Args:
            file_name (str): The name of the file.

        Returns:
            str: The full file path within the temporary directory.
        """
        if self.try_create_folder(self.tmp_path):
            return os.path.join(self.tmp_path, file_name)
        else:
            raise IntegrationException(f"get_file_path({file_name}) failed!?")

    async def download_file(self, file_url: str, file_name: str, headers: dict[str, str] = {}) -> str:
        """
        Downloads a file from a specified URL and saves it to the temporary directory.

        Args:
            file_url (str): The URL of the file to download.
            file_name (str): The name of the file to save.
            headers (dict[str, str], optional): The headers to include in the request. Defaults to {}.

        Returns:
            str: The full file path of the downloaded file.
        """
        log.info(f"Downloading file from {file_url} to {file_name}")
        file_path = self.get_file_path(file_name)
        try:

            async with httpx.AsyncClient() as client:
                response = await client.get(file_url, headers=headers)

                response.raise_for_status()

                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

            log.debug(f"File downloaded to {file_path}")

            return file_path

        except Exception as e:
            log.error(f"Failed to download file from {file_url}: {e}")
            raise IntegrationException(f"Failed to download file from {file_url}: {e}")

    def delete_file(self, local_file_path: str) -> bool:
        """
        Deletes the specified file if it exists.

        Args:
            path (str): The path to the directory to clean up.
        """
        try:
            full_file_path = self.get_file_path(local_file_path)
            if os.path.exists(self.tmp_path) and os.path.isfile(full_file_path):
                os.remove(full_file_path)
                return True
            return False
        except Exception as e:
            raise IntegrationException(f"Exception when deleting {local_file_path}: {e}")

    def clean_up(self):
        """
        Cleans up the specified directory by deleting all files and
        subdirectories.

        Args:
            path (str): The path to the directory to clean up.
        """
        n = 0
        if os.path.exists(self.tmp_path):
            for root, dirs, files in os.walk(self.tmp_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)
                    n += 1
                    # log.debug(f"Deleted file: {file_path}")
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)
                    n += 1
                    # log.debug(f"Deleted directory: {dir_path}")
            log.debug(f"Cleanup of {self.tmp_path} completed: deleted {n} items.")
        else:
            log.debug(f"The directory {self.tmp_path} does not exist.")

    def unzip_file(self, extract_folder_name, zip_file_path):
        """
        Extracts contents from a zip file to a specified folder.

        Args:
            extract_folder (str): The name of the folder to extract the contents into.
            zip_file_path (str): The file path of the zip file to be extracted.

        Returns:
            str: The directory path where the contents were extracted.
        """
        extract_dir = os.path.join(self.tmp_path, extract_folder_name)

        # Ensure the extraction directory exists
        if not os.path.exists(extract_dir):
            try:
                os.makedirs(extract_dir, exist_ok=True)
            except OSError as e:
                logging.error(f"Couldnt create the extract_folder {extract_dir}: {e}")
                raise IntegrationException(f"Couldnt create the extract_folder {extract_dir}: {e}")

        # Open the zip file and extract its contents
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        log.debug(f"Contents of the zip file extracted to {extract_dir}")

        # List the contents of the base path directory
        contents = os.listdir(extract_dir)

        if len(contents) > 1:
            raise ValueError(f"Expecting only one folder. Found {len(contents)}. Please check the downloaded QTI package again.")
        else:
            item = contents[0]
            item_path = os.path.join(extract_dir, item)
            if os.path.isdir(item_path):
                return item_path
            raise Exception("There seems to be an issue with the Downloaded QTI Package.")

    def read_secret(
        self,
        secret_name: str,
        top_level_key: str | None = None,
        local_dev: bool = False,
    ) -> typing.Dict[str, typing.Dict[str, str]]:
        """
        Reads a secret from a specified secret file.

        Args:
            secret_name (str): The name of the secret file.
            top_level_key (str | None, optional): The top-level key to
            retrieve from the secret JSON data. Defaults to None.
            local_dev (bool, optional): Flag indicating if running in local
            development mode. Defaults to False.

        Returns:
            dict: The secret data as a dictionary. If top_level_key is
            provided, returns a nested dictionary with the specified key.
        """
        secret_filename = ""
        secret = {}
        if local_dev:
            # Docker Desktop mounts secrets in /run/secrets/secret_name
            secret_filename = f"/run/secrets/{secret_name}"
            try:
                log.debug(f"Reading secret {secret_name} from {secret_filename}")
                with open(secret_filename, "r") as secret_file:
                    secret_data = secret_file.read()
                    decoded_data = base64.b64decode(secret_data)
                    secret = json.loads(decoded_data)
                if top_level_key in secret:
                    return secret[top_level_key]
                return secret
            except Exception as e:
                log.error(e)
        else:
            # OpenFaas mounts secrets as JSON files in /run/secrets/secret_name
            secret_filename = f"/run/secrets/secret-volume/{secret_name.split('.')[0]}/{secret_name}"
            log.debug(f"Reading secret {secret_name} from {secret_filename}")
            try:
                with open(secret_filename, "r") as secret_file:
                    secret_data = secret_file.read()
                    decoded_data = base64.b64decode(secret_data)
                    secret = json.loads(decoded_data)
                if top_level_key in secret:
                    return secret[top_level_key]
                return secret
            except Exception as e:
                log.error(e)
        return secret

    def get_file_size(self, file_path: Path, human_readable: bool = True) -> int | str:
        """Get the size of a file."""
        try:
            file_stats = file_path.stat()
            file_size = file_stats.st_size
            if human_readable:
                return self.get_human_readable_file_size(file_size)
            return file_size  # "File size: {file_size} bytes")
        except FileNotFoundError:
            # raise ApplicationException(f"File not found: {file_path}")
            return 0
        except OSError as e:  # Handle other potential errors
            # raise ApplicationException(f"Error accessing file: {e}")
            return 0

    def get_human_readable_file_size(self, size_bytes):
        import math

        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    @staticmethod
    def configure(builder: ApplicationBuilderBase):
        builder.services.try_add_singleton(LocalFileSystemManagerSettings, singleton=LocalFileSystemManagerSettings(tmp_path=builder.settings.tmp_path))
        builder.services.try_add_scoped(LocalFileSystemManager, implementation_type=LocalFileSystemManager)
