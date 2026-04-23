import logging
import sys
import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or str(uuid.uuid4())[:8]
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(correlation_id)s | %(name)s | %(message)s"
        ))
        handler.addFilter(_CorrelationFilter())
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
