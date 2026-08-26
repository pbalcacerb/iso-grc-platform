"""Worker de análisis de cumplimiento con IA (SiliconFlow)."""
import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AIAnalysis, EvidenceTextChunk


def assess_compliance(
    evidence_file_id: uuid.UUID, 
    audit_id: uuid.UUID, 
    db: Session,
    tenant_id: Optional[uuid.UUID] = None
) -> dict:
    """
    Ejecuta el flujo de IA: Retrieve -> Cortocircuito -> LLM -> Guardar.
    
    Reglas estrictas:
    - Si no hay chunks relevantes, NO llamar al LLM (cortocircuito).
    - Si confidence < 0.75, marcar requires_human_review=True.
    """
    # PASO A: RETRIEVE - Buscar chunks del archivo
    chunks = db.query(EvidenceTextChunk).filter(
        EvidenceTextChunk.evidence_file_id == evidence_file_id
    ).all()

    # PASO B: CORTOCIRCUITO - Sin evidencia, no llamamos al LLM
    if not chunks:
        analysis = AIAnalysis(
            tenant_id=tenant_id or uuid.uuid4(),
            audit_id=audit_id,
            evidence_file_id=evidence_file_id,
            compliance_assessment="insufficient_evidence",
            gaps=[],                    # ← Lista vacía nativa
            risks=[],                   # ← Lista vacía nativa
            confidence=0.0,
            requires_human_review=False,
            review_status="completed",
            tokens_est=0,
            provider="none",
            cited_chunk_ids=[],         # ← Lista vacía nativa
        )
        db.add(analysis)
        db.commit()
        return {
            "status": "cortocircuito",
            "assessment": "insufficient_evidence",
            "confidence": 0.0,
            "tokens_est": 0,
        }

    # PASO C: Simulación de LLM (por ahora, sin llamada real)
    # En producción, aquí iría la llamada a SiliconFlow
    confidence = 0.85  # Simulado
    requires_review = confidence < 0.75

    analysis = AIAnalysis(
        tenant_id=tenant_id or uuid.uuid4(),
        audit_id=audit_id,
        evidence_file_id=evidence_file_id,
        compliance_assessment="compliant",
        gaps=[],                        # ← CAMBIO: Lista vacía nativa (NO string "[]")
        risks=[],                       # ← CAMBIO: Lista vacía nativa (NO string "[]")
        confidence=confidence,
        requires_human_review=requires_review,
        review_status="completed" if not requires_review else "pending",
        tokens_est=150,
        provider="simulated",
        cited_chunk_ids=[],             # ← AÑADIDO: Lista vacía nativa
    )
    db.add(analysis)
    db.commit()
    
    return {
        "status": "success",
        "assessment": "compliant",
        "confidence": confidence,
        "requires_human_review": requires_review,
    }