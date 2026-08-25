"""
Catalog Graph — Product Catalog Agent
LangGraph StateGraph para roteamento de mensagens.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.catalog_agent import CatalogAgent
from src.agents.general_agent import GeneralAgent
from src.agents.intent_classifier import Intent, IntentClassifier
from src.agents.response_templates import format_response
from src.agents.sales_agent import SalesAgent
from src.agents.support_agent import SupportAgent
from src.services.rag_service import RAGService


class AgentState(TypedDict):
    """Estado do agente no grafo."""
    message: str
    intent: str
    confidence: float
    response: str
    context: dict
    iteration: int


# Intent to agent mapping
_INTENT_TO_AGENT: dict[Intent, str] = {
    # Catalog
    Intent.PRODUCT_INFO: "catalog",
    Intent.PRICING: "catalog",
    Intent.STOCK_CHECK: "catalog",
    Intent.SIZE_GUIDE: "catalog",
    Intent.RECOMMENDATION: "catalog",
    # Sales
    Intent.ORDER_STATUS: "sales",
    Intent.TRACK_DELIVERY: "sales",
    Intent.NEW_ORDER: "sales",
    # Support
    Intent.RETURN_POLICY: "support",
    Intent.EXCHANGE: "support",
    Intent.COMPLAINT: "support",
    # General
    Intent.GREETING: "general",
    Intent.HELP: "general",
    Intent.UNKNOWN: "general",
}

MAX_ITERATIONS = 10


class CatalogGraph:
    """LangGraph graph for product catalog agent."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.classifier = IntentClassifier()

        self.agents = {
            "catalog": CatalogAgent(rag_service),
            "sales": SalesAgent(rag_service),
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

    def _classify_intent(self, state: AgentState) -> dict:
        """Classify the user message intent."""
        message = state["message"]
        iteration = state.get("iteration", 0)

        if iteration >= MAX_ITERATIONS:
            return {
                "response": format_response(Intent.UNKNOWN),
                "iteration": iteration + 1,
            }

        intent, confidence = self.classifier.get_confidence(message)

        return {
            "intent": intent.value,
            "confidence": confidence,
            "iteration": iteration + 1,
        }

    def _decide_next(self, state: AgentState) -> Literal["route", "end"]:
        """Decide whether to route or end."""
        if state.get("response"):
            return "end"
        return "route"

    def _route_to_agent(self, state: AgentState) -> dict:
        """Route to the appropriate agent based on intent."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent_name = _INTENT_TO_AGENT.get(intent, "general")

        return {"intent": intent_str}

    def _decide_agent(self, state: AgentState) -> Literal["catalog", "sales", "support", "general"]:
        """Decide which agent node to use."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        return _INTENT_TO_AGENT.get(intent, "general")

    def _handle_catalog(self, state: AgentState) -> dict:
        """Handle catalog-related messages."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["catalog"]
        import asyncio

        response = asyncio.run(
            agent.handle(state["message"], intent, state.get("context", {}))
        )
        return {"response": response}

    def _handle_sales(self, state: AgentState) -> dict:
        """Handle sales-related messages."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["sales"]
        import asyncio

        response = asyncio.run(
            agent.handle(state["message"], intent, state.get("context", {}))
        )
        return {"response": response}

    def _handle_support(self, state: AgentState) -> dict:
        """Handle support-related messages."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["support"]
        import asyncio

        response = asyncio.run(
            agent.handle(state["message"], intent, state.get("context", {}))
        )
        return {"response": response}

    def _handle_general(self, state: AgentState) -> dict:
        """Handle general messages."""
        intent_str = state.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        agent = self.agents["general"]
        import asyncio

        response = asyncio.run(
            agent.handle(state["message"], intent, state.get("context", {}))
        )
        return {"response": response}

    async def run(self, message: str, context: dict = None) -> str:
        """Run the graph with a user message."""
        initial_state: AgentState = {
            "message": message,
            "intent": "",
            "confidence": 0.0,
            "response": "",
            "context": context or {},
            "iteration": 0,
        }

        result = await self.graph.ainvoke(initial_state)
        return result.get("response", format_response(Intent.UNKNOWN))
