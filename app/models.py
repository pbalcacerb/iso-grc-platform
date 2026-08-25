# Database models in SQLAlchemy 2.0
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()

class Tenant(Base):
    __tablename__ = 'tenants'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text('now()'), nullable=False)
    memberships: Mapped[list['Membership']] = relationship(back_populates="tenant")

class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text('now()'), nullable=False)
    memberships: Mapped[list['Membership']] = relationship(back_populates="user")

class Membership(Base):
    __tablename__ = 'memberships'
    __table_args__ = (
        UniqueConstraint('user_id', 'tenant_id', name='uq_membership_user_tenant'),
        {"schema": "public"}
    )
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('users.id'), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('tenants.id'), nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)
    user: Mapped['User'] = relationship(back_populates="memberships")
    tenant: Mapped['Tenant'] = relationship(back_populates="memberships")

class Client(Base):
    __tablename__ = 'clients'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    tenant_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('tenants.id'), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    sector: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)
    confidentiality_level: Mapped[str] = mapped_column(nullable=False)
    audits: Mapped[list['Audit']] = relationship(back_populates="client")
class Audit(Base):
    __tablename__ = 'audits'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    tenant_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('tenants.id'), nullable=False)
    client_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('clients.id'), nullable=False)
    standard_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('standards.id'), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'planned'"))
    start_date: Mapped[datetime] = mapped_column(nullable=True)
    end_date: Mapped[datetime] = mapped_column(nullable=True)
    lead_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('users.id'), nullable=True)
    client: Mapped['Client'] = relationship(back_populates="audits")
    standard: Mapped['Standard'] = relationship(back_populates="audits")
    checklist_items: Mapped[list['ChecklistItem']] = relationship(back_populates="audit")

class Standard(Base):
    __tablename__ = 'standards'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    code: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'active'"))
    audits: Mapped[list['Audit']] = relationship(back_populates="standard")
    clauses: Mapped[list['Clause']] = relationship(back_populates="standard")

class Clause(Base):
    __tablename__ = 'clauses'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    standard_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('standards.id'), nullable=False)
    number: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    standard: Mapped['Standard'] = relationship(back_populates="clauses")
    question_packs: Mapped[list['QuestionPack']] = relationship(back_populates="clause")

class QuestionPack(Base):
    __tablename__ = 'question_packs'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    clause_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('clauses.id'), nullable=False)
    question: Mapped[str] = mapped_column(nullable=False)
    expected_evidence: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    criteria: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default=text('0'))
    clause: Mapped['Clause'] = relationship(back_populates="question_packs")
    checklist_items: Mapped[list['ChecklistItem']] = relationship(back_populates="question_pack")

class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    tenant_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, nullable=False)
    audit_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('audits.id'), nullable=False)
    clause_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('clauses.id'), nullable=False)
    question_pack_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey('question_packs.id'), nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'pending'"))
    response: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    notes: Mapped[str] = mapped_column(nullable=False, server_default=text("''"))
    audit: Mapped['Audit'] = relationship(back_populates="checklist_items")
    question_pack: Mapped['QuestionPack'] = relationship(back_populates="checklist_items")