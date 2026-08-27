"""Verificación en vivo del proveedor de IA (requiere API key en .env)."""
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.providers import get_provider
from app.config import settings


def main() -> None:
    provider = get_provider()
    print(f"Proveedor activo: {provider.name}")
    if not provider.is_configured():
        print("⚠️ Sin API key: el worker usará modo simulado.")
        return
    emb = provider.embed("Política de calidad documentada.")
    print(f"✅ Embedding OK, dim={len(emb)}")
    assert len(emb) == settings.EMBEDDING_DIM, (
        f"Dimensión {len(emb)} != {settings.EMBEDDING_DIM}"
    )
    data = provider.chat_json(
        'Responde solo con JSON: {"compliance_assessment": "compliant",'
        ' "gaps": [], "risks": [], "confidence": 0.9}'
    )
    print(f"✅ Chat JSON OK: {data}")


if __name__ == "__main__":
    main()