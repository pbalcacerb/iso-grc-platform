import psycopg

def check_compatibility():
    conn = psycopg.connect("postgresql://grc:grc@localhost:5432/grc")
    cur = conn.cursor()
    
    # 1. Audits columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'audits' AND column_name IN ('closed_at', 'closed_by_id', 'closing_summary');
    """)
    print("--- Audits closure columns in grc ---")
    for r in cur.fetchall():
        print(r)

    # 2. Checklist items columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'checklist_items' AND column_name IN ('findings_summary');
    """)
    print("--- Checklist items summary in grc ---")
    for r in cur.fetchall():
        print(r)

    # 3. Findings columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'findings' AND column_name IN ('created_at', 'updated_at', 'closed_at');
    """)
    print("--- Findings timestamp columns in grc ---")
    for r in cur.fetchall():
        print(r)

    # 4. FKs in audits & findings
    cur.execute("""
        SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name, rc.delete_rule 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema 
        JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = ccu.table_schema 
        JOIN information_schema.referential_constraints AS rc ON rc.constraint_name = tc.constraint_name 
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ('audits', 'findings') AND (kcu.column_name = 'closed_by_id' OR kcu.column_name = 'checklist_item_id');
    """)
    print("--- Foreign keys relevant ---")
    for r in cur.fetchall():
        print(r)

    # 5. Data stats / null counts
    for tbl, col in [('audits', 'closed_at'), ('audits', 'closed_by_id'), ('audits', 'closing_summary'), ('checklist_items', 'findings_summary'), ('findings', 'created_at'), ('findings', 'updated_at'), ('findings', 'closed_at')]:
        cur.execute(f"SELECT count(*), count({col}) FROM {tbl};")
        total, non_null = cur.fetchone()
        print(f"Data stats {tbl}.{col}: total rows={total}, non-null={non_null}, null={total - non_null}")

    conn.close()

if __name__ == "__main__":
    check_compatibility()
