import datetime
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from minio import Minio
from neuroglia.hosting.abstractions import ApplicationBuilderBase

from integration.exceptions import IntegrationException

log = logging.getLogger("__name__")


class ObjectStorage(ABC):
    """Defines the fundamentals of a ObjectStorage"""

    @abstractmethod
    def store(self, bucket_name: str, src_filepath: str, dst_filename: str) -> bool:
        """Pushes the file from src to Object Storage bucket."""
        raise NotImplementedError()

    @abstractmethod
    def create_bucket(self, bucket_name: str):
        """Creates the bucket in the Object Storage."""
        raise NotImplementedError()

    @abstractmethod
    def get_public_url(self, bucket_name: str, filename: str):
        """Creates a pre-signed url for an object in the Bucket."""
        raise NotImplementedError()


@dataclass
class S3ClientOptions:
    endpoint: str

    access_key: str

    secret_key: str

    secure: bool


class MinioStorageManager(ObjectStorage):
    """Represents a MinIo implementation of the ObjectStorage Interface."""

    _minio_client: Minio
    """Gets the MinIO client"""

    def __init__(self, minio_client: Minio):
        self._minio_client = minio_client

    def list_bukets(self):
        """Lists all the buckets in the MinIO instance."""
        return self._minio_client.list_buckets()
    
    def list_objects(self, bucket_name: str):
        """Lists all the objects in the bucket."""
        try:
            # Check if the bucket exists
            if not self._minio_client.bucket_exists(bucket_name):
                log.info(f"The bucket {bucket_name} does not exist.")
                return False
            return self._minio_client.list_objects(bucket_name)
        except Exception as err:
            log.info(f"Error listing objects: {err}")
            return False

    def get_object(self, bucket_name: str, object_filename: str):
        """
        Downloads an object from the specified MinIO bucket and saves it to a local file.

        Args:
            bucket_name (str): The name of the MinIO bucket.
            local_filename (str): The local filename to save the downloaded object.

        Returns:
            bool: True if the download is successful, False otherwise.
        """
        try:
            # Check if the bucket exists
            if not self._minio_client.bucket_exists(bucket_name):
                log.info(f"The bucket {bucket_name} does not exist.")
                return False

            # Download the object from the bucket
            self._minio_client.fget_object(bucket_name, object_filename, object_filename)
            log.info(f"Successfully downloaded object '{bucket_name}/{object_filename}'")
            return True
        except Exception as err:
            log.info(f"Error downloading object: {err}")
            return False

    def store(self, bucket_name: str, src_filepath: str, dst_filename: str) -> bool:
        """
        Uploads a file from a source filepath to a specified MinIO bucket.

        Args:
            bucket_name (str): The name of the MinIO bucket.
            dst_filename (str): The filename to use in the MinIO bucket.
            src_filepath (str): The local filepath of the file to upload.

        Returns:
            bool: True if the upload is successful, False otherwise.
        """
        # Check if the bucket exists
        if not self._minio_client.bucket_exists(bucket_name):
            log.info("The bucket {bucket_name} was not found so it will be created.")
            self.create_bucket(bucket_name)

        # Upload the file to bucket
        try:
            res = self._minio_client.fput_object(bucket_name, dst_filename, src_filepath)
            if "bucket_name" in dir(res) and "object_name" in dir(res):
                log.info(f"Successfully uploaded as object '{bucket_name}/{dst_filename}'")
                return True
            raise IntegrationException(f"store: _minio_client.fput_object({bucket_name}, {dst_filename}, {src_filepath}) returned something weird: {res}")
        except Exception as err:
            log.info(f"Error pushing object: {err}")
            return False

    def create_bucket(self, bucket_name: str):
        """
        Creates a new bucket with the specified name in MinIO.

        Args:
            bucket_name (str): The name of the bucket to create.

        Raises:
            Exception: If bucket creation fails.
        """
        try:
            self._minio_client.make_bucket(bucket_name)
            log.info(f"Created a bucket {bucket_name}")
        except Exception as err:
            raise Exception(f"Couldnt create {bucket_name} because of the error {err}")

    def get_public_url(self, bucket_name: str, filename: str, expires: datetime.timedelta = datetime.timedelta(days=7)) -> str:
        """
        Generates a presigned URL for accessing an object in a MinIO bucket.

        Args:
            bucket_name (str): The name of the MinIO bucket.
            filename (str): The name of the file in the bucket.
            expires (datetime.timedelta): The duration until the URL expires. (e.g. timedelta(minutes=5), timedelta(days=30)... )

        Returns:
            str: The presigned URL for the file (with default expiry of 7d.)

        Raises:
            Exception: If generating the presigned URL fails.
        """
        try:
            log.info(f"Getting the presigned url for the file {filename} in " f"{bucket_name} bucket.")
            url = self._minio_client.presigned_get_object(bucket_name, filename, expires)
            return url
        except Exception as err:
            raise IntegrationException(f"Couldnt generate the presigned url because of {err}")

    @staticmethod
    def configure(builder: ApplicationBuilderBase):
        builder.services.try_add_singleton(
            S3ClientOptions,
            singleton=S3ClientOptions(endpoint=builder.settings.s3_endpoint, access_key=builder.settings.s3_access_key, secret_key=builder.settings.s3_secret_key, secure=builder.settings.s3_secure),  # , session_token=builder.settings.s3_session_token)  # , region=builder.settings.s3_region)
        )
        builder.services.try_add_scoped(Minio, implementation_factory=lambda provider: Minio(**provider.get_required_service(S3ClientOptions).__dict__))
        builder.services.try_add_scoped(MinioStorageManager, implementation_factory=lambda provider: MinioStorageManager(provider.get_required_service(Minio)))
        builder.services.try_add_scoped(ObjectStorage, implementation_factory=lambda provider: MinioStorageManager(provider.get_required_service(MinioStorageManager)))
