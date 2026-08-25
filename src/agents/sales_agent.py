"""
Sales Agent — Product Catalog Agent
Agente especializado em vendas e pedidos.
"""

from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService


class SalesAgent(BaseAgent):
    """Agente de vendas: pedidos, entregas, compras."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        super().__init__(
            name="sales",
            description="Agente de vendas e pedidos",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem do domínio de vendas."""

        if intent == Intent.ORDER_STATUS:
            return await self._order_status(message, context)
        elif intent == Intent.TRACK_DELIVERY:
            return await self._track_delivery(message, context)
        elif intent == Intent.NEW_ORDER:
            return await self._new_order(message, context)
        else:
            return format_response(Intent.UNKNOWN)

    async def _order_status(self, message: str, context: dict) -> str:
        """Verifica status do pedido."""
        return format_response(Intent.ORDER_STATUS)

    async def _track_delivery(self, message: str, context: dict) -> str:
        """Rastreia entrega."""
        context_rag = self.rag_service.get_relevant_context(
            "entrega frete prazo", k=3
        )
        return format_response(Intent.TRACK_DELIVERY, context_rag)

    async def _new_order(self, message: str, context: dict) -> str:
        """Ajuda a montar novo pedido."""
        return format_response(Intent.NEW_ORDER)
