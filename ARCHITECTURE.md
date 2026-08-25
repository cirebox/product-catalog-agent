# ARCHITECTURE.md — Product Catalog Agent

## System Overview

The Product Catalog Agent is a LangGraph-based conversational AI system designed for lingerie product catalog customer service. It uses RAG (Retrieval-Augmented Generation) to provide accurate responses about products, pricing, stock, and policies.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│                    (src/server.py)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────────────────────────────┐ │
│  │  /v1/chat   │───▶│         LangGraph StateGraph        │ │
│  └─────────────┘    │        (catalog_graph.py)           │ │
│                     └─────────────────────────────────────┘ │
│                              │                              │
│              ┌───────────────┼───────────────┐              │
│              ▼               ▼               ▼              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │  CatalogAgent │ │  SalesAgent   │ │ SupportAgent  │    │
│  │  (produtos)   │ │  (pedidos)    │ │ (trocas)      │    │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘    │
│          │                 │                 │              │
│          └─────────────────┼─────────────────┘              │
│                            ▼                                │
│                  ┌─────────────────┐                        │
│                  │   RAG Service   │                        │
│                  │  (FAISS + CSV)  │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Intent Classifier (`intent_classifier.py`)
- Rule-based classifier using regex patterns
- 13 intents across 4 domains
- Returns intent + confidence score
- Fast, no LLM dependency

### 2. LangGraph StateGraph (`catalog_graph.py`)
- **State**: message, intent, confidence, response, context, iteration
- **Nodes**: classify → route → agent → END
- **Guardrail**: MAX_ITERATIONS = 10

### 3. Specialized Agents

| Agent | Domain | Intents |
|-------|--------|---------|
| CatalogAgent | Products | product_info, pricing, stock_check, size_guide, recommendation |
| SalesAgent | Orders | order_status, track_delivery, new_order |
| SupportAgent | Support | return_policy, exchange, complaint |
| GeneralAgent | General | greeting, help, unknown |

### 4. RAG Service (`rag_service.py`)
- **Embeddings**: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Vector Store**: FAISS (local, no external dependencies)
- **Sources**: CSV catalog + markdown documents
- **Chunking**: 500 chars, 50 overlap

### 5. Response Templates (`response_templates.py`)
- PT-BR templates for each intent
- Context injection from RAG results
- Consistent voice and tone

## Data Flow

1. User sends message via `/v1/chat`
2. IntentClassifier determines intent (rule-based)
3. Graph routes to appropriate agent
4. Agent queries RAG service for relevant context
5. Agent formats response using templates
6. Response returned to user

## Performance Characteristics

- **Intent classification**: <1ms (regex-based)
- **RAG search**: ~10-50ms (FAISS local)
- **Response generation**: No LLM calls (template-based)
- **Total latency**: ~50-100ms per request

## Scalability

- **Horizontal**: Multiple FastAPI instances behind load balancer
- **Vertical**: FAISS index can handle 100k+ documents
- **Stateless**: No session state in server (session_id in request)

## Security Considerations

- No PII stored in logs
- Input validation via Pydantic models
- CORS configurable via environment
- No external API calls (local LLM only)

## Trade-offs

| Decision | Pros | Cons |
|----------|------|------|
| Rule-based classifier | Fast, predictable, no LLM cost | Limited to predefined patterns |
| FAISS local | No external dependencies, fast | No persistence across restarts (solved with save/load) |
| Template responses | Consistent, fast, no hallucination | Less flexible than LLM-generated |
| Multi-agent routing | Specialized handling | More complex than single agent |
