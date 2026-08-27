# Product Catalog Agent

Agente de IA para atendimento interno (backoffice) de uma loja de lingerie. O sistema auxilia o time de vendas e operações com consultas de produtos, preços, estoque, pedidos, clientes e relatórios — tudo via interface conversacional em português.

O agente combina classificação determinística de intenção, LangGraph, recuperação semântica com ChromaDB e serviços de catálogo, clientes, vendas e histórico em SQLite.

As respostas dos agentes são em PT-BR. A integração com OpenRouter está encapsulada em `LLMService` para chamadas `ChatOpenAI`, incluindo prompts de fallback e clarificação contextual. O fluxo principal atual ainda usa templates determinísticos para as respostas dos agentes; o serviço de LLM está preparado para os cenários que o adotarem.

## Funcionalidades

- Consulta de produtos, preços, estoque, tamanhos e recomendações
- Contagem de produtos por categoria
- Roteamento por intenção com 4 agentes especializados (Catálogo, Vendas, Suporte, Geral)
- RAG com ChromaDB persistente e embeddings multilíngues
- Relatórios de vendas (pendentes, faturamento do dia)
- Informações da loja (endereço, formas de pagamento)
- Cadastro e consulta de clientes
- Registro de vendas e pagamentos
- Persistência de sessões, mensagens e feedback em SQLite
- API REST com FastAPI e interface web em `static/`

## Arquitetura resumida

1. `POST /v1/chat` recebe a mensagem e o `session_id`.
2. O `IntentClassifier` identifica a intenção por padrões regex e calcula confiança.
3. O `CatalogGraph` roteia a mensagem para Catalog, Sales, Support ou General.
4. O agente consulta SQLite para dados estruturados ou ChromaDB para contexto documental.
5. O resultado é persistido em SQLite e retornado pela API.

As últimas 10 mensagens da sessão são encaminhadas ao grafo como memória de curto prazo. Isso permite interpretar acompanhamentos como `e esse?` usando a referência do produto mencionada anteriormente, sem enviar o histórico inteiro ao modelo ou ao recuperador.

Para referências explícitas, como `produto 81`, o agente de catálogo tenta primeiro uma busca exata no SQLite. O RAG é usado como fallback ou para documentos de políticas, FAQ e medidas.

## Início rápido

### Pré-requisitos

- Python 3.11 ou superior
- Docker Desktop, caso use o ambiente containerizado
- Chave da OpenRouter apenas para os fluxos que utilizam `LLMService`

### Instalação local

```bash
git clone git@github.com:cirebox/product-catalog-agent.git
cd product-catalog-agent
pip install -e ".[dev]"
```

Copie `.env.example` para `.env` e configure as variáveis necessárias, especialmente `OPENROUTER_API_KEY` quando o LLM for utilizado.

### Executar o servidor

```bash
python main.py
```

A interface fica disponível em `http://localhost:8000/chat`.

### Executar o demo

```bash
python main.py --demo
```

### Executar com Docker

```bash
docker compose up -d --build
```

O banco SQLite é montado em `data/sqlite/sessions.db` no workspace. O ChromaDB usa o volume Docker `chroma_data`.

## Configuração do LLM

O `LLMService` usa `ChatOpenAI` com a API compatível da OpenRouter:

- Base URL: `https://openrouter.ai/api/v1`
- Modelo: `OPENROUTER_MODEL` ou `z-ai/glm-5.2:free`
- Chave: `OPENROUTER_API_KEY`
- Temperatura padrão: `0.1`

Se a chave não estiver configurada, chamadas de LLM retornam fallback controlado; o processamento determinístico do grafo continua disponível.

## API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/v1/chat` | Processa uma mensagem |
| `GET` | `/v1/chat/history/{session_id}` | Recupera o histórico da sessão |
| `POST` | `/v1/feedback` | Registra avaliação de uma resposta |
| `GET` | `/v1/products` | Lista produtos com busca e paginação |
| `POST` | `/v1/products` | Cadastra produto |
| `GET` | `/v1/customers` | Lista e pesquisa clientes |
| `POST` | `/v1/customers` | Cadastra cliente |
| `GET` | `/v1/sales` | Lista vendas |
| `POST` | `/v1/sales` | Registra venda |
| `GET` | `/v1/rag/reindex` | Reindexa a base via SSE |
| `GET` | `/health` | Verifica a saúde da aplicação |
| `GET` | `/metrics` | Métricas gerais da aplicação |
| `GET` | `/metrics/latency` | Latência detalhada com percentis (p50/p95/p99) |
| `GET` | `/metrics/summary` | Resumo de métricas com traces recentes |

Exemplo:

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quero saber sobre o produto 81","session_id":"teste"}'
```

## Métricas de Latência

O sistema coleta automaticamente a latência de cada request, incluindo o tempo gasto em cada nó do LangGraph (classify, route, agent).

```bash
# Latência detalhada com percentis
curl http://localhost:8000/metrics/latency

# Resumo geral
curl http://localhost:8000/metrics/summary
```

Exemplo de resposta:

```json
{
  "total_requests": 100,
  "percentiles": {
    "p50": 85.2,
    "p95": 245.8,
    "p99": 412.3
  },
  "avg_latency_ms": 98.5,
  "by_intent": {
    "product_info": { "count": 30, "avg_ms": 95.2, "p50": 82.1, "p95": 198.5 },
    "greeting": { "count": 20, "avg_ms": 45.3, "p50": 42.1, "p95": 89.2 }
  },
  "by_node": {
    "classify": { "avg_ms": 2.1, "p50": 1.8, "p95": 4.2 },
    "route": { "avg_ms": 0.5, "p50": 0.4, "p95": 0.8 },
    "agent": { "avg_ms": 95.9, "p50": 82.5, "p95": 240.1 }
  }
}
```

## Testes de Latência

Para executar o benchmark de latência com ≥20 perguntas representativas:

```bash
# Certifique-se de que o servidor está rodando
python main.py

# Em outro terminal
python -m tests.latency_benchmark
```

Os resultados são salvos em `reports/`:
- `latency_benchmark.csv` — Dados brutos
- `LATENCY_REPORT.md` — Relatório formatado

## Testes de Carga

Para executar testes de carga com Locust:

```bash
pip install locust

# Com interface web
locust -f tests/load_test/locustfile.py --host=http://localhost:8000

# Headless (sem UI)
locust -f tests/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  -u 10 \
  -r 2 \
  --run-time 2m
```

Veja `tests/load_test/README.md` para mais detalhes.

## Dados e persistência

- `assets/produtos.csv`: origem para popular produtos ausentes no SQLite
- `docs/`: FAQ, catálogo, política de trocas e guia de medidas usados pelo RAG
- `data/sqlite/sessions.db`: sessões, mensagens, produtos, clientes, vendas e feedback
- `/data/chroma` no container: coleção persistente do ChromaDB
- `reports/`: relatórios de benchmark de latência (gerados automaticamente)

O startup importa produtos ausentes do CSV sem substituir registros existentes. Os diretórios `data/` e `reports/` são ignorados pelo Git.

## Estrutura

```text
src/
├── agents/          # Agentes e classificador de intenção
├── graphs/          # LangGraph StateGraph
├── services/        # RAG, LLM, SQLite, produtos, clientes e vendas
├── infrastructure/  # Cache, erros e métricas
├── tools/           # Validação de entrada
└── utils/           # Configuração, logging e reducers
static/              # Interface web
tests/               # Testes unitários, latência e carga
reports/             # Relatórios gerados (benchmark de latência)
```

## Como Rodar os Testes

### 1. Testes unitários

```bash
python -m pytest tests/ -v
```

### 2. Benchmark de latência (≥20 perguntas)

Envia 26 perguntas representativas para o servidor e mede p50/p95/p99.

```bash
# Terminal 1: iniciar o servidor
python main.py

# Terminal 2: rodar o benchmark
python -m tests.latency_benchmark
```

**Saída gerada em `reports/`:**
- `latency_benchmark.csv` — dados brutos por pergunta
- `LATENCY_REPORT.md` — relatório com percentis e análise

### 3. Testes de carga (Locust)

Simula múltiplos usuários simultâneos enviando mensagens.

```bash
# Instalar Locust (uma vez)
pip install locust

# Terminal 1: iniciar o servidor
python main.py

# Terminal 2a: com interface web (abre http://localhost:8089)
locust -f tests/load_test/locustfile.py --host=http://localhost:8000

# Terminal 2b: headless (sem UI, gera CSV)
locust -f tests/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  -u 10 \
  -r 2 \
  --run-time 2m \
  --csv=reports/load_test
```

**Parâmetros do Locust:**

| Param | Descrição | Exemplo |
|-------|-----------|---------|
| `-u` | Usuários simultâneos | `-u 10` |
| `-r` | Novos usuários/segundo | `-r 2` |
| `--run-time` | Duração do teste | `--run-time 2m` |
| `--csv` | Prefixo dos arquivos CSV | `--csv=reports/load_test` |

**Cenários sugeridos:**

| Cenário | Comando |
|---------|---------|
| Baseline (1 user) | `locust -f tests/load_test/locustfile.py --host=http://localhost:8000 --headless -u 1 -r 1 --run-time 1m` |
| Leve (5 users) | `locust -f tests/load_test/locustfile.py --host=http://localhost:8000 --headless -u 5 -r 1 --run-time 2m` |
| Moderada (10 users) | `locust -f tests/load_test/locustfile.py --host=http://localhost:8000 --headless -u 10 -r 2 --run-time 3m` |
| Pesada (20 users) | `locust -f tests/load_test/locustfile.py --host=http://localhost:8000 --headless -u 20 -r 3 --run-time 5m` |
| Extrema (50 users) | `locust -f tests/load_test/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 5m` |

### 4. Ver métricas em tempo real

```bash
# Percentis de latência (p50, p95, p99)
curl http://localhost:8000/metrics/latency

# Resumo com traces recentes
curl http://localhost:8000/metrics/summary

# Health check
curl http://localhost:8000/health
```

### 5. Formatação e lint

```bash
black src tests
isort src tests
```

O VS Code inclui configurações de debug em `.vscode/launch.json` para `main.py` e `main.py --demo`.

## Documentação relacionada

- [ARCHITECTURE.md](ARCHITECTURE.md): componentes, fluxo e trade-offs
- [docs/ADR.md](docs/ADR.md): decisões arquiteturais (inclui ADR-005 e ADR-006 sobre latência e load test)
- [CHANGELOG.md](CHANGELOG.md): histórico de mudanças
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md): roteiro de demonstração (5-10 min)
- [tests/load_test/README.md](tests/load_test/README.md): guia de testes de carga

## Licença

Privado — Eric Pereira.
