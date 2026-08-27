# Arquitetura — Product Catalog Agent

## Visão geral

O Product Catalog Agent é uma API FastAPI que recebe mensagens, classifica a intenção, roteia cada solicitação em um `StateGraph` do LangGraph e consulta as fontes adequadas. SQLite guarda dados operacionais e ChromaDB fornece recuperação semântica para o catálogo e os documentos de domínio.

```text
Browser / cliente REST
          |
          v
FastAPI - src/server.py
  |       |       |
  |       |       +--> SQLiteService
  |       |             sessões, mensagens, produtos,
  |       |             clientes, vendas e feedback
  |       v
  |   CatalogGraph (LangGraph)
  |       |
  |       +--> IntentClassifier --> CatalogAgent
  |       |                         SalesAgent
  |       |                         SupportAgent
  |       |                         GeneralAgent
  |       |
  |       +--> RAGService --> ChromaDB + embeddings
  |       +--> LLMService --> ChatOpenAI / OpenRouter
  |
  +--> interface estática em static/
```

## Fluxo de uma mensagem

1. O cliente envia `POST /v1/chat` com `message` e `session_id`.
2. O servidor cria ou atualiza a sessão e persiste a mensagem do usuário.
3. O `CatalogGraph` executa `classify -> route -> agent -> END`.
4. O classificador regex determina uma intenção e uma confiança relativa.
5. O agente especializado acessa SQLite para dados estruturados ou `RAGService` para contexto semântico.
6. A resposta é gerada pelo handler atual, normalmente com `response_templates.py`, e a mensagem do assistente é persistida.
7. O servidor retorna `reply`, `session_id`, `message_id` e `latency_ms`.

O endpoint `GET /v1/chat/history/{session_id}` consulta as mensagens persistidas, permitindo que a interface restaure a conversa depois de um `F5`.

Além da restauração visual, o `POST /v1/chat` recupera as últimas 10 mensagens antes de processar a nova entrada. Esse histórico é memória de curto prazo do grafo: o `CatalogAgent` usa-o para resolver referências implícitas em perguntas de acompanhamento, como `e esse?`. A janela limitada evita crescimento ilimitado de contexto e mantém previsíveis o custo e a latência.

## Componentes

### FastAPI (`src/server.py`)

Responsável pelo ciclo de vida da aplicação, configuração, montagem dos arquivos estáticos e endpoints REST. No startup:

- inicializa o SQLite;
- importa produtos ausentes de `assets/produtos.csv`;
- inicializa o ChromaDB e constrói o índice quando necessário;
- cria o `CatalogGraph` com os serviços de domínio.

### LangGraph (`src/graphs/catalog_graph.py`)

O estado tipado contém `message`, `intent`, `confidence`, `response`, `context`, `feedback_context`, `iteration` e `node_timings`. O grafo possui limite de `MAX_ITERATIONS = 10` e roteia as intenções para quatro agentes. Cada nó instrumenta seu tempo de execução em `node_timings` para observabilidade de latência.

### Classificador (`src/agents/intent_classifier.py`)

É determinístico e não depende de LLM. Os padrões regex cobrem intenções de catálogo, vendas, suporte e atendimento geral. A confiança é calculada como a pontuação da intenção vencedora dividida pela soma das pontuações encontradas.

### Agentes

| Agente | Responsabilidade |
|---|---|
| `CatalogAgent` | produtos, preços, estoque, tamanhos e recomendações |
| `SalesAgent` | pedidos, entregas e compras |
| `SupportAgent` | trocas, devoluções e reclamações |
| `GeneralAgent` | saudações, ajuda e intenção desconhecida |

Para uma referência explícita, o `CatalogAgent` consulta primeiro `ProductService.get_by_ref`. Quando não há referência encontrada, ele usa o RAG como fallback.

### RAG (`src/services/rag_service.py`)

- **Vector store**: ChromaDB persistente
- **Embeddings**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Fontes**: produtos do SQLite e arquivos Markdown em `docs/`
- **Chunking**: `RecursiveCharacterTextSplitter`, 500 caracteres e sobreposição de 50
- **Persistência**: `/data/chroma` no container ou caminho configurado em `settings.yaml`

O índice é reconstruído quando a coleção está vazia. A reindexação de um produto pode atualizar sua entrada individualmente.

### LLM (`src/services/llm_service.py`)

`LLMService` centraliza a criação de `ChatOpenAI` apontando para `https://openrouter.ai/api/v1`. O modelo e a chave vêm de `OPENROUTER_MODEL` e `OPENROUTER_API_KEY`. Há operações para humanizar erros e gerar clarificações usando histórico.

No estado atual, os handlers principais dos agentes ainda usam `format_response` e templates determinísticos. O serviço de LLM está isolado para adoção progressiva sem acoplar os agentes diretamente ao provedor.

### Persistência (`src/services/sqlite_service.py`)

Uma única base `sessions.db` contém:

- `sessions` e `messages` para conversas;
- `products` e `categories` para catálogo;
- `customers` e `customer_notes` para CRM;
- `sales` e `sale_items` para vendas;
- `feedback` para avaliações das respostas.

No Docker, `./data/sqlite` é montado em `/data/sqlite`, permitindo consultar a mesma base pelo SQLTools no VS Code.

## Configuração e execução

Configurações não sensíveis ficam em `config/settings.yaml`. Segredos ficam no `.env`.

```text
OPENROUTER_API_KEY   chave da OpenRouter
OPENROUTER_MODEL     modelo opcional
SERVER_HOST          host da API
SERVER_PORT          porta da API
```

O Docker Compose persiste ChromaDB em um volume nomeado e SQLite em `data/sqlite`.

## Observabilidade e diagnóstico

### Logging

O logging configurável registra, entre outros eventos:

- intenção e confiança classificadas;
- agente selecionado;
- busca exata de produto e indicação de encontrado;
- consulta RAG e quantidade de resultados;
- tamanho da resposta final.

Esses logs ajudam a distinguir falhas de classificação, roteamento, dados estruturados ausentes e recuperação semântica irrelevante.

### Métricas de Latência

O `MetricsCollector` (`src/infrastructure/metrics.py`) coleta traces de cada request com:

- **Latência total** (end-to-end)
- **Latência por nó** do LangGraph (classify, route, agent)
- **Intent** classificada
- **Erros** quando ocorrem

Endpoints disponíveis:

| Endpoint | Descrição |
|----------|-----------|
| `GET /metrics/latency` | Percentis p50/p95/p99, latência por intent e por nó |
| `GET /metrics/summary` | Resumo geral com traces recentes |

### Benchmarks

Para medir latência com ≥20 perguntas representativas:

```bash
python -m tests.latency_benchmark
```

Gera `reports/LATENCY_REPORT.md` com análise completa.

### Testes de Carga

Para testar sob carga com múltiplos usuários simultâneos:

```bash
locust -f tests/load_test/locustfile.py --host=http://localhost:8000
```

Veja `tests/load_test/README.md` para cenários e parâmetros.

## Segurança e limites

- Pydantic valida o corpo das requisições.
- CORS é configurável por ambiente.
- O conteúdo enviado ao usuário não deve expor detalhes internos de exceções.
- A chave da OpenRouter deve permanecer no `.env` ou em secret manager.
- SQLite e ChromaDB são persistências locais; para múltiplas réplicas, é necessário substituir ou externalizar essas camadas.

## Trade-offs

| Decisão | Benefício | Custo |
|---|---|---|
| Classificador regex | rápido, previsível e barato | limitado a padrões conhecidos |
| ChromaDB persistente | busca semântica e persistência local | exige embeddings e armazenamento vetorial |
| SQLite | simples para dados relacionais e histórico | limita concorrência e escala horizontal |
| Templates determinísticos | respostas consistentes e controláveis | menos flexibilidade linguística |
| OpenRouter via `ChatOpenAI` | acesso padronizado a modelos | depende de credencial, rede e disponibilidade do provedor |
| LangGraph | separa classificação, roteamento e handlers | mais componentes que uma função única |
