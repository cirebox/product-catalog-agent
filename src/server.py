"""
FastAPI server for the Product Catalog Agent.

Provides REST endpoints for:
- Chat endpoint (POST /v1/chat)
- Product CRUD (GET/POST/PUT/DELETE /v1/products)
- Customer management (GET/POST/PUT/DELETE /v1/customers)
- Customer notes (GET/POST/PUT/DELETE /v1/customers/{id}/notes)
- Sales (POST /v1/sales, GET /v1/sales/{id})
- Credit management (GET /v1/customers/{id}/credit)
- Reports (GET /v1/reports/daily)
- Health check (GET /health)
"""

import csv
import io
import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .graphs.catalog_graph import CatalogGraph
from .infrastructure.metrics import MetricsCollector, RequestTrace
from .services.customer_service import CustomerService
from .services.sale_service import SaleService
from .services.product_service import ProductService
from .services.category_service import CategoryService
from .services.rag_service import RAGService
from .services.sqlite_service import SQLiteService
from .utils.config import Config
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)

# Global metrics collector
_metrics = MetricsCollector(max_traces=5000)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", description="Session identifier")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    message_id: int = 0
    intent: str = ""
    latency_ms: float = 0.0


class FeedbackRequest(BaseModel):
    message_id: int = Field(..., description="ID of the assistant message")
    session_id: str = Field(..., description="Session identifier")
    rating: int = Field(..., description="1 for positive, -1 for negative")
    comment: str = Field(default="", max_length=500, description="Optional comment")


class ProductCreate(BaseModel):
    ref: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=500)
    price: float = Field(default=0, ge=0)
    cost_price: float = Field(default=0, ge=0)
    margin: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    manufacturer: str = Field(default="", max_length=200)
    material: str = Field(default="", max_length=200)
    size: str = Field(default="", max_length=100)
    category: str = Field(default="", max_length=100)


class ProductUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    cost_price: Optional[float] = Field(None, ge=0)
    margin: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    manufacturer: Optional[str] = Field(None, max_length=200)
    material: Optional[str] = Field(None, max_length=200)
    size: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)


class StockReduction(BaseModel):
    quantity: int = Field(..., gt=0)


class ProductResponse(BaseModel):
    id: int
    ref: str
    description: str
    price: float
    cost_price: float = Field(default=0.0)
    margin: float = Field(default=0.0)
    stock: int
    manufacturer: str
    material: str
    size: str
    category: str
    created_at: str
    updated_at: str


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    pages: int


# --- Customer models ---

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=1, max_length=20)
    email: Optional[str] = Field(None, max_length=200)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    email: Optional[str] = Field(None, max_length=200)


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    created_at: str
    updated_at: str


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    pages: int


# --- Note models ---

class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    note_type: str = Field(default="observacao", pattern="^(observacao|preferencia|pedido_especial)$")
    pinned: bool = Field(default=False)


class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    note_type: Optional[str] = Field(None, pattern="^(observacao|preferencia|pedido_especial)$")
    pinned: Optional[bool] = None


class NoteStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(aberto|atendido|cancelado)$")


class NoteResponse(BaseModel):
    id: int
    customer_id: str
    note_type: str
    content: str
    status: str
    pinned: int
    created_at: str
    updated_at: str


# --- Sale models ---

class SaleItemCreate(BaseModel):
    ref: str = Field(..., min_length=1)
    description: str = Field(default="")
    price: float = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0)
    color: str = Field(default="")
    size: str = Field(default="")


class SaleCreate(BaseModel):
    customer_id: Optional[str] = None
    items: List[SaleItemCreate]
    payment_method: str = Field(..., pattern="^(pix|cartao|dinheiro|prazo)$")
    discount: float = Field(default=0, ge=0)
    payment_days: Optional[int] = Field(None, ge=15, le=90)


class SaleResponse(BaseModel):
    id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    total: float
    discount: float
    payment_method: str
    payment_days: Optional[int] = None
    sale_date: str
    due_date: Optional[str] = None
    payment_status: str
    paid_date: Optional[str] = None
    paid_amount: Optional[float] = None
    items: list = []
    created_at: str


class SaleListResponse(BaseModel):
    items: List[SaleResponse]
    total: int
    page: int
    pages: int


class PaymentConfirm(BaseModel):
    paid_date: Optional[str] = None
    paid_amount: Optional[float] = None
    payment_method: Optional[str] = None
    payment_note: Optional[str] = None


class InstallmentSimulation(BaseModel):
    amount: float = Field(..., gt=0)
    installments: int = Field(..., ge=1, le=12)


class DailyReportResponse(BaseModel):
    date: str
    sales: dict
    payments_received: dict
    pending: dict


# --- Category models ---

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: str


# ---------------------------------------------------------------------------
# App factory & lifespan
# ---------------------------------------------------------------------------

_config: Config = Config()
_rag_service: Optional[RAGService] = None
_sqlite_service: Optional[SQLiteService] = None
_product_service: Optional[ProductService] = None
_customer_service: Optional[CustomerService] = None
_sale_service: Optional[SaleService] = None
_category_service: Optional[CategoryService] = None
_catalog_graph: Optional[CatalogGraph] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag_service, _sqlite_service, _product_service, _customer_service, _sale_service, _category_service, _catalog_graph

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

    # Initialize Product Service
    _product_service = ProductService(db_path=_config.sqlite.db_path)

    # Initialize Customer and Sale Services
    _customer_service = CustomerService(db_path=_config.sqlite.db_path)
    _sale_service = SaleService(db_path=_config.sqlite.db_path)

    # Initialize Category Service and seed defaults
    _category_service = CategoryService(db_path=_config.sqlite.db_path)
    seeded_cats = await _category_service.seed_defaults()
    if seeded_cats:
        logger.info("Seeded %d default categories", seeded_cats)

    # Ensure products added to the CSV are present in an existing database.
    seeded = await _product_service.seed_from_csv(_config.rag.csv_path)
    if seeded:
        logger.info("Seeded %d missing products from CSV.", seeded)
    product_count = await _product_service.count()

    logger.info("Products loaded: %d", product_count)

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
        logger.info("Building RAG index from SQLite products...")
        all_products = await _product_service.list_all_active()
        num_chunks = _rag_service.load_products_from_sqlite(all_products)
        logger.info("RAG index built with %d chunks.", num_chunks)
    else:
        logger.info("RAG index loaded: %d chunks.", stats["count"])

    # Initialize catalog graph with all services
    _catalog_graph = CatalogGraph(
        _rag_service,
        _product_service,
        _customer_service,
        _sale_service,
        _sqlite_service,
    )
    logger.info("Catalog graph compiled with all services.")

    yield

    # --- shutdown ---
    logger.info("Server shutting down.")


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


def create_app() -> FastAPI:
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

    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ------------------------------------------------------------------
    # HTML routes
    # ------------------------------------------------------------------

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_ui():
        index_html = static_dir / "index.html"
        if index_html.exists():
            return HTMLResponse(content=index_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Chat UI not found</h1>", status_code=404)

    @app.get("/pdv", response_class=HTMLResponse)
    async def pdv_ui():
        pdv_html = static_dir / "pdv.html"
        if pdv_html.exists():
            return HTMLResponse(content=pdv_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>PDV UI not found</h1>", status_code=404)

    @app.get("/financeiro", response_class=HTMLResponse)
    async def financeiro_ui():
        financeiro_html = static_dir / "financeiro.html"
        if financeiro_html.exists():
            return HTMLResponse(content=financeiro_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Financeiro UI not found</h1>", status_code=404)

    @app.get("/clientes", response_class=HTMLResponse)
    async def clientes_ui():
        clientes_html = static_dir / "clientes.html"
        if clientes_html.exists():
            return HTMLResponse(content=clientes_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Clientes UI not found</h1>", status_code=404)

    @app.get("/produtos", response_class=HTMLResponse)
    async def produtos_ui():
        produtos_html = static_dir / "produtos.html"
        if produtos_html.exists():
            return HTMLResponse(content=produtos_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Produtos UI not found</h1>", status_code=404)

    @app.get("/historico", response_class=HTMLResponse)
    async def historico_ui():
        historico_html = static_dir / "historico.html"
        if historico_html.exists():
            return HTMLResponse(content=historico_html.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Histórico UI not found</h1>", status_code=404)

    # ------------------------------------------------------------------
    # Chat routes
    # ------------------------------------------------------------------

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        trace = RequestTrace()
        start = time.time()

        if _catalog_graph is None:
            trace.error = "graph_not_initialized"
            trace.finish()
            _metrics.record(trace)
            raise HTTPException(503, "Graph not initialized")

        history = []
        if _sqlite_service:
            history = await _sqlite_service.get_messages(req.session_id, limit=10)
            await _sqlite_service.create_session(req.session_id)
            await _sqlite_service.add_message(
                session_id=req.session_id,
                role="user",
                content=req.message,
                metadata={"source": "api", "session_id": req.session_id},
            )

        result = await _catalog_graph.run(req.message, history=history)
        latency_ms = (time.time() - start) * 1000

        # Record trace with node timings
        trace.intent = result.get("intent", "unknown")
        trace.node_timings = result.get("node_timings", {})
        trace.finish()
        _metrics.record(trace)

        assistant_msg_id = 0
        if _sqlite_service:
            db_result = await _sqlite_service.add_message(
                session_id=req.session_id,
                role="assistant",
                content=result["response"],
                intent=result.get("intent", ""),
                metadata={
                    "node_timings": result.get("node_timings", {}),
                    "latency_ms": round(latency_ms, 2),
                },
            )
            assistant_msg_id = db_result.get("message_id", 0)

            # Update session metadata with latest summary
            await _sqlite_service.update_session_metadata(req.session_id)

        return ChatResponse(
            reply=result["response"],
            session_id=req.session_id,
            message_id=assistant_msg_id,
            intent=result.get("intent", ""),
            latency_ms=round(latency_ms, 2),
        )

    @app.get("/v1/chat/history/{session_id}")
    async def chat_history(session_id: str, limit: int = Query(50, ge=1, le=100)):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        return await _sqlite_service.get_messages(session_id, limit=limit)

    # ------------------------------------------------------------------
    # Feedback (RLHF)
    # ------------------------------------------------------------------

    @app.post("/v1/feedback")
    async def submit_feedback(req: FeedbackRequest):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")

        # Check if already feedbacked
        existing = await _sqlite_service.has_feedback(req.message_id)
        if existing:
            return {"status": "already_feedbacked", "message_id": req.message_id}

        # Get intent from the message
        messages = await _sqlite_service.get_messages(req.session_id, limit=50)
        intent = ""
        for msg in messages:
            if msg["id"] == req.message_id:
                intent = msg.get("intent", "")
                break

        result = await _sqlite_service.add_feedback(
            message_id=req.message_id,
            session_id=req.session_id,
            rating=req.rating,
            comment=req.comment,
            intent=intent,
        )

        # Update session metadata with feedback info
        await _sqlite_service.update_session_metadata(req.session_id)

        return result

    @app.get("/v1/feedback/check/{message_id}")
    async def check_feedback(message_id: int):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        has = await _sqlite_service.has_feedback(message_id)
        return {"message_id": message_id, "has_feedback": has}

    @app.get("/v1/feedback/stats")
    async def feedback_stats():
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        return await _sqlite_service.get_feedback_stats()

    @app.get("/v1/feedback/by-intent")
    async def feedback_by_intent():
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        return await _sqlite_service.get_feedback_by_intent()

    @app.get("/v1/feedback/negatives")
    async def feedback_negatives(limit: int = Query(50, ge=1, le=200)):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        return await _sqlite_service.get_negative_feedback_with_context(limit=limit)

    @app.get("/v1/feedback/export")
    async def feedback_export():
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        data = await _sqlite_service.export_feedback()
        return {"total": len(data), "records": data}

    # ------------------------------------------------------------------
    # Session metadata routes
    # ------------------------------------------------------------------

    @app.get("/v1/sessions")
    async def list_sessions(limit: int = Query(50, ge=1, le=200)):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        sessions = await _sqlite_service.list_sessions(limit=limit)
        # Parse metadata JSON for each session
        for session in sessions:
            if isinstance(session.get("metadata"), str):
                try:
                    session["metadata"] = json.loads(session["metadata"])
                except json.JSONDecodeError:
                    session["metadata"] = {}
        return {"sessions": sessions}

    @app.get("/v1/sessions/{session_id}/metadata")
    async def get_session_metadata(session_id: str):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        session = await _sqlite_service.get_session(session_id)
        if not session:
            raise HTTPException(404, f"Session '{session_id}' not found")
        metadata = session.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        return {"session_id": session_id, "metadata": metadata}

    @app.post("/v1/sessions/{session_id}/metadata/refresh")
    async def refresh_session_metadata(session_id: str):
        if _sqlite_service is None:
            raise HTTPException(503, "SQLite service not initialized")
        result = await _sqlite_service.update_session_metadata(session_id)
        if result.get("status") == "no_messages":
            raise HTTPException(404, f"Session '{session_id}' has no messages")
        return result

    # ------------------------------------------------------------------
    # Product CRUD routes
    # ------------------------------------------------------------------

    @app.get("/v1/products", response_model=ProductListResponse)
    async def list_products(
        search: Optional[str] = Query(None, description="Search in description/ref"),
        category: Optional[str] = Query(None, description="Filter by category"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
    ):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")
        result = await _product_service.list_products(
            search=search, category=category, page=page, limit=limit
        )
        return result

    @app.get("/v1/products/search", response_model=ProductListResponse)
    async def search_products(
        query: str = Query(..., min_length=1),
        limit: int = Query(10, ge=1, le=50),
    ):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")
        items = await _product_service.search_products(query, limit=limit)
        return {"items": items, "total": len(items), "page": 1, "pages": 1}

    @app.get("/v1/products/{ref}", response_model=ProductResponse)
    async def get_product(ref: str):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")
        product = await _product_service.get_by_ref(ref)
        if not product:
            matches = await _product_service.search_products(ref, limit=1)
            product = matches[0] if matches else None
        if not product:
            raise HTTPException(404, f"Product '{ref}' not found")
        return product

    @app.post("/v1/products", response_model=ProductResponse, status_code=201)
    async def create_product(req: ProductCreate):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")
        try:
            product = await _product_service.create(
                ref=req.ref,
                description=req.description,
                price=req.price,
                cost_price=req.cost_price,
                margin=req.margin,
                stock=req.stock,
                manufacturer=req.manufacturer,
                material=req.material,
                size=req.size,
                category=req.category,
            )
        except ValueError as e:
            raise HTTPException(409, str(e))

        # Reindex in RAG
        if _rag_service:
            _rag_service.reindex_product(product)

        return product

    @app.put("/v1/products/{ref}", response_model=ProductResponse)
    async def update_product(ref: str, req: ProductUpdate):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")

        existing = await _product_service.get_by_ref(ref)
        if not existing:
            raise HTTPException(404, f"Product '{ref}' not found")

        update_data = req.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(400, "No fields to update")

        product = await _product_service.update(ref, **update_data)

        # Reindex in RAG
        if _rag_service and product:
            _rag_service.reindex_product(product)

        return product

    @app.delete("/v1/products/{ref}", status_code=204)
    async def delete_product(ref: str):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")

        existing = await _product_service.get_by_ref(ref)
        if not existing:
            raise HTTPException(404, f"Product '{ref}' not found")

        await _product_service.delete(ref)

        # Remove from RAG
        if _rag_service:
            _rag_service.remove_product(ref)

        return None

    @app.post("/v1/products/{ref}/reduce", response_model=ProductResponse)
    async def reduce_stock(ref: str, req: StockReduction):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")
        try:
            product = await _product_service.reduce_stock(ref, req.quantity)
        except ValueError as e:
            raise HTTPException(400, str(e))

        # Reindex in RAG (stock changed)
        if _rag_service and product:
            _rag_service.reindex_product(product)

        return product

    @app.get("/v1/products/export/csv")
    async def export_csv():
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")

        products = await _product_service.list_all_active()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=",", quotechar='"')
        for p in products:
            price_str = f"{p['price']:.2f}".replace(".", ",")
            writer.writerow([
                p["ref"],
                p["description"],
                price_str,
                p["stock"],
                p.get("manufacturer", ""),
                p.get("material", ""),
                p.get("size", ""),
                p.get("category", ""),
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=produtos.csv"},
        )

    @app.post("/v1/products/import-csv")
    async def import_csv(file: UploadFile = File(...)):
        if _product_service is None:
            raise HTTPException(503, "Product service not initialized")

        if not file.filename.endswith(".csv"):
            raise HTTPException(400, "Arquivo deve ser .csv")

        content = await file.read()
        try:
            csv_text = content.decode("utf-8-sig")  # utf-8-sig remove BOM automaticamente
        except UnicodeDecodeError:
            csv_text = content.decode("latin-1")

        result = await _product_service.upsert_from_csv(csv_text)

        # Reindex all products in RAG
        if _rag_service:
            all_products = await _product_service.list_all_active()
            _rag_service.reindex_all(all_products)

        return result

    # ------------------------------------------------------------------
    # Category routes
    # ------------------------------------------------------------------

    @app.get("/v1/categories", response_model=List[CategoryResponse])
    async def list_categories():
        if _category_service is None:
            raise HTTPException(503, "Category service not initialized")
        return await _category_service.list_all()

    @app.post("/v1/categories", response_model=CategoryResponse, status_code=201)
    async def create_category(req: CategoryCreate):
        if _category_service is None:
            raise HTTPException(503, "Category service not initialized")
        try:
            return await _category_service.create(name=req.name, description=req.description)
        except ValueError as e:
            raise HTTPException(409, str(e))

    @app.put("/v1/categories/{name}", response_model=CategoryResponse)
    async def update_category(name: str, req: CategoryUpdate):
        if _category_service is None:
            raise HTTPException(503, "Category service not initialized")
        try:
            update_data = req.model_dump(exclude_unset=True)
            if not update_data:
                raise HTTPException(400, "No fields to update")
            return await _category_service.update(name, **update_data)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.delete("/v1/categories/{name}", status_code=204)
    async def delete_category(name: str):
        if _category_service is None:
            raise HTTPException(503, "Category service not initialized")
        try:
            await _category_service.delete(name)
            return None
        except ValueError as e:
            raise HTTPException(400, str(e))

    # ------------------------------------------------------------------
    # Customer routes
    # ------------------------------------------------------------------

    @app.get("/v1/customers", response_model=CustomerListResponse)
    async def list_customers(
        search: Optional[str] = Query(None, description="Search by name or phone"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
    ):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        return await _customer_service.list_customers(search=search, page=page, limit=limit)

    @app.get("/v1/customers/recent")
    async def list_recent_customers():
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        return await _customer_service.list_recent(limit=10)

    @app.post("/v1/customers", response_model=CustomerResponse, status_code=201)
    async def create_customer(req: CustomerCreate):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        try:
            return await _customer_service.create(
                name=req.name, phone=req.phone, email=req.email
            )
        except ValueError as e:
            raise HTTPException(409, str(e))

    @app.get("/v1/customers/{customer_id}", response_model=CustomerResponse)
    async def get_customer(customer_id: str):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        customer = await _customer_service.get_by_id(customer_id)
        if not customer:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        return customer

    @app.put("/v1/customers/{customer_id}", response_model=CustomerResponse)
    async def update_customer(customer_id: str, req: CustomerUpdate):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        existing = await _customer_service.get_by_id(customer_id)
        if not existing:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        try:
            update_data = req.model_dump(exclude_unset=True)
            if not update_data:
                raise HTTPException(400, "No fields to update")
            return await _customer_service.update(customer_id, **update_data)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.delete("/v1/customers/{customer_id}", status_code=204)
    async def delete_customer(customer_id: str):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        existing = await _customer_service.get_by_id(customer_id)
        if not existing:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        await _customer_service.delete(customer_id)
        return None

    # ------------------------------------------------------------------
    # Customer Notes routes
    # ------------------------------------------------------------------

    @app.get("/v1/customers/{customer_id}/notes")
    async def list_notes(
        customer_id: str,
        note_type: Optional[str] = Query(None, description="Filter by type"),
        status: Optional[str] = Query(None, description="Filter by status"),
    ):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        return await _customer_service.list_notes(customer_id, note_type=note_type, status=status)

    @app.post("/v1/customers/{customer_id}/notes", response_model=NoteResponse, status_code=201)
    async def create_note(customer_id: str, req: NoteCreate):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        existing = await _customer_service.get_by_id(customer_id)
        if not existing:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        try:
            return await _customer_service.add_note(
                customer_id, content=req.content, note_type=req.note_type, pinned=req.pinned
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.put("/v1/customers/{customer_id}/notes/{note_id}", response_model=NoteResponse)
    async def update_note(customer_id: str, note_id: int, req: NoteUpdate):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        try:
            update_data = req.model_dump(exclude_unset=True)
            if not update_data:
                raise HTTPException(400, "No fields to update")
            return await _customer_service.update_note(customer_id, note_id, **update_data)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.put("/v1/customers/{customer_id}/notes/{note_id}/pin")
    async def toggle_pin(customer_id: str, note_id: int):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        note = await _customer_service.get_note(customer_id, note_id)
        if not note:
            raise HTTPException(404, "Note not found")
        try:
            new_pinned = not note["pinned"]
            return await _customer_service.update_note(customer_id, note_id, pinned=new_pinned)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.put("/v1/customers/{customer_id}/notes/{note_id}/status")
    async def update_note_status(customer_id: str, note_id: int, req: NoteStatusUpdate):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        try:
            return await _customer_service.update_note(customer_id, note_id, status=req.status)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.delete("/v1/customers/{customer_id}/notes/{note_id}", status_code=204)
    async def delete_note(customer_id: str, note_id: int):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        note = await _customer_service.get_note(customer_id, note_id)
        if not note:
            raise HTTPException(404, "Note not found")
        await _customer_service.delete_note(customer_id, note_id)
        return None

    # ------------------------------------------------------------------
    # Customer Alerts route (for PDV)
    # ------------------------------------------------------------------

    @app.get("/v1/customers/{customer_id}/alerts")
    async def get_customer_alerts(customer_id: str):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        existing = await _customer_service.get_by_id(customer_id)
        if not existing:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        return await _customer_service.get_alerts(customer_id)

    # ------------------------------------------------------------------
    # Customer Credit route (Fiado)
    # ------------------------------------------------------------------

    @app.get("/v1/customers/{customer_id}/credit")
    async def get_customer_credit(customer_id: str):
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        existing = await _customer_service.get_by_id(customer_id)
        if not existing:
            raise HTTPException(404, f"Customer '{customer_id}' not found")
        return await _customer_service.get_credit(customer_id)

    @app.get("/v1/customers/credit/pending")
    async def get_all_pending_credit():
        if _customer_service is None:
            raise HTTPException(503, "Customer service not initialized")
        return await _customer_service.get_all_pending_credit()

    # ------------------------------------------------------------------
    # Sales routes
    # ------------------------------------------------------------------

    @app.post("/v1/sales", response_model=SaleResponse, status_code=201)
    async def create_sale(req: SaleCreate):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        try:
            items = []
            for item in req.items:
                item_data = item.model_dump()
                # Fetch cost_price from product
                if _product_service:
                    product = await _product_service.get_by_ref(item.ref)
                    if product:
                        item_data["cost_price"] = product.get("cost_price", 0)
                items.append(item_data)
            return await _sale_service.create_sale(
                items=items,
                customer_id=req.customer_id,
                payment_method=req.payment_method,
                discount=req.discount,
                payment_days=req.payment_days,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.get("/v1/sales", response_model=SaleListResponse)
    async def list_sales(
        customer_id: Optional[str] = Query(None),
        payment_status: Optional[str] = Query(None),
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
    ):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        return await _sale_service.list_sales(
            customer_id=customer_id,
            payment_status=payment_status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        )

    @app.get("/v1/sales/{sale_id}", response_model=SaleResponse)
    async def get_sale(sale_id: str):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        sale = await _sale_service.get_sale(sale_id)
        if not sale:
            raise HTTPException(404, f"Sale '{sale_id}' not found")
        return sale

    @app.post("/v1/sales/{sale_id}/pay", response_model=SaleResponse)
    async def confirm_payment(sale_id: str, req: PaymentConfirm):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        try:
            return await _sale_service.confirm_payment(
                sale_id=sale_id,
                paid_date=req.paid_date,
                paid_amount=req.paid_amount,
                payment_method=req.payment_method,
                payment_note=req.payment_note,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

    # ------------------------------------------------------------------
    # Reports route
    # ------------------------------------------------------------------

    @app.get("/v1/reports/daily", response_model=DailyReportResponse)
    async def daily_report(
        date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
    ):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        return await _sale_service.get_daily_report(date)

    # ------------------------------------------------------------------
    # Installment simulation
    # ------------------------------------------------------------------

    @app.post("/v1/payments/simulate-installments")
    async def simulate_installments(req: InstallmentSimulation):
        if _sale_service is None:
            raise HTTPException(503, "Sale service not initialized")
        return await _sale_service.simulate_installments(req.amount, req.installments)

    # ------------------------------------------------------------------
    # RAG Reindex (SSE)
    # ------------------------------------------------------------------

    @app.get("/v1/rag/reindex")
    async def rag_reindex():
        if _rag_service is None or _product_service is None:
            raise HTTPException(503, "Services not initialized")

        from fastapi.responses import StreamingResponse
        import json

        async def event_stream():
            products = await _product_service.list_all_active()
            for step, current, total, message in _rag_service.reindex_with_progress(products):
                data = json.dumps({
                    "step": step,
                    "current": current,
                    "total": total,
                    "message": message,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ------------------------------------------------------------------
    # Health & Metrics
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health():
        rag_stats = _rag_service.get_collection_stats() if _rag_service else {}
        sqlite_stats = await _sqlite_service.get_stats() if _sqlite_service else {}
        product_count = await _product_service.count() if _product_service else 0
        return {
            "status": "ok",
            "service": "product-catalog-agent",
            "rag": rag_stats,
            "sqlite": sqlite_stats,
            "products": product_count,
        }

    @app.get("/metrics")
    async def metrics():
        rag_stats = _rag_service.get_collection_stats() if _rag_service else {}
        sqlite_stats = await _sqlite_service.get_stats() if _sqlite_service else {}
        product_count = await _product_service.count() if _product_service else 0
        return {
            "service": "product-catalog-agent",
            "status": "running",
            "rag": rag_stats,
            "sqlite": sqlite_stats,
            "products": product_count,
        }

    @app.get("/metrics/latency")
    async def latency_metrics():
        """Detailed latency report with percentiles (p50, p95, p99)."""
        return _metrics.latency_report()

    @app.get("/metrics/summary")
    async def metrics_summary():
        """General metrics summary with traces."""
        return _metrics.summary()

    return app


app = create_app()
