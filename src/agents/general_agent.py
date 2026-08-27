"""
General Agent — Product Catalog Agent
Agente para saudações, ajuda geral, informações da loja e identidade.
"""

from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService
from src.prompts.system_prompt import get_store_info


class GeneralAgent(BaseAgent):
    """Agente geral: saudações, ajuda, informações da loja, identidade."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        super().__init__(
            name="general",
            description="Agente geral para saudações, ajuda e informações da loja",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem geral."""

        if intent == Intent.GREETING:
            return format_response(Intent.GREETING)
        elif intent == Intent.HELP:
            return format_response(Intent.HELP)
        elif intent == Intent.IDENTITY:
            return await self._identity(message, context)
        elif intent == Intent.STORE_INFO:
            return await self._store_info(message, context)
        else:
            return format_response(Intent.UNKNOWN)

    async def _identity(self, message: str, context: dict) -> str:
        """Retorna informações de identidade do assistente."""
        return (
            "Eu sou a **Maria**, assistente virtual da **Gio Roupa Íntimas**! 💕\n\n"
            "Posso te ajudar com:\n"
            "- Informações sobre produtos\n"
            "- Preços e disponibilidade\n"
            "- Guia de medidas\n"
            "- Pedidos e entregas\n"
            "- Trocas e devoluções\n\n"
            "Como posso te ajudar hoje?"
        )

    async def _store_info(self, message: str, context: dict) -> str:
        """Retorna informações sobre a loja."""
        store_info = get_store_info()
        
        return (
            f"📍 **{store_info['name']}**\n\n"
            f"**Endereço:** {store_info['location']}\n"
            f"**Telefone/WhatsApp:** {store_info['phone']}\n\n"
            f"**Formas de pagamento:**\n"
            f"• PIX\n"
            f"• Cartão\n"
            f"• Dinheiro\n"
            f"• Prazo (15, 30, 60 ou 90 dias)\n\n"
            "Posso te ajudar com mais alguma coisa?"
        )
