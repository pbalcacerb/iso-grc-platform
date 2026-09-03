CHECKPOINT 2026-09-03 — ISO GRC Platform
Repo: github.com/pbalcacerb/iso-grc-platform · Local: D:\dev\iso-grc-platform (venv, PowerShell, VS Code)
Prod: Droplet 165.22.181.183 → https://165.22.181.183.nip.io (nginx+Certbot; app solo en 127.0.0.1:8000); server /root/iso-grc, .env fuera de Git
CI/CD: Actions deploy.yml (appleboy/ssh-action) con secrets SSH_PRIVATE_KEY/SERVER_HOST/SERVER_USER; push→reset --hard→rebuild ~3-4 min
Login demo: demo@grc.com / SecurePass123!
Stack: FastAPI+Jinja, SQLAlchemy 2 (UUID), pgvector, Azure OpenAI, argon2, slowapi; tablas vía create_all en lifespan; alembic en db/migrations
Archivos clave: app/web.py (rutas server-rendered), app/security.py (require_role), app/permissions.py (role_can/require_perm), app/worker/assess.py, app/models.py
Fase 2: Incr. 1 (layout sidebar/header) ✅ verificado local; Incr. 2 (reset password) código entregado, faltan 3 templates ← estamos aquí; siguientes: Incr. 3 RBAC enforcement, Incr. 4 SSE, Incr. 5 audit-log UI
Hardening pendiente: cookie de sesión NO firmada (crítico), CSRF, tokens_est reales, prompts versionados+Pydantic, golden evals en CI
Preferencias usuario: paso a paso, nunca secretos en el chat, pegar desde VS Code al chat (no a la terminal)