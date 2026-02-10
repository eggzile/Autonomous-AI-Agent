# database.py
import psycopg2
import re  # <--- NEW IMPORT
from psycopg2.extras import Json
from dateutil import parser
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
            )
            self.conn.autocommit = True
        except Exception as e:
            print(f"❌ DB Connection Error: {e}")

    def save_audio_note(self, doc_id, data):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audio_notes (doc_id, transcript, summary, sentiment)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    doc_id, 
                    data.get('transcript', ''), 
                    data.get('summary', ''), 
                    data.get('sentiment', 'Neutral')
                )
            )

    def save_resume(self, doc_id, data):
        print(f"\n🔍 [DEBUG] Raw Resume Data from AI: {data}")

        # 1. Aggressive Score Cleaning (Regex)
        raw_score = str(data.get('score', 0))
        try:
            # Find the first sequence of digits in the string
            match = re.search(r'\d+', raw_score)
            if match:
                clean_score = int(match.group())
            else:
                clean_score = 0
        except:
            print(f"⚠️ Could not parse score: {raw_score}")
            clean_score = 0

        # 2. Skills Cleaning
        skills = data.get('skills', [])
        if isinstance(skills, str):
            # If AI gave "Python, Java", split it into a list
            if "," in skills:
                skills = [s.strip() for s in skills.split(",")]
            else:
                skills = [skills]
        
        # 3. Name Cleaning
        name = data.get('name') or data.get('candidate_name') or "Unknown Candidate"

        print(f"💾 [DEBUG] Saving -> Name: {name}, Score: {clean_score}, Skills: {len(skills)} count")

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO resumes (doc_id, candidate_name, score, skills)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doc_id, name, clean_score, Json(skills))
                )
            print("✅ Resume saved successfully.")
        except Exception as e:
            print(f"❌ FATAL DB ERROR in save_resume: {e}")
            raise e  # Force the error to show in Streamlit

   

    def check_duplicate(self, file_hash: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM processed_docs WHERE file_hash = %s", (file_hash,))
            return cur.fetchone() is not None

    def log_process(self, doc_id, filename, doc_type, file_hash):
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO processed_docs (id, filename, doc_type, file_hash) 
                   VALUES (%s, %s, %s, %s) ON CONFLICT (file_hash) DO NOTHING""",
                (doc_id, filename, doc_type, file_hash)
            )

    def save_invoice(self, doc_id, data):
        total = data.get('total_amount')
        try: total = float(str(total).replace(',', '').replace('$','')) 
        except: total = 0.0
        date = data.get('date')
        try: date = parser.parse(str(date), dayfirst=True).strftime('%Y-%m-%d')
        except: date = None
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO invoices (doc_id, vendor, inv_date, total_amount, raw_data) VALUES (%s, %s, %s, %s, %s)",
                (doc_id, data.get('vendor'), date, total, Json(data))
            )

    def save_research_paper(self, doc_id, data):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO research_papers (doc_id, title, summary) VALUES (%s, %s, %s)",
                (doc_id, data.get('title', 'Unknown Title'), data.get('summary', 'No summary available.'))
            )

    def save_unknown(self, doc_id, data):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO unknown_docs (doc_id, summary, extracted_keywords) VALUES (%s, %s, %s)",
                (doc_id, data.get('summary', ''), Json(data.get('keywords', [])))
            )

    def close(self):
        self.conn.close()