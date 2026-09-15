# Reporte de Auditoría OpenCode - GAEA Bootstrap Agent

## 1. Sistema Operativo
- **OS:** Windows_NT (Windows 11 / win32)
- **Entorno de Shell:** PowerShell 5.1

## 2. Versión de OpenCode
- **OpenCode Plugin / CLI Client:** v1.18.30 (`@opencode-ai/plugin`)
- **Modo de Cliente:** Desktop (`desktop`)

## 3. Carpeta Raíz del Proyecto
- `D:\dev\iso-grc-platform`

## 4. Python Detectado
- **Versión del Sistema:** Python 3.13.15
- **Ruta de Ejecutable (Global):** `C:\Users\natta\AppData\Local\Programs\Python\Python313\python.exe`
- **Entornos Virtuales Detectados:**
  - `venv\` (Python 3.13 local con paquetes completos)
  - `.venv\` (Python 3.13 de desarrollo)

## 5. Docker Detectado
- **Versión:** Docker version 29.7.2, build a7dcaa6

## 6. Git Detectado
- **Versión:** git version 2.55.0.windows.4

## 7. Archivos de Configuración OpenCode Encontrados
- `C:\Users\natta\.config\opencode\opencode.jsonc`
- `C:\Users\natta\.config\opencode\package.json`
- `C:\Users\natta\.config\opencode\package-lock.json`

## 8. Variables de Entorno Utilizadas por OpenCode
*(Secretos ocultos por seguridad)*
- `OPENCODE_CLIENT`
- `OPENCODE_DISABLE_EMBEDDED_WEBVIEW`
- `OPENCODE_EXPERIMENTAL_FILEWATCHER`
- `OPENCODE_EXPERIMENTAL_ICON_THEME`
- `OPENCODE_SERVER_PASSWORD` `[SECRET HIDDEN]`
- `OPENCODE_SERVER_USERNAME`
- `NO_PROXY`
- `XDG_STATE_HOME`

## 9. Lista de Herramientas Disponibles
- **Python / Pip:** Disponible (Python 3.13.15, pip 26.2.1)
- **Node.js / npm:** Disponible (Node v24.14.0 / v24.15.0, npm 11.19.0)
- **Git:** Disponible (v2.55.0)
- **Docker:** Disponible (v29.7.2)
- **Ruff (Linter/Formatter):** Disponible (`ruff` v0.16.4)
- **Pytest (Testing):** Disponible (`pytest` v9.1.1)
- **Uvicorn / FastAPI / Alembic:** Disponibles en entorno virtual (`venv`)
- **Mypy (Type Checker):** Disponible en entorno virtual (`venv`)
- **Herramientas NO detectadas en PATH global:** `uv`, `poetry`, `pyright`

## 10. Árbol de Directorios del Proyecto (hasta profundidad 3)

```text
iso-grc-platform/
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── AUDIT_BOOTSTRAP.md
├── Dockerfile
├── docker-compose.prod.yml
├── docker-compose.yml
├── pyproject.toml
├── requirements-prod.txt
├── requirements.txt
├── seed_standards.py
├── test_worker_manual.py
├── app/
│   ├── .env.example
│   ├── .env.production.example
│   ├── .gitignore
│   ├── .ruff_cache/
│   ├── ai/
│   ├── alembic.ini
│   ├── api/
│   ├── app/
│   ├── audit_execution.py
│   ├── audits.py
│   ├── auth/
│   ├── config.py
│   ├── db.py
│   ├── docker-compose.yml
│   ├── docs/
│   ├── findings.py
│   ├── health.py
│   ├── logging_config.py
│   ├── main.py
│   ├── middleware.py
│   ├── models.py
│   ├── permissions.py
│   ├── pyproject.toml
│   ├── security.py
│   ├── taxonomy.py
│   ├── templates/
│   ├── ui/
│   ├── utils/
│   ├── web.py
│   └── worker/
├── data/
│   └── evidence/
├── db/
│   ├── __init__.py
│   ├── migration_0001.sql
│   └── migrations/
├── rag/
│   └── __init__.py
├── scripts/
│   ├── add_status_column.py
│   ├── check_provider.py
│   ├── create_test_pdf.py
│   └── seed_demo.py
├── static/
│   └── css/
├── tests/
│   ├── README.md
│   ├── conftest.py
│   ├── test_audit_closure.py
│   ├── test_audit_execution.py
│   ├── test_audit_pipeline.py
│   ├── test_auth_roles.py
│   ├── test_findings_management.py
│   ├── test_pre_audit.py
│   ├── test_rbac.py
│   ├── test_security.py
│   ├── test_sse.py
│   └── test_worker_sse.py
├── venv/
│   ├── Include/
│   ├── Lib/
│   ├── Scripts/
│   └── pyvenv.cfg
├── worker/
│   └── __init__.py
├── .venv/
└── .vscode/
```
