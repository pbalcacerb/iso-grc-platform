import os
import subprocess
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://grc:grc@localhost:5432/grc_test",
)

TENANT_A = uuid.uuid4()          # Paso 2: UUIDs reales, generados por corrida
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
CLIENT_A = uuid.uuid4()
CLIENT_B = uuid.uuid4()


@pytest.fixture(scope="session")
def engine():
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
    eng = create_engine(TEST_URL)
    yield eng
    eng.dispose()


@contextmanager
def tenant_session(eng, tenant_id, user_id=None):
    """Paso 1: SET LOCAL efectivo = set_config(..., true) DENTRO de una transacción."""
    with eng.begin() as conn:                       # begin() abre transacción real
        conn.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tenant_id)})
        if user_id is not None:
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_id)})
        yield conn


@pytest.fixture(scope="session", autouse=True)
def seed(engine):
    with engine.begin() as c:                       # tenants/users: sin RLS por diseño
        c.execute(text("INSERT INTO tenants (id, name, slug, status) VALUES (:id,'Tenant A','tenant-a','active')"), {"id": TENANT_A})
        c.execute(text("INSERT INTO tenants (id, name, slug, status) VALUES (:id,'Tenant B','tenant-b','active')"), {"id": TENANT_B})
        c.execute(text("INSERT INTO users (id, email, password_hash, full_name, status) VALUES (:id,'a@test.com','x','User A','active')"), {"id": USER_A})
        c.execute(text("INSERT INTO users (id, email, password_hash, full_name, status) VALUES (:id,'b@test.com','x','User B','active')"), {"id": USER_B})
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text("INSERT INTO memberships (id, user_id, tenant_id, role) VALUES (:id,:u,:t,'owner')"), {"id": uuid.uuid4(), "u": USER_A, "t": TENANT_A})
        c.execute(text("INSERT INTO clients (id, tenant_id, name, sector, country, confidentiality_level, status) VALUES (:id,:t,'Client A','tech','DO','internal','active')"), {"id": CLIENT_A, "t": TENANT_A})
    with tenant_session(engine, TENANT_B, USER_B) as c:
        c.execute(text("INSERT INTO memberships (id, user_id, tenant_id, role) VALUES (:id,:u,:t,'owner')"), {"id": uuid.uuid4(), "u": USER_B, "t": TENANT_B})
        c.execute(text("INSERT INTO clients (id, tenant_id, name, sector, country, confidentiality_level, status) VALUES (:id,:t,'Client B','tech','DO','internal','active')"), {"id": CLIENT_B, "t": TENANT_B})
    yield


def test_tenant_isolation(engine):
    with tenant_session(engine, TENANT_A, USER_A) as c:
        cross = c.execute(text("SELECT id FROM clients WHERE tenant_id = :b"), {"b": TENANT_B}).fetchall()
        own = c.execute(text("SELECT id FROM clients WHERE tenant_id = :a"), {"a": TENANT_A}).fetchall()
    assert cross == []          # A no ve a B
    assert len(own) == 1        # doble aserción: RLS filtra, no bloquea todo


def test_audit_logs_append_only(engine):
    log_id = uuid.uuid4()
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text("INSERT INTO audit_logs (id, tenant_id, actor_user_id, action, entity_type, entity_id) VALUES (:id,:t,:u,'create','client',:e)"), {"id": log_id, "t": TENANT_A, "u": USER_A, "e": CLIENT_A})
    with pytest.raises(Exception):
        with tenant_session(engine, TENANT_A, USER_A) as c:
            c.execute(text("UPDATE audit_logs SET action='x' WHERE id=:id"), {"id": log_id})
    with pytest.raises(Exception):
        with tenant_session(engine, TENANT_A, USER_A) as c:
            c.execute(text("DELETE FROM audit_logs WHERE id=:id"), {"id": log_id})


def test_force_rls_applies_to_owner(engine):
    with engine.begin() as c:   # sesión del OWNER sin contexto de tenant
        rls = c.execute(text("SELECT relrowsecurity FROM pg_class WHERE relname='clients'")).scalar()
        force = c.execute(text("SELECT relforcerowsecurity FROM pg_class WHERE relname='clients'")).scalar()
        count = c.execute(text("SELECT count(*) FROM clients")).scalar()
    assert rls is True
    assert force is True
    assert count == 0           # el owner TAMBIÉN es filtrado => FORCE demostrado


def test_evidence_vectors_reindex_allowed(engine):
    std_id, audit_id, ef_id, ex_id, ch_id, vec_id = (uuid.uuid4() for _ in range(6))
    emb = "[" + ",".join(["0.1"] * 1024) + "]"      # vector(1024)
    with engine.begin() as c:
        c.execute(text("SELECT set_config('app.is_platform_admin','true',true)"))
        c.execute(text("INSERT INTO standards (id, code, name, version, status) VALUES (:id,'ISO9001-DEMO','Demo','2015','active')"), {"id": std_id})
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text("INSERT INTO audits (id, tenant_id, client_id, standard_id, name, status) VALUES (:id,:t,:cl,:st,'Audit A','planned')"), {"id": audit_id, "t": TENANT_A, "cl": CLIENT_A, "st": std_id})
        c.execute(text("INSERT INTO evidence_files (id, tenant_id, audit_id, original_filename, mime_type, file_size, sha256, storage_path, classification, upload_status, extraction_status, uploaded_by) VALUES (:id,:t,:a,'a.txt','text/plain',10,'h','p','internal','ready','completed',:u)"), {"id": ef_id, "t": TENANT_A, "a": audit_id, "u": USER_A})
        c.execute(text("INSERT INTO evidence_text_extractions (id, tenant_id, evidence_file_id, extractor, status, extracted_text, text_sha256, character_count, requested_by) VALUES (:id,:t,:ef,'utf8','completed','texto','h2',5,:u)"), {"id": ex_id, "t": TENANT_A, "ef": ef_id, "u": USER_A})
        c.execute(text("INSERT INTO evidence_text_chunks (id, tenant_id, extraction_id, evidence_file_id, seq, text, sha256, character_count) VALUES (:id,:t,:ex,:ef,0,'chunk','h3',5)"), {"id": ch_id, "t": TENANT_A, "ex": ex_id, "ef": ef_id})
        c.execute(text("INSERT INTO evidence_vectors (id, chunk_id, tenant_id, model, dim, embedding) VALUES (:id,:ch,:t,'test',1024,:emb)"), {"id": vec_id, "ch": ch_id, "t": TENANT_A, "emb": emb})
        c.execute(text("DELETE FROM evidence_vectors WHERE id=:id"), {"id": vec_id})   # reindex
        c.execute(text("INSERT INTO evidence_vectors (id, chunk_id, tenant_id, model, dim, embedding) VALUES (:id,:ch,:t,'test',1024,:emb)"), {"id": uuid.uuid4(), "ch": ch_id, "t": TENANT_A, "emb": emb})
        n = c.execute(text("SELECT count(*) FROM evidence_vectors WHERE chunk_id=:ch"), {"ch": ch_id}).scalar()
    assert n == 1