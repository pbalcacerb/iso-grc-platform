# COMPONENT DISCOVERY - ISO-GRC Platform

## 1. Resumen Ejecutivo
La plataforma **ISO-GRC Platform** es un sistema backend y web desarrollado en Python (FastAPI + SQLAlchemy + PostgreSQL/SQLite + Alembic) diseñado para la gestión de Gobernanza, Riesgo y Cumplimiento (GRC) de normas ISO (ej. ISO 9001, ISO 27001). Implementa análisis asistido por IA (RAG / proveedores de LLM), control de acceso basado en roles (RBAC), flujos de trabajo de auditoría, cola de revisión humana y auditoría de acciones (Audit Logs).

## 2. Arquitectura y Módulos Principales

### 2.1 Módulos Backend (`app/`)
- **`main.py`**: Punto de entrada de FastAPI, inicialización de la base de datos (DDL), carga de datos semilla (`seed_demo`), rate limiting (`slowapi`), middleware de logging de peticiones, y registro dinámico de routers.
- **`web.py`**: Enrutador principal web server-rendered con Jinja2. Maneja autenticación (cookies con argon2), dashboard, gestión de clientes, creación y detalle de auditorías, cola de revisión humana (`review-queue`), subida de evidencias, streaming SSE (`/audit/{id}/stream`), portal del cliente, gestión de usuarios, recuperación de contraseña y logs de auditoría.
- **`db.py`**: Configuración de SQLAlchemy, sesión de base de datos (`get_db`), inicialización y sincronización de esquemas (`init_db`).
- **`models.py`**: Definición de modelos ORM: `Tenant`, `User`, `Membership`, `Client`, `Standard`, `Clause`, `QuestionPack`, `Audit`, `ChecklistItem`, `EvidenceFile`, `AIAnalysis`, `AuditLog`, `PasswordResetToken`, `PreAuditMaturityReport`.
- **`security.py`**: Funciones de autenticación, parsing de sesiones y validación de roles/permisos.
- **`permissions.py`**: Definición de la matriz de roles y permisos (ej. `owner`, `admin`, `lead_auditor`, `auditor`, `coordinator`, `observer`, `client_responsible`, etc.).
- **`health.py`**: Endpoints de verificación de estado y salud del sistema (`/health`).
- **`taxonomy.py`**: Estructuras taxonómicas de normas y cláusulas.
- **`ai/`**: Proveedores de IA y conectores LLM (`providers.py`).
- **`utils/`**: Utilidades de procesamiento de texto (`text_extractor.py`), embeddings (`embeddings.py`), y segmentación (`chunker.py`).
- **`worker/`**: Procesamiento asíncrono y evaluación de cumplimiento (`assess.py`).

### 2.2 Base de Datos y Migraciones (`db/`)
- **`migrations/`**: Versiones de Alembic (migraciones incrementales para esquemas de tenants, auditorías, campos de cierre de auditoría, claves foráneas, timestamps, etc.).
- **`migration_0001.sql`**: Script DDL SQL inicial.

### 2.3 Scripts Auxiliares (`scripts/`)
- **`seed_demo.py`**: Población idempotente de datos demo (usuarios administradores, normas ISO, cláusulas, paquetes de preguntas).
- **`create_test_pdf.py`**: Generación de archivos PDF de prueba para evidencias.
- **`check_provider.py`**: Verificación de conectividad con proveedores de IA.
- **`add_status_column.py`**: Utilidad de migración/ajuste de columnas de estado.

### 2.4 Pruebas Automatizadas (`tests/`)
- Suite completa con `pytest` (`test_auth_roles.py`, `test_audit_closure.py`, `test_audit_execution.py`, `test_audit_pipeline.py`, `test_findings_management.py`, `test_pre_audit.py`, `test_rbac.py`, `test_security.py`, `test_sse.py`, `test_worker_sse.py`, `conftest.py`).

### 2.5 Interfaz de Usuario y Plantillas (`app/templates/`, `static/`)
- Plantillas HTML Jinja2 para vistas web (`login.html`, `register.html`, `dashboard.html`, `audit_detail.html`, `create_client.html`, `create_audit.html`, `review_queue.html`, `portal.html`, `manage_users.html`, `audit_logs.html`, `pre_audit_report.html`, etc.).
- Estilos CSS (`static/css/main.css`).

## 3. Matriz de Componentes Clave
| Componente | Tipo | Ubicación | Responsabilidad Principal |
|------------|------|-----------|---------------------------|
| FastAPI Entrypoint | Backend / API | `app/main.py` | Arranque de la app, lifespan, middlewares, registro de routers |
| Web Router & UI | Web / SSR | `app/web.py` | Vistas Jinja2, autenticación, formularios, flujos GRC |
| Base de Datos ORM | Persistence | `app/db.py`, `app/models.py` | Conexión SQLAlchemy, modelos relacionales multi-tenant |
| Worker / Asesor | AI / Business Logic | `app/worker/assess.py` | Evaluación de evidencias documentales con IA |
| Seguridad y Permisos | Security / RBAC | `app/security.py`, `app/permissions.py` | Control de acceso basado en roles y permisos |
| Migraciones Alembic | Database Migration | `db/migrations/` | Versionado de esquemas SQL |
| Scripts Semilla | Bootstrap / Seeds | `scripts/seed_demo.py` | Inicialización de datos de demostración y catálogos ISO |
