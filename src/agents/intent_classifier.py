"""
Intent Classifier — Product Catalog Agent
Classifica a intenção do usuário em domínios de lingerie.
"""

import re
import unicodedata
from enum import Enum


class Intent(Enum):
    # Catálogo
    PRODUCT_COUNT = "product_count"
    PRODUCT_INFO = "product_info"
    PRICING = "pricing"
    STOCK_CHECK = "stock_check"
    SIZE_GUIDE = "size_guide"
    RECOMMENDATION = "recommendation"
    USER_MEASUREMENT = "user_measurement"

    # Vendas
    ORDER_STATUS = "order_status"
    TRACK_DELIVERY = "track_delivery"
    NEW_ORDER = "new_order"

    # Ações do PDV (backoffice)
    LOOKUP_CUSTOMER = "lookup_customer"
    CREATE_SALE = "create_sale"
    GET_DAILY_REPORT = "get_daily_report"
    GET_CUSTOMER_HISTORY = "get_customer_history"
    GET_CUSTOMER_CREDIT = "get_customer_credit"

    # Suporte
    RETURN_POLICY = "return_policy"
    EXCHANGE = "exchange"
    COMPLAINT = "complaint"

    # Geral
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


def _normalize(text: str) -> str:
    """Normaliza texto para comparação: minúsculas + remoção de acentos.

    Isso permite que os patterns sejam escritos em ASCII puro (sem
    character classes tipo `[cç]` ou `[aã]`), já que tanto "preço" quanto
    "preco" chegam normalizados como "preco" antes do match.
    """
    text = text.strip().lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


# Keyword patterns per intent.
# Todos os patterns assumem texto já normalizado (sem acento, minúsculo).
# `\b` é usado para evitar falsos positivos por substring (ex.: "credito"
# não deve casar dentro de "acredito").
#
# NOTA sobre empate de score: quando duas intents empatam, vence a que
# aparece primeiro neste dicionário (ver IntentClassifier._score). A ordem
# abaixo foi definida propositalmente da mais específica para a mais
# genérica dentro de cada bloco.
_INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.PRODUCT_COUNT: [
        r"quantos?\s+produtos?\b",
        r"qtd(?:ade)?\s+de\s+produtos?\b",
        r"total\s+de\s+produtos?\b",
        r"numero\s+de\s+produtos?\b",
    ],
    Intent.PRODUCT_INFO: [
        r"\bprodutos?\b",
        r"\bdescricao\b",
        r"\bdetalhes?\b",
        r"como\s+e\s+o\s+produto",
        r"me\s+mostr\w*",
        r"informacoes?\s+(?:do|sobre)\s+produto",
        r"quais?\s+(?:sao\s+)?os?\s+produtos?",
        r"\bcatalogo\b",
    ],
    Intent.PRICING: [
        r"\bpreco\b",
        r"\bvalor\b",
        r"\bcusto\b",
        r"quanto\s+(?:custa|custam|e|eh|fica|sai)\b",
    ],
    Intent.STOCK_CHECK: [
        r"\bestoque\b",
        r"\bdisponivel\b",
        r"tem\s+(?:em\s+)?estoque",
        r"ainda\s+tem\b",
        r"quantos?\s+(?:tem|restam|faltam)\b",
        r"\besgotado\b",
    ],
    Intent.SIZE_GUIDE: [
        r"\btamanhos?\b",
        r"\bmedidas?\b",
        r"tabelas?\s+de\s+medidas?",
        r"qual\s+(?:o\s+)?meu\s+tamanho",
        r"como\s+(?:escolher|tirar)\s+(?:o\s+)?tamanho",
    ],
    Intent.USER_MEASUREMENT: [
        r"\d+\s*(?:cm|centimetros?)\s+(?:de\s+)?(?:quadril|cintura|busto|peito|seios?)",
        r"(?:quadril|cintura|busto|peito|seios?)\s*(?:de\s+)?\d+\s*(?:cm|centimetros?)",
        r"meu(?:s)?\s+(?:quadril|cintura|busto|peito|seios?)\s*(?:e|é|=|mede)?\s*\d+",
        r"(?:tenho|meio)\s+\d+\s*(?:cm|centimetros?)\s+(?:de\s+)?(?:quadril|cintura|busto)",
        r"(?:quadril|cintura|busto)\s+(?:de\s+)?\d+",
        r"(?:cm|centimetros?)\s+de\s+(?:quadril|cintura|busto)",
        r"(?:medindo|com)\s+\d+\s*(?:cm|centimetros?)",
    ],
    Intent.RECOMMENDATION: [
        r"\brecomend\w*",
        r"\bsugere?\b",
        r"\bindica(?:cao|r)?\b",
        r"qual\s+(?:eu|voce|vc)\s+(?:deveria|deve|pode)",
        r"me\s+ajuda\s+a\s+escolher",
        r"o\s+que\s+(?:voce|vc)\s+recomenda",
        r"melhor\s+(?:para|opcao)",
    ],
    Intent.ORDER_STATUS: [
        r"\bpedido\b",
        r"\bstatus\b",
        r"\bacompanhar\b",
        r"\bandamento\b",
        r"meu\s+pedido",
        r"onde\s+(?:esta|meu\s+pedido)",
    ],
    Intent.TRACK_DELIVERY: [
        r"\bentrega\b",
        r"\bfrete\b",
        r"\brastreio\b",
        r"\brastrear\b",
        r"codigo\s+de\s+rastreio",
        r"quando\s+(?:chega|chegar|recebo)",
        r"prazo\s+de\s+entrega",
    ],
    Intent.NEW_ORDER: [
        r"\bcomprar\b",
        r"\badicionar\b",
        r"colocar\s+no\s+carrinho",
        r"\blevar\b",
        r"quero\s+comprar",
    ],
    # Ações do PDV
    Intent.LOOKUP_CUSTOMER: [
        r"buscar\s+cliente",
        r"procurar\s+cliente",
        r"cliente\s+chamado",
        r"cliente\s+de\s+nome",
        r"qual\s+o\s+telefone",
        r"cadastro\s+de\s+cliente",
    ],
    Intent.CREATE_SALE: [
        r"registrar\s+venda",
        r"criar\s+venda",
        r"nova\s+venda",
        r"registrar\s+pedido",
        r"\bvender\b",
        r"venda\s+de",
        r"quanto\s+vendi\b",
        r"\bregistr\w*",
    ],
    Intent.GET_DAILY_REPORT: [
        r"\brelatorio\b",
        r"quanto\s+vendi\s+hoje",
        r"vendas?\s+de\s+hoje",
        r"\bfaturamento\b",
        r"quanto\s+rendeu",
        r"resumo\s+do\s+dia",
    ],
    Intent.GET_CUSTOMER_HISTORY: [
        r"historico\s+de\s+cliente",
        r"compras?\s+de\s+cliente",
        r"o\s+que\s+comprou",
        r"historico\s+de\s+compras?",
    ],
    Intent.GET_CUSTOMER_CREDIT: [
        r"\bcredito\b",
        r"\bfiado\b",
        r"\bdevendo\b",
        r"quanto\s+deve\b",
        r"\bpendencia\b",
        r"\bdivida\b",
    ],
    Intent.RETURN_POLICY: [
        r"\bdevolucao\b",
        r"\bdevolver\b",
        r"\breembolso\b",
        r"\breembolsar\b",
        r"reclamar\s+do\s+produto",
        r"produto\s+(?:com\s+)?(?:defeito|problema)",
    ],
    Intent.EXCHANGE: [
        r"\btroca\b",
        r"\btrocar\b",
        r"tamanho\s+errado",
        r"trocar\s+(?:o\s+)?tamanho",
        r"outra\s+cor",
        r"outro\s+tamanho",
    ],
    Intent.COMPLAINT: [
        r"\breclamacao\b",
        r"\breclamar\b",
        r"\binsatisfeit\w*",
        r"\bproblema\b",
        r"nao\s+(?:gostei|funcionou|chegou)",
        r"\berrado\b",
        r"\bincorreto\b",
    ],
    Intent.GREETING: [
        r"^oi\b",
        r"^ola\b",
        r"^bom\s+dia\b",
        r"^boa\s+tarde\b",
        r"^boa\s+noite\b",
        r"^hello\b",
        r"^hi\b",
        r"^hey\b",
        r"^e\s+ai\b",
        r"^fala\b",
        # Small talk / conversa casual
        r"^tudo\s+(?:bem|bom|joia|certo|ok)\b",
        r"^como\s+(?:vai|esta|vc\s+esta)\b",
        r"^beleza\b",
        r"^e\s+voce\b",
        r"^bom\s+tc\b",
    ],
    Intent.HELP: [
        r"\bajuda\b",
        r"como\s+funciona",
        r"o\s+que\s+voce\s+faz",
        r"\bopcoes?\b",
        r"\bmenu\b",
        r"\bcomandos?\b",
        r"\bajudar\b",
    ],
}


class IntentClassifier:
    """Rule-based intent classifier for lingerie customer service."""

    def __init__(self):
        self._patterns: dict[Intent, list[re.Pattern]] = {
            intent: [re.compile(p) for p in patterns]
            for intent, patterns in _INTENT_PATTERNS.items()
        }

    def _score(self, message: str) -> dict[Intent, int]:
        """Calcula a pontuação de cada intent para a mensagem.

        Método único usado tanto por `classify` quanto por `get_confidence`
        para evitar duplicação de lógica.
        """
        if not message or not message.strip():
            return {}

        text = _normalize(message)

        scores: dict[Intent, int] = {}
        for intent, patterns in self._patterns.items():
            score = sum(1 for pattern in patterns if pattern.search(text))
            if score > 0:
                scores[intent] = score

        return scores

    def classify(self, message: str) -> Intent:
        """Classify user message into an Intent."""
        scores = self._score(message)
        if not scores:
            return Intent.UNKNOWN
        return max(scores, key=scores.get)

    def get_confidence(self, message: str) -> tuple[Intent, float]:
        """Classify and return intent with confidence score.

        A confiança é a proporção de "votos" (patterns casados) que a
        intent vencedora recebeu em relação ao total de votos de todas as
        intents que casaram — não é uma probabilidade calibrada, é uma
        medida relativa de dominância entre as intents candidatas.
        """
        scores = self._score(message)
        if not scores:
            return Intent.UNKNOWN, 0.0

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        total = sum(scores.values())

        confidence = best_score / total if total > 0 else 0.0
        return best_intent, round(confidence, 2)