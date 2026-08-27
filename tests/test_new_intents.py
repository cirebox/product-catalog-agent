"""
Tests — Novas Intents
Valida as novas intents adicionadas: PRODUCT_COUNT por categoria, IDENTITY, STORE_INFO, SALES_REPORT.
"""

from src.agents.intent_classifier import Intent, IntentClassifier


class TestNewIntents:
    """Testes para as novas intents."""

    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_product_count_category_calcinha(self):
        """PRODUCT_COUNT deve detectar contagem por categoria: calcinha."""
        assert self.classifier.classify("Quantas calcinhas temos?") == Intent.PRODUCT_COUNT

    def test_product_count_category_cueca(self):
        """PRODUCT_COUNT deve detectar contagem por categoria: cueca."""
        assert self.classifier.classify("Quantas cuecas temos?") == Intent.PRODUCT_COUNT

    def test_product_count_category_sutian(self):
        """PRODUCT_COUNT deve detectar contagem por categoria: sutiã."""
        assert self.classifier.classify("Quantos sutiãs temos?") == Intent.PRODUCT_COUNT

    def test_product_count_generic(self):
        """PRODUCT_COUNT deve detectar contagem genérica."""
        assert self.classifier.classify("Quantos produtos temos?") == Intent.PRODUCT_COUNT

    def test_identity_qual_nome(self):
        """IDENTITY deve detectar pergunta sobre nome."""
        assert self.classifier.classify("Qual seu nome?") == Intent.IDENTITY

    def test_identity_quem_e(self):
        """IDENTITY deve detectar pergunta sobre identidade."""
        assert self.classifier.classify("Quem é você?") == Intent.IDENTITY

    def test_identity_como_chama(self):
        """IDENTITY deve detectar pergunta sobre nome."""
        assert self.classifier.classify("Como você se chama?") == Intent.IDENTITY

    def test_store_info_onde_fica(self):
        """STORE_INFO deve detectar pergunta sobre localização."""
        assert self.classifier.classify("Onde fica a loja?") == Intent.STORE_INFO

    def test_store_info_endereco(self):
        """STORE_INFO deve detectar pergunta sobre endereço."""
        assert self.classifier.classify("Qual o endereço?") == Intent.STORE_INFO

    def test_store_info_localizacao(self):
        """STORE_INFO deve detectar pergunta sobre localização."""
        assert self.classifier.classify("Qual a localização?") == Intent.STORE_INFO

    def test_sales_report_vendas_pendentes(self):
        """SALES_REPORT deve detectar pergunta sobre vendas pendentes."""
        assert self.classifier.classify("Quantas vendas pendentes temos?") == Intent.SALES_REPORT

    def test_sales_report_faturamento(self):
        """SALES_REPORT deve detectar pergunta sobre faturamento."""
        assert self.classifier.classify("Quanto faturamos hoje?") == Intent.SALES_REPORT

    def test_sales_report_vendas_hoje(self):
        """SALES_REPORT deve detectar pergunta sobre vendas do dia."""
        assert self.classifier.classify("Quanto vendemos hoje?") == Intent.SALES_REPORT

    def test_product_count_followup_e_pijamas(self):
        """PRODUCT_COUNT deve detectar follow-up: E pijamas?"""
        assert self.classifier.classify("E pijamas?") == Intent.PRODUCT_COUNT

    def test_product_count_followup_e_calcinhas(self):
        """PRODUCT_COUNT deve detectar follow-up: E calcinhas?"""
        assert self.classifier.classify("E calcinhas?") == Intent.PRODUCT_COUNT

    def test_product_count_followup_e_cuecas(self):
        """PRODUCT_COUNT deve detectar follow-up: E cuecas?"""
        assert self.classifier.classify("E cuecas?") == Intent.PRODUCT_COUNT
