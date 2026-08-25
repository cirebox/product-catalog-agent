"""
Custom state reducers for LangGraph.

Reducers define *how* each field in the graph state is updated
when a node returns a partial dict.
"""

from typing import Any, Dict, List


def add_messages(current: list, update: list) -> list:
    """Reducer that appends new messages to existing list."""
    if not isinstance(update, list):
        update = [update]
    return current + update


def add_agent_outputs(current: list, update: list) -> list:
    """Reducer for agent outputs — append new outputs."""
    if not isinstance(update, list):
        update = [update]
    return current + update


def update_supervisor_decision(current: str, update: str) -> str:
    """Reducer for supervisor decision — last write wins."""
    return update
