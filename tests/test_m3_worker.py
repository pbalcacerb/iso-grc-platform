"""Tests del worker de análisis con proveedor conmutable (WP0)."""
import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.worker import assess as worker


def _mock_db():
    return MagicMock(spec=Session)


def _mock_evidence():
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.tenant_id = uuid.uuid4()
    ev.storage_path = "data/evidence/test.txt"
    return ev


def _run(db, ev):
    return worker.assess_compliance(
        evidence_file_id=ev.id,
        audit_id=uuid.uuid4(),
        db=db,
        tenant_id=ev.tenant_id,
    )


def test_evidencia_no_encontrada():
    db = _mock_db()
    db.query.return_value.filter.return_value.first.return_value = None
    result = worker.assess_compliance(uuid.uuid4(), uuid.uuid4(), db)
    assert result["status"] == "error"
    assert not db.add.called


def test_cortocircuito_archivo_vacio():
    db, ev = _mock_db(), _mock_evidence()
    db.query.return_value.filter.return_value.first.return_value = ev
    with patch.object(worker, "extract_text_from_file", return_value=""):
        result = _run(db, ev)
    assert result["status"] == "cortocircuito"
    assert db.add.called and db.commit.called


def test_cortocircuito_sin_chunks_relevantes():
    """
    Si el proveedor está configurado, el worker debe:
    1. Extraer texto
    2. Crear chunks/embeddings
    3. Buscar chunks similares
    4. Si no encuentra chunks relevantes, hacer cortocircuito
    """
    db, ev = _mock_db(), _mock_evidence()
    db.query.return_value.filter.return_value.first.return_value = ev

    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.text = "Texto de prueba"

    provider = MagicMock()
    provider.is_configured.return_value = True
    provider.name = "siliconflow"

    with patch.object(worker, "extract_text_from_file", return_value="Texto válido"), \
         patch.object(worker, "get_provider", return_value=provider), \
         patch.object(worker, "create_chunks_and_embeddings", return_value=[chunk]), \
         patch.object(worker, "search_similar_chunks", return_value=[]):
        result = _run(db, ev)

    assert result["status"] == "cortocircuito"
    assert result["assessment"] == "insufficient_evidence"
    assert db.add.called
    assert db.commit.called


def test_simulacion_sin_api_key():
    db, ev = _mock_db(), _mock_evidence()
    db.query.return_value.filter.return_value.first.return_value = ev
    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.text = "Texto de prueba"  # ← AGREGADO
    provider = MagicMock()
    provider.is_configured.return_value = False
    with patch.object(worker, "extract_text_from_file", return_value="Texto válido"), \
         patch.object(worker, "create_chunks_and_embeddings", return_value=[chunk]), \
         patch.object(worker, "search_similar_chunks", return_value=[(chunk, 0.85)]), \
         patch.object(worker, "get_provider", return_value=provider):
        result = _run(db, ev)
    assert result["status"] == "simulated"
    assert result["requires_human_review"] is True


def test_analisis_con_proveedor_configurado():
    db, ev = _mock_db(), _mock_evidence()
    db.query.return_value.filter.return_value.first.return_value = ev
    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.text = "Texto de prueba"  # ← AGREGADO
    provider = MagicMock()
    provider.is_configured.return_value = True
    provider.name = "azure_openai"
    provider.chat_json.return_value = {
        "compliance_assessment": "compliant",
        "gaps": [],
        "risks": [],
        "confidence": 0.9,
    }
    with patch.object(worker, "extract_text_from_file", return_value="Texto válido"), \
         patch.object(worker, "create_chunks_and_embeddings", return_value=[chunk]), \
         patch.object(worker, "search_similar_chunks", return_value=[(chunk, 0.85)]), \
         patch.object(worker, "get_provider", return_value=provider):
        result = _run(db, ev)
    assert result["status"] == "success"
    assert result["assessment"] == "compliant"
    assert result["requires_human_review"] is False
    assert db.add.called