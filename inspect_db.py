import psycopg

def inspect(db_url, name):
    print(f"=== DATABASE: {name} ({db_url}) ===")
    try:
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        cur.execute("SELECT version();")
        print("Version:", cur.fetchone()[0])
        
        cur.execute("SELECT current_database();")
        print("Database:", cur.fetchone()[0])
        
        try:
            cur.execute("SELECT version_num FROM alembic_version;")
            print("Alembic version:", cur.fetchone())
        except Exception as e:
            print("Alembic version error:", e)
            conn.rollback()
            
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = [r[0] for r in cur.fetchall()]
        print("Tables:", tables)
        
        cur.execute("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name, rc.delete_rule 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema 
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema 
            JOIN information_schema.referential_constraints AS rc ON rc.constraint_name = tc.constraint_name 
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ('memberships', 'findings', 'audits', 'checklist_items', 'audit_checklist_items', 'evidence_files');
        """)
        print("Foreign Keys:", cur.fetchall())
        
        cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'audits';")
        print("Audits columns:", cur.fetchall())
        
        conn.close()
    except Exception as e:
        print(f"Error connecting to {name}: {e}")

if __name__ == "__main__":
    inspect("postgresql://grc:grc@localhost:5432/grc", "grc")
    inspect("postgresql://grc:grc@localhost:5432/grc_test", "grc_test")
