# setup_legal_db.py
import psycopg2
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

try:
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
    conn.autocommit = True
    with conn.cursor() as cur:
        print("⚖️  Creating Legal Docs Table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS legal_docs (
                doc_id VARCHAR(36) REFERENCES processed_docs(id),
                document_type VARCHAR(100), -- e.g. "NDA", "Will", "Lease"
                parties TEXT[],             -- Array of names
                effective_date DATE,
                expiration_date DATE,
                key_clauses JSONB,          -- Store terms as flexible JSON
                summary TEXT
            );
        """)
        print("✅ 'legal_docs' table created successfully.")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")