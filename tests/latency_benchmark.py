"""
Latency Benchmark — Product Catalog Agent

Sends ≥20 representative questions to /v1/chat and measures p50/p95/p99.
Run with: python -m tests.latency_benchmark
"""

import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import List, Dict

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
SESSION_PREFIX = "bench_"
OUTPUT_DIR = Path(__file__).parent.parent / "reports"

# ---------------------------------------------------------------------------
# Test questions — covers all 20 intents
# ---------------------------------------------------------------------------

QUESTIONS: List[Dict[str, str]] = [
    # GREETING
    {"intent": "GREETING", "message": "oi"},
    {"intent": "GREETING", "message": "bom dia, tudo bem?"},
    # HELP
    {"intent": "HELP", "message": "quais serviços vocês oferecem?"},
    # PRODUCT_INFO
    {"intent": "PRODUCT_INFO", "message": "quero saber sobre o produto 81"},
    {"intent": "PRODUCT_INFO", "message": "me fale sobre o conjunto kayla"},
    # PRICING
    {"intent": "PRICING", "message": "quanto custa a tanga 216?"},
    {"intent": "PRICING", "message": "preço do sutiã 6000"},
    # STOCK_CHECK
    {"intent": "STOCK_CHECK", "message": "tem estoque de tanga 215?"},
    {"intent": "STOCK_CHECK", "message": "disponibilidade do conjunto 8508"},
    # SIZE_GUIDE
    {"intent": "SIZE_GUIDE", "message": "como tirar medida de busto?"},
    {"intent": "SIZE_GUIDE", "message": "guia de medidas sutiã"},
    # RECOMMENDATION
    {"intent": "RECOMMENDATION", "message": "me recomende um conjunto para presente"},
    {"intent": "RECOMMENDATION", "message": "qual sutiã vocês indicam?"},
    # PRODUCT_COUNT
    {"intent": "PRODUCT_COUNT", "message": "quantos produtos vocês têm?"},
    # RETURN_POLICY
    {"intent": "RETURN_POLICY", "message": "qual a política de trocas?"},
    {"intent": "RETURN_POLICY", "message": "posso devolver meu pedido?"},
    # EXCHANGE
    {"intent": "EXCHANGE", "message": "quero trocar de tamanho"},
    {"intent": "EXCHANGE", "message": "como faço para trocar?"},
    # COMPLAINT
    {"intent": "COMPLAINT", "message": "meu pedido veio com defeito"},
    {"intent": "COMPLAINT", "message": "estou insatisfeito com o produto"},
    # ORDER_STATUS
    {"intent": "ORDER_STATUS", "message": "onde está meu pedido?"},
    {"intent": "ORDER_STATUS", "message": "status do pedido 12345"},
    # TRACK_DELIVERY
    {"intent": "TRACK_DELIVERY", "message": "rastrear entrega"},
    {"intent": "TRACK_DELIVERY", "message": "código de rastreio do meu pedido"},
    # NEW_ORDER
    {"intent": "NEW_ORDER", "message": "como faço um pedido?"},
    # UNKNOWN (fallback)
    {"intent": "UNKNOWN", "message": "qual é o sentido da vida?"},
]


def run_benchmark() -> Dict:
    """Send all questions and collect latency data."""
    results = []
    errors = 0

    print(f"Running benchmark with {len(QUESTIONS)} questions...")
    print(f"Target: {BASE_URL}/v1/chat\n")

    with httpx.Client(timeout=30.0) as client:
        for i, q in enumerate(QUESTIONS, 1):
            session_id = f"{SESSION_PREFIX}{i}"
            payload = {"message": q["message"], "session_id": session_id}

            start = time.monotonic()
            try:
                resp = client.post(f"{BASE_URL}/v1/chat", json=payload)
                elapsed_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    results.append({
                        "index": i,
                        "intent_expected": q["intent"],
                        "intent_returned": data.get("intent", ""),
                        "message": q["message"],
                        "latency_ms": round(elapsed_ms, 2),
                        "server_latency_ms": data.get("latency_ms", 0),
                        "reply_length": len(data.get("reply", "")),
                        "error": None,
                    })
                    print(f"  [{i:2d}/{len(QUESTIONS)}] {q['intent']:20s} {elapsed_ms:7.1f}ms")
                else:
                    errors += 1
                    results.append({
                        "index": i,
                        "intent_expected": q["intent"],
                        "intent_returned": "",
                        "message": q["message"],
                        "latency_ms": round(elapsed_ms, 2),
                        "server_latency_ms": 0,
                        "reply_length": 0,
                        "error": f"HTTP {resp.status_code}",
                    })
                    print(f"  [{i:2d}/{len(QUESTIONS)}] {q['intent']:20s} ERROR {resp.status_code}")
            except Exception as e:
                elapsed_ms = (time.monotonic() - start) * 1000
                errors += 1
                results.append({
                    "index": i,
                    "intent_expected": q["intent"],
                    "intent_returned": "",
                    "message": q["message"],
                    "latency_ms": round(elapsed_ms, 2),
                    "server_latency_ms": 0,
                    "reply_length": 0,
                    "error": str(e),
                })
                print(f"  [{i:2d}/{len(QUESTIONS)}] {q['intent']:20s} EXCEPTION {e}")

    # Calculate stats
    client_latencies = [r["latency_ms"] for r in results if r["error"] is None]
    server_latencies = [r["server_latency_ms"] for r in results if r["error"] is None and r["server_latency_ms"] > 0]

    def percentile(data, p):
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        d = k - f
        return round(sorted_data[f] + d * (sorted_data[c] - sorted_data[f]), 2)

    stats = {
        "total_questions": len(QUESTIONS),
        "successful": len(client_latencies),
        "errors": errors,
        "client_latency": {
            "avg_ms": round(statistics.mean(client_latencies), 2) if client_latencies else 0,
            "min_ms": round(min(client_latencies), 2) if client_latencies else 0,
            "max_ms": round(max(client_latencies), 2) if client_latencies else 0,
            "p50_ms": percentile(client_latencies, 50),
            "p95_ms": percentile(client_latencies, 95),
            "p99_ms": percentile(client_latencies, 99),
            "stdev_ms": round(statistics.stdev(client_latencies), 2) if len(client_latencies) > 1 else 0,
        },
        "server_latency": {
            "avg_ms": round(statistics.mean(server_latencies), 2) if server_latencies else 0,
            "p50_ms": percentile(server_latencies, 50),
            "p95_ms": percentile(server_latencies, 95),
        },
    }

    return {"results": results, "stats": stats}


def save_csv(results: List[Dict], path: Path):
    """Save results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "index", "intent_expected", "intent_returned", "message",
            "latency_ms", "server_latency_ms", "reply_length", "error",
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nCSV saved to: {path}")


def save_markdown_report(stats: Dict, results: List[Dict], path: Path):
    """Save markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    s = stats["client_latency"]
    sv = stats["server_latency"]

    md = f"""# Latency Report — Product Catalog Agent

**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**Questions**: {stats['total_questions']}
**Successful**: {stats['successful']}
**Errors**: {stats['errors']}

## Client Latency (end-to-end)

| Metric | Value |
|--------|-------|
| Average | {s['avg_ms']} ms |
| Min | {s['min_ms']} ms |
| Max | {s['max_ms']} ms |
| **p50** | **{s['p50_ms']} ms** |
| **p95** | **{s['p95_ms']} ms** |
| p99 | {s['p99_ms']} ms |
| Std Dev | {s['stdev_ms']} ms |

## Server Latency (graph only)

| Metric | Value |
|--------|-------|
| Average | {sv['avg_ms']} ms |
| p50 | {sv['p50_ms']} ms |
| p95 | {sv['p95_ms']} ms |

## Results by Intent

| # | Intent | Message | Client (ms) | Server (ms) | Status |
|---|--------|---------|-------------|-------------|--------|
"""
    for r in results:
        status = "OK" if r["error"] is None else f"ERR: {r['error']}"
        msg_short = r["message"][:40] + ("..." if len(r["message"]) > 40 else "")
        md += f"| {r['index']} | {r['intent_expected']} | {msg_short} | {r['latency_ms']} | {r['server_latency_ms']} | {status} |\n"

    md += f"""
## Percentile Analysis

- **p50 = {s['p50_ms']} ms**: 50% das requisições são mais rápidas que este valor
- **p95 = {s['p95_ms']} ms**: 95% das requisições são mais rápidas que este valor
- **p99 = {s['p99_ms']} ms**: 99% das requisições são mais rápidas que este valor

## Interpretation

"""
    if s["p50_ms"] < 100:
        md += "- **Excelente**: p50 abaixo de 100ms, experiência muito responsiva\n"
    elif s["p50_ms"] < 500:
        md += "- **Bom**: p50 abaixo de 500ms, experiência aceitável\n"
    else:
        md += "- **Atenção**: p50 acima de 500ms, pode causar frustração\n"

    if s["p95_ms"] < 200:
        md += "- **p95 < 200ms**: Margem para escala sem degradar experiência\n"
    elif s["p95_ms"] < 1000:
        md += "- **p95 < 1s**: Aceitável para atendimento ao consumidor\n"
    else:
        md += "- **p95 > 1s**: Necessário otimizar para cargas maiores\n"

    path.write_text(md, encoding="utf-8")
    print(f"Report saved to: {path}")


def main():
    data = run_benchmark()

    save_csv(data["results"], OUTPUT_DIR / "latency_benchmark.csv")
    save_markdown_report(data["stats"], data["results"], OUTPUT_DIR / "LATENCY_REPORT.md")

    print("\n" + "=" * 60)
    print("LATENCY SUMMARY")
    print("=" * 60)
    s = data["stats"]["client_latency"]
    print(f"  Questions:  {data['stats']['total_questions']}")
    print(f"  Successful: {data['stats']['successful']}")
    print(f"  Errors:     {data['stats']['errors']}")
    print(f"  Avg:        {s['avg_ms']} ms")
    print(f"  p50:        {s['p50_ms']} ms")
    print(f"  p95:        {s['p95_ms']} ms")
    print(f"  p99:        {s['p99_ms']} ms")
    print("=" * 60)


if __name__ == "__main__":
    main()
