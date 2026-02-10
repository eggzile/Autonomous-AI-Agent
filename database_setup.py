# database_setup.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

def setup_database():
    try:
        # 1. Create DB if needed
        conn = psycopg2.connect(
            host=DB_HOST, database="postgres", user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if not cur.fetchone():
            print(f"📦 Creating database '{DB_NAME}'...")
            cur.execute(f"CREATE DATABASE {DB_NAME}")
        cur.close()
        conn.close()

        # 2. Connect to DB and Update Tables
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("🛠️  Updating Schema...")

        # Master Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_docs (
                id VARCHAR(36) PRIMARY KEY,
                filename TEXT,
                file_hash VARCHAR(64) UNIQUE,
                doc_type TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Invoices
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                doc_id VARCHAR(36) REFERENCES processed_docs(id),
                vendor TEXT,
                inv_date DATE,
                total_amount NUMERIC,
                raw_data JSONB
            );
        """)

        # Resumes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                doc_id VARCHAR(36) REFERENCES processed_docs(id),
                candidate_name TEXT,
                score INTEGER,
                skills JSONB
            );
        """)

        # Unknown Docs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS unknown_docs (
                doc_id VARCHAR(36) REFERENCES processed_docs(id),
                summary TEXT,
                extracted_keywords JSONB
            );
        """)

        # --- THE CHANGE: Research Papers (Text, not Vectors) ---
        print("   -> converting 'research_papers' from Vectors to Summaries...")
        cur.execute("DROP TABLE IF EXISTS research_papers;")
        cur.execute("""
            CREATE TABLE research_papers (
                doc_id VARCHAR(36) REFERENCES processed_docs(id),
                title TEXT,
                summary TEXT
            );
        """)

        print("✅ Database Updated!")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Setup Failed: {e}")

if __name__ == "__main__":
    setup_database()