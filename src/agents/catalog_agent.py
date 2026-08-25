"""
Catalog Agent — Product Catalog Agent
Agente especializado em informações de produtos de lingerie.
"""

from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService


class CatalogAgent(BaseAgent):
    """Agente de catálogo: produtos, preços, estoque, medidas."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        super().__init__(
            name="catalog",
            description="Agente de catálogo de produtos de lingerie",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem do domínio de catálogo."""

        if intent == Intent.PRODUCT_INFO:
            return await self._product_info(message, context)
        elif intent == Intent.PRICING:
            return await self._pricing(message, context)
        elif intent == Intent.STOCK_CHECK:
            return await self._stock_check(message, context)
        elif intent == Intent.SIZE_GUIDE:
            return await self._size_guide(message, context)
        elif intent == Intent.RECOMMENDATION:
            return await self._recommendation(message, context)
        else:
            return format_response(Intent.UNKNOWN)

    async def _product_info(self, message: str, context: dict) -> str:
        """Busca informações do produto via RAG."""
        context_rag = self.rag_service.get_relevant_context(message, k=3)
        return format_response(Intent.PRODUCT_INFO, context_rag)

    async def _pricing(self, message: str, context: dict) -> str:
        """Busca preço do produto via RAG."""
        context_rag = self.rag_service.get_relevant_context(message, k=3)
        return format_response(Intent.PRICING, context_rag)

    async def _stock_check(self, message: str, context: dict) -> str:
        """Verifica estoque do produto via RAG."""
        context_rag = self.rag_service.get_relevant_context(message, k=3)
        return format_response(Intent.STOCK_CHECK, context_rag)

    async def _size_guide(self, message: str, context: dict) -> str:
        """Retorna guia de medidas."""
        context_rag = self.rag_service.get_relevant_context(
            "tamanho medida tabela", k=3
        )
        return format_response(Intent.SIZE_GUIDE, context_rag)

    async def _recommendation(self, message: str, context: dict) -> str:
        """Recomenda produtos baseado na preferência do usuário."""
        context_rag = self.rag_service.get_relevant_context(message, k=5)
        return format_response(Intent.RECOMMENDATION, context_rag)
