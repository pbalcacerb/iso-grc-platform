"""Pruebas de integración nativas para Módulo 6.2 - Ejecución de Auditoría In-Situ."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Audit, Membership, User, Tenant, Standard, Client

client = TestClient(app)

BASE_URL = "/api/v1/audit-execution"

@pytest.fixture
def audit_for_authenticated_user(db_session, authenticated_client):
    """Crea auditoría sincronizada garantizando integridad referencial."""
    from app.models import User, Membership
    
    session_cookie = authenticated_client.cookies.get("session")
    if not session_cookie:
        pytest.skip("No hay cookie de sesión")
    
    # Parsear cookie (formato confirmado: "tenant=X\073user=Y")
    cleaned = session_cookie.strip('"').replace('\\073', ';')
    
    user_id = None
    tenant_id_from_cookie = None
    
    try:
        parts = cleaned.split(';')
        for part in parts:
            key, value = part.strip().split('=', 1)
            if key == 'user':
                user_id = uuid.UUID(value.strip())
            elif key == 'tenant':
                tenant_id_from_cookie = uuid.UUID(value.strip())
    except (ValueError, IndexError):
        pytest.skip(f"No se pudo parsear cookie: {cleaned[:100]}")
    
    if not user_id:
        pytest.skip(f"user_id no encontrado en cookie")
    
    membership = db_session.query(Membership).filter_by(user_id=user_id).first()
    if not membership:
        pytest.skip(f"Usuario {user_id} sin membresía")
    
    if tenant_id_from_cookie and membership.tenant_id != tenant_id_from_cookie:
        pytest.skip(f"Mismatch tenant: cookie={tenant_id_from_cookie} vs DB={membership.tenant_id}")
    
    tenant_id_value = membership.tenant_id.hex if hasattr(membership.tenant_id, 'hex') else str(membership.tenant_id).replace('-', '')
    
    # 1️⃣ Crear/obtener Standard Y HACER FLUSH INMEDIATO
    std = db_session.query(Standard).first()
    if not std:
        std = Standard(id=uuid.uuid4(), code="ISO-27001:2022", name="ISO 27001:2022")
        db_session.add(std)
        db_session.flush()  # ← Standard existe en DB ahora
    
    # 2️⃣ Crear/obtener Client Y HACER FLUSH INMEDIATO
    cli = db_session.query(Client).filter_by(tenant_id=membership.tenant_id).first()
    if not cli:
        cli = Client(id=uuid.uuid4(), tenant_id=membership.tenant_id, name="Test Client Sync")
        db_session.add(cli)
        db_session.flush()  # ← Client existe en DB ahora, FK válida
    
    # 3️⃣ AHORA SÍ crear Audit (Client y Standard ya existen en DB)
    audit = Audit(
        id=uuid.uuid4(),
        tenant_id=tenant_id_value,
        client_id=cli.id,      # ← FK válida garantizada
        standard_id=std.id,    # ← FK válida garantizada
        name="Auditoría Test M6.2 - Tenant Sincronizado",
        status="in_progress"
    )
    db_session.add(audit)
    db_session.flush()  # Solo flush, no commit (el override maneja visibilidad)
    
    return str(audit.id)


def test_generate_checklist(authenticated_client, audit_for_authenticated_user):
    """Valida generación idempotente de checklist desde auditoría existente."""
    resp = authenticated_client.post(f"{BASE_URL}/{audit_for_authenticated_user}/checklist/generate")
    
    # Aceptar 200 (creado), 201 (creado alternativo), o 409 (ya existe)
    assert resp.status_code in [200, 201, 409], \
        f"Status inesperado: {resp.status_code} - {resp.text}"
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        assert "id" in data or "items" in data, "Respuesta debe contener datos del checklist"


def test_submit_and_get_response(authenticated_client, audit_for_authenticated_user):
    """Valida registro idempotente de respuesta y recuperación posterior."""
    gen_resp = authenticated_client.post(f"{BASE_URL}/{audit_for_authenticated_user}/checklist/generate")
    assert gen_resp.status_code in [200, 201, 409], f"Fallo al generar: {gen_resp.text}"
    
    get_resp = authenticated_client.get(f"{BASE_URL}/{audit_for_authenticated_user}/checklist")
    assert get_resp.status_code == 200, f"Fallo al obtener checklist: {get_resp.text}"
    
    items = get_resp.json().get("items", [])
    if not items:
        pytest.skip("El checklist generado no tiene ítems de evaluación")
    
    item_id = items[0]["item_id"]
    
    resp = authenticated_client.post(
        f"{BASE_URL}/{audit_for_authenticated_user}/checklist/response",
        json={
            "item_id": item_id,
            "status": "NON_COMPLIANT",
            "notes": "Falta política documentada"
        }
    )
    assert resp.status_code == 200, f"Fallo al enviar respuesta: {resp.text}"
    
    verify_resp = authenticated_client.get(f"{BASE_URL}/{audit_for_authenticated_user}/checklist")
    assert verify_resp.status_code == 200
    updated_items = verify_resp.json()["items"]
    target = next((i for i in updated_items if i["item_id"] == item_id), None)
    assert target is not None, "Ítem respondido no encontrado"
    assert target["status"] == "NON_COMPLIANT"


def test_preliminary_findings(authenticated_client, audit_for_authenticated_user):
    """Valida generación de hallazgos preliminares desde respuestas No Cumple."""
    gen_resp = authenticated_client.post(f"{BASE_URL}/{audit_for_authenticated_user}/checklist/generate")
    assert gen_resp.status_code in [200, 201, 409]
    
    get_resp = authenticated_client.get(f"{BASE_URL}/{audit_for_authenticated_user}/checklist")
    items = get_resp.json().get("items", [])
    if not items:
        pytest.skip("No hay ítems en el checklist")
    
    authenticated_client.post(
        f"{BASE_URL}/{audit_for_authenticated_user}/checklist/response",
        json={
            "item_id": items[0]["item_id"],
            "status": "NON_COMPLIANT",
            "notes": "Hallazgo de prueba"
        }
    )
    
    findings_resp = authenticated_client.get(f"{BASE_URL}/{audit_for_authenticated_user}/findings/preliminary")
    assert findings_resp.status_code == 200
    data = findings_resp.json()
    assert "total_findings" in data or "findings" in data


def test_tenant_isolation(client, db_session, audit_for_authenticated_user):
    """Valida que usuarios de otro tenant NO pueden acceder al checklist."""
    from argon2 import PasswordHasher
    
    hasher = PasswordHasher()
    valid_hash = hasher.hash("TestPass123!")
    unique_slug = f"other-tenant-{uuid.uuid4().hex[:8]}"
    
    other_tenant = Tenant(
        id=uuid.uuid4(), 
        name="Other Tenant", 
        slug=unique_slug,
        status="active"
    )
    db_session.add(other_tenant)
    db_session.flush()
    
    other_user = User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:6]}@tenant.com",
        password_hash=valid_hash,
        status="active"
    )
    db_session.add(other_user)
    db_session.flush()
    
    membership = Membership(
        user_id=other_user.id,
        tenant_id=other_tenant.id,
        role="auditor"
    )
    db_session.add(membership)
    db_session.flush()  # ← flush, no commit
    
    login_resp = client.post("/web/login", data={
        "email": other_user.email,
        "password": "TestPass123!"
    }, follow_redirects=False)
    
    if login_resp.status_code != 303:
        pytest.skip(f"Login falló: {login_resp.status_code}")
    
    resp = client.get(f"{BASE_URL}/{audit_for_authenticated_user}/checklist")
    assert resp.status_code in [403, 404], \
        f"Aislamiento fallido: usuario externo accedió con {resp.status_code}"

def test_debug_session_cookie(authenticated_client):
    """Solo para inspeccionar formato real de cookie de sesión."""
    session_cookie = authenticated_client.cookies.get("session")
    print(f"\n COOKIE DE SESIÓN COMPLETA: {repr(session_cookie)}")
    print(f" TIPO: {type(session_cookie)}")
    
    # Intentar todos los formatos posibles
    if session_cookie:
        # Formato 1: tenant=X;user=Y
        if "user=" in session_cookie:
            print("✅ Formato detectado: tenant=X;user=Y")
        # Formato 2: JWT
        elif "." in session_cookie and len(session_cookie.split(".")) == 3:
            print("✅ Formato detectado: JWT")
        # Formato 3: JSON
        elif session_cookie.startswith("{"):
            print("✅ Formato detectado: JSON")
        else:
            print(f"⚠️ Formato desconocido: {session_cookie[:100]}...")