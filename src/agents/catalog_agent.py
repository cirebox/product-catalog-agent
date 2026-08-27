"""
Catalog Agent — Product Catalog Agent
Agente especializado em informações de produtos de lingerie e ações do PDV.
"""

import logging
import re
from src.agents.base_agent import BaseAgent
from src.agents.intent_classifier import Intent
from src.agents.response_templates import format_response
from src.services.product_service import ProductService
from src.services.customer_service import CustomerService
from src.services.sale_service import SaleService
from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class CatalogAgent(BaseAgent):
    """Agente de catálogo: produtos, preços, estoque, medidas + ações PDV."""

    def __init__(
        self,
        rag_service: RAGService,
        product_service: ProductService = None,
        customer_service: CustomerService = None,
        sale_service: SaleService = None,
    ):
        self.rag_service = rag_service
        self.product_service = product_service
        self.customer_service = customer_service
        self.sale_service = sale_service
        super().__init__(
            name="catalog",
            description="Agente de catálogo e PDV de lingerie",
        )

    async def handle(self, message: str, intent: Intent, context: dict) -> str:
        """Processa mensagem do domínio de catálogo e PDV."""

        # Catálogo
        if intent == Intent.PRODUCT_COUNT:
            return await self._product_count()
        elif intent == Intent.PRODUCT_INFO:
            return await self._product_info(message, context)
        elif intent == Intent.PRICING:
            return await self._pricing(message, context)
        elif intent == Intent.STOCK_CHECK:
            return await self._stock_check(message, context)
        elif intent == Intent.SIZE_GUIDE:
            return await self._size_guide(message, context)
        elif intent == Intent.USER_MEASUREMENT:
            return await self._user_measurement(message, context)
        elif intent == Intent.RECOMMENDATION:
            return await self._recommendation(message, context)

        # Ações do PDV
        elif intent == Intent.LOOKUP_CUSTOMER:
            return await self._lookup_customer(message, context)
        elif intent == Intent.CREATE_SALE:
            return await self._create_sale(message, context)
        elif intent == Intent.GET_DAILY_REPORT:
            return await self._get_daily_report(message, context)
        elif intent == Intent.GET_CUSTOMER_HISTORY:
            return await self._get_customer_history(message, context)
        elif intent == Intent.GET_CUSTOMER_CREDIT:
            return await self._get_customer_credit(message, context)

        else:
            return format_response(Intent.UNKNOWN)

    # --- Catálogo ---

    async def _product_count(self) -> str:
        """Retorna a quantidade atual de produtos ativos."""
        if not self.product_service:
            return "Não consegui consultar o total de produtos agora."

        count = await self.product_service.count()
        logger.info("Contagem de produtos consultada: total=%d", count)
        return f"Temos **{count} produtos** cadastrados no catálogo."

    async def _product_info(self, message: str, context: dict) -> str:
        """Busca informações do produto por referência ou via RAG."""
        ref_match = re.search(
            r"(?:produto|c[oó]digo|ref(?:er[eê]ncia)?)\b\s*[#:\-]?\s*([A-Za-z0-9][A-Za-z0-9-]*)",
            message,
            re.IGNORECASE,
        )
        if not ref_match:
            ref_match = self._reference_from_history(message, context.get("history", []))
        if ref_match and self.product_service:
            ref = ref_match.group(1)
            product = await self.product_service.get_by_ref(ref)
            logger.info("Busca exata de produto: ref=%s, encontrado=%s", ref, bool(product))
            if product:
                return (
                    f"**{product['description']}** (código {product['ref']})\n"
                    f"Preço: R$ {product['price']:.2f}\n"
                    f"Estoque: {product['stock']} unidades disponíveis\n"
                    f"Categoria: {product.get('category') or 'Não informada'}\n"
                    f"Material: {product.get('material') or 'Não informado'}\n"
                    f"Tamanhos: {product.get('size') or 'Não informados'}"
                )

        context_rag = self.rag_service.get_relevant_context(message, k=3)
        logger.info("Busca RAG de produto: resultados=%d", len(context_rag.split("\n---\n")) if context_rag else 0)
        return format_response(Intent.PRODUCT_INFO, context_rag)

    @staticmethod
    def _reference_from_history(message: str, history: list[dict]):
        """Reaproveita a última referência quando a pergunta é um follow-up."""
        follow_up = re.search(
            r"\b(e\s+esse|esse|ele|ela|mais\s+detalhes?|outra\s+cor|outro\s+tamanho)\b",
            message,
            re.IGNORECASE,
        )
        if not follow_up:
            return None

        for previous in reversed(history):
            if previous.get("role") != "user":
                continue
            match = re.search(
                r"(?:produto|c[oó]digo|ref(?:er[eê]ncia)?)\b\s*[#:\-]?\s*([A-Za-z0-9][A-Za-z0-9-]*)",
                previous.get("content", ""),
                re.IGNORECASE,
            )
            if match:
                return match
        return None

    async def _pricing(self, message: str, context: dict) -> str:
        """Busca preço do produto via RAG."""
        context_rag = self.rag_service.get_relevant_context(message, k=3)
        return format_response(Intent.PRICING, context_rag)

    async def _stock_check(self, message: str, context: dict) -> str:
        """Verifica estoque do produto via SQLite."""
        ref_match = re.search(r'\b(\d{3,5})\b', message)
        if ref_match and self.product_service:
            ref = ref_match.group(1)
            product = await self.product_service.get_by_ref(ref)
            if product:
                stock = product["stock"]
                desc = product["description"]
                price = product["price"]
                return (
                    f"**{desc}** (código {ref})\n"
                    f"Preço: R$ {price:.2f}\n"
                    f"Estoque: {stock} unidades disponíveis"
                )

        context_rag = self.rag_service.get_relevant_context(message, k=3)
        if context_rag:
            return format_response(Intent.STOCK_CHECK, context_rag)

        return (
            "Não consegui encontrar esse produto. "
            "Por favor, informe o **código de referência** (ex: 252, 3452)."
        )

    async def _size_guide(self, message: str, context: dict) -> str:
        """Retorna guia de medidas."""
        context_rag = self.rag_service.get_relevant_context(
            "tamanho medida tabela", k=3
        )
        return format_response(Intent.SIZE_GUIDE, context_rag)

    async def _user_measurement(self, message: str, context: dict) -> str:
        """Processa medida do usuário e recomenda tamanho."""
        # Extrair medidas do usuário
        measurements = self._extract_measurements(message)
        
        if not measurements:
            return (
                "Não consegui identificar suas medidas. "
                "Por favor, informe no formato: **75 cm de quadril** ou **38 de cintura**.\n\n"
                "Medidas que posso usar:\n"
                "• **Quadril** (cm)\n"
                "• **Cintura** (cm)\n"
                "• **Busto** (cm)"
            )
        
        # Determinar tamanho baseado nas medidas
        size = self._determine_size(measurements)
        
        # Montar resposta
        measurement_text = ", ".join([f"{v} cm de {k}" for k, v in measurements.items()])
        
        return (
            f"Suas medidas: **{measurement_text}**\n\n"
            f"Baseado nisso, seu tamanho recomendado é **{size}**! 🎯\n\n"
            f"Quer que eu mostre produtos disponíveis nesse tamanho?"
        )

    def _extract_measurements(self, message: str) -> dict:
        """Extrai medidas numéricas do mensagem."""
        import re
        measurements = {}
        
        # Padrões para extrair medidas
        patterns = [
            (r"(\d+)\s*(?:cm|centimetros?)\s+(?:de\s+)?(?:quadril)", "quadril"),
            (r"(?:quadril)\s*(?:de\s+)?(\d+)\s*(?:cm|centimetros?)", "quadril"),
            (r"(\d+)\s*(?:cm|centimetros?)\s+(?:de\s+)?(?:cintura)", "cintura"),
            (r"(?:cintura)\s*(?:de\s+)?(\d+)\s*(?:cm|centimetros?)", "cintura"),
            (r"(\d+)\s*(?:cm|centimetros?)\s+(?:de\s+)?(?:busto|peito|seios?)", "busto"),
            (r"(?:busto|peito|seios?)\s*(?:de\s+)?(\d+)\s*(?:cm|centimetros?)", "busto"),
        ]
        
        for pattern, body_part in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                measurements[body_part] = int(match.group(1))
        
        return measurements

    def _determine_size(self, measurements: dict) -> str:
        """Determina tamanho baseado nas medidas (tabela padrão lingerie)."""
        # Tabela de referência para lingerie feminina
        # Valores aproximados em cm
        size_chart = {
            "P": {"quadril": (85, 90), "cintura": (60, 68), "busto": (80, 85)},
            "M": {"quadril": (90, 95), "cintura": (68, 75), "busto": (85, 90)},
            "G": {"quadril": (95, 100), "cintura": (75, 82), "busto": (90, 95)},
            "GG": {"quadril": (100, 110), "cintura": (82, 90), "busto": (95, 105)},
        }
        
        # Se tem quadril, usar como referência principal
        if "quadril" in measurements:
            quadril = measurements["quadril"]
            if quadril < 90:
                return "P"
            elif quadril < 95:
                return "M"
            elif quadril < 100:
                return "G"
            else:
                return "GG"
        
        # Se tem busto, usar como referência
        if "busto" in measurements:
            busto = measurements["busto"]
            if busto < 85:
                return "P"
            elif busto < 90:
                return "M"
            elif busto < 95:
                return "G"
            else:
                return "GG"
        
        # Se tem cintura, usar como referência
        if "cintura" in measurements:
            cintura = measurements["cintura"]
            if cintura < 68:
                return "P"
            elif cintura < 75:
                return "M"
            elif cintura < 82:
                return "G"
            else:
                return "GG"
        
        return "M"  # Padrão se não conseguir determinar

    async def _recommendation(self, message: str, context: dict) -> str:
        """Recomenda produtos baseado na preferência do usuário."""
        context_rag = self.rag_service.get_relevant_context(message, k=5)
        return format_response(Intent.RECOMMENDATION, context_rag)

    # --- Ações do PDV ---

    async def _lookup_customer(self, message: str, context: dict) -> str:
        """Busca cliente por nome ou telefone."""
        if not self.customer_service:
            return "Serviço de clientes não disponível no momento."

        # Tentar extrair telefone (números)
        phone_match = re.search(r'[\d\-\(\)\s]{8,}', message)
        if phone_match:
            phone = re.sub(r'\D', '', phone_match.group())
            customer = await self.customer_service.get_by_phone(phone)
            if customer:
                return (
                    f"**Cliente encontrado:**\n"
                    f"Nome: {customer['name']}\n"
                    f"Telefone: {customer['phone']}\n"
                    f"Email: {customer.get('email', 'Não informado')}\n"
                    f"Cadastrado em: {customer['created_at']}"
                )

        # Buscar por nome
        name_match = re.search(r'(?:chamado|nome|de)\s+(\w+)', message, re.IGNORECASE)
        if name_match:
            name = name_match.group(1)
            result = await self.customer_service.search(name, limit=5)
            if result["items"]:
                lines = ["**Clientes encontrados:**"]
                for c in result["items"]:
                    lines.append(f"• {c['name']} — {c['phone']}")
                return "\n".join(lines)

        return (
            "Para buscar um cliente, informe o **telefone** ou **nome**.\n"
            "Exemplo: \"Buscar cliente 11999887766\" ou \"Cliente chamado Maria\""
        )

    async def _create_sale(self, message: str, context: dict) -> str:
        """Registra uma venda (precisa de dados estruturados via PDV)."""
        return (
            "Para registrar uma venda, use o **PDV** (menu → PDV).\n"
            "Lá você pode selecionar o cliente, adicionar itens e escolher a forma de pagamento.\n\n"
            "Ou me envie os dados no formato:\n"
            "• Cliente: [nome ou telefone]\n"
            "• Produto: [código] x [quantidade]\n"
            "• Pagamento: [pix/cartão/dinheiro/prazo]"
        )

    async def _get_daily_report(self, message: str, context: dict) -> str:
        """Retorna relatório do dia."""
        if not self.sale_service:
            return "Serviço de vendas não disponível no momento."

        try:
            report = await self.sale_service.get_daily_report()
            sales = report["sales"]
            payments = report["payments_received"]
            pending = report["pending"]

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

            lines.append(f"**Pagamentos recebidos:** {payments['count']} — R$ {payments['total']:.2f}")
            lines.append(f"**Pendências:** {pending['count']} — R$ {pending['total']:.2f}")

            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao gerar relatório: {str(e)}"

    async def _get_customer_history(self, message: str, context: dict) -> str:
        """Retorna histórico de compras do cliente."""
        if not self.customer_service or not self.sale_service:
            return "Serviços não disponíveis no momento."

        # Buscar cliente
        phone_match = re.search(r'[\d\-\(\)\s]{8,}', message)
        if not phone_match:
            return "Informe o **telefone** do cliente para ver o histórico."

        phone = re.sub(r'\D', '', phone_match.group())
        customer = await self.customer_service.get_by_phone(phone)
        if not customer:
            return "Cliente não encontrado."

        # Buscar vendas
        result = await self.sale_service.list_sales(customer_id=customer["id"], limit=10)
        if not result["items"]:
            return f"**{customer['name']}** não possui compras registradas."

        lines = [f"**Histórico de {customer['name']}:**\n"]
        for sale in result["items"]:
            status_icon = "✅" if sale["payment_status"] == "pago" else "⏳"
            lines.append(
                f"• {sale['sale_date']} — R$ {sale['total']:.2f} "
                f"({sale['payment_method'].upper()}) {status_icon}"
            )

        return "\n".join(lines)

    async def _get_customer_credit(self, message: str, context: dict) -> str:
        """Retorna crédito pendente do cliente."""
        if not self.customer_service:
            return "Serviço de clientes não disponível no momento."

        # Buscar cliente
        phone_match = re.search(r'[\d\-\(\)\s]{8,}', message)
        if not phone_match:
            # Mostrar todos com fiado pendente
            try:
                credit_data = await self.customer_service.get_all_pending_credit()
                if not credit_data:
                    return "Nenhum cliente com fiado pendente."

                lines = ["**Clientes com fiado pendente:**\n"]
                for item in credit_data:
                    lines.append(
                        f"• {item['name']} ({item['phone']}): "
                        f"R$ {item['total_pending']:.2f}"
                    )
                return "\n".join(lines)
            except Exception:
                return "Informe o telefone do cliente para consultar o fiado."

        phone = re.sub(r'\D', '', phone_match.group())
        customer = await self.customer_service.get_by_phone(phone)
        if not customer:
            return "Cliente não encontrado."

        credit = await self.customer_service.get_credit_summary(customer["id"])
        if credit["total_pending"] == 0:
            return f"**{customer['name']}** não possui fiado pendente."

        lines = [
            f"**Fiado de {customer['name']}:**\n",
            f"Total pendente: **R$ {credit['total_pending']:.2f}**\n",
        ]

        if credit["pending"]:
            lines.append("Pedidos pendentes:")
            for sale in credit["pending"]:
                status = "🔴 VENCIDO" if sale["status"] == "atrasado" else "🟢 Em dia"
                lines.append(
                    f"  • #{sale['id'][:8]} — R$ {sale['total']:.2f} "
                    f"— Prazo: {sale['due_date']} {status}"
                )

        return "\n".join(lines)
