"""Seed script para crear estándar de prueba."""
from app.db import SessionLocal
from app.models import Standard, Clause, QuestionPack

db = SessionLocal()
try:
    # Verificar si ya existe
    existing = db.query(Standard).filter(Standard.code == "ISO-27001-TEST").first()
    if existing:
        print(f"Estándar ya existe: {existing.name}")
    else:
        std = Standard(
            code="ISO-27001-TEST",
            name="ISO 27001 Test",
            version="2022",
            status="active",
            # ← ELIMINADO: tenant_id NO existe en Standard
        )
        db.add(std)
        db.flush()

        # Añadir cláusulas mínimas
        for num, title in [("5.1", "Liderazgo"), ("6.1", "Riesgos"), ("8.1", "Operación")]:
            clause = Clause(
                standard_id=std.id,
                number=num,
                title=title,
                # ← ELIMINADO: tenant_id NO existe en Clause
            )
            db.add(clause)
            db.flush()

            qp = QuestionPack(
                clause_id=clause.id,
                question=f"¿Existe documentación para {title}?",
                # ← ELIMINADO: tenant_id NO existe en QuestionPack
            )
            db.add(qp)

        db.commit()
        print("✅ Estándar ISO-27001-TEST creado con 3 cláusulas")

finally:
    db.close()