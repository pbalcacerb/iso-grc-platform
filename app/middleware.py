"""Middleware que extrae tenant_id/user_id de la cookie y lo inyecta en la DB."""
import re
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_cookie = request.cookies.get("session")
        tenant_id: uuid.UUID | None = None
        user_id: uuid.UUID | None = None

        if session_cookie:
            # Formato esperado: "tenant=<uuid>;user=<uuid>"
            match_t = re.search(r"tenant=([a-f0-9\-]+)", session_cookie)
            match_u = re.search(r"user=([a-f0-9\-]+)", session_cookie)
            if match_t:
                try:
                    tenant_id = uuid.UUID(match_t.group(1))
                except ValueError:
                    pass
            if match_u:
                try:
                    user_id = uuid.UUID(match_u.group(1))
                except ValueError:
                    pass

        # Inyectar en la conexión de la request (para endpoints que usen engine directamente)
        # Nota: Para endpoints que usen get_session_with_rls, este middleware solo valida la cookie.
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        response = await call_next(request)
        return response