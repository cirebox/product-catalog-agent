"""Structured output models for agent responses."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Structured result from a domain agent execution."""

    response: str = ""
    action_result: Optional[Dict[str, Any]] = None
    action_error: Optional[str] = None
    pending_intent: Optional[str] = None
    pending_entities: Dict[str, Any] = Field(default_factory=dict)
    extra_state: Dict[str, Any] = Field(default_factory=dict)

    def to_state_update(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Merge this result into a LangGraph state dict."""
        update = dict(state)
        if self.response:
            update["response"] = self.response
        if self.action_result is not None:
            update["action_result"] = self.action_result
        if self.action_error is not None:
            update["action_error"] = self.action_error
        update["pending_intent"] = self.pending_intent
        update["pending_entities"] = self.pending_entities
        update.update(self.extra_state)
        return update
