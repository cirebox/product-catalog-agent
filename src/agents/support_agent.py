"""
Support Agent — Product Catalog Agent
Agente especializado em suporte ao cliente.
"""

from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService


class SupportAgent(BaseAgent):
    """Agente de suporte: trocas, devoluções, reclamações."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        super().__init__(
            name="support",
            description="Agente de suporte ao cliente",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem do domínio de suporte."""

        if intent == Intent.RETURN_POLICY:
            return await self._return_policy(message, context)
        elif intent == Intent.EXCHANGE:
            return await self._exchange(message, context)
        elif intent == Intent.COMPLAINT:
            return await self._complaint(message, context)
        else:
            return format_response(Intent.UNKNOWN)

    async def _return_policy(self, message: str, context: dict) -> str:
        """Retorna política de devolução."""
        context_rag = self.rag_service.get_relevant_context(
            "devolução reembolso política", k=3
        )
        return format_response(Intent.RETURN_POLICY, context_rag)

    async def _exchange(self, message: str, context: dict) -> str:
        """Processa solicitação de troca."""
        context_rag = self.rag_service.get_relevant_context(
            "troca tamanho errado", k=3
        )
        return format_response(Intent.EXCHANGE, context_rag)

    async def _complaint(self, message: str, context: dict) -> str:
        """Processa reclamação do cliente."""
        return format_response(Intent.COMPLAINT)
