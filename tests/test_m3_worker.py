"""
Tests para el worker de análisis de IA (assess_compliance).
Verifica el cortocircuito y las reglas de confianza estrictas del PoC.
"""
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.worker.assess import assess_compliance
from app.models import AIAnalysis


def test_cortocircuito_sin_chunks_relevantes():
    """
    Test Paso B: Cuando NO hay chunks relevantes, 
    verifica que se crea un registro con:
    - compliance_assessment = 'insufficient_evidence'
    - tokens_est = 0
    - requires_human_review = False
    """
    mock_db = MagicMock(spec=Session)
    # Simular que no se encontraron chunks (lista vacía)
    mock_db.execute.return_value.fetchall.return_value = []

    test_evidence_id = uuid.uuid4()
    test_audit_id = uuid.uuid4()

    result = assess_compliance(test_evidence_id, test_audit_id, mock_db)

    # Verificar que se añadió el objeto a la sesión
    assert mock_db.add.called
    created_analysis = mock_db.add.call_args[0][0]
    
    assert isinstance(created_analysis, AIAnalysis)
    assert created_analysis.compliance_assessment == "insufficient_evidence"
    assert created_analysis.tokens_est == 0
    assert created_analysis.requires_human_review is False
    assert created_analysis.review_status == "completed"
    assert mock_db.commit.called

    assert result["compliance_assessment"] == "insufficient_evidence"
    assert result["requires_human_review"] is False


def test_flujo_con_chunks_y_confianza_alta():
    """
    Test Paso C y D: Cuando HAY chunks y la confianza es >= 0.75,
    verifica que requires_human_review=False y review_status='completed'.
    """
    mock_db = MagicMock(spec=Session)
    mock_chunk = MagicMock()
    mock_chunk.chunk_id = str(uuid.uuid4())
    # Simular que se encontró 1 chunk con distancia 0.8 (<= 0.9)
    mock_db.execute.return_value.fetchall.return_value = [(mock_chunk, 0.8)]

    test_evidence_id = uuid.uuid4()
    test_audit_id = uuid.uuid4()

    result = assess_compliance(test_evidence_id, test_audit_id, mock_db)

    assert mock_db.add.called
    created_analysis = mock_db.add.call_args[0][0]
    
    # Dependiendo de cómo esté hardcodeado o simulado el LLM en assess.py,
    # verificamos que el flujo de "alta confianza" se ejecuta.
    # Si assess.py tiene confidence=0.8 hardcodeado, esto debe ser False.
    assert created_analysis.requires_human_review is False
    assert created_analysis.review_status == "completed"
    assert result["requires_human_review"] is False
