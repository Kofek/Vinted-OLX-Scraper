import logging
import os

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level=None):
    name = (level or os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()

    root = logging.getLogger()
    try:
        root.setLevel(name)
    except ValueError:
        name = DEFAULT_LOG_LEVEL
        root.setLevel(name)

    if root.handlers:
        for handler in root.handlers:
            handler.setLevel(name)
        return

    logging.basicConfig(
        level=name,
        format=DEFAULT_FORMAT,
        datefmt=DEFAULT_DATEFMT,
    )
