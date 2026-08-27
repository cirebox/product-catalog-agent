# AGENTS_ALLOS.md — Product Catalog Agent

## Visão Geral

Agente de IA para atendimento interno (backoffice) de loja de lingerie.
Auxilia o time de vendas e operações com consultas de produtos, preços, estoque, pedidos, clientes e relatórios via interface conversacional em PT-BR.

---

## Stack

- **Framework**: LangGraph (StateGraph)
- **Embeddings**: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Vector Store**: ChromaDB (persistente)
- **LLM**: OpenRouter (opcional, para fallback e clarificação contextual)
- **API**: FastAPI + Uvicorn
- **Banco**: SQLite (sessões, mensagens, produtos, clientes, vendas, feedback)
- **Linguagem**: Python 3.11+

---

## Estrutura do Projeto

```
product-catalog-agent/
├── src/
│   ├── agents/
│   │   ├── base_agent.py        # BaseAgent (dispatch pattern)
│   │   ├── models.py            # AgentResult Pydantic model
│   │   ├── intent_classifier.py # Classificador de intents (27 intents)
│   │   ├── response_templates.py # Templates de resposta
│   │   ├── catalog_agent.py     # Agente de catálogo
│   │   ├── sales_agent.py       # Agente de vendas
│   │   ├── support_agent.py     # Agente de suporte
│   │   └── general_agent.py     # Agente geral
│   ├── graphs/
│   │   └── catalog_graph.py     # StateGraph principal
│   ├── services/
│   │   ├── rag_service.py       # RAG com ChromaDB
│   │   ├── llm_service.py       # Serviço LLM (OpenRouter)
│   │   ├── sqlite_service.py    # SQLite (sessões, mensagens)
│   │   ├── product_service.py   # CRUD de produtos
│   │   ├── customer_service.py  # CRUD de clientes
│   │   ├── sale_service.py      # CRUD de vendas
│   │   ├── category_service.py  # Categorias
│   │   └── feedback_context.py  # Contexto de feedback
│   ├── prompts/
│   │   └── system_prompt.py     # Persona "Maria"
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
│   ├── produtos.csv             # Catálogo de produtos
│   └── produtos_completo.csv    # Catálogo completo com categorias
├── docs/
│   ├── ADR.md                   # Decisões arquiteturais
│   ├── DEMO_SCRIPT.md           # Roteiro de demonstração
│   ├── FAQ.md                   # Perguntas frequentes
│   ├── catalogo-produtos.md     # Catálogo formatado
│   ├── politica-trocas.md       # Política de trocas/devoluções
│   └── guia-medidas.md          # Guia de medidas
├── tests/
│   ├── test_intent_classifier.py
│   ├── test_new_intents.py
│   ├── test_system_prompt.py
│   ├── test_rag_service.py
│   ├── latency_benchmark.py     # Benchmark de latência
│   └── load_test/
│       ├── locustfile.py        # Teste de carga
│       └── README.md
├── static/                      # Interface web
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
**Quando chamar**: informações de produtos, preços, estoque, guia de medidas, recomendações, contagem por categoria.

### @sales
**Quando chamar**: status de pedidos, rastreamento de entregas, como comprar, relatórios de vendas.

### @support
**Quando chamar**: trocas, devoluções, reclamações, política de trocas.

### @general
**Quando chamar**: saudações, ajuda geral, informações da loja, identidade, fallback.

---

## Intents do Domínio

| Intent | Descrição | Agente |
|--------|-----------|--------|
| `product_count` | Contagem de produtos (total ou por categoria) | catalog |
| `product_info` | Informações sobre produto | catalog |
| `pricing` | Preço de produto | catalog |
| `stock_check` | Verificar estoque | catalog |
| `size_guide` | Guia de medidas | catalog |
| `user_measurement` | Medidas do usuário | catalog |
| `recommendation` | Recomendação de produto | catalog |
| `order_status` | Status do pedido | sales |
| `track_delivery` | Rastreamento de entrega | sales |
| `new_order` | Como fazer pedido | sales |
| `sales_report` | Relatório de vendas | sales |
| `return_policy` | Política de devolução | support |
| `exchange` | Troca de produto | support |
| `complaint` | Reclamação | support |
| `store_info` | Informações da loja (endereço, pagamento) | general |
| `identity` | Identidade do assistente | general |
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
cp .env.example .env
# Editar .env com sua OPENROUTER_API_KEY (opcional)
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
| `GET` | `/v1/chat/history/{session_id}` | Histórico da sessão |
| `POST` | `/v1/feedback` | Registrar feedback |
| `GET` | `/v1/products` | Lista de produtos |
| `POST` | `/v1/products` | Cadastrar produto |
| `POST` | `/v1/products/import-csv` | Importar CSV |
| `GET` | `/v1/customers` | Lista de clientes |
| `POST` | `/v1/customers` | Cadastrar cliente |
| `GET` | `/v1/sales` | Lista de vendas |
| `POST` | `/v1/sales` | Registrar venda |
| `GET` | `/v1/categories` | Lista de categorias |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Métricas |
| `GET` | `/metrics/latency` | Latência com percentis |
| `GET` | `/metrics/summary` | Resumo de métricas |

---

## Testes

```bash
# Testes unitários
pytest tests/ -v

# Benchmark de latência (26 perguntas)
python -m tests.latency_benchmark

# Teste de carga (Locust)
locust -f tests/load_test/locustfile.py --host=http://localhost:8000
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
