# Product Catalog Agent

LangGraph agent for lingerie product catalog customer service via RAG.

## Overview

An intelligent customer service agent that helps customers with:
- Product information and pricing
- Stock availability checks
- Size guide assistance
- Product recommendations
- Order tracking
- Returns and exchanges

All responses are in PT-BR (Brazilian Portuguese).

## Architecture

- **LangGraph StateGraph** for routing messages to specialized agents
- **RAG** with FAISS + sentence-transformers for catalog search
- **4 specialized agents**: Catalog, Sales, Support, General
- **Rule-based intent classifier** for fast routing
- **FastAPI server** with REST endpoints

## Quick Start

### Prerequisites
- Python 3.11+
- Ollama (for local LLM) or OpenAI API key

### Installation

```bash
# Clone the repository
git clone git@github.com:cirebox/product-catalog-agent.git
cd product-catalog-agent

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your OpenRouter API key
```

### Run Demo

```bash
python main.py --demo
```

### Start Server

```bash
python main.py
```

### Test API

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "oi", "session_id": "test"}'
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/v1/chat` | Send message, get response |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Metrics |

## Project Structure

```
src/
├── agents/          # Specialized agents
├── graphs/          # LangGraph StateGraph
├── services/        # RAG, LLM, Session services
├── infrastructure/  # Cache, errors, metrics
├── tools/           # Input validation
└── utils/           # Config, logging, state reducers

docs/                # RAG documents
assets/              # Product catalog CSV
config/              # Settings and env vars
tests/               # Unit tests
```

## Data Sources

- **Product Catalog**: `assets/produtos.csv` (63 lingerie products)
- **FAQ**: `docs/FAQ.md`
- **Returns Policy**: `docs/politica-trocas.md`
- **Size Guide**: `docs/guia-medidas.md`

## Testing

```bash
pytest tests/ -v
```

## Docker

```bash
docker-compose up -d
```

## CI/CD

GitHub Actions pipeline runs:
- Black (code formatting)
- isort (import sorting)
- Pytest (unit tests)

## License

Private - Cirebox Team
