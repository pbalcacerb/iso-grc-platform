# Middleware for handling sessions and RLS
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Parse session cookie
        session_cookie = request.cookies.get("session")
        tenant_id: int | None = None
        user_id: int | None = None

        if session_cookie:
            # Extract tenant_id and user_id from cookie
            tenant_match = re.search(r"tenant_id=(\d+)", session_cookie)
            user_match = re.search(r"user_id=(\d+)", session_cookie)

            if tenant_match and user_match:
                tenant_id = int(tenant_match.group(1))
                user_id = int(user_match.group(1))

        # Set current_tenant_id and current_user_id on request.app
        request.app.current_tenant_id = tenant_id
        request.app.current_user_id = user_id

        response = await call_next(request)
        return response