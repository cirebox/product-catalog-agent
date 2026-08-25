#!/usr/bin/env python3
"""
Main entry point for Product Catalog Agent.

Run modes:
    python main.py          → start FastAPI server
    python main.py --demo   → run offline demo (no server)
"""

import argparse
import sys


def run_server() -> None:
    """Start the FastAPI server via uvicorn."""
    import uvicorn
    from src.utils.config import Config

    config = Config()
    uvicorn.run(
        "src.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )


def run_demo() -> None:
    """Run an offline demo of the Product Catalog Agent."""
    from src.agents.intent_classifier import IntentClassifier
    from src.services.rag_service import RAGService
    from src.utils.config import Config
    from src.utils.logging import setup_logging

    config = Config()
    setup_logging(
        level=config.logging.level,
        fmt=config.logging.format,
        json_output=config.logging.json_output,
        file_path=config.logging.file_path,
    )

    print("=" * 60)
    print("  Product Catalog Agent — Demo Mode")
    print("  Lingerie Customer Service via RAG")
    print("=" * 60)

    # Initialize RAG service
    rag_service = RAGService(
        docs_dir=config.rag.docs_dir,
        csv_path=config.rag.csv_path,
        persist_dir=config.rag.persist_dir,
    )

    print("\nBuilding RAG index...")
    num_chunks = rag_service.load_and_index()
    print(f"Indexed {num_chunks} chunks from catalog + docs")

    # Initialize classifier
    classifier = IntentClassifier()

    demo_messages = [
        "oi",
        "quero ver os conjuntos",
        "quanto custa o conjunto brilho carol?",
        "tem estoque de tanga 216?",
        "qual o tamanho de busto para P?",
        "me recomende um baby doll",
        "como faço para trocar?",
        "quero devolver um produto",
        "onde está meu pedido?",
        "ajuda",
    ]

    print("\n" + "-" * 60)
    print("Simulating customer messages...")
    print("-" * 60)

    for i, message in enumerate(demo_messages, 1):
        print(f"\n[{i}] Customer: \"{message}\"")

        # Classify intent
        intent, confidence = classifier.get_confidence(message)
        print(f"     Intent: {intent.value} (confidence: {confidence})")

        # Get RAG context
        context = rag_service.get_relevant_context(message, k=2)
        if context:
            print(f"     Context found: {len(context)} chars")

    print("\n" + "=" * 60)
    print("Demo completed.")
    print("\nTo start the API server:")
    print("  python main.py")
    print("\nEndpoints:")
    print("  POST /v1/chat — Send message, get response")
    print("  GET  /health  — Health check")
    print("  GET  /metrics — Metrics")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Catalog Agent")
    parser.add_argument("--demo", action="store_true", help="Run offline demo instead of server")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        run_server()
