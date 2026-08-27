"""
Sales Agent — Product Catalog Agent
Agente especializado em vendas e pedidos.
"""

import logging
from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.rag_service import RAGService
from src.services.sale_service import SaleService

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """Agente de vendas: pedidos, entregas, compras."""

    def __init__(self, rag_service: RAGService, sale_service: SaleService = None):
        self.rag_service = rag_service
        self.sale_service = sale_service
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
        elif intent == Intent.SALES_REPORT:
            return await self._sales_report(message, context)
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

    async def _sales_report(self, message: str, context: dict) -> str:
        """Gera relatório de vendas baseado na pergunta do usuário."""
        if not self.sale_service:
            return "Serviço de vendas não disponível no momento."

        try:
            report = await self.sale_service.get_daily_report()
            sales = report["sales"]
            pending = report["pending"]

            # Verificar o que o usuário perguntou
            message_lower = message.lower()
            
            if "pendente" in message_lower:
                return (
                    f"**Vendas pendentes:** {pending['count']} vendas\n"
                    f"**Total pendente:** R$ {pending['total']:.2f}\n\n"
                    "Quer ver o relatório completo do dia?"
                )
            elif "faturamento" in message_lower or "faturamos" in message_lower or "recebemos" in message_lower:
                return (
                    f"**Faturamento de hoje:** R$ {sales['total']:.2f}\n"
                    f"**Vendas realizadas:** {sales['count']}\n\n"
                    "Quer ver mais detalhes?"
                )
            elif "vendemos" in message_lower or "vendas" in message_lower:
                return (
                    f"**Vendas de hoje:** {sales['count']} vendas\n"
                    f"**Total:** R$ {sales['total']:.2f}\n\n"
                    "Quer ver o relatório completo?"
                )
            else:
                # Relatório completo
                lines = [
                    f"**Relatório do dia — {report['date']}**\n",
                    f"**Vendas realizadas:** {sales['count']}",
                    f"**Faturamento:** R$ {sales['total']:.2f}\n",
                ]

                if sales["by_method"]:
                    lines.append("**Por método:**")
                    for method, data in sales["by_method"].items():
                        lines.append(f"  • {method.upper()}: {data['count']} vendas — R$ {data['total']:.2f}")
                    lines.append("")

                lines.append(f"**Pendências:** {pending['count']} — R$ {pending['total']:.2f}")

                return "\n".join(lines)
        except Exception as e:
            logger.error("Erro ao gerar relatório de vendas: %s", e)
            return f"Erro ao gerar relatório: {str(e)}"
