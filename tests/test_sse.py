"""Tests SSE - Incremento 4: Streaming de análisis IA en tiempo real."""
import uuid
from tests.test_auth_roles import client as test_client, _create_user_with_role


def test_sse_endpoint_returns_stream():
    """Verifica que el endpoint SSE retorna status 200, content-type correcto y eventos válidos."""
    # Crear usuario owner con permiso view_internal
    email, tenant_id = _create_user_with_role("owner")
    
    # Login para obtener cookie de sesión válida
    resp_login = test_client.post(
        "/web/login", 
        data={"email": email, "password": "pass123"},
        follow_redirects=False
    )
    assert resp_login.status_code == 303
    
    # Crear auditoría dummy para el stream (ajusta si tu ruta requiere audit_id válido)
    # Si la ruta valida existencia de audit, usa _create_audit de test_auth_roles
    audit_id = str(uuid.uuid4())
    
    # TestClient maneja cookies automáticamente tras login
    response = test_client.get(f"/audit/{audit_id}/stream")
    
    # Verificaciones críticas
    assert response.status_code == 200, f"SSE endpoint falló: {response.status_code}"
    assert "text/event-stream" in response.headers.get("content-type", ""), \
        f"Content-Type incorrecto: {response.headers.get('content-type')}"
    
    # Verificar que hay contenido SSE básico (eventos dummy)
    text = response.text
    assert "data:" in text, "No se encontraron eventos SSE en la respuesta"
    assert "event:" in text or "id:" in text, "Formato SSE incompleto"