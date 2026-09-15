# RUNTIME BASELINE - GAEA Runtime Snapshot Agent

## 1. Dependencias Python Instaladas
Lista completa de paquetes en el entorno virtual activo:

| Paquete | Versión |
|---|---|
| alembic | 1.19.1 |
| annotated-doc | 0.0.5 |
| annotated-types | 0.8.0 |
| anyio | 4.14.2 |
| argon2-cffi | 25.1.0 |
| argon2-cffi-bindings | 26.1.0 |
| ast_serialize | 0.8.0 |
| certifi | 2026.7.22 |
| cffi | 2.1.1 |
| charset-normalizer | 3.5.1 |
| click | 8.4.2 |
| colorama | 0.4.6 |
| Deprecated | 1.3.1 |
| dnspython | 2.8.0 |
| email-validator | 2.3.0 |
| fastapi | 0.141.1 |
| filelock | 3.32.4 |
| fsspec | 2026.7.0 |
| greenlet | 3.5.5 |
| h11 | 0.16.0 |
| hf-xet | 1.6.0 |
| httpcore | 1.0.9 |
| httpx | 0.28.1 |
| huggingface_hub | 1.29.0 |
| idna | 3.19 |
| iniconfig | 2.3.0 |
| Jinja2 | 3.1.6 |
| joblib | 1.5.3 |
| librt | 0.15.0 |
| limits | 5.8.0 |
| Mako | 1.4.1 |
| markdown-it-py | 4.2.0 |
| MarkupSafe | 3.0.3 |
| mdurl | 0.1.2 |
| mpmath | 1.3.0 |
| mypy | 2.3.1 |
| mypy_extensions | 1.1.0 |
| narwhals | 2.25.0 |
| networkx | 3.6.1 |
| numpy | 2.5.2 |
| packaging | 26.3 |
| pathspec | 1.1.1 |
| pillow | 12.3.0 |
| pip | 26.2.1 |
| pluggy | 1.6.0 |
| psycopg | 3.3.4 |
| psycopg-binary | 3.3.4 |
| psycopg2-binary | 2.9.12 |
| pycparser | 3.0 |
| pydantic | 2.13.4 |
| pydantic_core | 2.46.4 |
| Pygments | 2.21.0 |
| pytest | 9.1.1 |
| python-multipart | 0.0.32 |
| PyYAML | 6.0.3 |
| regex | 2026.7.19 |
| reportlab | 5.0.1 |
| requests | 2.34.2 |
| rich | 15.0.0 |
| ruff | 0.16.4 |
| safetensors | 0.8.0 |
| scikit-learn | 1.9.0 |
| scipy | 1.18.1 |
| sentence-transformers | 6.0.0 |
| setuptools | 84.0.0 |
| shellingham | 1.5.4 |
| slowapi | 0.1.10 |
| SQLAlchemy | 2.0.52 |
| starlette | 1.6.0 |
| sympy | 1.14.0 |
| threadpoolctl | 3.6.0 |
| tokenizers | 0.23.1 |
| torch | 2.13.0 |
| tqdm | 4.70.0 |
| transformers | 5.16.1 |
| typer | 0.27.1 |
| typing_extensions | 4.16.0 |
| typing-inspection | 0.4.4 |
| tzdata | 2026.3 |
| urllib3 | 2.7.0 |
| uvicorn | 0.52.4 |
| wrapt | 2.4.0 |

## 2. Paquetes FastAPI
- `fastapi`: `0.141.1`
- `starlette`: `1.6.0` (core ASGI framework)
- `uvicorn`: `0.52.4` (ASGI web server)
- `pydantic`: `2.13.4` (data validation)
- `pydantic_core`: `2.46.4`
- `python-multipart`: `0.0.32` (form/file uploads)
- `slowapi`: `0.1.10` (rate limiting)

## 3. SQLAlchemy
- `SQLAlchemy`: `2.0.52`
- `greenlet`: `3.5.5`
- `psycopg` / `psycopg-binary`: `3.3.4`
- `psycopg2-binary`: `2.9.12`

## 4. Alembic
- `alembic`: `1.19.1`
- `Mako`: `1.4.1`

## 5. Ruff
- `ruff`: `0.16.4`

## 6. Pytest
- `pytest`: `9.1.1`
- `pluggy`: `1.6.0`
- `iniconfig`: `2.3.0`

## 7. Docker Images Utilizadas
- `axllent/mailpit:latest`
- `mcr.microsoft.com/azure-storage/azurite:latest`
- `pgvector/pgvector:pg16`

## 8. Docker Containers Activos
- **Container ID:** `b633cc6443a5`
- **Nombre:** `grc-db`
- **Imagen:** `pgvector/pgvector:pg16`
- **Estado:** `Up 31 hours (healthy)`
- **Puertos:** `0.0.0.0:5432->5432/tcp`

## 9. Variables `.env` Detectadas
*(Valores sensibles ocultados por seguridad)*
- `DATABASE_URL` = `[MASKED]`
- `TEST_DATABASE_URL` = `[MASKED]`
- `AI_PROVIDER` = `[MASKED]`
- `AZURE_OPENAI_ENDPOINT` = `[MASKED]`
- `AZURE_OPENAI_API_KEY` = `[MASKED]`
- `AZURE_OPENAI_API_VERSION` = `[MASKED]`
- `AZURE_CHAT_DEPLOYMENT` = `[MASKED]`
- `AZURE_EMBEDDING_DEPLOYMENT` = `[MASKED]`
- `SILICONFLOW_API_KEY` = `[MASKED]`
- `SILICONFLOW_BASE_URL` = `[MASKED]`
- `EMBEDDING_MODEL` = `[MASKED]`
- `CHAT_MODEL` = `[MASKED]`
- `RERANK_MODEL` = `[MASKED]`
- `RETRIEVAL_DISTANCE_THRESHOLD` = `[MASKED]`
- `CONFIDENCE_REVIEW_THRESHOLD` = `[MASKED]`
- `SESSION_SECRET` = `[MASKED]`
- `EVIDENCE_DIR` = `[MASKED]`
