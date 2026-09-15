import psycopg
from app.models import Base

def get_orm_details():
    orm_cols = {}
    for table_name, table in Base.metadata.tables.items():
        orm_cols[table_name] = {}
        for col in table.columns:
            orm_cols[table_name][col.name] = {
                "type": str(col.type),
                "nullable": col.nullable
            }
    return orm_cols

def get_db_details(db_url):
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    db_cols = {}
    for t, c, dt, nul in cur.fetchall():
        if t not in db_cols:
            db_cols[t] = {}
        db_cols[t][c] = {
            "type": dt,
            "nullable": (nul == 'YES')
        }
    conn.close()
    return db_cols

if __name__ == "__main__":
    orm = get_orm_details()
    grc = get_db_details("postgresql://grc:grc@localhost:5432/grc")
    test = get_db_details("postgresql://grc:grc@localhost:5432/grc_test")

    print(f"ORM Tables: {len(orm)}, Total cols: {sum(len(v) for v in orm.values())}")
    print(f"GRC Tables: {len(grc)}, Total cols: {sum(len(v) for v in grc.values())}")
    print(f"GRC_Test Tables: {len(test)}, Total cols: {sum(len(v) for v in test.values())}")

    print("\n=== ONLY IN GRC ===")
    for t in grc:
        for c in grc[t]:
            if t not in test or c not in test[t]:
                print(f"{t} | {c} | {grc[t][c]['type']}")

    print("\n=== ONLY IN GRC_TEST ===")
    for t in test:
        for c in test[t]:
            if t not in grc or c not in grc[t]:
                print(f"{t} | {c} | {test[t][c]['type']}")
