import logging
import os
import typing

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname) - 8s %(name)s:%(lineno)d %(message)s"
DEFAULT_LOG_FILENAME = "logs/debug.log"
DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LOG_LIBRARIES_LIST = ["asyncio", "httpx", "httpcore", "pymongo"]
DEFAULT_LOG_LIBRARIES_LEVEL = "WARN"


def configure_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    log_format: str = DEFAULT_LOG_FORMAT,
    console: bool = True,
    file: bool = True,
    filename: str = DEFAULT_LOG_FILENAME,
    lib_list: typing.List = DEFAULT_LOG_LIBRARIES_LIST,
    lib_level: str = DEFAULT_LOG_LIBRARIES_LEVEL,
):
    """Configures the root logger with the given format and handler(s).
       Optionally, the log level for some libraries may be customized separately
       (which is interesting when setting a log level DEBUG on root but not wishing to see debugs for all libs).

    Args:
        log_level (str, optional): The log_level for the root logger. Defaults to DEFAULT_LOG_LEVEL.
        log_format (str, optional): The format of the log records. Defaults to DEFAULT_LOG_FORMAT.
        console (bool, optional): Whether to enable the console handler. Defaults to True.
        file (bool, optional): Whether to enable the file-based handler. Defaults to True.
        filename (str, optional): If file-based handler is enabled, this will set the filename of the log file. Defaults to DEFAULT_LOG_FILENAME.
        lib_list (typing.List, optional): List of libraries/packages name. Defaults to DEFAULT_LOG_LIBRARIES_LIST.
        lib_level (str, optional): The separate log level for the libraries included in the lib_list. Defaults to DEFAULT_LOG_LIBRARIES_LEVEL.
    """
    # Ensure log_level is uppercase for consistency
    log_level = log_level.upper()
    lib_level = lib_level.upper()

    # Get root logger and clear any existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Set the root logger level
    root_logger.setLevel(log_level)
    formatter = logging.Formatter(log_format)

    if console:
        _configure_console_based_logging(root_logger, log_level, formatter)
    if file:
        _configure_file_based_logging(root_logger, log_level, formatter, filename)

    # Configure library-specific log levels
    for lib_name in lib_list:
        logging.getLogger(lib_name).setLevel(lib_level)

    # Ensure uvicorn loggers respect the root log level
    uvicorn_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    for logger_name in uvicorn_loggers:
        logging.getLogger(logger_name).setLevel(log_level)


def _configure_console_based_logging(root_logger, log_level, formatter):
    console_handler = logging.StreamHandler()
    handler = _configure_handler(console_handler, log_level, formatter)
    root_logger.addHandler(handler)


def _configure_file_based_logging(root_logger, log_level, formatter, filename):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Check if the file exists, if not, create it
    if not os.path.isfile(filename):
        with open(filename, "w"):  # This will create the file if it does not exist
            pass

    file_handler = logging.FileHandler(filename)
    handler = _configure_handler(file_handler, log_level, formatter)
    root_logger.addHandler(handler)


def _configure_handler(handler: logging.StreamHandler, log_level, formatter) -> logging.StreamHandler:
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    return handler
