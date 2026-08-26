"""Seed idempotente: estándar demo + cuenta demo lista para la web."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argon2
from sqlalchemy import text

from app.db import engine


def seed_demo_data() -> None:
    ph = argon2.PasswordHasher()
    with engine.begin() as conn:
        # 1) Estándar (idempotente por unique code)
        conn.execute(text("""
            INSERT INTO standards (id, code, name, version, status)
            VALUES (gen_random_uuid(), 'ISO9001-DEMO', 'ISO 9001 Demo Fixture', '2015', 'active')
            ON CONFLICT (code) DO NOTHING
        """))
        std_id = conn.execute(text(
            "SELECT id FROM standards WHERE code = 'ISO9001-DEMO'"
        )).scalar()

        # 2) Cláusulas y preguntas (idempotente por conteo)
        clause_count = conn.execute(text(
            "SELECT count(*) FROM clauses WHERE standard_id = :s"
        ), {"s": std_id}).scalar()
        if clause_count == 0:
            clauses = [
                ("4", "Contexto de la organización"), ("5", "Liderazgo"),
                ("6", "Planificación"), ("7", "Apoyo"), ("8", "Operación"),
                ("9", "Evaluación del desempeño"), ("10", "Mejora"),
            ]
            for num, title in clauses:
                conn.execute(text(
                    "INSERT INTO clauses (id, standard_id, number, title, description) "
                    "VALUES (gen_random_uuid(), :s, :n, :t, '')"
                ), {"s": std_id, "n": num, "t": title})

            clause_ids = dict(conn.execute(text(
                "SELECT number, id FROM clauses WHERE standard_id = :s"
            ), {"s": std_id}).all())

            questions = [
                ("4", "¿Se han determinado las cuestiones externas e internas pertinentes?"),
                ("5", "¿La alta dirección demuestra liderazgo y compromiso?"),
                ("6", "¿Se han abordado riesgos y oportunidades?"),
                ("7", "¿Los recursos son adecuados para el SGC?"),
                ("8", "¿Los procesos operacionales están controlados?"),
                ("9", "¿Se realiza seguimiento y medición del desempeño?"),
                ("10", "¿Se implementan mejoras y acciones correctivas?"),
            ]
            for num, q in questions:
                conn.execute(text(
                    "INSERT INTO question_packs "
                    "(id, clause_id, question, expected_evidence, criteria, sort_order) "
                    "VALUES (gen_random_uuid(), :c, :q, 'Evidencia documental', 'Criterio demo', 0)"
                ), {"c": clause_ids[num], "q": q})

        # 3) Cuenta demo + tenant + cliente + auditoría (solo primera vez)
        exists = conn.execute(text(
            "SELECT id FROM users WHERE email = 'demo@grc.com'"
        )).scalar()
        if exists:
            print("✅ Demo data seeded successfully (idempotent).")
            return

        user_id = conn.execute(text(
            "INSERT INTO users (email, password_hash, full_name) "
            "VALUES ('demo@grc.com', :h, 'Usuario Demo') RETURNING id"
        ), {"h": ph.hash("SecurePass123!")}).scalar()

        tenant_id = conn.execute(text(
            "INSERT INTO tenants (name, slug) "
            "VALUES ('Tenant Demo', 'demo-tenant') RETURNING id"
        )).scalar()

        conn.execute(text(
            "INSERT INTO memberships (user_id, tenant_id, role) "
            "VALUES (:u, :t, 'owner')"
        ), {"u": user_id, "t": tenant_id})

        client_id = conn.execute(text(
            "INSERT INTO clients (tenant_id, name, sector, country) "
            "VALUES (:t, 'Cliente Piloto S.A.', 'Tecnología', 'DO') RETURNING id"
        ), {"t": tenant_id}).scalar()

        audit_id = conn.execute(text(
            "INSERT INTO audits (tenant_id, client_id, standard_id, name) "
            "VALUES (:t, :c, :s, 'Auditoría ISO 9001 Demo') RETURNING id"
        ), {"t": tenant_id, "c": client_id, "s": std_id}).scalar()

        rows = conn.execute(text(
            "SELECT c.id, qp.id FROM clauses c "
            "JOIN question_packs qp ON qp.clause_id = c.id "
            "WHERE c.standard_id = :s"
        ), {"s": std_id}).all()
        for cid, qpid in rows:
            conn.execute(text(
                "INSERT INTO checklist_items (tenant_id, audit_id, clause_id, question_pack_id) "
                "VALUES (:t, :a, :c, :q)"
            ), {"t": tenant_id, "a": audit_id, "c": cid, "q": qpid})
        conn.execute(text(
            "INSERT INTO users (email, password_hash, full_name) "
            "VALUES ('reviewer@grc.com', :h, 'Reviewer Demo') "
            "ON CONFLICT (email) DO NOTHING"
        ), {"h": ph.hash("SecurePass123!")})
        
        rev_id = conn.execute(text(
            "SELECT id FROM users WHERE email = 'reviewer@grc.com'"
        )).scalar()
        conn.execute(text(
            "INSERT INTO memberships (user_id, tenant_id, role) "
            "SELECT :u, :t, 'reviewer' WHERE NOT EXISTS ("
            "SELECT 1 FROM memberships WHERE user_id = :u AND tenant_id = :t)"
        ), {"u": rev_id, "t": tenant_id})

    print("✅ Demo data seeded successfully (idempotent).")


if __name__ == "__main__":
    seed_demo_data()