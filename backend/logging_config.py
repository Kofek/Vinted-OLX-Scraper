import logging
import os

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


class HeaderThenMessageFormatter(logging.Formatter):
        def format(self, record):
        timestamp_text  = self.formatTime(record, self.datefmt)
        header = f"{timestamp_text } | {record.levelname:8s} | {record.name}"
        body = record.getMessage()
        out = f"{header}\n{body}"
        if record.exc_info:
            out += "\n" + self.formatException(record.exc_info)
        return out 


def configure_logging(level=None):
    log_level = (level or os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()

    root = logging.getLogger()
    try:
        root.setLevel(log_level)
    except ValueError:
        log_level = DEFAULT_LOG_LEVEL
        root.setLevel(log_level)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)

    if root.handlers:
        for handler in root.handlers:
            handler.setLevel(log_level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(HeaderThenMessageFormatter(datefmt=DEFAULT_DATEFMT))
    root.addHandler(handler)
