# 🧪 Suite de Pruebas ISO-GRC Platform

Este directorio contiene el conjunto oficial de pruebas automatizadas para la plataforma **ISO-GRC Platform**.

## 📊 Cobertura Actual

- **Módulo 6.1 (Pre-Auditoría Documental - ISO 19011 §6.2)**: `test_pre_audit.py` y `test_audit_pipeline.py`
  - Carga de documentos de auditoría (PDF/DOCX) en memoria vía `TestClient` con redirección HITL.
  - Validación de formatos aceptados y rechazo de peticiones malformadas.
  - Extracción de texto y chunking con metadatos (`chunk_index`, `start_offset`, `end_offset`).
  - Ingesta vectorial e IA mockeados con `unittest.mock.patch` (sub-10s, sin llamadas a APIs externas).
  - Flujo HITL completo: Carga → Revisión → Aprobación → Persistencia en DB y `AuditLog`.

- **Control de Acceso y RBAC**: `test_auth_roles.py` y `test_rbac.py`
  - Verificación del modelo de 8 roles ISO 19011 / ISO 27001.
  - Aislamiento de vistas y endpoints de gestión de usuarios por permisos (`create_audit`, `upload_evidence`, `manage_users`).

- **Seguridad e Aislamiento Multi-Tenant**: `test_security.py`
  - Políticas RLS (Row Level Security) y aislamiento estricto por `tenant_id`.
  - Inmutabilidad (append-only) en registros de `AuditLog`.

- **Eventos en Tiempo Real (SSE)**: `test_worker_sse.py` y `test_sse.py`
  - Emisión de eventos SSE para tareas asíncronas de análisis.

---

## 🚀 Ejecución del Suite de Pruebas

Para ejecutar el suite completo de pruebas:

```bash
pytest tests/ -v
```

Para ejecutar únicamente los tests del Módulo 6.1:

```bash
pytest tests/test_pre_audit.py tests/test_audit_pipeline.py -v
```

---

## 🧹 Limpieza y Consolidación de Tests Legacy

Durante la fase de consolidación técnica, se eliminaron los siguientes archivos de prueba obsoletos:
- `test_m2_auth.py`, `test_m2_checklist.py`, `test_m2_isolation.py`, `test_m3_evidence.py`: apuntaban a endpoints JSON extintos de iteraciones iniciales (`/auth/register`, `/auth/login`, `/api/clients`, `/api/evidences`) que fueron migrados al flujo nativo ASGI server-rendered (`/web/login`, `/login`).
- `test_m3_worker.py`: intentaba mockear la función `extract_text_from_file` en `app.worker.assess`, la cual fue refactorizada e integrada en el pipeline centralizado.
