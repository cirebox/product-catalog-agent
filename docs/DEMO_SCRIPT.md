# Roteiro de Demonstração — Product Catalog Agent

## Pré-requisitos

1. Servidor rodando: `python main.py`
2. Interface web: `http://localhost:8000/chat`

---

## Demo Flow (5-10 minutos)

### 1. Contextualização (2 min)

**Falar sobre:**
- Cenário: Atendimento ao consumidor de loja de lingerie
- Stack: LangGraph + ChromaDB + SQLite + FastAPI
- Decisões: Classificador regex (sem LLM para classificação), templates determinísticos
- 20 intents, 4 agentes especializados

### 2. Demo ao Vivo (3-5 min)

#### Pergunta 1: Saudação
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"oi", "session_id":"demo_1"}'
```
**Esperado**: Resposta de saudação em PT-BR, intent=GREETING

#### Pergunta 2: Informação de Produto (busca exata)
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"quero saber sobre o produto 81", "session_id":"demo_1"}'
```
**Esperado**: Card do produto com código, nome, preço, estoque

#### Pergunta 3: Preço
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"quanto custa a tanga 216?", "session_id":"demo_1"}'
```
**Esperado**: Preço do produto, intent=PRICING

#### Pergunta 4: Estoque
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"tem estoque de sutiã 6000?", "session_id":"demo_1"}'
```
**Esperado**: Informação de estoque, intent=STOCK_CHECK

#### Pergunta 5: RAG (política de trocas)
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"qual a política de trocas?", "session_id":"demo_1"}'
```
**Esperado**: Resposta baseada no documento politica-trocas.md

#### Pergunta 6: Guia de Medidas (RAG)
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"como tirar medida de busto?", "session_id":"demo_1"}'
```
**Esperado**: Instruções do guia-medidas.md

#### Pergunta 7: Recomendação
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"me recomende um conjunto para presente", "session_id":"demo_1"}'
```
**Esperado**: Sugestão de produto com base no catálogo

#### Pergunta 8: Fallback (intenção desconhecida)
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"qual é o sentido da vida?", "session_id":"demo_1"}'
```
**Esperado**: Resposta genérica de fallback, intent=UNKNOWN

### 3. Métricas de Latência (2 min)

#### Mostrar percentis
```bash
curl http://localhost:8000/metrics/latency
```

**Explicar:**
- p50: mediana da latência (50% das requisições são mais rápidas)
- p95: 95% das requisições são mais rápidas que este valor
- p99: 99% das requisições são mais rápidas que este valor

#### Rodar benchmark
```bash
python -m tests.latency_benchmark
```

**Mostrar:** `reports/LATENCY_REPORT.md`

### 4. Discussão Técnica (2-3 min)

#### Trade-offs
| Decisão | Benefício | Custo |
|---------|-----------|-------|
| Regex classifier | <1ms, sem custo | Limitado a padrões conhecidos |
| Templates | Respostas consistentes | Menos flexibilidade |
| ChromaDB | Busca semântica local | Precisa de embeddings |
| SQLite | Simples, persistente | Limita concorrência |

#### Escalabilidade
- **Current**: 1 usuário simultâneo (produção local)
- **Load test**: Testar com 10, 20, 50 usuários
- **Bottleneck**: SQLite (concorrência), embeddings (CPU)

#### O que mudaria em produção
- SQLite → PostgreSQL
- ChromaDB → Qdrant/Pinecone
- Templates → LLM para respostas naturais
- Cache Redis para sessões

---

## Perguntas Esperadas do Avaliador

### "Como o sistema lida com falhas?"
- Se LLM falha: fallback para templates
- Se SQLite falha: erro 503
- Se ChromaDB falha: busca exata no SQLite

### "Como medir performance sob carga?"
- Locust com múltiplos usuários
- Métricas de p50/p95/p99
- Análise de RPS e taxa de erro

### "O que falta para produção?"
- Autenticação (JWT)
- Rate limiting
- Cache distribuído
- Banco relacional (PostgreSQL)
- Monitoramento (Prometheus/Grafana)

---

## Arquivos de Referência

- `README.md` — Setup e execução
- `ARCHITECTURE.md` — Componentes e trade-offs
- `docs/ADR.md` — Decisões arquiteturais
- `tests/latency_benchmark.py` — Benchmark de latência
- `tests/load_test/` — Testes de carga
