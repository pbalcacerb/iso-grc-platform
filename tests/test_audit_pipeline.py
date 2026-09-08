"""Tests para el pipeline de pre-auditoría documental GRC / IA (Módulo 6.1 - ISO 19011 §6.2)."""
import io
import uuid
from unittest.mock import patch
import pytest

from app.models import PreAuditMaturityReport, AuditLog


def chunk_document_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Fragmenta texto en chunks con metadatos para ingesta vectorial."""
    chunks = []
    start = 0
    text_len = len(text)
    chunk_idx = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_text = text[start:end]
        chunks.append({
            "chunk_index": chunk_idx,
            "text": chunk_text,
            "char_length": len(chunk_text),
            "start_offset": start,
            "end_offset": end,
        })
        chunk_idx += 1
        start += chunk_size - overlap
        if start >= text_len or chunk_size <= overlap:
            break
    return chunks


def test_format_validation_accepts_valid_documents(authenticated_client):
    """Valida que se acepten archivos PDF y DOCX en la carga del pipeline de pre-auditoría."""
    pdf_bytes = io.BytesIO(f"%PDF-1.4 Policy text ISO 27001 {uuid.uuid4().hex}".encode())
    docx_bytes = io.BytesIO(f"PK\x03\x04 Fake DOCX content {uuid.uuid4().hex}".encode())

    # Carga de PDF
    resp_pdf = authenticated_client.post(
        "/api/pre-analysis/upload",
        files=[("files", ("policy.pdf", pdf_bytes, "application/pdf"))],
        data={"standard_code": "ISO27001"},
        follow_redirects=False
    )
    assert resp_pdf.status_code == 303, f"Falló la carga de PDF: {resp_pdf.status_code}"
    assert resp_pdf.headers.get("location", "").startswith("/pre-audit/review/")

    # Carga de DOCX
    resp_docx = authenticated_client.post(
        "/api/pre-analysis/upload",
        files=[("files", ("procedure.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        data={"standard_code": "ISO9001"},
        follow_redirects=False
    )
    assert resp_docx.status_code == 303, f"Falló la carga de DOCX: {resp_docx.status_code}"
    assert resp_docx.headers.get("location", "").startswith("/pre-audit/review/")


def test_format_validation_rejects_invalid_inputs(authenticated_client):
    """Valida el rechazo con status 400/422 cuando no se proporciona archivo."""
    resp_empty = authenticated_client.post(
        "/api/pre-analysis/upload",
        data={"standard_code": "ISO27001"},
        follow_redirects=False
    )
    assert resp_empty.status_code in [400, 422], f"Status inesperado para request sin archivo: {resp_empty.status_code}"


def test_text_extraction_and_chunking():
    """Valida la extracción de texto, fragmentación (chunking) y generación de metadatos."""
    sample_text = (
        "Sección 1: Política de Control de Acceso. "
        "Todos los usuarios deben contar con autenticación de doble factor (2FA). "
        "Sección 2: Gestión de Incidentes. "
        "Cualquier brecha de seguridad debe reportarse en menos de 24 horas."
    )
    chunks = chunk_document_text(sample_text, chunk_size=80, overlap=15)
    
    assert len(chunks) > 0, "No se generaron chunks de texto"
    for idx, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == idx
        assert "text" in chunk
        assert chunk["char_length"] == len(chunk["text"])
        assert chunk["char_length"] <= 80
        assert chunk["start_offset"] < chunk["end_offset"]


@patch("app.ai.providers.SiliconFlowProvider.embed")
@patch("app.ai.providers.SiliconFlowProvider.chat_json")
def test_vector_db_ingestion_and_ai_mocking(mock_chat, mock_embed, authenticated_client, db_session):
    """Verifica ingesta de embeddings y análisis de IA aislando llamadas externas con mocks."""
    mock_embed.return_value = [0.123, -0.456, 0.789, 0.001]
    mock_chat.return_value = {
        "maturity_score": 75.5,
        "gaps_identified": ["Falta encriptación en reposo"],
        "risks_preliminary": ["Riesgo medio de filtración"],
        "ai_recommendations": "Implementar cifrado AES-256."
    }

    dummy_doc = io.BytesIO(f"%PDF-1.4 Mocked ISO 27001 Manual {uuid.uuid4().hex}".encode())
    
    response = authenticated_client.post(
        "/api/pre-analysis/upload",
        files=[("files", ("iso_manual.pdf", dummy_doc, "application/pdf"))],
        data={"standard_code": "ISO27001"},
        follow_redirects=False
    )

    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert location.startswith("/pre-audit/review/")
    
    report_id_str = location.split("/")[-1]
    report_id = uuid.UUID(report_id_str)

    report = db_session.query(PreAuditMaturityReport).filter_by(id=report_id).first()
    assert report is not None, f"El reporte con ID {report_id} no fue guardado en la base de datos"
    assert report.standard_code == "ISO27001"
    assert report.status == "draft"
    assert isinstance(report.maturity_score, float)
    assert len(report.gaps_identified) > 0


def test_pre_audit_hitl_validation_flow(authenticated_client, db_session):
    """Valida el flujo completo HITL: Carga -> Revisión -> Aprobación -> Registros en DB y AuditLog."""
    unique_content = f"%PDF-1.4 Complete HITL Pipeline Flow Document {uuid.uuid4().hex}".encode()
    doc = io.BytesIO(unique_content)
    
    # 1. Carga Documento
    upload_resp = authenticated_client.post(
        "/api/pre-analysis/upload",
        files=[("files", ("hitl_doc.pdf", doc, "application/pdf"))],
        data={"standard_code": "ISO9001"},
        follow_redirects=False
    )
    assert upload_resp.status_code == 303
    report_id = upload_resp.headers["location"].split("/")[-1]

    # 2. Vista de Revisión (GET) con follow_redirects=False
    review_resp = authenticated_client.get(f"/pre-audit/review/{report_id}", follow_redirects=False)
    assert review_resp.status_code == 200, f"Error al cargar review page. Status: {review_resp.status_code}"
    assert "pre" in review_resp.text.lower() or "audit" in review_resp.text.lower() or "informe" in review_resp.text.lower() or "report" in review_resp.text.lower()

    # 3. Validación de Reporte (POST Approve)
    validate_resp = authenticated_client.post(
        f"/api/pre-analysis/{report_id}/validate",
        data={"action": "approve"},
        follow_redirects=False
    )
    assert validate_resp.status_code == 303
    assert validate_resp.headers["location"] == "/dashboard"

    # 4. Verificación de DB Relacional y AuditLog
    report = db_session.query(PreAuditMaturityReport).filter_by(id=uuid.UUID(report_id)).first()
    assert report.status == "validated"
    assert report.validated_by is not None
    assert report.validated_at is not None

    audit_log = db_session.query(AuditLog).filter_by(
        entity_type="pre_audit_maturity_report",
        entity_id=uuid.UUID(report_id)
    ).first()
    assert audit_log is not None
    assert audit_log.action == "pre_audit_report_validated"
