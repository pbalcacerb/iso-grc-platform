"""Worker de análisis de cumplimiento con IA (WP0 + reglas de negocio WP2)."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.models import AIAnalysis, EvidenceFile, EvidenceTextExtraction
from app.utils.embeddings import create_chunks_and_embeddings, search_similar_chunks
from app.utils.text_extractor import extract_text_from_file

CONFIDENCE_THRESHOLD = 0.75
DEFAULT_REQUIREMENT = "Requisitos generales de ISO 9001:2015 aplicables al ítem auditado."


def _save_analysis(db, tenant_id, audit_id, evidence_file_id, **kwargs) -> AIAnalysis:
    analysis = AIAnalysis(
        tenant_id=tenant_id, audit_id=audit_id,
        evidence_file_id=evidence_file_id, **kwargs,
    )
    db.add(analysis)
    db.commit()
    return analysis


def assess_compliance(
    evidence_file_id: uuid.UUID,
    audit_id: uuid.UUID,
    db: Session,
    tenant_id: Optional[uuid.UUID] = None,
    requirement_text: Optional[str] = None,
) -> dict:
    """Flujo: Extraer -> Chunks -> Retrieve(por requisito) -> Juicio de relevancia -> IA."""
    requirement = requirement_text or DEFAULT_REQUIREMENT

    evidence = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not evidence:
        return {"status": "error", "detail": "Evidencia no encontrada"}

    effective_tenant = tenant_id or evidence.tenant_id
    provider = get_provider()

    try:
        extracted = extract_text_from_file(evidence.storage_path)
    except Exception as e:
        return {"status": "error", "detail": f"Error extrayendo texto: {e}"}

    if not extracted or not extracted.strip():
        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
                       compliance_assessment="insufficient_evidence", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=False,
                       review_status="completed", tokens_est=0,
                       provider="none", cited_chunk_ids=[])
        return {"status": "cortocircuito", "assessment": "insufficient_evidence",
                "reason": "Archivo vacío o no extraíble", "relevant": False}

    extraction = EvidenceTextExtraction(
        tenant_id=effective_tenant, evidence_file_id=evidence_file_id,
        extractor="pypdf" if evidence.storage_path.endswith('.pdf') else "utf8",
        status="completed", extracted_text=extracted,
        text_sha256="", character_count=len(extracted),
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    if not provider.is_configured():
        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
                       compliance_assessment="partial",
                       gaps=["Requiere revisión manual: sin proveedor de IA configurado"],
                       risks=["Análisis basado solo en extracción de texto"],
                       confidence=0.70, requires_human_review=True,
                       review_status="pending", tokens_est=0,
                       provider="simulated", cited_chunk_ids=[])
        return {"status": "simulated", "assessment": "partial",
                "confidence": 0.70, "requires_human_review": True, "relevant": True}

    chunks = create_chunks_and_embeddings(
        evidence_file_id=evidence_file_id, extraction_id=extraction.id,
        text=extracted, tenant_id=effective_tenant, db=db,
    )
    if not chunks:
        return {"status": "error", "detail": "No se pudieron crear chunks"}

    # CAMBIO WP2: la consulta de recuperación es el REQUISITO, no el documento
    similar = search_similar_chunks(
        query_text=requirement, audit_id=audit_id, db=db, top_k=5, threshold=0.5,
    )
    if not similar:
        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
                       compliance_assessment="insufficient_evidence", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=False,
                       review_status="completed", tokens_est=0,
                       provider=provider.name, cited_chunk_ids=[])
        return {"status": "cortocircuito", "assessment": "insufficient_evidence",
                "reason": "Sin chunks relevantes para el requisito", "relevant": False}

    cited = [str(chunk.id) for chunk, _ in similar]
    context_text = "\n\n---\n\n".join(chunk.text for chunk, _ in similar)

    prompt = f"""Eres un auditor experto en ISO 9001:2015, estricto y escéptico.

REQUISITO A EVALUAR:
{requirement}

EVIDENCIA RECUPERADA:
{context_text}

PROCEDIMIENTO OBLIGATORIO:
1. RELEVANCIA: ¿La evidencia aborda DIRECTAMENTE el requisito anterior? Si el documento trata temas distintos o no responde a la pregunta, marca is_relevant=false y compliance_assessment="insufficient_evidence". PROHIBIDO otorgar crédito parcial a documentos no relacionados.
2. Si es relevante, evalúa: "compliant" | "partial" | "non_compliant".
3. Confianza 0.0-1.0 según calidad y especificidad de la evidencia.

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

        # CAMBIO WP2: documento no relacionado = rechazo categórico
        if not is_relevant:
            assessment = "insufficient_evidence"
            confidence = min(confidence, 0.3)

        requires_review = is_relevant and confidence < CONFIDENCE_THRESHOLD

        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
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
        _save_analysis(db, effective_tenant, audit_id, evidence_file_id,
                       compliance_assessment="error", gaps=[], risks=[],
                       confidence=0.0, requires_human_review=True,
                       review_status="pending", tokens_est=0,
                       provider="error", cited_chunk_ids=[])
        return {"status": "error", "detail": str(e), "relevant": False}