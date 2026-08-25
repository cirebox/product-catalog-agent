"""Structured error codes for agent responses."""

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes used by agents — string-compatible for backward compat."""

    USER_NOT_FOUND = "user_not_found"
    MCP_ERROR = "mcp_error"
    TIMEOUT = "timeout"
    GENERIC = "error"
