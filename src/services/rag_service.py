"""
RAG Service — Product Catalog Agent
Carrega CSV de produtos e documentos markdown, indexa com ChromaDB.
"""

import csv
import os
from typing import List, Optional

import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings


class RAGService:
    def __init__(
        self,
        docs_dir: str = "docs",
        csv_path: str = "assets/produtos.csv",
        persist_dir: str = "/data/chroma",
        collection_name: str = "product_catalog",
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.docs_dir = docs_dir
        self.csv_path = csv_path
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        # Initialize embeddings
        self.embedder = HuggingFaceEmbeddings(model_name=model_name)

        # Initialize ChromaDB
        os.makedirs(persist_dir, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _load_csv_products(self) -> List[Document]:
        """Load products from CSV file and convert to LangChain Documents."""
        documents = []
        if not os.path.exists(self.csv_path):
            return documents

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                ref = row.get("ref", "").strip()
                desc = row.get("descrição", "").strip()
                price_str = row.get("preço", "0").strip().replace(",", ".")
                stock_str = row.get("estoque", "0").strip()

                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                try:
                    stock = int(stock_str)
                except ValueError:
                    stock = 0

                content = (
                    f"Produto: {desc}\n"
                    f"Código de referência: {ref}\n"
                    f"Preço: R$ {price:.2f}\n"
                    f"Estoque: {stock} unidades\n"
                )

                doc = Document(
                    page_content=content,
                    metadata={
                        "source": "catalog_csv",
                        "ref": ref,
                        "description": desc,
                        "price": price,
                        "stock": stock,
                    },
                )
                documents.append(doc)

        return documents

    def _load_markdown_docs(self) -> List[Document]:
        """Load markdown documents from docs directory."""
        if not os.path.exists(self.docs_dir):
            return []

        loader = DirectoryLoader(
            self.docs_dir,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        return loader.load()

    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks for embedding."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " "],
        )
        return splitter.split_documents(documents)

    def load_and_index(self) -> int:
        """Load all sources, index into ChromaDB. Returns number of chunks."""
        csv_docs = self._load_csv_products()
        md_docs = self._load_markdown_docs()

        all_docs = csv_docs + md_docs

        if not all_docs:
            return 0

        chunks = self._chunk_documents(all_docs)

        if not chunks:
            return 0

        # Generate embeddings and add to ChromaDB
        texts = [doc.page_content for doc in chunks]
        metadatas = [doc.metadata for doc in chunks]
        ids = [f"doc_{i}" for i in range(len(chunks))]

        # Batch add to ChromaDB
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            self.collection.add(
                documents=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids,
            )

        return len(chunks)

    def search(self, query: str, k: int = 5) -> List[dict]:
        """Search the vector store for relevant documents."""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
        )

        # Format results
        formatted_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                formatted_results.append({
                    "content": doc,
                    "metadata": metadata,
                })

        return formatted_results

    def get_relevant_context(self, query: str, k: int = 5) -> str:
        """Get formatted context string from search results."""
        results = self.search(query, k=k)
        if not results:
            return ""

        context_parts = [r["content"] for r in results]
        return "\n---\n".join(context_parts)

    def get_collection_stats(self) -> dict:
        """Get statistics about the ChromaDB collection."""
        return {
            "collection": self.collection_name,
            "count": self.collection.count(),
            "persist_dir": self.persist_dir,
        }
