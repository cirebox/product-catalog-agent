"""
RAG Service — Product Catalog Agent
Carrega produtos do SQLite e documentos markdown, indexa com ChromaDB.
"""

import csv
import os
import logging
from typing import List, Optional

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


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

    # ------------------------------------------------------------------
    # Product document builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_product_content(product: dict) -> str:
        """Build rich text content for a product document (for embedding)."""
        ref = product.get("ref", "")
        desc = product.get("description", "")
        price = product.get("price", 0)
        manufacturer = product.get("manufacturer", "")
        material = product.get("material", "")
        size = product.get("size", "")
        category = product.get("category", "")

        parts = [f"Produto: {desc}", f"Código de referência: {ref}"]
        if manufacturer:
            parts.append(f"Fabricante: {manufacturer}")
        if material:
            parts.append(f"Material: {material}")
        if size:
            parts.append(f"Tamanho: {size}")
        if category:
            parts.append(f"Categoria: {category}")
        parts.append(f"Preço: R$ {price:.2f}")

        return "\n".join(parts)

    @staticmethod
    def _build_product_metadata(product: dict) -> dict:
        """Build metadata dict for a product document."""
        return {
            "source": "catalog",
            "ref": product.get("ref", ""),
            "description": product.get("description", ""),
            "price": float(product.get("price", 0)),
            "manufacturer": product.get("manufacturer", ""),
            "material": product.get("material", ""),
            "size": product.get("size", ""),
            "category": product.get("category", ""),
        }

    # ------------------------------------------------------------------
    # Legacy CSV loader (for seed / backup import)
    # ------------------------------------------------------------------

    def _load_csv_products(self) -> List[Document]:
        """Load products from CSV file (legacy format: ref,name,price,category)."""
        documents = []
        if not os.path.exists(self.csv_path):
            return documents

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            for row in reader:
                if len(row) < 3:
                    continue
                ref = row[0].strip()
                desc = row[1].strip()
                price_str = row[2].strip().replace(",", ".")
                category = row[3].strip() if len(row) > 3 else ""

                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                product = {
                    "ref": ref,
                    "description": desc,
                    "price": price,
                    "category": category,
                    "manufacturer": "",
                    "material": "",
                    "size": "",
                }

                content = self._build_product_content(product)
                metadata = self._build_product_metadata(product)

                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

        return documents

    # ------------------------------------------------------------------
    # SQLite loader (primary source)
    # ------------------------------------------------------------------

    def load_products_from_sqlite(self, products: List[dict]) -> int:
        """Index products from SQLite into ChromaDB. Returns chunk count."""
        if not products:
            return 0

        documents = []
        for p in products:
            content = self._build_product_content(p)
            metadata = self._build_product_metadata(p)
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)

        # Also load markdown docs
        md_docs = self._load_markdown_docs()
        all_docs = documents + md_docs

        chunks = self._chunk_documents(all_docs)
        if not chunks:
            return 0

        # Clear existing collection before reindex
        self._clear_collection()

        # Batch add to ChromaDB
        texts = [doc.page_content for doc in chunks]
        metadatas = [doc.metadata for doc in chunks]
        ids = [f"doc_{i}" for i in range(len(chunks))]

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

        logger.info("Indexed %d products (%d chunks) into ChromaDB", len(products), len(chunks))
        return len(chunks)

    def reindex_all(self, products: List[dict]) -> int:
        """Reindex all products in ChromaDB. Returns chunk count.

        This is a convenience method that clears the existing collection
        and reindexes all products from the provided list.
        """
        if not products:
            logger.warning("reindex_all called with empty products list")
            return 0

        # Clear existing collection before full reindex
        self._clear_collection()

        # Reindex using the existing method
        return self.load_products_from_sqlite(products)

    def reindex_product(self, product: dict) -> None:
        """Reindex a single product in ChromaDB (add or update)."""
        ref = product.get("ref", "")
        if not ref:
            return

        # Remove existing entries for this ref
        self.remove_product(ref)

        # Add new entry
        content = self._build_product_content(product)
        metadata = self._build_product_metadata(product)

        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[f"product_{ref}"],
        )

    def remove_product(self, ref: str) -> None:
        """Remove a product from ChromaDB by ref."""
        try:
            self.collection.delete(ids=[f"product_{ref}"])
        except Exception:
            # ID might not exist, try finding by metadata
            results = self.collection.get(
                where={"ref": ref}
            )
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])

    # ------------------------------------------------------------------
    # Markdown docs
    # ------------------------------------------------------------------

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

    def _clear_collection(self) -> None:
        """Delete all documents from the collection."""
        try:
            existing = self.collection.get()
            if existing and existing["ids"]:
                self.collection.delete(ids=existing["ids"])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 5) -> List[dict]:
        """Search the vector store for relevant documents."""
        if self.collection.count() == 0:
            logger.info("Busca RAG sem índice: query=%r", query)
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
        )

        formatted_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                formatted_results.append({
                    "content": doc,
                    "metadata": metadata,
                })

            logger.info("Busca RAG concluída: query=%r, resultados=%d", query, len(formatted_results))

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

    def reindex_with_progress(self, products: List[dict]):
        """Full reindex with progress generator. Yields (step, current, total, message)."""
        total_steps = 4  # clear, products, markdown, finalize
        step = 0

        # Step 1: Clear collection
        step += 1
        yield (step, 0, total_steps, "Limpando índice anterior...")
        self._clear_collection()
        yield (step, 1, total_steps, "Índice limpo")

        # Step 2: Index products
        step += 1
        documents = []
        for i, p in enumerate(products):
            content = self._build_product_content(p)
            metadata = self._build_product_metadata(p)
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
            if (i + 1) % 10 == 0 or i == len(products) - 1:
                yield (step, i + 1, len(products), f"Indexando produto {i + 1}/{len(products)}: {p.get('ref', '')}")

        # Step 3: Load markdown docs
        step += 1
        yield (step, 0, 1, "Carregando documentos markdown...")
        md_docs = self._load_markdown_docs()
        all_docs = documents + md_docs
        yield (step, 1, 1, f"{len(md_docs)} docs markdown carregados")

        # Step 4: Chunk and add to ChromaDB
        step += 1
        chunks = self._chunk_documents(all_docs)
        yield (step, 0, len(chunks), f"Dividindo em {len(chunks)} pedaços...")

        if not chunks:
            yield (step, 1, 1, "Nenhum documento para indexar")
            return

        texts = [doc.page_content for doc in chunks]
        metadatas = [doc.metadata for doc in chunks]
        ids = [f"doc_{i}" for i in range(len(chunks))]

        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            self.collection.add(
                documents=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids,
            )
            yield (step, min(i + batch_size, len(texts)), len(texts), f"Indexando batch {i // batch_size + 1}...")

        logger.info("Full reindex: %d products, %d chunks", len(products), len(chunks))
        yield (step, len(chunks), len(chunks), f"Concluído! {len(products)} produtos, {len(chunks)} chunks")
