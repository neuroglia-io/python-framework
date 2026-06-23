import re
from typing import Tuple


def validate_bucket_name(bucket_name) -> Tuple[bool, str]:
    """
    Validates an S3/MinIO bucket name according to AWS/MinIO rules.

    Args:
        bucket_name: The bucket name string to validate.

    Returns:
        True if the bucket name is valid, False otherwise.  Also returns a
        string with an error message if the name is invalid.
    """

    if not (2 <= len(bucket_name) <= 63):
        return False, "Bucket name must be between 2 and 63 characters long."

    if not re.match(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", bucket_name):
        return False, "Bucket name must start and end with a letter or number and can contain only lowercase letters, numbers, dots, and hyphens."

    if ".." in bucket_name or ".-" in bucket_name or "-." in bucket_name:
        return False, "Bucket name cannot contain consecutive periods, a period followed by a hyphen, or a hyphen followed by a period."

    # Optional: Check for IP address format (less common for bucket names)
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", bucket_name):
        return False, "Bucket name cannot be in IP address format."

    return True, ""  # Valid bucket name


# Example usage
# bucket_names_to_test = [
#     "my-valid-bucket",
#     "invalid-bucket-name-too-long-123456789012345678901234567890123",
#     "MyBucket",  # Uppercase
#     "invalid_bucket",  # Underscore
#     "invalid..bucket",  # Consecutive periods
#     "invalid-.bucket",  # Hyphen and period
#     "invalid.-bucket",  # Period and hyphen
#     "192.168.1.1",  # IP Address
#     "valid.bucket.name",
#     "bucket-with-numbers-123",
#     "starts-with-number",
#     "ends-with-number1",
#     "bucket.name.with.dots",
# ]

# for name in bucket_names_to_test:
#     is_valid, error_message = validate_bucket_name(name)
#     print(f"'{name}': Valid? {is_valid}")
#     if not is_valid:
#         print(f"  Error: {error_message}")
