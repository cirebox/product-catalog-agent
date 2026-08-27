"""
LLM Service — Product Catalog Agent
Centralized LLM interaction via OpenRouter (free models).
"""

import logging
import os
from typing import List, Optional

from ..prompts.system_prompt import SYSTEM_PROMPT
from ..utils.config import Config

logger = logging.getLogger(__name__)


class LLMService:
    """Centralized LLM interaction service via OpenRouter."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._api_key = os.getenv("OPENROUTER_API_KEY", "")
        self._model = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.2:free")
        self._base_url = "https://openrouter.ai/api/v1"

    def _get_llm(self, max_tokens: int = 150, timeout: int = 30):
        """Factory for creating a ChatOpenAI instance with OpenRouter."""
        if not self._api_key:
            logger.warning("OPENROUTER_API_KEY not set — LLM calls will fail.")
            return None

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=self._model,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=2,
            openai_api_key=self._api_key,
            base_url=self._base_url,
            default_headers={
                "HTTP-Referer": self._app_url,   # recomendado pelo OpenRouter para identificar a app
                "X-Title": self._app_name,
            },
            model_kwargs={
                "provider": {"order": ["openrouter"]},
            },
        )

    def humanize_error(self, user_message: str) -> Optional[str]:
        """Use LLM to produce a friendly error message. Returns None on failure."""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = self._get_llm(max_tokens=120, timeout=15)
            if not llm:
                return None

            response = llm.invoke(
                [
                    SystemMessage(
                        content=SYSTEM_PROMPT + "\n\n"
                        "REGRAS PARA ERROS:\n"
                        "- Responda sempre em português (PT-BR).\n"
                        "- Seja curto e amigável: no máximo 2 frases.\n"
                        "- Não explique detalhes técnicos do erro nem exponha informações internas do sistema.\n"
                        "- Assuma a culpa pela falha (nunca culpe o cliente ou a mensagem enviada).\n\n"
                        "Contexto: ocorreu um erro inesperado ao processar a solicitação do cliente. "
                        "Informe brevemente que houve um problema temporário, peça desculpas e sugira tentar novamente "
                        "em instantes ou reformular a mensagem."
                    ),
                    HumanMessage(
                        content=f'O usuário enviou: "{user_message}" e ocorreu um erro ao processar essa solicitação.'
                    ),
                ]
            )
            return response.content.strip()
        except Exception as e:
            logger.error("LLM humanize_error failed: %s", e)
            return None

    def contextual_clarification(
        self,
        user_message: str,
        history: List[dict],
        user_name: str = "",
    ) -> Optional[str]:
        """Use LLM with conversation history to produce a contextual clarification.

        Returns None on failure or if no LLM is configured.
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = self._get_llm(max_tokens=150, timeout=15)
            if not llm:
                return None

            history_lines = []
            for msg in history:
                role = "Cliente" if msg.get("role") == "user" else "Atendente"
                history_lines.append(f"{role}: {msg.get('content', '')}")
            history_text = "\n".join(history_lines)

            response = llm.invoke(
                [
                    SystemMessage(
                        content=SYSTEM_PROMPT + "\n\n"
                        "REGRAS PARA CLARIFICAÇÃO CONTEXTUAL:\n"
                        "- Responda sempre em português (PT-BR).\n"
                        "- Seja curto, amigável e direto: no máximo 2 frases.\n"
                        "- Nunca invente informações sobre produtos, preços ou prazos.\n\n"
                        "Contexto: o cliente enviou uma mensagem que não foi compreendida. "
                        "Use o histórico da conversa para inferir a intenção mais provável. "
                        "Se o histórico não for suficiente para entender o que ele quer, "
                        "pergunte educadamente o que ele precisa, sem tentar adivinhar.\n\n"
                        "Sempre finalize oferecendo 2 ou 3 exemplos práticos do que você pode ajudar, "
                        "como: ver produtos, consultar preço, ver guia de medidas ou falar sobre formas de pagamento."
                    ),
                    HumanMessage(
                        content=(
                            f"Histórico recente:\n{history_text}\n\n"
                            f'Mensagem não entendida: "{user_message}"'
                        )
                    ),
                ]
            )
            result = response.content.strip()
            if result and len(result) > 5:
                return result
        except Exception as e:
            logger.error("LLM contextual clarification failed: %s", e)
        return None
