"""Tests Worker SSE - Incremento 4 Fase 2."""
import asyncio
import uuid
from app.worker.assess import assess_compliance, assess_item  # ← Importación explícita
from tests.test_auth_roles import _create_user_with_role


def test_worker_sends_sse_events():
    """Verifica que assess_item envía eventos SSE cuando se pasa queue."""
    email, tenant_id = _create_user_with_role("owner")
    
    test_queue = asyncio.Queue()
    fake_uuid = uuid.uuid4()
    
    # Llamar assess_item SÍNCRONO (no await)
    assess_item(
        checklist_item_id=fake_uuid,
        audit_id=fake_uuid,
        evidence_file_id=fake_uuid,
        db=None,
        tenant_id=tenant_id,
        sse_queue=test_queue
    )

    # Recolectar eventos
    events = []
    while not test_queue.empty():
        events.append(test_queue.get_nowait())

    # Verificaciones
    assert len(events) >= 3, f"Solo {len(events)} eventos recibidos: {events}"
    assert any(e["type"] == "progress" for e in events), "Falta evento progress"
    assert any(e["type"] == "complete" for e in events), "Falta evento complete"