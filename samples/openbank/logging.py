import logging
# import sys


# def configure_simplest_logging():
#     logging.basicConfig(filename='logs/openbank.log', format='%(asctime)s %(levelname)-8s %(message)s', encoding='utf-8', level=logging.DEBUG)
#     console_handler = logging.StreamHandler(sys.stdout)
#     console_handler.setLevel(logging.DEBUG)
#     log = logging.getLogger(__name__)
#     log.addHandler(console_handler)


# def configure_logging_from_config(config_path: str):
#     # config_path = "logging.conf"
#     logging.config.fileConfig(config_path, disable_existing_loggers=True)


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname) - 8s %(name)s:%(lineno)d %(message)s"
DEFAULT_LOG_FILENAME = "logs/debug.log"
DEFAULT_LOG_LEVEL = "DEBUG"


def configure_logging(log_level: str = DEFAULT_LOG_LEVEL, log_format: str = DEFAULT_LOG_FORMAT, console: bool = True, file: bool = True, filename: str = DEFAULT_LOG_FILENAME, ):

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    formatter = logging.Formatter(log_format)
    _configure_console_based_logging(root_logger, log_level, formatter) if console else None
    _configure_file_based_logging(root_logger, log_level, formatter, filename) if file else None

    for lib_name in ['asyncio', 'httpx', 'httpcore']:
        logging.getLogger(lib_name).setLevel("WARN")


def _configure_console_based_logging(root_logger, log_level, formatter):
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def _configure_file_based_logging(root_logger, log_level, formatter, filename):
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
