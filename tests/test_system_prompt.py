"""
Tests — System Prompt Maria
Valida o system prompt da persona Maria.
"""

from src.prompts.system_prompt import (
    SYSTEM_PROMPT,
    build_system_prompt,
    get_out_of_scope_response,
    get_product_not_found_response,
    get_store_info,
)


class TestSystemPrompt:
    """Testes para o system prompt da Maria."""

    def test_prompt_contains_maria_identity(self):
        """Prompt deve conter a identidade Maria."""
        assert "Maria" in SYSTEM_PROMPT
        assert "assistente virtual" in SYSTEM_PROMPT.lower()

    def test_prompt_contains_store_name(self):
        """Prompt deve conter o nome da loja."""
        assert "Gio Roupa Íntimas" in SYSTEM_PROMPT

    def test_prompt_contains_phone(self):
        """Prompt deve conter o telefone da loja."""
        assert "(24) 99240-5601" in SYSTEM_PROMPT

    def test_prompt_contains_location(self):
        """Prompt deve conter a localização da loja."""
        assert "Paraíba do Sul" in SYSTEM_PROMPT
        assert "RJ" in SYSTEM_PROMPT

    def test_prompt_contains_payment_methods(self):
        """Prompt deve conter formas de pagamento."""
        assert "PIX" in SYSTEM_PROMPT
        assert "cartão" in SYSTEM_PROMPT
        assert "prazo" in SYSTEM_PROMPT

    def test_prompt_contains_payment_terms(self):
        """Prompt deve conter prazos de pagamento."""
        assert "15" in SYSTEM_PROMPT
        assert "30" in SYSTEM_PROMPT
        assert "60" in SYSTEM_PROMPT
        assert "90" in SYSTEM_PROMPT

    def test_prompt_language_is_ptbr(self):
        """Prompt deve especificar português do Brasil."""
        assert "português do Brasil" in SYSTEM_PROMPT

    def test_prompt_contains_behavior_rules(self):
        """Prompt deve conter regras de comportamento."""
        assert "Regras de Comportamento" in SYSTEM_PROMPT
        assert "Idioma" in SYSTEM_PROMPT
        assert "Busca de produtos" in SYSTEM_PROMPT

    def test_prompt_contains_examples(self):
        """Prompt deve conter exemplos de interação."""
        assert "Exemplos de Interação" in SYSTEM_PROMPT
        assert "Exemplo 1" in SYSTEM_PROMPT
        assert "Exemplo 2" in SYSTEM_PROMPT

    def test_build_system_prompt_with_client_name(self):
        """build_system_prompt deve incluir nome do cliente."""
        prompt = build_system_prompt(client_name="Ana")
        assert "Cliente identificado: Ana" in prompt
        assert "trate o cliente pelo nome" in prompt

    def test_build_system_prompt_with_custom_date(self):
        """build_system_prompt deve incluir data customizada."""
        prompt = build_system_prompt(current_date="01/01/2025")
        assert "Data atual: 01/01/2025" in prompt

    def test_build_system_prompt_with_additional_context(self):
        """build_system_prompt deve incluir contexto adicional."""
        prompt = build_system_prompt(additional_context="Cliente VIP")
        assert "Cliente VIP" in prompt

    def test_get_out_of_scope_response(self):
        """Resposta fora do escopo deve mencionar a loja."""
        response = get_out_of_scope_response()
        assert "Gio Roupa Íntimas" in response
        assert "Maria" in response

    def test_get_product_not_found_response(self):
        """Resposta de produto não encontrado deve ser amigável."""
        response = get_product_not_found_response()
        assert "pedido especial" in response.lower()
        assert "interesse" in response.lower()

    def test_get_store_info(self):
        """get_store_info deve retornar informações corretas."""
        info = get_store_info()
        assert info["name"] == "Gio Roupa Íntimas"
        assert info["phone"] == "(24) 99240-5601"
        assert "PIX" in info["payment_methods"]
        assert 15 in info["payment_terms"]
        assert 90 in info["payment_terms"]
        assert len(info["categories"]) > 0
