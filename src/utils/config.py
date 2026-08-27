"""
Configuration management for Product Catalog Agent.

Uses pydantic-settings for validated, type-safe configuration from
YAML files and environment variables.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-configs
# ---------------------------------------------------------------------------


class LLMConfig(BaseSettings):
    """Configuration for LLM settings (OpenRouter)."""

    provider: str = Field(default="openrouter")
    model: str = Field(default="openrouter/free")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=1000)
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")


class ChromaConfig(BaseSettings):
    """Configuration for ChromaDB vector store."""

    persist_dir: str = Field(default="/data/chroma")
    collection: str = Field(default="product_catalog")
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")


class SQLiteConfig(BaseSettings):
    """Configuration for SQLite database."""

    db_path: str = Field(default="/data/sqlite/sessions.db")


class RAGConfig(BaseSettings):
    """Configuration for RAG service."""

    docs_dir: str = Field(default="docs")
    csv_path: str = Field(default="assets/produtos_completo.csv")
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)


class AgentConfig(BaseSettings):
    """Configuration for agent behavior."""

    max_iterations: int = Field(default=10)
    timeout: int = Field(default=30)


class LoggingConfig(BaseSettings):
    """Configuration for logging."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    json_output: bool = Field(default=False)
    file_path: Optional[str] = Field(default=None)


class ServerConfig(BaseSettings):
    """Configuration for the FastAPI server."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    cors_origins: str = Field(default="*")


# ---------------------------------------------------------------------------
# Central Config
# ---------------------------------------------------------------------------


class Config:
    """Central configuration class.

    Loads settings from YAML file and merges with environment variables.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        yaml_config = self._load_yaml(config_path)

        # Initialize sub-configs
        self.llm = LLMConfig(**yaml_config.get("llm", {}))
        self.chroma = ChromaConfig(**yaml_config.get("chroma", {}))
        self.sqlite = SQLiteConfig(**yaml_config.get("sqlite", {}))
        self.rag = RAGConfig(**yaml_config.get("rag", {}))
        self.agents = AgentConfig(**yaml_config.get("agents", {}))
        self.logging = LoggingConfig(**yaml_config.get("logging", {}))
        self.server = ServerConfig(**yaml_config.get("server", {}))

        # Environment variable overrides
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "")

        if self.openrouter_model:
            self.llm.model = self.openrouter_model

        self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "")
        self.langsmith_tracing = (
            os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(config_path: str) -> Dict[str, Any]:
        """Load YAML config file with graceful fallback."""
        resolved = Path(__file__).parent.parent.parent / config_path
        try:
            with open(resolved, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return data
        except FileNotFoundError:
            logger.warning("Config file not found: %s — using defaults.", resolved)
            return {}
        except yaml.YAMLError as exc:
            logger.error("Invalid YAML in %s: %s — using defaults.", resolved, exc)
            return {}

    def validate_startup(self) -> None:
        """Validate that critical configuration is present.

        Call this during server startup to fail fast if misconfigured.
        """
        warnings = []

        if not self.openrouter_api_key:
            warnings.append(
                "OPENROUTER_API_KEY not set — LLM calls will fail. "
                "Get a free key at https://openrouter.ai/keys"
            )

        logger.info(
            "[CONFIG] LLM provider: %s (model: %s)",
            self.llm.provider,
            self.llm.model,
        )
        logger.info(
            "[CONFIG] ChromaDB: persist_dir=%s collection=%s",
            self.chroma.persist_dir,
            self.chroma.collection,
        )
        logger.info(
            "[CONFIG] SQLite: db_path=%s",
            self.sqlite.db_path,
        )

        if self.langsmith_tracing:
            logger.info("[CONFIG] LangSmith tracing enabled")

        for msg in warnings:
            logger.warning("[CONFIG] %s", msg)
