"""
FastAPI server for the Product Catalog Agent.

Provides REST endpoints for:
- Chat endpoint (POST /v1/chat)
- Health check (GET /health)
- Metrics (GET /metrics)
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .graphs.catalog_graph import CatalogGraph
from .services.rag_service import RAGService
from .services.sqlite_service import SQLiteService
from .utils.config import Config
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", description="Session identifier")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    reply: str
    session_id: str
    intent: str = ""
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# App factory & lifespan
# ---------------------------------------------------------------------------

_config: Config = Config()
_rag_service: Optional[RAGService] = None
_sqlite_service: Optional[SQLiteService] = None
_catalog_graph: Optional[CatalogGraph] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    global _rag_service, _sqlite_service, _catalog_graph

    # --- startup ---
    setup_logging(
        level=_config.logging.level,
        fmt=_config.logging.format,
        json_output=_config.logging.json_output,
        file_path=_config.logging.file_path,
    )
    _config.validate_startup()

    # Initialize SQLite service
    _sqlite_service = SQLiteService(db_path=_config.sqlite.db_path)
    await _sqlite_service.initialize()
    logger.info("SQLite initialized at %s", _config.sqlite.db_path)

    # Initialize RAG service with ChromaDB
    _rag_service = RAGService(
        docs_dir=_config.rag.docs_dir,
        csv_path=_config.rag.csv_path,
        persist_dir=_config.chroma.persist_dir,
        collection_name=_config.chroma.collection,
        model_name=_config.chroma.embedding_model,
    )

    # Build RAG index if empty
    stats = _rag_service.get_collection_stats()
    if stats["count"] == 0:
        logger.info("Building RAG index from scratch...")
        num_chunks = _rag_service.load_and_index()
        logger.info("RAG index built with %d chunks.", num_chunks)
    else:
        logger.info("RAG index loaded: %d chunks.", stats["count"])

    # Initialize catalog graph
    _catalog_graph = CatalogGraph(_rag_service)
    logger.info("Catalog graph compiled.")

    yield

    # --- shutdown ---
    logger.info("Server shutting down.")


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="Product Catalog Agent API",
        version="1.0.0",
        lifespan=lifespan,
        default_response_class=UTF8JSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_config.server.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---

    @app.get("/health")
    async def health():
        rag_stats = _rag_service.get_collection_stats() if _rag_service else {}
        sqlite_stats = await _sqlite_service.get_stats() if _sqlite_service else {}
        return {
            "status": "ok",
            "service": "product-catalog-agent",
            "rag": rag_stats,
            "sqlite": sqlite_stats,
        }

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        """Process a message through the catalog agent graph."""
        import time

        start = time.time()

        if _catalog_graph is None:
            raise HTTPException(503, "Graph not initialized")

        # Store user message
        if _sqlite_service:
            await _sqlite_service.create_session(req.session_id)
            await _sqlite_service.add_message(
                session_id=req.session_id,
                role="user",
                content=req.message,
            )

        # Get response from graph
        response = await _catalog_graph.run(req.message)
        latency_ms = (time.time() - start) * 1000

        # Store assistant response
        if _sqlite_service:
            await _sqlite_service.add_message(
                session_id=req.session_id,
                role="assistant",
                content=response,
            )

        return ChatResponse(
            reply=response,
            session_id=req.session_id,
            latency_ms=round(latency_ms, 2),
        )

    @app.get("/metrics")
    async def metrics():
        """Return basic metrics."""
        rag_stats = _rag_service.get_collection_stats() if _rag_service else {}
        sqlite_stats = await _sqlite_service.get_stats() if _sqlite_service else {}
        return {
            "service": "product-catalog-agent",
            "status": "running",
            "rag": rag_stats,
            "sqlite": sqlite_stats,
        }

    return app


# Allow ``uvicorn src.server:app``
app = create_app()
