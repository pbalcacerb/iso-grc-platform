"""Seed idempotente de ISO9001-DEMO."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402


def seed_demo_data() -> None:
    with engine.begin() as conn:
        # 1. Standard (idempotente)
        conn.execute(text("""
            INSERT INTO standards (id, code, name, version, status)
            VALUES (gen_random_uuid(), 'ISO9001-DEMO', 'ISO 9001 Demo Fixture', '2015', 'active')
            ON CONFLICT (code) DO NOTHING
        """))

        std_id = conn.execute(text(
            "SELECT id FROM standards WHERE code = 'ISO9001-DEMO'"
        )).scalar()

        clauses_data = [
            ("4", "Context", "Understanding the organization"),
            ("5", "Leadership", "Leadership and commitment"),
            ("6", "Planning", "Actions to address risks"),
            ("7", "Support", "Resources and competence"),
            ("8", "Operation", "Operational planning"),
            ("9", "Performance", "Monitoring and measurement"),
            ("10", "Improvement", "Nonconformity and corrective action"),
        ]

        clause_ids = {}
        for num, title, desc in clauses_data:
            res = conn.execute(text("""
                INSERT INTO clauses (id, standard_id, number, title, description)
                VALUES (gen_random_uuid(), :std_id, :num, :title, :desc)
                ON CONFLICT DO NOTHING RETURNING id
            """), {"std_id": std_id, "num": num, "title": title, "desc": desc})
            row = res.fetchone()
            clause_ids[num] = row[0] if row else conn.execute(
                text("SELECT id FROM clauses WHERE standard_id = :std_id AND number = :num"),
                {"std_id": std_id, "num": num},
            ).scalar()

        questions_data = [
            ("4", "Has the organization determined external/internal issues?", "Context doc"),
            ("5", "Does top management demonstrate leadership?", "Meeting minutes"),
            ("6", "Have risks and opportunities been addressed?", "Risk assessment"),
            ("7", "Are resources adequate for the QMS?", "Resource reports"),
            ("8", "Are operational processes controlled?", "Process docs"),
            ("9", "Is performance monitored and measured?", "Performance reports"),
            ("10", "Are improvements identified and implemented?", "Improvement records"),
        ]

        for num, question, evidence in questions_data:
            c_id = clause_ids.get(num)
            if c_id:
                conn.execute(text("""
                    INSERT INTO question_packs (id, clause_id, question, expected_evidence, criteria, sort_order)
                    VALUES (gen_random_uuid(), :c_id, :q, :ev, 'Demo criteria', 0)
                    ON CONFLICT DO NOTHING
                """), {"c_id": c_id, "q": question, "ev": evidence})

    print("✅ Demo data seeded successfully (idempotent).")


if __name__ == "__main__":
    seed_demo_data()