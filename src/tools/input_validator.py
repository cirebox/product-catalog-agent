"""Input validation and sanitization utilities."""

import re
from typing import Optional

# Control characters except common whitespace
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Brazilian phone: 10-13 digits (with or without country code)
_PHONE_RE = re.compile(r"^\d{10,13}$")


def sanitize_message(message: str, max_length: int = 2000) -> str:
    """Strip, limit length, and remove control characters."""
    message = message.strip()
    message = _CONTROL_RE.sub("", message)
    if len(message) > max_length:
        message = message[:max_length]
    return message


def validate_phone(phone: str) -> Optional[str]:
    """Validate and normalize a Brazilian phone number.

    Returns digits-only string if valid (10-13 digits), or None if invalid.
    """
    digits = re.sub(r"\D", "", phone)
    if _PHONE_RE.match(digits):
        return digits
    return None
