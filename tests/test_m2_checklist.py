import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session_with_rls
from app.main import app
from app.models import ChecklistItem

client = TestClient(app)

@pytest.fixture
def test_db():
    # Setup test database
    db = get_session_with_rls(None, None)
    yield db
    db.rollback()


def test_checklist_creation_and_update(test_db: Session):
    # Setup: register a user and login
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password", "full_name": "Test User"}
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )
    assert login_response.status_code == 200

    # Create a client
    client_post_response = client.post(
        "/api/clients",
        json={"name": "Test Client", "sector": "Finance", "country": "US", "confidentiality_level": "medium"}
    )
    assert client_post_response.status_code == 200
    client_id = client_post_response.json()["id"]

    # Create an audit
    audit_post_response = client.post(
        "/api/audits",
        json={"client_id": client_id, "standard_id": 1, "name": "Test Audit", "status": "planned"}
    )
    assert audit_post_response.status_code == 200
    audit_id = audit_post_response.json()["id"]

    # Get checklist items for the audit
    checklist_response = client.get(f"/api/audits/{audit_id}/checklist")
    assert checklist_response.status_code == 200
    checklist_items = checklist_response.json()
    assert len(checklist_items) > 0  # Should have seeded questions

    # Update a checklist item
    item_id = checklist_items[0]["id"]
    update_response = client.post(
        f"/api/audits/{audit_id}/checklist/{item_id}",
        json={"response": "Completed", "notes": "All good", "status": "completed"}
    )
    assert update_response.status_code == 200

    # Verify the update
    updated_item = test_db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    assert updated_item is not None
    assert updated_item.response == "Completed"
    assert updated_item.status == "completed"