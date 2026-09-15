"""
Modelos SQLAlchemy 2.0 con UUID para la plataforma ISO GRC.
Organizados por dominio funcional conforme a las especificaciones ISO 19011.
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, synonym


class Base(DeclarativeBase):
    pass


# ==============================================================================
# ENUMS
# ==============================================================================

class ComplianceStatus(str, PyEnum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    OBSERVATION = "OBSERVATION"
    NA = "NA"


class FindingSeverity(str, PyEnum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class FindingStatus(str, PyEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CAPAStatus(str, PyEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"


# ==============================================================================
# 1. SISTEMA BASE MULTI-TENANT Y AUTENTICACIÓN
# ==============================================================================

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    findings: Mapped[List["Finding"]] = relationship("Finding", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id"),
)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, default="", nullable=False)
    country: Mapped[str] = mapped_column(String, default="", nullable=False)
    confidentiality_level: Mapped[str] = mapped_column(
        String, default="internal", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default="active", server_default="active", nullable=False
    )

    audits: Mapped[List["Audit"]] = relationship("Audit", back_populates="client")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
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


# ==============================================================================
# 2. NORMATIVA Y CATÁLOGOS STANDARD
# ==============================================================================

class Standard(Base):
    __tablename__ = "standards"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("standards.id"), nullable=False
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
        server_default=func.gen_random_uuid(),
    )
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# ==============================================================================
# 3. PLANIFICACIÓN Y EJECUCIÓN DE AUDITORÍAS (ISO 19011 §6.4 - §6.6)
# ==============================================================================

class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("standards.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="planned", nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column()
    end_date: Mapped[Optional[datetime]] = mapped_column()
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closing_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship("Client", back_populates="audits")
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="audit", cascade="all, delete-orphan"
    )


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"), nullable=False
    )
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id"), nullable=False
    )
    question_pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_packs.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    response: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default="", nullable=True)
    findings_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditChecklist(Base):
    __tablename__ = "audit_checklists"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"), nullable=False
    )
    standard_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="")
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    items: Mapped[List["AuditChecklistItem"]] = relationship(
        "AuditChecklistItem",
        back_populates="checklist",
        cascade="all, delete-orphan",
    )


class AuditChecklistItem(Base):
    __tablename__ = "audit_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audit_checklists.id"), nullable=False
    )
    clause_ref: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[Optional[str]] = mapped_column(String(100))

    checklist: Mapped["AuditChecklist"] = relationship(
        "AuditChecklist", back_populates="items"
    )
    responses: Mapped[List["AuditChecklistResponse"]] = relationship(
        "AuditChecklistResponse",
        back_populates="item",
        cascade="all, delete-orphan",
    )


class AuditChecklistResponse(Base):
    __tablename__ = "audit_checklist_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("audit_checklist_items.id"), nullable=False
    )
    evidence_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("evidence_files.id"), nullable=True
    )
    auditor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliancestatus", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplianceStatus.NON_COMPLIANT,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    checklist_item_id = synonym("item_id")

    item: Mapped["AuditChecklistItem"] = relationship(
        "AuditChecklistItem", back_populates="responses"
    )
    evidence: Mapped[Optional["EvidenceFile"]] = relationship(
        "EvidenceFile", foreign_keys=[evidence_file_id]
    )

    def __init__(self, **kwargs):
        kwargs.pop("audit_id", None)
        super().__init__(**kwargs)

    @property
    def audit_id(self):
        if self.item and self.item.checklist:
            return self.item.checklist.audit_id
        return None


# ==============================================================================
# 4. GESTIÓN DE EVIDENCIAS Y MOTOR VECTORIAL RAG
# ==============================================================================

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"), nullable=False
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
        String, default="internal", nullable=False
    )
    upload_status: Mapped[str] = mapped_column(
        String, default="ready", nullable=False
    )
    extraction_status: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class EvidenceTextExtraction(Base):
    __tablename__ = "evidence_text_extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"), nullable=False
    )
    extractor: Mapped[str] = mapped_column(String, default="utf8", nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="completed", nullable=False
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
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_text_extractions.id"), nullable=False
    )
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"), nullable=False
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
        server_default=func.gen_random_uuid(),
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_text_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    model: Mapped[str] = mapped_column(String, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)


# ==============================================================================
# 5. ASISTENCIA DE IA Y TRABAJOS ASÍNCRONOS
# ==============================================================================

class AIJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    input_ref: Mapped[uuid.UUID] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    output_ref: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audits.id"), nullable=False
    )
    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id"), nullable=False
    )
    compliance_assessment: Mapped[str] = mapped_column(
        String, default="insufficient_evidence", nullable=False
    )
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[Optional[float]] = mapped_column()
    requires_human_review: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    cited_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String, default="", nullable=False)
    tokens_est: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )


class PreAuditMaturityReport(Base):
    __tablename__ = "pre_audit_maturity_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
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


# ==============================================================================
# 6. HALLAZGOS Y ACCIONES CORRECTIVAS (CAPA) - ISO 19011 §6.5
# ==============================================================================

class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True
    )
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("audit_checklist_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ai_analyses.id"), nullable=True
    )

    type: Mapped[str] = mapped_column(String(50), default="non_conformity", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(50), default="MINOR", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    corrective_actions: Mapped[List["CorrectiveAction"]] = relationship(
        "CorrectiveAction", back_populates="finding", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["FindingAttachment"]] = relationship(
        "FindingAttachment", back_populates="finding", cascade="all, delete-orphan"
    )
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="findings")
    audit: Mapped["Audit"] = relationship("Audit", back_populates="findings")
    checklist_item: Mapped[Optional["AuditChecklistItem"]] = relationship("AuditChecklistItem")


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("findings.id"), nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    action_plan: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=CAPAStatus.PLANNED.value, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    finding: Mapped["Finding"] = relationship(
        "Finding", back_populates="corrective_actions"
    )
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assigned_to])


class FindingAttachment(Base):
    __tablename__ = "finding_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("findings.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    finding: Mapped["Finding"] = relationship("Finding", back_populates="attachments")


# ==============================================================================
# 7. LOGS DE SISTEMA Y AUDITORÍA DE ACCIONES
# ==============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column()
    before: Mapped[Optional[str]] = mapped_column(JSON)
    after: Mapped[Optional[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )