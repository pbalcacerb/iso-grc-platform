# Reglas de casa (todo agente)
1. DoD: sin salidas pegadas de pytest+ruff+mypy+build y Problems 0, no hay "terminado".
2. Archivos congelados (el agente PROPONE, el humano APLICA): pyproject.toml,
   docker-compose.yml, alembic.ini, .env.example, configs ruff/mypy, DESIGN.md, AGENTS.md.
3. Una tarea = un paquete, con lista de archivos PERMITIDOS y PROHIBIDOS.
4. Si un mismo error exige >2 iteraciones: DETENER y reportar causa raíz, no parchear.
5. Cierre de tarea a ~100k tokens con handoff corto; snapshots (commit) antes de riesgo.
6. Sin dependencias nuevas sin mini-ADR (motivo, alternativas, costo).
7. Migraciones manuales; RLS/policies/índices SIEMPRE explícitos en SQL, nunca autogenerate.
8. Tests de seguridad a nivel de DB: tenant A NO lee tenant B (SQL directo), no solo filtros Python.
9. Separación: humano = configs/infra/verificación; agente = lógica acotada.
10. PowerShell: comandos separados (sin &&), mensajes de commit entre comillas.