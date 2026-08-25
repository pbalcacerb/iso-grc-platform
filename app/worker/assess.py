"""
Worker de análisis de IA para evaluar el cumplimiento de evidencias.
Implementa la lógica estricta del PoC con umbrales de costo y confianza.
"""
import uuid
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import AIAnalysis, EvidenceVector

def assess_compliance(evidence_file_id: uuid.UUID, audit_id: uuid.UUID, db: Session) -> Dict:
    """
    Evalúa el cumplimiento de una evidencia usando IA.
    
    Args:
        evidence_file_id: UUID del archivo de evidencia.
        audit_id: UUID de la auditoría asociada.
        db: Sesión de base de datos.
    
    Returns:
        Dict con los resultados del análisis.
    """
    # Paso A: Buscar chunks relevantes en evidence_vectors con distancia <= 0.9
    query = text("""
        SELECT chunk_id, distance
        FROM evidence_vectors
        WHERE evidence_file_id = :evidence_file_id
        AND distance <= 0.9
        ORDER BY distance ASC
    """)
    result = db.execute(query, {"evidence_file_id": str(evidence_file_id)}).fetchall()
    
    # Paso B: Cortocircuito si no hay chunks relevantes (ahorro de costos)
    if not result:
        analysis = AIAnalysis(
            tenant_id=uuid.uuid4(),  # Esto debería obtenerse del contexto real
            audit_id=audit_id,
            evidence_file_id=evidence_file_id,
            compliance_assessment="insufficient_evidence",
            gaps="[]",
            risks="[]",
            confidence=None,
            requires_human_review=False,
            review_status="completed",
            tokens_est=0,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        return {
            "compliance_assessment": "insufficient_evidence",
            "requires_human_review": False,
            "review_status": "completed",
        }
    
    # Paso C (simulado): Si hay chunks, simular la llamada al LLM
    # Nota: En producción, esto se reemplazaría con una llamada real a un LLM.
    compliance_assessment = "sufficient_evidence"
    gaps = ["gap_1", "gap_2"]  # Lista simulada de brechas
    risks = ["risk_1", "risk_2"]  # Lista simulada de riesgos
    confidence = 0.8  # Valor simulado (cambiar a 0.6 para probar revisión humana)
    cited_chunk_ids = [str(row[0]) for row in result]  # UUIDs de chunks relevantes
    
    # Paso D: Evaluar la confianza y decidir si requiere revisión humana
    requires_human_review = confidence < 0.75
    review_status = "pending" if requires_human_review else "completed"
    
    analysis = AIAnalysis(
        tenant_id=uuid.uuid4(),  # Esto debería obtenerse del contexto real
        audit_id=audit_id,
        evidence_file_id=evidence_file_id,
        compliance_assessment=compliance_assessment,
        gaps=str(gaps),
        risks=str(risks),
        confidence=confidence,
        requires_human_review=requires_human_review,
        review_status=review_status,
        cited_chunk_ids=str(cited_chunk_ids),
        tokens_est=100,  # Valor simulado
        provider="simulated_llm",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    return {
        "compliance_assessment": compliance_assessment,
        "gaps": gaps,
        "risks": risks,
        "confidence": confidence,
        "requires_human_review": requires_human_review,
        "review_status": review_status,
        "cited_chunk_ids": cited_chunk_ids,
    }
