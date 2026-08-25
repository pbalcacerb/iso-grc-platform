"""M1: seguridad a nivel de DB (RLS, FORCE, append-only, reindex)."""
import os
import subprocess
import uuid
from contextlib import contextmanager
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BOOT_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://grc:grc@localhost:5432/grc_test",
)
APP_URL = BOOT_URL.replace("grc:grc@", "grc_app:grc_app@", 1)
OWNER_URL = BOOT_URL.replace("grc:grc@", "grc_owner:grc_owner@", 1)

RUN = uuid.uuid4().hex[:8]
TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
CLIENT_A = uuid.uuid4()
CLIENT_B = uuid.uuid4()


@pytest.fixture(scope="session")
def bootstrap() -> Iterator[Engine]:
    env = {**os.environ, "DATABASE_URL": BOOT_URL}
    proc = subprocess.run(
        ["alembic", "upgrade", "head"], env=env, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"alembic falló:\n{proc.stdout}\n{proc.stderr}")
    eng = create_engine(BOOT_URL)
    with eng.begin() as c:
        c.execute(text(
            "DO $$ BEGIN IF NOT EXISTS"
            " (SELECT FROM pg_roles WHERE rolname='grc_owner') THEN"
            " CREATE ROLE grc_owner LOGIN PASSWORD 'grc_owner' NOBYPASSRLS;"
            " END IF; END $$"
        ))
        c.execute(text(
            "DO $$ BEGIN IF NOT EXISTS"
            " (SELECT FROM pg_roles WHERE rolname='grc_app') THEN"
            " CREATE ROLE grc_app LOGIN PASSWORD 'grc_app' NOBYPASSRLS;"
            " END IF; END $$"
        ))
        c.execute(text("REASSIGN OWNED BY grc TO grc_owner"))
        c.execute(text("GRANT USAGE ON SCHEMA public TO grc_app"))
        c.execute(text(
            "GRANT SELECT, INSERT, UPDATE, DELETE"
            " ON ALL TABLES IN SCHEMA public TO grc_app"
        ))
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def engine(bootstrap: Engine) -> Iterator[Engine]:
    eng = create_engine(APP_URL)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def owner_engine(bootstrap: Engine) -> Iterator[Engine]:
    eng = create_engine(OWNER_URL)
    yield eng
    eng.dispose()


@contextmanager
def tenant_session(eng: Engine, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Iterator[object]:
    with eng.begin() as conn:
        conn.execute(text(
            "SELECT set_config('app.current_tenant_id', :t, true)"
        ), {"t": str(tenant_id)})
        if user_id is not None:
            conn.execute(text(
                "SELECT set_config('app.current_user_id', :u, true)"
            ), {"u": str(user_id)})
        yield conn


@pytest.fixture(scope="session", autouse=True)
def seed(engine: Engine) -> Iterator[None]:
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO tenants (id, name, slug, status)"
            " VALUES (:id,'Tenant A',:slug,'active')"
        ), {"id": TENANT_A, "slug": f"tenant-a-{RUN}"})
        c.execute(text(
            "INSERT INTO tenants (id, name, slug, status)"
            " VALUES (:id,'Tenant B',:slug,'active')"
        ), {"id": TENANT_B, "slug": f"tenant-b-{RUN}"})
        c.execute(text(
            "INSERT INTO users (id, email, password_hash, full_name, status)"
            " VALUES (:id,:email,'x','User A','active')"
        ), {"id": USER_A, "email": f"a-{RUN}@test.com"})
        c.execute(text(
            "INSERT INTO users (id, email, password_hash, full_name, status)"
            " VALUES (:id,:email,'x','User B','active')"
        ), {"id": USER_B, "email": f"b-{RUN}@test.com"})
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text(
            "INSERT INTO memberships (id, user_id, tenant_id, role)"
            " VALUES (:id,:u,:t,'owner')"
        ), {"id": uuid.uuid4(), "u": USER_A, "t": TENANT_A})
        c.execute(text(
            "INSERT INTO clients (id, tenant_id, name, sector, country,"
            " confidentiality_level, status)"
            " VALUES (:id,:t,'Client A','tech','DO','internal','active')"
        ), {"id": CLIENT_A, "t": TENANT_A})
    with tenant_session(engine, TENANT_B, USER_B) as c:
        c.execute(text(
            "INSERT INTO memberships (id, user_id, tenant_id, role)"
            " VALUES (:id,:u,:t,'owner')"
        ), {"id": uuid.uuid4(), "u": USER_B, "t": TENANT_B})
        c.execute(text(
            "INSERT INTO clients (id, tenant_id, name, sector, country,"
            " confidentiality_level, status)"
            " VALUES (:id,:t,'Client B','tech','DO','internal','active')"
        ), {"id": CLIENT_B, "t": TENANT_B})
    yield


def test_tenant_isolation(engine: Engine) -> None:
    with tenant_session(engine, TENANT_A, USER_A) as c:
        cross = c.execute(text(
            "SELECT id FROM clients WHERE tenant_id = :b"
        ), {"b": TENANT_B}).fetchall()
        own = c.execute(text(
            "SELECT id FROM clients WHERE tenant_id = :a"
        ), {"a": TENANT_A}).fetchall()
    assert cross == []
    assert len(own) == 1


def test_audit_logs_append_only(engine: Engine) -> None:
    log_id = uuid.uuid4()
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text(
            "INSERT INTO audit_logs (id, tenant_id, actor_user_id,"
            " action, entity_type, entity_id)"
            " VALUES (:id,:t,:u,'create','client',:e)"
        ), {"id": log_id, "t": TENANT_A, "u": USER_A, "e": CLIENT_A})
    with pytest.raises(Exception):
        with tenant_session(engine, TENANT_A, USER_A) as c:
            c.execute(text(
                "UPDATE audit_logs SET action='x' WHERE id=:id"
            ), {"id": log_id})
    with pytest.raises(Exception):
        with tenant_session(engine, TENANT_A, USER_A) as c:
            c.execute(text(
                "DELETE FROM audit_logs WHERE id=:id"
            ), {"id": log_id})


def test_force_rls_applies_to_owner(owner_engine: Engine) -> None:
    with owner_engine.begin() as c:
        rls = c.execute(text(
            "SELECT relrowsecurity FROM pg_class WHERE relname='clients'"
        )).scalar()
        force = c.execute(text(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname='clients'"
        )).scalar()
        count = c.execute(text("SELECT count(*) FROM clients")).scalar()
    assert rls is True
    assert force is True
    assert count == 0


def test_evidence_vectors_reindex_allowed(engine: Engine) -> None:
    ids = [uuid.uuid4() for _ in range(6)]
    std_id, audit_id, ef_id, ex_id, ch_id, vec_id = ids
    emb = "[" + ",".join(["0.1"] * 1024) + "]"
    with engine.begin() as c:
        c.execute(text(
            "SELECT set_config('app.is_platform_admin','true',true)"
        ))
        c.execute(text(
            "INSERT INTO standards (id, code, name, version, status)"
            " VALUES (:id,'ISO9001-DEMO','Demo','2015','active')"
        ), {"id": std_id})
    with tenant_session(engine, TENANT_A, USER_A) as c:
        c.execute(text(
            "INSERT INTO audits (id, tenant_id, client_id, standard_id,"
            " name, status) VALUES (:id,:t,:cl,:st,'Audit A','planned')"
        ), {"id": audit_id, "t": TENANT_A, "cl": CLIENT_A, "st": std_id})
        c.execute(text(
            "INSERT INTO evidence_files (id, tenant_id, audit_id,"
            " original_filename, mime_type, file_size, sha256, storage_path,"
            " classification, upload_status, extraction_status, uploaded_by)"
            " VALUES (:id,:t,:a,'a.txt','text/plain',10,'h','p','internal',"
            "'ready','completed',:u)"
        ), {"id": ef_id, "t": TENANT_A, "a": audit_id, "u": USER_A})
        c.execute(text(
            "INSERT INTO evidence_text_extractions (id, tenant_id,"
            " evidence_file_id, extractor, status, extracted_text,"
            " text_sha256, character_count, requested_by)"
            " VALUES (:id,:t,:ef,'utf8','completed','texto','h2',5,:u)"
        ), {"id": ex_id, "t": TENANT_A, "ef": ef_id, "u": USER_A})
        c.execute(text(
            "INSERT INTO evidence_text_chunks (id, tenant_id, extraction_id,"
            " evidence_file_id, seq, text, sha256, character_count)"
            " VALUES (:id,:t,:ex,:ef,0,'chunk','h3',5)"
        ), {"id": ch_id, "t": TENANT_A, "ex": ex_id, "ef": ef_id})
        c.execute(text(
            "INSERT INTO evidence_vectors (id, chunk_id, tenant_id, model,"
            " dim, embedding) VALUES (:id,:ch,:t,'test',1024,:emb)"
        ), {"id": vec_id, "ch": ch_id, "t": TENANT_A, "emb": emb})
        c.execute(text(
            "DELETE FROM evidence_vectors WHERE id=:id"
        ), {"id": vec_id})
        c.execute(text(
            "INSERT INTO evidence_vectors (id, chunk_id, tenant_id, model,"
            " dim, embedding) VALUES (:id,:ch,:t,'test',1024,:emb)"
        ), {"id": uuid.uuid4(), "ch": ch_id, "t": TENANT_A, "emb": emb})
        n = c.execute(text(
            "SELECT count(*) FROM evidence_vectors WHERE chunk_id=:ch"
        ), {"ch": ch_id}).scalar()
    assert n == 1