# AGENTS_ALLOS.md — Product Catalog Agent

## Visão Geral

Agent LangGraph para atendimento a consumidor de loja de lingerie.
Respostas em PT-BR via RAG sobre catálogo de produtos (CSV) e documentos de domínio.

---

## Stack

- **Framework**: LangGraph (StateGraph)
- **Embeddings**: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Vector Store**: FAISS (local)
- **LLM**: Ollama (local, sem custo) ou OpenAI (opcional)
- **API**: FastAPI + Uvicorn
- **Linguagem**: Python 3.11+

---

## Estrutura do Projeto

```
product-catalog-agent/
├── src/
│   ├── agents/
│   │   ├── base_agent.py        # BaseAgent (dispatch pattern)
│   │   ├── models.py            # AgentResult Pydantic model
│   │   ├── intent_classifier.py # Classificador de intents
│   │   ├── response_templates.py # Templates de resposta
│   │   ├── catalog_agent.py     # Agente de catálogo
│   │   ├── sales_agent.py       # Agente de vendas
│   │   ├── support_agent.py     # Agente de suporte
│   │   └── general_agent.py     # Agente geral
│   ├── graphs/
│   │   └── catalog_graph.py     # StateGraph principal
│   ├── services/
│   │   ├── rag_service.py       # RAG com FAISS
│   │   ├── llm_service.py       # Serviço LLM
│   │   └── session_manager.py   # Gerenciamento de sessões
│   ├── infrastructure/
│   │   ├── cache.py             # Cache TTL
│   │   ├── errors.py            # Erros padronizados
│   │   └── metrics.py           # Métricas de request
│   ├── tools/
│   │   └── input_validator.py   # Validação de input
│   ├── utils/
│   │   ├── config.py            # Configuração (pydantic-settings)
│   │   ├── logging.py           # Logging configurável
│   │   └── state_reducers.py    # Reducers do LangGraph
│   └── server.py                # FastAPI server
├── assets/
│   └── produtos.csv             # Catálogo de produtos (63 itens)
├── docs/
│   ├── catalogo-produtos.md     # Catálogo formatado
│   ├── FAQ.md                   # Perguntas frequentes
│   ├── politica-trocas.md       # Política de trocas/devoluções
│   └── guia-medidas.md          # Guia de medidas
├── config/
│   ├── settings.yaml            # Config não-sensível
│   └── .env.example             # Template de variáveis
├── tests/
│   ├── test_intent_classifier.py
│   └── test_rag_service.py
├── main.py                      # Entry point
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Agentes Disponíveis

### @catalog
**Quando chamar**: informações de produtos, preços, estoque, guia de medidas, recomendações.

### @sales
**Quando chamar**: status de pedidos, rastreamento de entregas, como comprar.

### @support
**Quando chamar**: trocas, devoluções, reclamações, política de trocas.

### @general
**Quando chamar**: saudações, ajuda geral, fallback.

---

## Intents do Domínio

| Intent | Descrição | Agente |
|--------|-----------|--------|
| `product_info` | Informações sobre produto | catalog |
| `pricing` | Preço de produto | catalog |
| `stock_check` | Verificar estoque | catalog |
| `size_guide` | Guia de medidas | catalog |
| `recommendation` | Recomendação de produto | catalog |
| `order_status` | Status do pedido | sales |
| `track_delivery` | Rastreamento de entrega | sales |
| `new_order` | Como fazer pedido | sales |
| `return_policy` | Política de devolução | support |
| `exchange` | Troca de produto | support |
| `complaint` | Reclamação | support |
| `greeting` | Saudação | general |
| `help` | Ajuda | general |

---

## Como Rodar

### 1. Instalar dependências
```bash
pip install -e ".[dev]"
```

### 2. Configurar variáveis
```bash
cp config/.env.example config/.env
# Editar .env com suas configurações
```

### 3. Rodar demo (offline)
```bash
python main.py --demo
```

### 4. Iniciar servidor
```bash
python main.py
```

### 5. Testar endpoint
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "oi", "session_id": "test"}'
```

---

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/v1/chat` | Enviar mensagem, obter resposta |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Métricas |

---

## Testes

```bash
pytest tests/ -v
```

---

## Deploy

### Docker
```bash
docker-compose up -d
```

### CI/CD
O pipeline CI roda automaticamente:
- Black (formatação)
- isort (imports)
- Pytest (testes)
