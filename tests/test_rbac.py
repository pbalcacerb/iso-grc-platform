"""Tests RBAC - Incremento 3: Control de acceso por roles (ISO GRC)."""
import uuid

from tests.test_auth_roles import (
    client as test_client,
    _create_user_with_role,
)


def test_owner_can_access_users_page():
    """Owner debe poder acceder a /users y ver la gestión de usuarios."""
    email, tenant_id = _create_user_with_role("owner")
    
    # Login: follow_redirects=False para capturar el 303 original
    resp_login = test_client.post(
        "/web/login", 
        data={"email": email, "password": "pass123"},
        follow_redirects=False
    )
    assert resp_login.status_code == 303, f"Login falló: {resp_login.status_code}"
    
    # TestClient gestiona cookies automáticamente tras login exitoso
    # Solo hacemos GET a /users sin pasar cookies manualmente
    response = test_client.get("/users")
    
    assert response.status_code == 200, f"Owner no pudo acceder a /users: {response.status_code}"
    assert "Gestión de Usuarios" in response.text or "Invitar Usuario" in response.text


def test_auditor_cannot_access_users_page():
    """Auditor NO debe poder acceder a /users (redirect a login o 403)."""
    email, _ = _create_user_with_role("auditor")
    
    resp_login = test_client.post(
        "/web/login", 
        data={"email": email, "password": "pass123"},
        follow_redirects=False
    )
    assert resp_login.status_code == 303, f"Login falló: {resp_login.status_code}"
    
    # Auditor intenta acceder a /users
    response = test_client.get("/users", follow_redirects=False)
    
    # Debe ser rechazado
    assert response.status_code in [303, 403], \
        f"Auditor pudo acceder a /users: {response.status_code}"
    
    if response.status_code == 303:
        location = response.headers.get("location", "").lower()
        assert "/login" in location, f"Redirect fue a {location}, no a /login"


def test_role_can_observer_view_portal():
    """Test unitario directo a la función role_can sin levantar servidor ni DB."""
    from app.permissions import role_can
    
    assert role_can("observer", "view_portal") is True
    assert role_can("owner", "manage_users") is True
    assert role_can("client_responsible", "upload_evidence") is True
    
    assert role_can("observer", "manage_users") is False
    assert role_can("auditor", "manage_users") is False
    assert role_can("client_sponsor", "upload_evidence") is False
    
    assert role_can("nonexistent_role", "view_portal") is False
    assert role_can("", "manage_users") is False