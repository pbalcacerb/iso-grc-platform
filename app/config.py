"""Configuración central de la plataforma (WP0)."""
import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Carga .env sin dependencias externas (no pisa variables existentes)."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(
            key.strip(), value.strip().strip('"').strip("'")
        )


_load_dotenv()

_TESTING = "pytest" in sys.modules


class Settings:
    """Configuración leída de variables de entorno."""

    def __init__(self) -> None:
        # Base de datos
        default_db = "postgresql+psycopg://grc:grc@localhost:5432/grc"
        test_db = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://grc:grc@localhost:5432/grc_test",
        )
        self.DATABASE_URL = (
            test_db if _TESTING else os.environ.get("DATABASE_URL", default_db)
        )

        # Proveedor de IA activo: "siliconflow" | "azure_openai"
        self.AI_PROVIDER = os.environ.get("AI_PROVIDER", "siliconflow")

        # SiliconFlow (desarrollo/demo)
        self.SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-gxfkesoyiggsyfbrrewahlhmwtzswmfoophfadrfnfgmvzpx")
        self.SILICONFLOW_BASE_URL = os.environ.get(
            "SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1"
        )
        self.CHAT_MODEL = os.environ.get("CHAT_MODEL", "deepseek-ai/DeepSeek-V3")
        self.SF_EMBEDDING_MODEL = os.environ.get(
            "SF_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B"
        )

        # Azure OpenAI (producción)
        self.AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self.AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
        self.AZURE_OPENAI_API_VERSION = os.environ.get(
            "AZURE_OPENAI_API_VERSION", "2024-10-21"
        )
        self.AZURE_CHAT_DEPLOYMENT = os.environ.get(
            "AZURE_CHAT_DEPLOYMENT", "gpt-4o-mini"
        )
        self.AZURE_EMBEDDING_DEPLOYMENT = os.environ.get(
            "AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        )

        # Dimensión de vectores (debe coincidir con vector(1024) del schema)
        self.EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1024"))

        # Umbrales del pipeline de IA
        self.RETRIEVAL_DISTANCE_THRESHOLD = float(
            os.environ.get("RETRIEVAL_DISTANCE_THRESHOLD", "0.9")
        )
        self.CONFIDENCE_REVIEW_THRESHOLD = float(
            os.environ.get("CONFIDENCE_REVIEW_THRESHOLD", "0.75")
        )


settings = Settings()