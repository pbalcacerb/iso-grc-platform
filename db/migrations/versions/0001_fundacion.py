"""Fundación

Revision ID: 0001_fundacion
Revises: 
Create Date: 2026-08-23 00:00:00
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0001_fundacion'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Crear extensión para vectores
    op.execute("""CREATE EXTENSION IF NOT EXISTS vector""")

    # Tabla: tenants
    op.execute("""
    CREATE TABLE tenants (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL
    )""")

    # Tabla: users
    op.execute("""
    CREATE TABLE users (
        id UUID PRIMARY KEY,
        email TEXT NOT NULL UNIQUE
    )""")

    # Tabla: memberships
    op.execute("""
    CREATE TABLE memberships (
        user_id UUID REFERENCES users(id),
        tenant_id UUID REFERENCES tenants(id),
        role TEXT CHECK (role IN ('owner', 'lead_auditor', 'auditor', 'client_admin', 'viewer')),
        PRIMARY KEY (user_id, tenant_id)
    )""")

    # Tabla: clients
    op.execute("""
    CREATE TABLE clients (
        id UUID PRIMARY KEY,
        tenant_id UUID REFERENCES tenants(id),
        name TEXT NOT NULL
    )""")

    # Tabla: standards
    op.execute("""
    CREATE TABLE standards (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL
    )""")

    # Tabla: clauses
    op.execute("""
    CREATE TABLE clauses (
        id UUID PRIMARY KEY,
        standard_id UUID REFERENCES standards(id),
        text TEXT NOT NULL
    )""")

    # Tabla: question_packs
    op.execute("""
    CREATE TABLE question_packs (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL
    )""")

    # Tabla: audits
    op.execute("""
    CREATE TABLE audits (
        id UUID PRIMARY KEY,
        tenant_id UUID REFERENCES tenants(id),
        client_id UUID REFERENCES clients(id),
        status TEXT NOT NULL
    )""")

    # Tabla: checklist_items
    op.execute("""
    CREATE TABLE checklist_items (
        id UUID PRIMARY KEY,
        audit_id UUID REFERENCES audits(id),
        clause_id UUID REFERENCES clauses(id),
        status TEXT NOT NULL
    )""")

    # Tabla: evidence_files
    op.execute("""
    CREATE TABLE evidence_files (
        id UUID PRIMARY KEY,
        audit_id UUID REFERENCES audits(id),
        file_path TEXT NOT NULL
    )""")

    # Tabla: evidence_text_extractions
    op.execute("""
    CREATE TABLE evidence_text_extractions (
        id UUID PRIMARY KEY,
        evidence_file_id UUID REFERENCES evidence_files(id),
        extracted_text TEXT NOT NULL
    )""")

    # Tabla: evidence_text_chunks
    op.execute("""
    CREATE TABLE evidence_text_chunks (
        id UUID PRIMARY KEY,
        extraction_id UUID REFERENCES evidence_text_extractions(id),
        chunk_text TEXT NOT NULL
    )""")

    # Tabla: evidence_vectors
    op.execute("""
    CREATE TABLE evidence_vectors (
        chunk_id UUID PRIMARY KEY REFERENCES evidence_text_chunks(id),
        tenant_id UUID REFERENCES tenants(id),
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        embedding vector(1024)
    )""")

    # Tabla: ai_jobs
    op.execute("""
    CREATE TABLE ai_jobs (
        id UUID PRIMARY KEY,
        input_ref TEXT NOT NULL,
        job_type TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        UNIQUE (input_ref, job_type, content_hash)
    )""")

    # Tabla: ai_analyses
    op.execute("""
    CREATE TABLE ai_analyses (
        id UUID PRIMARY KEY,
        job_id UUID REFERENCES ai_jobs(id),
        cited_chunk_ids UUID[] NOT NULL,
        confidence FLOAT NOT NULL,
        requires_human_review BOOLEAN NOT NULL,
        review_status TEXT NOT NULL,
        tokens_est INTEGER NOT NULL
    )""")

    # Tabla: findings
    op.execute("""
    CREATE TABLE findings (
        id UUID PRIMARY KEY,
        audit_id UUID REFERENCES audits(id),
        analysis_id UUID REFERENCES ai_analyses(id),
        description TEXT NOT NULL
    )""")

    # Tabla: audit_logs (append-only)
    op.execute("""
    CREATE TABLE audit_logs (
        id UUID PRIMARY KEY,
        tenant_id UUID REFERENCES tenants(id),
        action TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    )""")

    # ========== POLÍTICAS DE RLS ==========

    # Políticas para tablas tenant-scoped
    op.execute("""ALTER TABLE memberships ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE memberships FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY tenant_isolation_policy ON memberships
        USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    """)

    op.execute("""ALTER TABLE clients ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE clients FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY client_tenant_policy ON clients
        USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    """)

    op.execute("""ALTER TABLE audits ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE audits FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY audit_tenant_policy ON audits
        USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    """)

    # Políticas para tablas shared
    op.execute("""ALTER TABLE standards ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE standards FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY shared_select_policy ON standards
        USING (true)
    """)

    op.execute("""ALTER TABLE clauses ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE clauses FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY clauses_select_policy ON clauses
        USING (true)
    """)

    # Política para audit_logs (append-only)
    op.execute("""ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY""")
    op.execute("""
    CREATE POLICY audit_logs_insert_policy ON audit_logs
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID)
    """)

    # Índices por tenant_id
    op.execute("""CREATE INDEX idx_clients_tenant_id ON clients(tenant_id)""")
    op.execute("""CREATE INDEX idx_evidence_vectors_tenant_id ON evidence_vectors(tenant_id)""")


def downgrade():
    # Eliminar índices
    op.execute("""DROP INDEX IF EXISTS idx_evidence_vectors_tenant_id""")
    op.execute("""DROP INDEX IF EXISTS idx_clients_tenant_id""")

    # Eliminar políticas RLS
    op.execute("""DROP POLICY IF EXISTS audit_logs_insert_policy ON audit_logs""")
    op.execute("""DROP POLICY IF EXISTS clauses_select_policy ON clauses""")
    op.execute("""DROP POLICY IF EXISTS shared_select_policy ON standards""")
    op.execute("""DROP POLICY IF EXISTS audit_tenant_policy ON audits""")
    op.execute("""DROP POLICY IF EXISTS client_tenant_policy ON clients""")
    op.execute("""DROP POLICY IF EXISTS tenant_isolation_policy ON memberships""")

    # Deshabilitar RLS
    op.execute("""ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE clauses DISABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE standards DISABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE audits DISABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE clients DISABLE ROW LEVEL SECURITY""")
    op.execute("""ALTER TABLE memberships DISABLE ROW LEVEL SECURITY""")

    # Eliminar tablas en orden inverso
    op.execute("""DROP TABLE IF EXISTS findings""")
    op.execute("""DROP TABLE IF EXISTS ai_analyses""")
    op.execute("""DROP TABLE IF EXISTS ai_jobs""")
    op.execute("""DROP TABLE IF EXISTS evidence_vectors""")
    op.execute("""DROP TABLE IF EXISTS evidence_text_chunks""")
    op.execute("""DROP TABLE IF EXISTS evidence_text_extractions""")
    op.execute("""DROP TABLE IF EXISTS evidence_files""")
    op.execute("""DROP TABLE IF EXISTS checklist_items""")
    op.execute("""DROP TABLE IF EXISTS audits""")
    op.execute("""DROP TABLE IF EXISTS question_packs""")
    op.execute("""DROP TABLE IF EXISTS clauses""")
    op.execute("""DROP TABLE IF EXISTS standards""")
    op.execute("""DROP TABLE IF EXISTS clients""")
    op.execute("""DROP TABLE IF EXISTS memberships""")
    op.execute("""DROP TABLE IF EXISTS users""")
    op.execute("""DROP TABLE IF EXISTS tenants""")

    # Eliminar extensión
    op.execute("""DROP EXTENSION IF EXISTS vector""")