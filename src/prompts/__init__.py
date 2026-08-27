"""
Prompts module — Product Catalog Agent
System prompts e templates para o agente Maria.
"""

from src.prompts.system_prompt import (
    SYSTEM_PROMPT,
    build_system_prompt,
    get_out_of_scope_response,
    get_product_not_found_response,
    get_store_info,
)

__all__ = [
    "SYSTEM_PROMPT",
    "build_system_prompt",
    "get_out_of_scope_response",
    "get_product_not_found_response",
    "get_store_info",
]
