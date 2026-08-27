"""
Load Test — Product Catalog Agent (Locust)

Simulates multiple concurrent users sending chat messages.
Run with: locust -f locustfile.py --host=http://localhost:8000

Web UI: http://localhost:8089
"""

import random
from locust import HttpUser, task, between


# Representative messages for load testing
MESSAGES = [
    "oi",
    "bom dia",
    "quero saber sobre o produto 81",
    "quanto custa a tanga 216?",
    "tem estoque de sutiã 6000?",
    "me recomende um conjunto",
    "qual a política de trocas?",
    "como faço um pedido?",
    "onde está meu pedido?",
    "guia de medidas",
    "meu pedido veio com defeito",
    "preço do conjunto 8508",
    "quero trocar de tamanho",
    "quais formas de pagamento?",
    "quanto custa a camisola 885?",
    "produto 8520",
    "disponibilidade da tanga 215",
    "rastrear entrega",
    "ajuda",
    "calcinha 3714",
]


class ChatUser(HttpUser):
    """Simulates a user interacting with the chat agent."""

    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Initialize session for this user."""
        self.session_id = f"load_test_{random.randint(10000, 99999)}"

    @task(5)
    def chat_message(self):
        """Send a chat message (weighted task)."""
        message = random.choice(MESSAGES)
        self.client.post(
            "/v1/chat",
            json={"message": message, "session_id": self.session_id},
            name="/v1/chat",
        )

    @task(1)
    def chat_history(self):
        """Fetch chat history (less frequent)."""
        self.client.get(
            f"/v1/chat/history/{self.session_id}",
            name="/v1/chat/history/{session_id}",
        )

    @task(2)
    def list_products(self):
        """List products."""
        self.client.get("/v1/products", name="/v1/products")

    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health", name="/health")
