"""Base class for deterministic domain agents."""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from ..infrastructure.errors import ErrorCode
from .models import AgentResult

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base agent with common dispatch and error handling logic.

    Subclasses should override `_handlers` to map intents to handler methods.
    """

    def __init__(self, mcp=None) -> None:
        self._mcp = mcp

    @property
    def _handlers(self) -> Dict[str, Callable]:
        """Map of intent → handler method. Override in subclasses."""
        return {}

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the correct handler based on intent."""
        intent = state.get("intent", "unknown")
        handler = self._handlers.get(intent)
        if not handler:
            return AgentResult(
                action_error=f"{type(self).__name__}: unknown intent '{intent}'"
            ).to_state_update(state)
        result = handler(state)
        if isinstance(result, AgentResult):
            return result.to_state_update(state)
        return result

    def _safe_mcp_call(
        self,
        state: Dict[str, Any],
        fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Any, Optional[AgentResult]]:
        """Call an MCP method with standardized error handling.

        Returns:
            (result, None) on success
            (None, AgentResult) on failure
        """
        try:
            result = fn(*args, **kwargs)
            return result, None
        except Exception as e:
            fn_name = getattr(fn, "__name__", repr(fn))
            logger.error("%s failed: %s", fn_name, e)
            return None, AgentResult(action_error=ErrorCode.GENERIC)
