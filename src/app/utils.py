import hashlib
import hmac
import logging
import sys


# --- Logger ---

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


# --- HMAC signature validator (Meta webhook) ---

def verify_meta_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
    """Validates the X-Hub-Signature-256 header sent by Meta."""
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)
