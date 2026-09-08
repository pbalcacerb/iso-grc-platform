"""Fixtures globales para el suite de pruebas de ISO GRC Platform."""
import uuid
import pytest
import argon2
from fastapi.testclient import TestClient

from app.main import app, limiter as main_limiter
from app.web import limiter as web_limiter
from app.db import SessionLocal
from app.models import User, Tenant, Membership

hasher = argon2.PasswordHasher()


@pytest.fixture(autouse=True)
def disable_rate_limiters():
    """Desactiva temporalmente los límites de peticiones (slowapi) durante los tests."""
    main_limiter.enabled = False
    web_limiter.enabled = False
    yield
    main_limiter.enabled = True
    web_limiter.enabled = True


@pytest.fixture
def client():
    """Cliente ASGI de pruebas con lifespan activo."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Sesión de base de datos aislada por test con rollback y cierre estricto post-ejecución."""
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()


@pytest.fixture
def authenticated_client(client, db_session):
    """Cliente ASGI autenticado con rol de owner (posee permisos de auditoría)."""
    email = f"test_owner_{uuid.uuid4().hex[:6]}@grc.com"
    password = "AdminPassword123!"
    
    tenant = Tenant(name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:6]}")
    db_session.add(tenant)
    db_session.flush()
    
    user = User(
        email=email,
        password_hash=hasher.hash(password),
        full_name="PreAudit Admin Test"
    )
    db_session.add(user)
    db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role="owner"
    )
    db_session.add(membership)
    db_session.commit()
    
    # POST login con follow_redirects=False
    response = client.post(
        "/web/login",
        data={"email": email, "password": password},
        follow_redirects=False
    )
    
    assert response.status_code == 303, f"Login en fixture falló con status {response.status_code}"
    assert "session" in client.cookies or "session" in response.cookies, "La cookie de sesión no fue emitida"
    
    yield client