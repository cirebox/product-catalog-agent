"""
Intent Classifier — Product Catalog Agent
Classifica a intenção do usuário em domínios de lingerie.
"""

import re
from enum import Enum
from typing import Optional


class Intent(Enum):
    # Catálogo
    PRODUCT_INFO = "product_info"
    PRICING = "pricing"
    STOCK_CHECK = "stock_check"
    SIZE_GUIDE = "size_guide"
    RECOMMENDATION = "recommendation"

    # Vendas
    ORDER_STATUS = "order_status"
    TRACK_DELIVERY = "track_delivery"
    NEW_ORDER = "new_order"

    # Suporte
    RETURN_POLICY = "return_policy"
    EXCHANGE = "exchange"
    COMPLAINT = "complaint"

    # Geral
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


# Keyword patterns per intent
_INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.PRODUCT_INFO: [
        r"produto",
        r"descricao",
        r"detalhes?",
        r"como\s+(e|eh)\s+o\s+produto",
        r"me\s+mostra(?:r)?",
        r"informa[cç][oã]es?\s+(?:do|sobre)\s+produto",
        r"quais?\s+(?:s[aã]o?\s+)?os?\s+produtos?",
        r"catalogo",
        r"cat[aá]logo",
    ],
    Intent.PRICING: [
        r"pre[cç]o",
        r"valor",
        r"quanto\s+(?:custa|custa?|e|faz|s[aã]o)",
        r"custo",
        r"pre[cç]o\s+(?:de|do|da)",
    ],
    Intent.STOCK_CHECK: [
        r"estoque",
        r"dispon[ií]ve[l]",
        r"tem\s+(?:em\s+)?estoque",
        r"ainda\s+tem",
        r"quantos?\s+(?:tem|restam|faltam)",
        r"esgotado",
    ],
    Intent.SIZE_GUIDE: [
        r"tamanho",
        r"medida",
        r"medidas?",
        r"tabelas?\s+(?:de\s+)?medida",
        r"qual\s+(?:o|meu)\s+tamanho",
        r"como\s+(?:escolher|tirar)\s+(?:o\s+)?tamanho",
    ],
    Intent.RECOMMENDATION: [
        r"recomend[aã]",
        r"sugere?",
        r"indica(?:r|c[aã]o)",
        r"qual\s+(?:eu|você|vc)\s+(?:deveria|deve|pode)",
        r"me\s+ajuda(?:r)?\s+a\s+escolher",
        r"o\s+que\s+(?:você|vc)\s+recomenda",
        r"melhor\s+(?:para|op[cç][aã]o)",
    ],
    Intent.ORDER_STATUS: [
        r"pedido",
        r"status",
        r"acompanhar",
        r"andamento",
        r"meu\s+pedido",
        r"onde\s+(?:est[aá]|meu\s+pedido)",
    ],
    Intent.TRACK_DELIVERY: [
        r"entrega",
        r"frete",
        r"rastreio",
        r"rastrear",
        r"c[oó]digo\s+de\s+rastreio",
        r"quando\s+(?:chega|chegar|recebo)",
        r"prazo\s+de\s+entrega",
    ],
    Intent.NEW_ORDER: [
        r"comprar",
        r"adicionar",
        r"colocar\s+no\s+carrinho",
        r"levar",
        r"quero\s+comprar",
    ],
    Intent.RETURN_POLICY: [
        r"devolu[cç][aã]o",
        r"devolver",
        r"reembolso",
        r"reembolsar",
        r"reclamar\s+do\s+produto",
        r"produto\s+(?:com\s+)?(?:defeito|problema)",
    ],
    Intent.EXCHANGE: [
        r"troca",
        r"trocar",
        r"tamanho\s+errado",
        r"trocar\s+(?:o\s+)?tamanho",
        r"outra\s+cor",
        r"outra\s+tamanho",
    ],
    Intent.COMPLAINT: [
        r"reclama[cç][aã]o",
        r"reclamar",
        r"insatisfei",
        r"problema",
        r"n[aã]o\s+(?:gostei|funcionou|chegou)",
        r"errado",
        r"incorreto",
    ],
    Intent.GREETING: [
        r"^oi$",
        r"^ol[aá]$",
        r"^bom\s+dia$",
        r"^boa\s+tarde$",
        r"^boa\s+noite$",
        r"^hello$",
        r"^hi$",
        r"^hey$",
        r"^e\s+ai$",
        r"^fala$",
    ],
    Intent.HELP: [
        r"ajuda",
        r"como\s+funciona",
        r"o\s+que\s+voc[eê]\s+faz",
        r"op[cç][oã]es?",
        r"menu",
        r"comandos?",
        r"ajudar",
    ],
}


class IntentClassifier:
    """Rule-based intent classifier for lingerie customer service."""

    def __init__(self):
        self._patterns: dict[Intent, list[re.Pattern]] = {}
        for intent, patterns in _INTENT_PATTERNS.items():
            self._patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def classify(self, message: str) -> Intent:
        """Classify user message into an Intent."""
        if not message or not message.strip():
            return Intent.UNKNOWN

        text = message.strip().lower()

        # Score each intent
        scores: dict[Intent, int] = {}
        for intent, patterns in self._patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            if score > 0:
                scores[intent] = score

        if not scores:
            return Intent.UNKNOWN

        # Return the intent with the highest score
        return max(scores, key=scores.get)

    def get_confidence(self, message: str) -> tuple[Intent, float]:
        """Classify and return intent with confidence score."""
        if not message or not message.strip():
            return Intent.UNKNOWN, 0.0

        text = message.strip().lower()

        scores: dict[Intent, int] = {}
        for intent, patterns in self._patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            if score > 0:
                scores[intent] = score

        if not scores:
            return Intent.UNKNOWN, 0.0

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        total = sum(scores.values())

        confidence = best_score / total if total > 0 else 0.0
        return best_intent, round(confidence, 2)
