"""Fixtures globales para el suite de pruebas de ISO GRC Platform."""
import uuid
import pytest
import argon2
from fastapi.testclient import TestClient

from app.main import app, limiter as main_limiter
from app.web import limiter as web_limiter
from app.db import SessionLocal, get_db, init_db
from app.models import User, Tenant, Membership

hasher = argon2.PasswordHasher()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Garantiza la sincronización de columnas DDL y la estructura completa antes de iniciar las pruebas."""
    init_db()


@pytest.fixture(autouse=True)
def disable_rate_limiters():
    """Desactiva temporalmente los límites de peticiones (slowapi) durante los tests."""
    main_limiter.enabled = False
    web_limiter.enabled = False
    yield
    main_limiter.enabled = True
    web_limiter.enabled = True


@pytest.fixture(autouse=True)
def override_get_db_for_tests(db_session):
    """
    Fuerza a TODOS los endpoints HTTP a usar la MISMA sesión 
    y conexión de la fixture db_session durante el test.
    
    Usa SAVEPOINT (begin_nested) para que los commit() internos 
    del endpoint NO cierren la transacción principal ni alteren 
    la DB real permanentemente.
    """
    db_session.expire_on_commit = False
    
    nested = db_session.begin_nested()

    def _get_db_override():
        try:
            print(f"[DEBUG] Overridden session ID: {id(db_session)}")
            yield db_session
        finally:
            pass

    print(f"[DEBUG] Test fixture session ID: {id(db_session)}")
    
    app.dependency_overrides[get_db] = _get_db_override
    
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        try:
            nested.rollback()
        except Exception:
            db_session.rollback()


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
    """Cliente ASGI autenticado con rol de owner."""
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
    
    print(f"[DEBUG] Authenticated client tenant_id: {tenant.id}")
    
    response = client.post(
        "/web/login",
        data={"email": email, "password": password},
        follow_redirects=False
    )
    
    assert response.status_code == 303, f"Login falló: {response.status_code}"
    assert "session" in client.cookies or "session" in response.cookies, "Sin cookie de sesión"
    
    # ✅ Asignación directa e implícita de cookies a la instancia para evitar el DeprecationWarning de per-request cookies
    client.cookies.update(response.cookies)
    
    client.tenant_id = tenant.id
    client.user_id = user.id
    
    yield client