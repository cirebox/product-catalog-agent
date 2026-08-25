"""
General Agent — Product Catalog Agent
Agente para saudações e ajuda geral.
"""

from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService


class GeneralAgent(BaseAgent):
    """Agente geral: saudações, ajuda, fallback."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        super().__init__(
            name="general",
            description="Agente geral para saudações e ajuda",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem geral."""

        if intent == Intent.GREETING:
            return format_response(Intent.GREETING)
        elif intent == Intent.HELP:
            return format_response(Intent.HELP)
        else:
            return format_response(Intent.UNKNOWN)
