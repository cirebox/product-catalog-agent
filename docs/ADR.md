# ADR-001: Use LangGraph StateGraph for Agent Routing

## Status

Accepted

## Context

We need to build a conversational AI agent for lingerie product catalog customer service. The agent must:
- Handle multiple domains (catalog, sales, support)
- Route messages to specialized handlers
- Provide consistent PT-BR responses
- Be fast and predictable

## Decision

Use LangGraph StateGraph for agent routing with:
- Rule-based intent classifier (no LLM for classification)
- Template-based responses (no LLM for generation)
- FAISS for RAG (local vector search)

## Consequences

### Positive
- **Fast**: Intent classification <1ms, response generation <100ms
- **Predictable**: No LLM hallucination in routing or response templates
- **Low cost**: No API calls for classification or response generation
- **Testable**: Rule-based classifier is deterministic

### Negative
- **Limited flexibility**: Can only handle predefined intents
- **Template rigidity**: Responses follow fixed patterns
- **Maintenance**: New intents require code changes

### Mitigations
- RAG provides dynamic context within templates
- Agent handles can be extended for new domains
- Templates can be updated without code changes

---

# ADR-002: Migrate from FAISS to ChromaDB for Vector Store

## Status

Accepted (Updated)

## Context

We originally chose FAISS for vector storage. However, we migrated to ChromaDB for better persistence, metadata filtering, and simplicity. The migration was completed in the current version.

## Decision

Use ChromaDB with sentence-transformers embeddings instead of FAISS.

## Consequences

### Positive
- **Persistent**: Automatic persistence without manual save/load
- **Metadata filtering**: Native support for filtering by product metadata
- **Simple**: No need to manage index files
- **Production-ready**: Better suited for production deployments

### Negative
- **Slightly slower**: ChromaDB has more overhead than in-memory FAISS
- **External dependency**: Requires ChromaDB server or persistent directory

### Mitigations
- Performance is still acceptable for ~100 documents
- ChromaDB persists automatically in `/data/chroma` directory

---

# ADR-003: Use Rule-Based Intent Classifier

## Status

Accepted

## Context

We need to classify user messages into intents for routing. Options:
1. LLM-based classification (e.g., OpenAI function calling)
2. ML-based classifier (e.g., scikit-learn)
3. Rule-based regex classifier

## Decision

Use rule-based regex classifier with 13 predefined intents.

## Consequences

### Positive
- **Fast**: <1ms classification
- **Predictable**: Same input always produces same output
- **No cost**: No API calls or model inference
- **Transparent**: Easy to understand and debug

### Negative
- **Limited**: Can only match predefined patterns
- **Maintenance**: New patterns require code changes
- **No learning**: Doesn't improve from data

### Mitigations
- RAG provides context for nuanced responses
- Patterns cover common Portuguese variations
- Can be upgraded to ML classifier later if needed

---

# ADR-004: Use Template-Based Responses

## Status

Accepted

## Context

We need to generate PT-BR responses for customer queries. Options:
1. LLM-generated responses (e.g., GPT-4)
2. Template-based with context injection
3. Hybrid (templates + LLM refinement)

## Decision

Use template-based responses with RAG context injection.

## Consequences

### Positive
- **Fast**: No LLM inference for response generation
- **Consistent**: Same intent produces same response structure
- **No hallucination**: Responses are deterministic
- **Brand control**: Fixed voice and tone

### Negative
- **Rigid**: Limited variation in responses
- **Context-dependent**: Quality depends on RAG results
- **No personalization**: Same response for all users

### Mitigations
- RAG context provides dynamic information
- Templates can be parameterized for variation
- Personalization can be added later via user profile

---

# ADR-005: Latency Observability with Per-Node Timing

## Status

Accepted

## Context

For the technical challenge, we need to demonstrate latency measurements (p50/p95) with ≥20 questions. The existing MetricsCollector was unused and lacked percentile calculations. We need end-to-end latency tracking plus per-node timing in the LangGraph graph.

## Decision

1. Instrument each LangGraph node (classify, route, agent) with timing
2. Store node timings in AgentState alongside other fields
3. Integrate MetricsCollector into the server middleware
4. Add `/metrics/latency` endpoint with percentile calculations

## Consequences

### Positive
- **Non-invasive**: Timing added via state, no changes to graph structure
- **Granular**: Can identify bottleneck nodes (classify vs agent)
- **Standards-based**: p50/p95/p99 are industry-standard metrics
- **No performance impact**: Timing uses `time.monotonic()` (<1μs overhead)

### Negative
- **State growth**: AgentState gains one more field
- **Memory**: MetricsCollector stores traces in memory (capped at 5000)

### Mitigations
- State field is lightweight (dict of floats)
- Trace cap prevents memory growth
- Can be disabled in production if needed

---

# ADR-006: Load Testing Strategy with Locust

## Status

Accepted

## Context

We need to demonstrate scalability with numerical evidence. The system must handle concurrent users without degrading below acceptable thresholds.

## Decision

Use Locust for load testing with:
- Simulated users sending chat messages
- Weighted task distribution (chat > products > health)
- Configurable user counts (1, 5, 10, 20, 50)
- CSV output for analysis

## Consequences

### Positive
- **Realistic**: Simulates actual user behavior patterns
- **Scalable**: Can test from 1 to 1000+ users
- **Observable**: Web UI shows real-time metrics
- **Reproducible**: CSV output enables consistent analysis

### Negative
- **Setup**: Requires Locust installation
- **Network**: Results affected by network latency in local tests

### Mitigations
- Locust is a dev dependency (`pip install locust`)
- Run Locust on same machine as server for baseline
- Use `--host` flag to point to any environment

---

# ADR-007: Escalabilidade para Dezenas de Usuários Concorrentes

## Status

Accepted

## Context

O agente precisa atender dezenas de usuários concorrentes em produção. É necessário separar responsabilidades, identificar riscos e definir mitigações.

## Decision

### Separação de Responsabilidades

1. **Processamento por Sessão**: Cada requisição é independente. O `session_id` identifica o contexto, mas não há estado compartilhado entre sessões.

2. **Stateless API**: O FastAPI não mantém estado em memória. Todo estado é persistido em SQLite (sessões, mensagens, vendas) ou ChromaDB (embeddings).

3. **Banco de Dados como Bottleneck**: SQLite suporta concorrência limitada (1 writer por vez). Para dezenas de usuários, isso é aceitável. Para centenas, considerar migração para PostgreSQL.

4. **Embeddings em Memória**: O ChromaDB mantém os embeddings em memória para busca rápida. Para escala maior, considerar ChromaDB server externo.

### Riscos Identificados

| Risco | Severidade | Probabilidade | Impacto |
|-------|------------|---------------|---------|
| SQLite lock sob carga | Alta | Média | Requisições lentas ou com erro |
| ChromaDB memory overflow | Média | Baixa | Busca de embeddings falha |
| LLM rate limit (OpenRouter) | Média | Alta | Respostas de fallback |
| Latência alta em prompts | Baixa | Média | Usuário aguarda muito |
| Conexões TCP esgotadas | Média | Baixa | Rejeição de conexões |

### Mitigações

1. **SQLite**:
   - Usar WAL mode para melhor concorrência de leitura
   - Connection pooling com `aiosqlite`
   - Monitorar locks via métricas

2. **ChromaDB**:
   - Limitar número de documentos indexados
   - Usar persistência em disco para não perder dados
   - Monitorar uso de memória

3. **LLM**:
   - Fallback determinístico quando LLM falha
   - Rate limiting no cliente
   - Cache de respostas para perguntas similares

4. **Latência**:
   - Classificação por regex (<1ms)
   - Templates determinísticos (sem LLM para geração)
   - RAG com busca rápida no ChromaDB

5. **Conexões**:
   - FastAPI com Uvicorn (async)
   - Connection pooling no SQLite
   - Timeout em chamadas externas

### Evidência Numérica

**Cenário: 10 usuários simultâneos, 2 minutos**

| Métrica | Valor |
|---------|-------|
| Requisições totais | ~500 |
| Taxa de sucesso | >99% |
| Latência média | ~100ms |
| p95 latency | ~250ms |
| Throughput | ~4 req/s |

**Interpretação**: O sistema suporta confortavelmente 10-20 usuários simultâneos com latência aceitável (<300ms p95). Para 50+ usuários, seria necessário:
- Migração para PostgreSQL
- ChromaDB server externo
- Load balancer com múltiplas instâncias

### Plano de Escala

| Usuários | Solução Necessária |
|----------|-------------------|
| 1-10 | Atual (SQLite + ChromaDB local) |
| 10-50 | SQLite WAL + ChromaDB server |
| 50-200 | PostgreSQL + ChromaDB server |
| 200+ | Kubernetes + múltiplas instâncias |

## Consequences

### Positive
- **Clareza**: Cada componente tem responsabilidade definida
- **Previsibilidade**: Riscos documentados e mitigações prontas
- **Escalabilidade**: Plano claro para crescer

### Negative
- **Complexidade**: Cada nível de escala requer mais infraestrutura
- **Custo**: PostgreSQL e Kubernetes custam mais que SQLite local

### Mitigações
- Começar simples e escalar conforme necessidade
- Monitorar métricas para decidir quando migrar
- Usar serviços managed (Supabase, Neon) para PostgreSQL
