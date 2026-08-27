"""
Catalog Graph — Product Catalog Agent
LangGraph StateGraph para roteamento de mensagens.
"""

import operator
import logging
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.catalog_agent import CatalogAgent
from src.agents.general_agent import GeneralAgent
from src.agents.intent_classifier import Intent, IntentClassifier
from src.agents.response_templates import format_response
from src.agents.sales_agent import SalesAgent
from src.agents.support_agent import SupportAgent
from src.services.customer_service import CustomerService
from src.services.product_service import ProductService
from src.services.sale_service import SaleService
from src.services.rag_service import RAGService
from src.services.sqlite_service import SQLiteService
from src.services.feedback_context import FeedbackContextBuilder

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Estado do agente no grafo."""
    message: str
    history: list[dict]
    intent: str
    confidence: float
    response: str
    context: dict
    feedback_context: str
    iteration: int
    node_timings: dict


# Intent to agent mapping
_INTENT_TO_AGENT: dict[Intent, str] = {
    # Catalog
    Intent.PRODUCT_COUNT: "catalog",
    Intent.PRODUCT_INFO: "catalog",
    Intent.PRICING: "catalog",
    Intent.STOCK_CHECK: "catalog",
    Intent.SIZE_GUIDE: "catalog",
    Intent.RECOMMENDATION: "catalog",
    # PDV Actions (routed to catalog agent)
    Intent.LOOKUP_CUSTOMER: "catalog",
    Intent.CREATE_SALE: "catalog",
    Intent.GET_DAILY_REPORT: "catalog",
    Intent.GET_CUSTOMER_HISTORY: "catalog",
    Intent.GET_CUSTOMER_CREDIT: "catalog",
    # Sales
    Intent.ORDER_STATUS: "sales",
    Intent.TRACK_DELIVERY: "sales",
    Intent.NEW_ORDER: "sales",
    Intent.SALES_REPORT: "sales",
    # Support
    Intent.RETURN_POLICY: "support",
    Intent.EXCHANGE: "support",
    Intent.COMPLAINT: "support",
    # General
    Intent.GREETING: "general",
    Intent.HELP: "general",
    Intent.UNKNOWN: "general",
    Intent.STORE_INFO: "general",
    Intent.IDENTITY: "general",
}

MAX_ITERATIONS = 10


class CatalogGraph:
    """LangGraph graph for product catalog agent."""

    def __init__(
        self,
        rag_service: RAGService,
        product_service: ProductService = None,
        customer_service: CustomerService = None,
        sale_service: SaleService = None,
        sqlite_service: SQLiteService = None,
    ):
        self.rag_service = rag_service
        self.product_service = product_service
        self.customer_service = customer_service
        self.sale_service = sale_service
        self.sqlite_service = sqlite_service
        self.classifier = IntentClassifier()
        self.feedback_builder = FeedbackContextBuilder(sqlite_service)

        self.agents = {
            "catalog": CatalogAgent(
                rag_service,
                product_service,
                customer_service,
                sale_service,
            ),
            "sales": SalesAgent(rag_service, sale_service),
            "support": SupportAgent(rag_service),
            "general": GeneralAgent(rag_service),
        }

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("classify", self._classify_intent)
        workflow.add_node("route", self._route_to_agent)
        workflow.add_node("catalog", self._handle_catalog)
        workflow.add_node("sales", self._handle_sales)
        workflow.add_node("support", self._handle_support)
        workflow.add_node("general", self._handle_general)

        # Entry point
        workflow.set_entry_point("classify")

        # Edges
        workflow.add_conditional_edges(
            "classify",
            self._decide_next,
            {
                "route": "route",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "route",
            self._decide_agent,
            {
                "catalog": "catalog",
                "sales": "sales",
                "support": "support",
                "general": "general",
            },
        )

        # All agents go to END
        workflow.add_edge("catalog", END)
        workflow.add_edge("sales", END)
        workflow.add_edge("support", END)
        workflow.add_edge("general", END)

        return workflow.compile()

    async def _classify_intent(self, state: AgentState) -> dict:
        """Classify the user message intent and fetch feedback context."""
        import time as _time
        node_start = _time.monotonic()

        message = state["message"]
        iteration = state.get("iteration", 0)
        timings = dict(state.get("node_timings", {}))

        if iteration >= MAX_ITERATIONS:
            timings["classify"] = round((_time.monotonic() - node_start) * 1000, 1)
            return {
                "response": format_response(Intent.UNKNOWN),
                "iteration": iteration + 1,
                "node_timings": timings,
            }

        intent, confidence = self.classifier.get_confidence(message)
        logger.info(
            "Intent classificada: intent=%s, confidence=%.2f, mensagem=%r",
            intent.value,
            confidence,
            message,
        )

        # Fetch feedback context for this intent
        try:
            feedback_context = await self.feedback_builder.build_context(intent.value)
        except Exception:
            feedback_context = ""

        timings["classify"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {
            "intent": intent.value,
            "confidence": confidence,
            "feedback_context": feedback_context,
            "iteration": iteration + 1,
            "node_timings": timings,
        }

    def _decide_next(self, state: AgentState) -> Literal["route", "end"]:
        """Decide whether to route or end."""
        if state.get("response"):
            return "end"
        return "route"

    def _route_to_agent(self, state: AgentState) -> dict:
        """Route to the appropriate agent based on intent."""
        import time as _time
        node_start = _time.monotonic()

        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent_name = _INTENT_TO_AGENT.get(intent, "general")
        logger.info("Roteando mensagem: intent=%s, agente=%s", intent_str, agent_name)

        timings = dict(state.get("node_timings", {}))
        timings["route"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {"intent": intent_str, "node_timings": timings}

    def _decide_agent(self, state: AgentState) -> Literal["catalog", "sales", "support", "general"]:
        """Decide which agent node to use."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        return _INTENT_TO_AGENT.get(intent, "general")

    async def _handle_catalog(self, state: AgentState) -> dict:
        """Handle catalog-related messages with feedback context."""
        import time as _time
        node_start = _time.monotonic()

        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["catalog"]

        # Build context with feedback
        context = state.get("context", {})
        context["history"] = state.get("history", [])
        feedback_context = state.get("feedback_context", "")
        if feedback_context:
            context["feedback_context"] = feedback_context

        response = await agent.handle(state["message"], intent, context)

        timings = dict(state.get("node_timings", {}))
        timings["agent"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {"response": response, "node_timings": timings}

    async def _handle_sales(self, state: AgentState) -> dict:
        """Handle sales-related messages with feedback context."""
        import time as _time
        node_start = _time.monotonic()

        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["sales"]

        context = state.get("context", {})
        feedback_context = state.get("feedback_context", "")
        if feedback_context:
            context["feedback_context"] = feedback_context

        response = await agent.handle(state["message"], intent, context)

        timings = dict(state.get("node_timings", {}))
        timings["agent"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {"response": response, "node_timings": timings}

    async def _handle_support(self, state: AgentState) -> dict:
        """Handle support-related messages with feedback context."""
        import time as _time
        node_start = _time.monotonic()

        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["support"]

        context = state.get("context", {})
        feedback_context = state.get("feedback_context", "")
        if feedback_context:
            context["feedback_context"] = feedback_context

        response = await agent.handle(state["message"], intent, context)

        timings = dict(state.get("node_timings", {}))
        timings["agent"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {"response": response, "node_timings": timings}

    async def _handle_general(self, state: AgentState) -> dict:
        """Handle general messages with feedback context."""
        import time as _time
        node_start = _time.monotonic()

        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["general"]

        context = state.get("context", {})
        feedback_context = state.get("feedback_context", "")
        if feedback_context:
            context["feedback_context"] = feedback_context

        response = await agent.handle(state["message"], intent, context)

        timings = dict(state.get("node_timings", {}))
        timings["agent"] = round((_time.monotonic() - node_start) * 1000, 1)
        return {"response": response, "node_timings": timings}

    async def run(
        self,
        message: str,
        context: dict = None,
        history: list[dict] = None,
    ) -> dict:
        """Run the graph with a user message.

        Returns:
            dict with keys: response, intent, node_timings
        """
        conversation_history = history or []
        logger.info(
            "Iniciando processamento do agent: mensagem=%r, historico=%d",
            message,
            len(conversation_history),
        )
        initial_state: AgentState = {
            "message": message,
            "history": conversation_history,
            "intent": "",
            "confidence": 0.0,
            "response": "",
            "context": context or {},
            "feedback_context": "",
            "iteration": 0,
            "node_timings": {},
        }

        result = await self.graph.ainvoke(initial_state)
        logger.info(
            "Processamento concluído: intent=%s, resposta_chars=%d",
            result.get("intent", "unknown"),
            len(result.get("response", "")),
        )
        return {
            "response": result.get("response", format_response(Intent.UNKNOWN)),
            "intent": result.get("intent", "unknown"),
            "node_timings": result.get("node_timings", {}),
        }
