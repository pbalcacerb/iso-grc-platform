"""Modelos SQLAlchemy 2.0 con UUID para ISO GRC Platform."""
import uuid
from datetime import datetime
from typing import Optional

# Imports de SQLAlchemy
from sqlalchemy import JSON, Float, ForeignKey, String, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class Base(DeclarativeBase):
    pass


class Standard(Base):
    __tablename__ = "standards"
    
    # Usamos PG_UUID para compatibilidad nativa con PostgreSQL
    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=func.gen_random_uuid()
    )
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id"),
        {"schema": "public"},
    )
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String)
    # Campo client_id para aislamiento por cliente
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, default="", nullable=False)
    country: Mapped[str] = mapped_column(String, default="", nullable=False)
    confidentiality_level: Mapped[str] = mapped_column(
        String,
        default="internal",
        nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)


class Clause(Base):
    __tablename__ = "clauses"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("standards.id"),
        nullable=False
    )
    number: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class QuestionPack(Base):
    __tablename__ = "question_packs"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id"),
        nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("standards.id"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="planned", nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column()
    end_date: Mapped[Optional[datetime]] = mapped_column()
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"),
        nullable=False
    )
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id"),
        nullable=False
    )
    question_pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_packs.id"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    response: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"),
        nullable=False
    )
    checklist_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("checklist_items.id")
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    classification: Mapped[str] = mapped_column(
        String,
        default="internal",
        nullable=False
    )
    upload_status: Mapped[str] = mapped_column(
        String,
        default="ready",
        nullable=False
    )
    extraction_status: Mapped[str] = mapped_column(
        String,
        default="pending",
        nullable=False
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class EvidenceTextExtraction(Base):
    __tablename__ = "evidence_text_extractions"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"),
        nullable=False
    )
    extractor: Mapped[str] = mapped_column(String, default="utf8", nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        default="completed",
        nullable=False
    )
    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    text_sha256: Mapped[str] = mapped_column(String, default="", nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class EvidenceTextChunk(Base):
    __tablename__ = "evidence_text_chunks"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_text_extractions.id"),
        nullable=False
    )
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"),
        nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String, default="", nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EvidenceVector(Base):
    __tablename__ = "evidence_vectors"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_text_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)


class AIJob(Base):
    __tablename__ = "ai_jobs"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    input_ref: Mapped[uuid.UUID] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    output_ref: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"),
        nullable=False
    )
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"),
        nullable=False
    )
    compliance_assessment: Mapped[str] = mapped_column(
        String,
        default="insufficient_evidence",
        nullable=False
    )
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[Optional[float]] = mapped_column()
    requires_human_review: Mapped[bool] = mapped_column(default=True, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String,
        default="pending",
        nullable=False
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    cited_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String, default="", nullable=False)
    tokens_est: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"),
        nullable=False
    )
    checklist_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("checklist_items.id")
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("ai_analyses.id")
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    ai_suggested: Mapped[bool] = mapped_column(default=False, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column()
    before: Mapped[Optional[str]] = mapped_column(JSON)
    after: Mapped[Optional[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )


class PreAuditMaturityReport(Base):
    """Informe de Madurez Preliminar generado por IA antes de la auditoría in-situ (§6.2 ISO 19011)."""
    __tablename__ = "pre_audit_maturity_reports"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    standard_code: Mapped[str] = mapped_column(String, nullable=False)
    document_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    maturity_score: Mapped[float] = mapped_column(Float, nullable=False)
    gaps_identified: Mapped[list] = mapped_column(JSON, default=list)
    risks_preliminary: Mapped[list] = mapped_column(JSON, default=list)
    ai_recommendations: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="draft")
    validated_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    validated_at: Mapped[Optional[datetime]] = mapped_column()


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )