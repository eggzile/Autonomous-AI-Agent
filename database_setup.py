import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

def create_database():
    """
    Connects to the default 'postgres' database to create 'agent_db_v2' 
    if it doesn't exist.
    """
    conn = None
    try:
        # 1. Connect to default 'postgres' database
        print(f"🔌 Connecting to system database 'postgres'...")
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            database='postgres'  # Connect to default system DB
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # 2. Check if your target database exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cur.fetchone()

        if not exists:
            print(f"🆕 Database '{DB_NAME}' not found. Creating it...")
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"✅ Database '{DB_NAME}' created successfully!")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists. Skipping creation.")

        cur.close()
        return True

    except Exception as e:
        print(f"❌ Database Creation Failed: {e}")
        return False
    finally:
        if conn: conn.close()

def create_tables():
    """
    Connects to the newly created 'agent_db_v2' and creates the schema.
    """
    conn = None
    try:
        # 1. Connect to YOUR specific database
        print(f"🔌 Connecting to '{DB_NAME}' to create tables...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()

        # --- 2. PARENT TABLE ---
        print("   -> Checking 'processed_docs' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_docs (
                id VARCHAR(36) PRIMARY KEY,
                filename VARCHAR(255),
                doc_type VARCHAR(50),
                file_hash VARCHAR(64) UNIQUE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # --- 3. CHILD TABLES ---

        # Invoices
        print("   -> Checking 'invoices' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                vendor VARCHAR(255),
                inv_date DATE,
                total_amount DECIMAL(10, 2),
                raw_data JSONB
            );
        """)

        # Resumes
        print("   -> Checking 'resumes' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                candidate_name VARCHAR(255),
                score INTEGER,
                skills JSONB
            );
        """)

        # Research Papers
        print("   -> Checking 'research_papers' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS research_papers (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                title VARCHAR(255),
                summary TEXT
            );
        """)

        # Audio Notes
        print("   -> Checking 'audio_notes' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audio_notes (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                transcript TEXT,
                summary TEXT,
                sentiment VARCHAR(50)
            );
        """)

        # Legal Documents (New Feature)
        print("   -> Checking 'legal_docs' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS legal_docs (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                document_type VARCHAR(100), -- e.g. "NDA", "Will"
                parties TEXT[],             -- Stores array of names
                effective_date DATE,
                expiration_date DATE,
                key_clauses JSONB,          -- Stores list of clauses as JSON
                summary TEXT
            );
        """)

        # Unknown / Generic Docs
        print("   -> Checking 'unknown_docs' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS unknown_docs (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(36) REFERENCES processed_docs(id) ON DELETE CASCADE,
                summary TEXT,
                extracted_keywords JSONB
            );
        """)

        print("✅ All tables created successfully!")
        cur.close()

    except Exception as e:
        print(f"❌ Table Setup Failed: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    # Step 1: Create DB
    if create_database():
        # Step 2: Create Tables
        create_tables()