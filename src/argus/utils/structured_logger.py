"""Simple structured JSON logger used by ARGUS services.

Provides get_logger(name) which returns a configured logger that emits
JSON objects on each log line for easier ingestion by logging systems.
"""

import json
import logging
import sys
from datetime import UTC, datetime

# Attributes every LogRecord has. Anything else was passed through `extra=`.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        # logging stores `extra=` fields as record attributes, not under a single key.
        payload.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS})
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_logger(name: str):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
