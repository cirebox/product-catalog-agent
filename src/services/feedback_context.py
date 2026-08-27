"""
Feedback Context Builder — RLHF
Analisa feedback e constrói contexto para ajustar prompts dos agents.
"""

import logging
from typing import Optional

from src.services.sqlite_service import SQLiteService

logger = logging.getLogger(__name__)

# Threshold: if negative feedback rate > 30%, add warning to prompt
NEGATIVE_THRESHOLD = 30.0


class FeedbackContextBuilder:
    """Builds feedback-aware context for agent prompts."""

    def __init__(self, sqlite_service: Optional[SQLiteService] = None):
        self.sqlite_service = sqlite_service

    async def get_prompt_adjustments(self, intent: str) -> str:
        """Get prompt adjustments based on feedback patterns for an intent."""
        if not self.sqlite_service:
            return ""

        try:
            stats_by_intent = await self.sqlite_service.get_feedback_by_intent()
        except Exception as e:
            logger.warning("Failed to get feedback stats: %s", e)
            return ""

        # Find stats for this intent
        intent_stats = None
        for s in stats_by_intent:
            if s["intent"] == intent:
                intent_stats = s
                break

        if not intent_stats:
            return ""

        negative_rate = (
            (intent_stats["negative"] / intent_stats["total"] * 100)
            if intent_stats["total"] > 0
            else 0
        )

        adjustments = []

        # If high negative rate, add warning
        if negative_rate > NEGATIVE_THRESHOLD and intent_stats["total"] >= 3:
            adjustments.append(
                f"⚠️ ATENÇÃO: Respostas anteriores para '{intent}' receberam "
                f"{negative_rate:.0f}% de avaliações negativas. "
                f"Revise cuidadosamente sua resposta antes de enviar."
            )

        # Add specific rules based on intent
        if intent == "pricing" and intent_stats["negative"] > 0:
            adjustments.append(
                "IMPORTANTE: Ao informar preços, SEMPRE consulte o banco de dados. "
                "Nunca invente preços. Se não encontrar, diga que precisa verificar."
            )

        if intent == "product_info" and intent_stats["negative"] > 0:
            adjustments.append(
                "IMPORTANTE: Ao descrever produtos, use apenas informações do catálogo. "
                "Não adicione características não mencionadas nos dados."
            )

        if intent == "stock_check" and intent_stats["negative"] > 0:
            adjustments.append(
                "IMPORTANTE: Ao verificar estoque, confirme os dados no banco. "
                "Se o produto não existir, diga claramente que não foi encontrado."
            )

        return "\n".join(adjustments)

    async def get_few_shot_examples(self, intent: str, max_examples: int = 2) -> str:
        """Get few-shot examples from good responses (👍 or implicit)."""
        if not self.sqlite_service:
            return ""

        try:
            examples = await self.sqlite_service.get_good_examples(intent, limit=max_examples)
        except Exception as e:
            logger.warning("Failed to get few-shot examples: %s", e)
            return ""

        if not examples:
            return ""

        lines = ["Exemplos de boas respostas para esta pergunta:"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"\n{i}. Pergunta: \"{ex['question']}\"")
            lines.append(f"   Resposta: \"{ex['answer']}\"")

        return "\n".join(lines)

    async def build_context(self, intent: str) -> str:
        """Build complete feedback context for an intent."""
        parts = []

        adjustments = await self.get_prompt_adjustments(intent)
        if adjustments:
            parts.append(adjustments)

        few_shot = await self.get_few_shot_examples(intent)
        if few_shot:
            parts.append(few_shot)

        return "\n\n".join(parts)
