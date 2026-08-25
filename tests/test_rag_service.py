"""
Tests for RAGService with ChromaDB.
"""

import os
import tempfile

import pytest
from src.services.rag_service import RAGService


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV for testing."""
    csv_content = """ref;descrição;preço;estoque
8520;CONJUNTO BRILHO CAROL;61,90;1
216;TANGA KAREN (COTTON);18,90;5
824;BABY DOLL GABY;49,90;1"""
    csv_path = tmp_path / "produtos.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return str(csv_path)


@pytest.fixture
def sample_docs(tmp_path):
    """Create sample markdown docs for testing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    faq_content = """# FAQ

## Preços
- Parcelamos em até 3x sem juros
- PIX com 5% de desconto
"""
    (docs_dir / "FAQ.md").write_text(faq_content, encoding="utf-8")
    return str(docs_dir)


@pytest.fixture
def rag_service(sample_csv, sample_docs):
    """Create a RAGService with sample data."""
    with tempfile.TemporaryDirectory() as persist_dir:
        service = RAGService(
            docs_dir=sample_docs,
            csv_path=sample_csv,
            persist_dir=persist_dir,
            collection_name="test_collection",
        )
        yield service


class TestRAGService:
    """Tests for RAG service with ChromaDB."""

    def test_load_csv_products(self, rag_service):
        docs = rag_service._load_csv_products()
        assert len(docs) == 3
        assert "CONJUNTO BRILHO CAROL" in docs[0].page_content

    def test_load_markdown_docs(self, rag_service):
        docs = rag_service._load_markdown_docs()
        assert len(docs) >= 1

    def test_load_and_index(self, rag_service):
        num_chunks = rag_service.load_and_index()
        assert num_chunks > 0

    def test_search(self, rag_service):
        rag_service.load_and_index()
        results = rag_service.search("conjunto")
        assert len(results) > 0

    def test_get_relevant_context(self, rag_service):
        rag_service.load_and_index()
        context = rag_service.get_relevant_context("tanga")
        assert "TANGA" in context or "tanga" in context.lower()

    def test_empty_search(self, rag_service):
        results = rag_service.search("xyzabc123")
        assert len(results) == 0

    def test_get_collection_stats(self, rag_service):
        stats = rag_service.get_collection_stats()
        assert "collection" in stats
        assert "count" in stats

    def test_collection_persistence(self, sample_csv, sample_docs):
        """Test that ChromaDB persists data across instances."""
        with tempfile.TemporaryDirectory() as persist_dir:
            # Create and populate first instance
            service1 = RAGService(
                docs_dir=sample_docs,
                csv_path=sample_csv,
                persist_dir=persist_dir,
                collection_name="persist_test",
            )
            service1.load_and_index()
            assert service1.get_collection_stats()["count"] > 0

            # Create second instance with same persist_dir
            service2 = RAGService(
                docs_dir=sample_docs,
                csv_path=sample_csv,
                persist_dir=persist_dir,
                collection_name="persist_test",
            )
            # Should have data from first instance
            assert service2.get_collection_stats()["count"] > 0
            results = service2.search("conjunto")
            assert len(results) > 0
