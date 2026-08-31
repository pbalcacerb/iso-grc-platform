"""Worker de análisis con IA: ingesta multi-evidencia y veredicto por ítem."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.config import settings
from app.models import (
    AIAnalysis, EvidenceFile, EvidenceTextChunk, EvidenceTextExtraction,
)
from app.utils.embeddings import create_chunks_and_embeddings, search_similar_chunks
from app.utils.text_extractor import extract_text_from_file

DEFAULT_REQUIREMENT = "Requisitos generales de ISO 9001:2015 aplicables al ítem auditado."


def _save_analysis(db, tenant_id, audit_id, evidence_file_id, **kwargs) -> AIAnalysis:
    analysis = AIAnalysis(
        tenant_id=tenant_id, audit_id=audit_id,
        evidence_file_id=evidence_file_id, **kwargs,
    )
    db.add(analysis)
    db.commit()
    return analysis


def ingest_evidence_file(
    evidence: EvidenceFile, db: Session, tenant_id: uuid.UUID,
) -> bool:
    """Extrae texto y genera chunks+embeddings (idempotente por estado)."""
    if evidence.extraction_status == "completed":
        return True

    try:
        extracted = extract_text_from_file(evidence.storage_path)
    except Exception:
        return False

    if not extracted or not extracted.strip():
        return False

    extraction = EvidenceTextExtraction(
        tenant_id=tenant_id, evidence_file_id=evidence.id,
        extractor="pypdf" if evidence.storage_path.endswith('.pdf') else "utf8",
        status="completed", extracted_text=extracted,
        text_sha256="", character_count=len(extracted),
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    if get_provider().is_configured():
        create_chunks_and_embeddings(
            evidence_file_id=evidence.id, extraction_id=extraction.id,
            text=extracted, tenant_id=tenant_id, db=db,
        )
    evidence.extraction_status = "completed"
    db.commit()
    return True


def _assess_scope(
    audit_id: uuid.UUID,
    db: Session,
    tenant_id: uuid.UUID,
    evidence_file_id: uuid.UUID,
    requirement_text: Optional[str],
    item_id: Optional[uuid.UUID],
) -> dict:
    """Veredicto del requisito contra la evidencia consolidada del ámbito."""
    requirement = requirement_text or DEFAULT_REQUIREMENT
    provider = get_provider()

    if not provider.is_configured():
        _save_analysis(db, tenant_id, audit_id, evidence_file_id,
                       compliance_assessment="partial",
                       gaps=["Requiere revisión manual: sin proveedor de IA configurado"],
                       risks=["Análisis basado solo en extracción de texto"],
                       confidence=0.70, requires_human_review=True,
                       review_status="pending", tokens_est=0,
                       provider="simulated", cited_chunk_ids=[])
        return {"status": "simulated", "assessment": "partial",
                "confidence": 0.70, "requires_human_review": True, "relevant": True}

    similar = search_similar_chunks(
        query_text=requirement, audit_id=audit_id, db=db,
        top_k=5, item_id=item_id,
    )
    if not similar:
        _save_analysis(db, tenant_id, audit_id, evidence_file_id,
                       compliance_assessment="insufficient_evidence", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=False,
                       review_status="completed", tokens_est=0,
                       provider=provider.name, cited_chunk_ids=[])
        return {"status": "cortocircuito", "assessment": "insufficient_evidence",
                "reason": "Sin chunks relevantes para el requisito", "relevant": False}

    cited = [str(c.id) for c, _ in similar]
    context_text = "\n\n---\n\n".join(c.text for c, _ in similar)

    prompt = f"""Eres un auditor experto en ISO 9001:2015, estricto y escéptico.

REQUISITO A EVALUAR:
{requirement}

EVIDENCIA CONSOLIDADA RECUPERADA:
{context_text}

PROCEDIMIENTO OBLIGATORIO:
1. RELEVANCIA: ¿La evidencia aborda DIRECTAMENTE el requisito? Si no, is_relevant=false y compliance_assessment="insufficient_evidence". PROHIBIDO otorgar crédito parcial a documentos no relacionados.
2. Si es relevante, evalúa: "compliant" | "partial" | "non_compliant".
3. Confianza 0.0-1.0 según calidad y especificidad.

RESPONDE ÚNICAMENTE con un objeto JSON válido:
{{
  "is_relevant": true | false,
  "compliance_assessment": "compliant" | "partial" | "non_compliant" | "insufficient_evidence",
  "gaps": ["..."],
  "risks": ["..."],
  "confidence": 0.0-1.0
}}"""

    try:
        ai_data = provider.chat_json(prompt)
        is_relevant = bool(ai_data.get("is_relevant", True))
        assessment = ai_data.get("compliance_assessment", "unknown")
        confidence = float(ai_data.get("confidence", 0.5))
        if not is_relevant:
            assessment = "insufficient_evidence"
            confidence = min(confidence, 0.3)
        requires_review = is_relevant and confidence < settings.CONFIDENCE_REVIEW_THRESHOLD

        _save_analysis(db, tenant_id, audit_id, evidence_file_id,
                       compliance_assessment=assessment,
                       gaps=ai_data.get("gaps", []),
                       risks=ai_data.get("risks", []),
                       confidence=confidence,
                       requires_human_review=requires_review,
                       review_status="pending" if requires_review else "completed",
                       tokens_est=150, provider=provider.name, cited_chunk_ids=cited)
        return {"status": "success", "assessment": assessment,
                "confidence": confidence, "requires_human_review": requires_review,
                "relevant": is_relevant}
    except Exception as e:
        _save_analysis(db, tenant_id, audit_id, evidence_file_id,
                       compliance_assessment="error", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=True,
                       review_status="pending", tokens_est=0,
                       provider="error", cited_chunk_ids=[])
        return {"status": "error", "detail": str(e), "relevant": False}


def assess_item(
    checklist_item_id: uuid.UUID,
    audit_id: uuid.UUID,
    evidence_file_id: uuid.UUID,
    db: Session,
    tenant_id: uuid.UUID,
    requirement_text: Optional[str] = None,
) -> dict:
    """Veredicto consolidado de un ítem con toda su evidencia."""
    return _assess_scope(audit_id, db, tenant_id, evidence_file_id,
                         requirement_text, checklist_item_id)


def assess_compliance(
    evidence_file_id: uuid.UUID,
    audit_id: uuid.UUID,
    db: Session,
    tenant_id: Optional[uuid.UUID] = None,
    requirement_text: Optional[str] = None,
    checklist_item_id: Optional[uuid.UUID] = None,
) -> dict:
    """Flujo por archivo (compatibilidad): ingesta + veredicto del ámbito."""
    evidence = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not evidence:
        return {"status": "error", "detail": "Evidencia no encontrada"}

    effective_tenant = tenant_id or evidence.tenant_id
    ok = ingest_evidence_file(evidence, db, effective_tenant)
    if not ok:
        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
                       compliance_assessment="insufficient_evidence", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=False,
                       review_status="completed", tokens_est=0,
                       provider="none", cited_chunk_ids=[])
        return {"status": "cortocircuito", "assessment": "insufficient_evidence",
                "reason": "Archivo vacío o no extraíble", "relevant": False}

    return _assess_scope(audit_id, db, effective_tenant, evidence_file_id,
                         requirement_text, checklist_item_id)