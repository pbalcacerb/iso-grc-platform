"""Endpoints para gestión de evidencias."""
import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EvidenceFile

router = APIRouter(prefix="/api", tags=["evidences"])

# Directorio base para almacenar evidencias
EVIDENCE_DIR = Path("data/evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


class EvidenceUploadResponse(BaseModel):
    id: str
    filename: str
    sha256: str
    extraction_status: str


@router.post("/evidences", response_model=EvidenceUploadResponse)
def upload_evidence(
    file: UploadFile,
    audit_id: str = Form(...),  # <-- CAMBIO CLAVE: Ahora lee del formulario
    db: Session = Depends(get_db),
) -> EvidenceUploadResponse:
    # 1. Validar tipo de archivo
    allowed_types = ["text/plain", "application/pdf", "text/csv"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Allowed: {allowed_types}",
        )

    # 2. Leer contenido y calcular hash SHA-256
    file_content = file.file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()

    # 3. Guardar archivo físicamente
    file_path = EVIDENCE_DIR / file_hash
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 4. Crear registro en la base de datos
    db_evidence = EvidenceFile(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),  # TODO: Derivar del contexto de sesión en M3 completo
        audit_id=uuid.UUID(audit_id),
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(file_content),
        sha256=file_hash,
        storage_path=str(file_path),
        classification="internal",
        upload_status="ready",
        extraction_status="pending",
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)

    return EvidenceUploadResponse(
        id=str(db_evidence.id),
        filename=db_evidence.original_filename,
        sha256=db_evidence.sha256,
        extraction_status=db_evidence.extraction_status,
    )