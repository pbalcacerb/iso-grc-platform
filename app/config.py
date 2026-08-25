"""Configuración de la plataforma (variables de entorno)."""
import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str = _env(
        "DATABASE_URL", "postgresql+psycopg://grc:grc@localhost:5432/grc"
    )
    TEST_DATABASE_URL: str = _env(
        "TEST_DATABASE_URL", "postgresql+psycopg://grc:grc@localhost:5432/grc_test"
    )
    SILICONFLOW_BASE_URL: str = _env(
        "SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1"
    )
    SILICONFLOW_API_KEY: str = _env("SILICONFLOW_API_KEY", "")
    EMBEDDING_MODEL: str = _env("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    CHAT_MODEL: str = _env("CHAT_MODEL", "deepseek-ai/DeepSeek-V3")
    RERANK_MODEL: str = _env("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
    RETRIEVAL_DISTANCE_THRESHOLD: float = float(
        _env("RETRIEVAL_DISTANCE_THRESHOLD", "0.9")
    )
    CONFIDENCE_REVIEW_THRESHOLD: float = float(
        _env("CONFIDENCE_REVIEW_THRESHOLD", "0.75")
    )
    SESSION_SECRET: str = _env("SESSION_SECRET", "cambiar-en-produccion")
    EVIDENCE_DIR: str = _env("EVIDENCE_DIR", "./data/evidence")


settings = Settings()