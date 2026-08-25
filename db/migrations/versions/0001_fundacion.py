"""Fundación

Revision ID: 0001_fundacion
Revises: 
Create Date: 2026-08-23 00:00:00
"""
from alembic import op

revision = "0001_fundacion"
down_revision = None
branch_labels = None
depends_on = None

EXT = """CREATE EXTENSION IF NOT EXISTS vector"""

CORE = """
create table tenants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    status text not null default 'active',
    created_at timestamptz not null default now()
);
create table users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    password_hash text not null,
    full_name text not null default '',
    status text not null default 'active',
    created_at timestamptz not null default now()
);
create table standards (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,
    name text not null,
    version text not null default '',
    status text not null default 'active'
);
create table clauses (
    id uuid primary key default gen_random_uuid(),
    standard_id uuid not null references standards(id),
    number text not null,
    title text not null,
    description text not null default ''
);
create table question_packs (
    id uuid primary key default gen_random_uuid(),
    clause_id uuid not null references clauses(id),
    question text not null,
    expected_evidence text not null default '',
    criteria text not null default '',
    sort_order int not null default 0
);
create table memberships (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id),
    tenant_id uuid not null references tenants(id),
    role text not null,
    unique (user_id, tenant_id)
);
create table clients (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id),
    name text not null,
    sector text not null default '',
    country text not null default '',
    confidentiality_level text not null default 'internal',
    status text not null default 'active'
);
create table audits (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    client_id uuid not null references clients(id),
    standard_id uuid not null references standards(id),
    name text not null,
    status text not null default 'planned',
    start_date date,
    end_date date,
    lead_id uuid references users(id)
);
create table checklist_items (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    audit_id uuid not null references audits(id),
    clause_id uuid not null references clauses(id),
    question_pack_id uuid not null references question_packs(id),
    status text not null default 'pending',
    response text not null default '',
    notes text not null default ''
);
create table evidence_files (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    audit_id uuid not null references audits(id),
    checklist_item_id uuid references checklist_items(id),
    original_filename text not null,
    mime_type text not null,
    file_size bigint not null default 0,
    sha256 text not null,
    storage_path text not null,
    classification text not null default 'internal',
    upload_status text not null default 'ready',
    extraction_status text not null default 'pending',
    uploaded_by uuid references users(id)
);
create table evidence_text_extractions (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    evidence_file_id uuid not null references evidence_files(id),
    extractor text not null default 'utf8',
    status text not null default 'completed',
    extracted_text text not null default '',
    text_sha256 text not null default '',
    character_count int not null default 0,
    requested_by uuid references users(id)
);
create table evidence_text_chunks (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    extraction_id uuid not null references evidence_text_extractions(id),
    evidence_file_id uuid not null references evidence_files(id),
    seq int not null,
    text text not null,
    sha256 text not null default '',
    character_count int not null default 0
);
create table evidence_vectors (
    id uuid primary key default gen_random_uuid(),
    chunk_id uuid not null unique references evidence_text_chunks(id) on delete cascade,
    tenant_id uuid not null,
    model text not null,
    dim int not null,
    embedding vector(1024)
);
create table ai_jobs (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    job_type text not null,
    input_ref uuid not null,
    content_hash text not null,
    status text not null default 'queued',
    attempts int not null default 0,
    error_message text,
    output_ref text,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    unique (input_ref, job_type, content_hash)
);
create table ai_analyses (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    audit_id uuid not null references audits(id),
    evidence_file_id uuid not null references evidence_files(id),
    compliance_assessment text not null default 'insufficient_evidence',
    gaps jsonb not null default '[]',
    risks jsonb not null default '[]',
    confidence numeric,
    requires_human_review boolean not null default true,
    review_status text not null default 'pending',
    reviewed_by uuid references users(id),
    cited_chunk_ids jsonb not null default '[]',
    provider text not null default '',
    tokens_est int not null default 0,
    created_at timestamptz not null default now()
);
create table findings (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    audit_id uuid not null references audits(id),
    checklist_item_id uuid references checklist_items(id),
    analysis_id uuid references ai_analyses(id),
    type text not null,
    title text not null,
    description text not null default '',
    status text not null default 'open',
    ai_suggested boolean not null default false
);
create table audit_logs (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null,
    actor_user_id uuid,
    action text not null,
    entity_type text not null,
    entity_id uuid,
    before jsonb,
    after jsonb,
    created_at timestamptz not null default now()
);
"""

INDEXES = """
create index idx_memberships_tenant on memberships(tenant_id);
create index idx_clients_tenant on clients(tenant_id);
create index idx_audits_tenant on audits(tenant_id);
create index idx_checklist_tenant on checklist_items(tenant_id);
create index idx_evidence_tenant on evidence_files(tenant_id);
create index idx_extractions_tenant on evidence_text_extractions(tenant_id);
create index idx_chunks_tenant on evidence_text_chunks(tenant_id);
create index idx_vectors_tenant on evidence_vectors(tenant_id);
create index idx_jobs_tenant on ai_jobs(tenant_id);
create index idx_analyses_tenant on ai_analyses(tenant_id);
create index idx_findings_tenant on findings(tenant_id);
create index idx_audit_logs_tenant on audit_logs(tenant_id);
"""

RLS = """
alter table memberships enable row level security;
alter table memberships force row level security;
alter table clients enable row level security;
alter table clients force row level security;
alter table audits enable row level security;
alter table audits force row level security;
alter table checklist_items enable row level security;
alter table checklist_items force row level security;
alter table evidence_files enable row level security;
alter table evidence_files force row level security;
alter table evidence_text_extractions enable row level security;
alter table evidence_text_extractions force row level security;
alter table evidence_text_chunks enable row level security;
alter table evidence_text_chunks force row level security;
alter table evidence_vectors enable row level security;
alter table evidence_vectors force row level security;
alter table ai_jobs enable row level security;
alter table ai_jobs force row level security;
alter table ai_analyses enable row level security;
alter table ai_analyses force row level security;
alter table findings enable row level security;
alter table findings force row level security;
alter table audit_logs enable row level security;
alter table audit_logs force row level security;
alter table standards enable row level security;
alter table standards force row level security;
alter table clauses enable row level security;
alter table clauses force row level security;
alter table question_packs enable row level security;
alter table question_packs force row level security;
"""

POLICIES = """
create policy memberships_tenant on memberships
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy clients_tenant on clients
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy audits_tenant on audits
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy checklist_items_tenant on checklist_items
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy evidence_files_tenant on evidence_files
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy extractions_tenant on evidence_text_extractions
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy chunks_tenant on evidence_text_chunks
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy vectors_tenant on evidence_vectors
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy ai_jobs_tenant on ai_jobs
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy ai_analyses_tenant on ai_analyses
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy findings_tenant on findings
    using (tenant_id::text = current_setting('app.current_tenant_id', true))
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));

-- AÑADIR ESTAS DOS LÍNEAS:
create policy audit_logs_select on audit_logs for select
    using (tenant_id::text = current_setting('app.current_tenant_id', true));
create policy audit_logs_insert on audit_logs for insert
    with check (tenant_id::text = current_setting('app.current_tenant_id', true));

create policy standards_select on standards for select using (true);
create policy standards_write on standards for insert
    with check (current_setting('app.is_platform_admin', true) = 'true');
create policy clauses_select on clauses for select using (true);
create policy clauses_write on clauses for insert
    with check (current_setting('app.is_platform_admin', true) = 'true');
create policy qpacks_select on question_packs for select using (true);
create policy qpacks_write on question_packs for insert
    with check (current_setting('app.is_platform_admin', true) = 'true');
"""

DOWN = """
drop table if exists audit_logs, findings, ai_analyses, ai_jobs,
    evidence_vectors, evidence_text_chunks, evidence_text_extractions,
    evidence_files, checklist_items, audits, clients, memberships,
    question_packs, clauses, standards, users, tenants cascade;
"""


def upgrade() -> None:
    try:
        op.execute(EXT)
    except Exception:
        pass  # Extensión ya creada por superuser en bootstrap de tests
    op.execute(CORE)
    op.execute(INDEXES)
    op.execute(RLS)
    op.execute(POLICIES)


def downgrade() -> None:
    op.execute(DOWN)