import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_session_with_rls
from app.models import Audit, Clause, Client, QuestionPack, Standard

# Define demo data
DEMO_STANDARD = {
    "code": "ISO9001-DEMO",
    "name": "ISO 9001 Demo Fixture",
    "version": "2015",
}

DEMO_CLAUSES = [
    {"number": "4", "title": "Context of the Organization"},
    {"number": "5", "title": "Leadership"},
    {"number": "6", "title": "Planning"},
    {"number": "7", "title": "Support"},
    {"number": "8", "title": "Operation"},
    {"number": "9", "title": "Performance Evaluation"},
    {"number": "10", "title": "Improvement"},
]

DEMO_QUESTIONS = [
    {
        "clause_number": "4",
        "question": "Has the organization determined external and internal issues "
                    "relevant to its purpose?",
        "expected_evidence": "Documented context analysis.",
    },
    {
        "clause_number": "5",
        "question": "Does top management demonstrate leadership and commitment?",
        "expected_evidence": "Leadership meeting minutes.",
    },
    {
        "clause_number": "6",
        "question": "Have risks and opportunities been addressed?",
        "expected_evidence": "Risk assessment records.",
    },
    {
        "clause_number": "7",
        "question": "Are resources adequate for the QMS?",
        "expected_evidence": "Resource allocation reports.",
    },
    {
        "clause_number": "8",
        "question": "Are operational processes controlled?",
        "expected_evidence": "Process control documentation.",
    },
    {
        "clause_number": "9",
        "question": "Is performance monitored and measured?",
        "expected_evidence": "Performance reports.",
    },
    {
        "clause_number": "10",
        "question": "Are improvements identified and implemented?",
        "expected_evidence": "Improvement records.",
    },
]

def seed_demo_data() -> None:
    db: Session | None = None
    try:
        db = get_session_with_rls(None, None)
        
        # Seed standard (idempotent)
        standard = db.query(Standard).filter(
            Standard.code == DEMO_STANDARD["code"]
        ).first()
        if not standard:
            standard = Standard(**DEMO_STANDARD)
            db.add(standard)
            db.commit()
            db.refresh(standard)
            print(f"Created standard: {standard.code}")
        
        # Seed clauses (idempotent)
        for clause_data in DEMO_CLAUSES:
            clause = db.query(Clause).filter(
                Clause.standard_id == standard.id,
                Clause.number == clause_data["number"]
            ).first()
            if not clause:
                clause = Clause(standard_id=standard.id, **clause_data)
                db.add(clause)
                db.commit()
                db.refresh(clause)
                print(f"Created clause: {clause.number} - {clause.title}")
        
        # Seed questions (idempotent)
        for question_data in DEMO_QUESTIONS:
            clause = db.query(Clause).filter(
                Clause.standard_id == standard.id,
                Clause.number == question_data["clause_number"]
            ).first()
            if clause:
                existing_question = db.query(QuestionPack).filter(
                    QuestionPack.clause_id == clause.id,
                    QuestionPack.question == question_data["question"]
                ).first()
                if not existing_question:
                    question = QuestionPack(
                        clause_id=clause.id,
                        question=question_data["question"],
                        expected_evidence=question_data["expected_evidence"],
                    )
                    db.add(question)
                    db.commit()
                    print(f"Created question for clause {clause.number}")
        
        # Seed demo client (idempotent)
        client = db.query(Client).filter(
            or_(
                Client.name == "Demo Client",
                Client.sector == "Technology"
            )
        ).first()
        if not client:
            client = Client(
                name="Demo Client",
                sector="Technology",
                country="US",
                confidentiality_level="high",
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            print(f"Created client: {client.name}")
        
        # Seed demo audit (idempotent)
        audit = db.query(Audit).filter(
            Audit.name == "Demo Audit"
        ).first()
        if not audit:
            audit = Audit(
                client_id=client.id,
                standard_id=standard.id,
                name="Demo Audit",
                status="planned",
            )
            db.add(audit)
            db.commit()
            print(f"Created audit: {audit.name}")
        
        print("Demo data seeding completed successfully!")
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error seeding demo data: {e}")
        raise
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    seed_demo_data()

# Define demo data
DEMO_STANDARD = {
    "code": "ISO9001-DEMO",
    "name": "ISO 9001 Demo Fixture",
    "version": "2015",
}

DEMO_CLAUSES = [
    {"number": "4", "title": "Context of the Organization"},
    {"number": "5", "title": "Leadership"},
    {"number": "6", "title": "Planning"},
    {"number": "7", "title": "Support"},
    {"number": "8", "title": "Operation"},
    {"number": "9", "title": "Performance Evaluation"},
    {"number": "10", "title": "Improvement"},
]

DEMO_QUESTIONS = [
    {"clause_number": "4", "question": "Has the organization determined external and internal issues relevant to its purpose?", "expected_evidence": "Documented context analysis."},
    {"clause_number": "5", "question": "Does top management demonstrate leadership and commitment?", "expected_evidence": "Leadership meeting minutes."},
    {"clause_number": "6", "question": "Have risks and opportunities been addressed?", "expected_evidence": "Risk assessment records."},
    {"clause_number": "7", "question": "Are resources adequate for the QMS?", "expected_evidence": "Resource allocation reports."},
    {"clause_number": "8", "question": "Are operational processes controlled?", "expected_evidence": "Process control documentation."},
    {"clause_number": "9", "question": "Is performance monitored and measured?", "expected_evidence": "Performance reports."},
    {"clause_number": "10", "question": "Are improvements identified and implemented?", "expected_evidence": "Improvement records."},
]

def seed_demo_data():
    db = get_session_with_rls(None, None)
    try:
        # Seed standard
        standard = Standard(**DEMO_STANDARD)
        db.add(standard)
        db.commit()
        db.refresh(standard)

        # Seed clauses
        for clause_data in DEMO_CLAUSES:
            clause = Clause(standard_id=standard.id, **clause_data)
            db.add(clause)
            db.commit()
            db.refresh(clause)

        # Seed questions
        for question_data in DEMO_QUESTIONS:
            clause = db.query(Clause).filter(Clause.number == question_data["clause_number"]).first()
            if clause:
                question = QuestionPack(
                    clause_id=clause.id,
                    question=question_data["question"],
                    expected_evidence=question_data["expected_evidence"],
                )
                db.add(question)
                db.commit()

        # Create a demo client
        client = Client(
            name="Demo Client",
            sector="Technology",
            country="US",
            confidentiality_level="high",
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        # Create a demo audit
        audit = Audit(
            client_id=client.id,
            standard_id=standard.id,
            name="Demo Audit",
            status="planned",
        )
        db.add(audit)
        db.commit()

        print("Demo data seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()