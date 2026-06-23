from pathlib import Path


def get_file_size(file_path: Path) -> int:
    """Get the size of a file."""
    try:
        file_stats = file_path.stat()
        file_size = file_stats.st_size
        return file_size  # "File size: {file_size} bytes")
    except FileNotFoundError:
        # raise ApplicationException(f"File not found: {file_path}")
        return 0
    except OSError as e:  # Handle other potential errors
        # raise ApplicationException(f"Error accessing file: {e}")
        return 0


def get_human_readable_file_size(size_bytes):
    import math

    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
