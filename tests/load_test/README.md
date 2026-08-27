# Load Test — Product Catalog Agent

## Pré-requisitos

```bash
pip install locust
```

## Como Rodar

### 1. Iniciar o servidor

```bash
python main.py
```

### 2. Executar load test (CLI)

```bash
locust -f tests/load_test/locustfile.py --host=http://localhost:8000
```

### 3. Executar load test (headless - sem UI)

```bash
locust -f tests/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  -u 10 \
  -r 2 \
  --run-time 2m \
  --csv=reports/load_test
```

### Parâmetros

| Param | Descrição | Default |
|-------|-----------|---------|
| `-u` | Número de usuários simultâneos | 1 |
| `-r` | Taxa de spawn (usuários/segundo) | 1 |
| `--run-time` | Duração do teste | indefinido |
| `--csv` | Prefixo para arquivos CSV de resultado | - |

## Cenários Testados

| Cenário | Usuários | Duração | Objetivo |
|---------|----------|---------|----------|
| Baseline | 1 | 1 min | Latência individual |
| Leve | 5 | 2 min | Carga normal |
| Moderada | 10 | 3 min | Pico de tráfego |
| Pesada | 20 | 5 min | Limite de estresse |
| Extrema | 50 | 5 min | Teste de saturação |

## Métricas Coletadas

- **RPS** (Requests per Second)
- **Latência média, p50, p95, p99**
- **Taxa de erro (%)**
- **Duração do teste**

## Saída

Os arquivos CSV são gerados em `reports/`:
- `load_test_stats.csv` — Estatísticas aggregadas
- `load_test_failures.csv` — Falhas detalhadas
- `load_test_stats_history.csv` — Histórico por segundo

## Interpretação

| Métrica | Ideal | Aceitável | Crítico |
|---------|-------|-----------|---------|
| RPS | >10 | 5-10 | <5 |
| p50 | <200ms | 200-500ms | >500ms |
| p95 | <500ms | 500-1000ms | >1000ms |
| Erros | 0% | <1% | >1% |
