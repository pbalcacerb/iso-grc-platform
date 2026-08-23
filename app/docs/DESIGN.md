# DESIGN v1 — Opción 2.5 (congelado)
## Criterio rector
El MVP demuestra UNA auditoría ISO completa, segura y trazable de principio a fin.
Todo lo que no sirva a ese circuito, queda fuera del hito.

## Stack
Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic (manual) · psycopg3 · pgvector ·
Pydantic 2 · Jinja2+HTMX (sin build) · pytest/ruff/mypy-strict · Docker (solo db en dev).

## Arquitectura
web(FastAPI+Jinja/HTMX) + worker(jobs) + PostgreSQL16/pgvector. Sin microservicios,
sin Redis/Kafka/K8s hasta necesidad demostrada.

## Seguridad (invariantes)
1. Tenant SIEMPRE derivado de sesión autenticada → SET LOCAL app.current_tenant_id
   en la transacción. NUNCA se acepta tenant_id del cliente.
2. RLS + FORCE en toda tabla tenant-scoped; políticas por current_setting.
3. audit_logs append-only desde M1 (INSERT único; UPDATE/DELETE denegados y testeado).
4. Revisión humana obligatoria: IA→recomendación→revisión→aprobación. Nunca IA→finding.
5. Sin texto de normas ISO almacenado: solo question packs propios (fixture demo).
6. Umbrales distintos: retrieval ≤0.9 (¿hay evidencia?) y confidence <0.75 (¿va a revisión?).
   Confidence = señal de workflow, no probabilidad calibrada.

## Esquema (17 tablas)
tenants; users; memberships(user,tenant,role); clients;
standards/clauses/question_packs (shared, lectura pública, escritura reservada);
audits; checklist_items;
evidence_files; evidence_text_extractions; evidence_text_chunks;
evidence_vectors(chunk_id, embedding vector(1024), model, dim)  ← derivado, reindexable;
ai_jobs(unique input_ref+type+content_hash); ai_analyses(cited_chunk_ids, confidence,
review_status, tokens_est); findings; audit_logs.

## Pipeline IA (especificación funcional heredada del PoC; implementación nueva)
retrieve(<=>≤0.9, top_k×3) → rerank(bge-reranker-v2-m3; fallback: orden por distancia)
→ prompt calibrado (texto del PoC, ver docs/ai-policy) → salida Pydantic →
sin chunks sobre umbral ⇒ insufficient_evidence SIN llamar al LLM →
confidence<0.75 ⇒ requires_human_review. Contenido siempre como datos (anti-inyección).

## Hitos
M0 Fundación (humano) · M1 Schema+RLS+audit_logs+tests DB · M2 Vertical slice
(login→tenant→cliente→auditoría→pregunta→respuesta) · M3 Evidencias+RAG+worker ·
M4 Revisión IA+asistente+UI IA · M5 Findings+informe básico.
## Fuera (explícito)
React, MFA/SSO, billing, S3, OCR, importador universal, crosswalks, multiidioma,
colas externas, arquitectura ceremonial.