"""
Tests for IntentClassifier.
"""

import pytest
from src.agents.intent_classifier import Intent, IntentClassifier


@pytest.fixture
def classifier():
    return IntentClassifier()


class TestIntentClassifier:
    """Tests for intent classification."""

    def test_greeting(self, classifier):
        assert classifier.classify("oi") == Intent.GREETING
        assert classifier.classify("olá") == Intent.GREETING
        assert classifier.classify("bom dia") == Intent.GREETING

    def test_product_info(self, classifier):
        assert classifier.classify("quero ver os produtos") == Intent.PRODUCT_INFO
        assert classifier.classify("me mostra o catálogo") == Intent.PRODUCT_INFO

    def test_product_count(self, classifier):
        assert classifier.classify("quantos produtos temos?") == Intent.PRODUCT_COUNT
        assert classifier.classify("qual o total de produtos?") == Intent.PRODUCT_COUNT

    def test_pricing(self, classifier):
        assert classifier.classify("quanto custa?") == Intent.PRICING
        assert classifier.classify("qual o preço?") == Intent.PRICING
        assert classifier.classify("valor do conjunto") == Intent.PRICING

    def test_stock_check(self, classifier):
        assert classifier.classify("tem estoque?") == Intent.STOCK_CHECK
        assert classifier.classify("ainda tem tanga 216?") == Intent.STOCK_CHECK

    def test_size_guide(self, classifier):
        assert classifier.classify("qual o tamanho?") == Intent.SIZE_GUIDE
        assert classifier.classify("tabela de medidas") == Intent.SIZE_GUIDE

    def test_recommendation(self, classifier):
        assert classifier.classify("me recomende algo") == Intent.RECOMMENDATION
        assert classifier.classify("o que você recomenda?") == Intent.RECOMMENDATION

    def test_order_status(self, classifier):
        assert classifier.classify("onde está meu pedido?") == Intent.ORDER_STATUS
        assert classifier.classify("status do pedido") == Intent.ORDER_STATUS

    def test_track_delivery(self, classifier):
        assert classifier.classify("quando chega?") == Intent.TRACK_DELIVERY
        assert classifier.classify("prazo de entrega") == Intent.TRACK_DELIVERY

    def test_return_policy(self, classifier):
        assert classifier.classify("quero devolver") == Intent.RETURN_POLICY
        assert classifier.classify("política de devolução") == Intent.RETURN_POLICY

    def test_exchange(self, classifier):
        assert classifier.classify("quero trocar") == Intent.EXCHANGE
        assert classifier.classify("tamanho errado") == Intent.EXCHANGE

    def test_complaint(self, classifier):
        assert classifier.classify("produto com defeito") == Intent.COMPLAINT
        assert classifier.classify("reclamação") == Intent.COMPLAINT

    def test_help(self, classifier):
        assert classifier.classify("ajuda") == Intent.HELP
        assert classifier.classify("como funciona?") == Intent.HELP

    def test_unknown(self, classifier):
        assert classifier.classify("") == Intent.UNKNOWN
        assert classifier.classify("xyzabc123") == Intent.UNKNOWN

    def test_confidence(self, classifier):
        intent, confidence = classifier.get_confidence("oi")
        assert intent == Intent.GREETING
        assert 0.0 <= confidence <= 1.0

    def test_empty_message(self, classifier):
        assert classifier.classify("") == Intent.UNKNOWN
        assert classifier.classify("   ") == Intent.UNKNOWN
