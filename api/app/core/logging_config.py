import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Include any extra fields passed via logger.info(..., extra={...})
        skip = logging.LogRecord.__dict__.keys() | {
            "message", "asctime", "args", "exc_info", "exc_text", "stack_info",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "process", "processName", "pathname", "filename", "module",
            "funcName", "lineno", "levelno", "name",
        }
        for key, val in record.__dict__.items():
            if key not in skip:
                entry[key] = val
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Reduce noise from third-party libs
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
