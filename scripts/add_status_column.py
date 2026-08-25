import psycopg

# Connect to the PostgreSQL database
conn = psycopg.connect(
    dbname="grc_test",
    user="grc_owner",
    password="grc_owner",
    host="localhost",
    port="5432"
)

# Execute the SQL command
with conn.cursor() as cur:
    cur.execute("ALTER TABLE users ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active';")
    conn.commit()

conn.close()