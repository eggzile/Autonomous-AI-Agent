import json
import re
from groq import Groq
from typing import Dict
from database import Database
from config import GROQ_API_KEY, MODEL_NAME

class ToolRegistry:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.db = Database()

    # --- 1. TRANSCRIPTION ---
    def transcribe_audio(self, audio_file) -> str:
        print("   [Tool] 🎙️ Transcribing audio via Groq Whisper...")
        try:
            transcription = self.client.audio.transcriptions.create(
                file=(audio_file.name, audio_file.read()), 
                model="whisper-large-v3", 
                response_format="text"
            )
            return transcription
        except Exception as e:
            return f"Error transcribing audio: {str(e)}"

    # --- 2. VISION (NEW) ---
    # ... inside ToolRegistry class in tools.py ...

    def analyze_image(self, base64_string: str) -> str:
        """
        Uses Llama 4 Scout (Vision) to transcribe text/objects from an image.
        """
        print("   [Tool] 👁️  Analyzing Image with Llama 4 Scout...")
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in detail. If there is text, extract it all. If it is a scene or object, describe what it is."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_string}",
                                },
                            },
                        ],
                    }
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct", 
                temperature=0,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Vision Error: {e}"

    # --- 3. CLASSIFICATION ---
    def classify_document(self, content: str) -> str:
        if "[METADATA: AUDIO_NOTE]" in content: return "AUDIO_NOTE"
        
        # NEW: Check for Image Tag
        if "[METADATA: IMAGE_Base64_START]" in content: return "IMAGE_NEEDS_OCR"

        prompt = f"""
        Classify into EXACTLY one category:
        1. INVOICE
        2. RESUME
        3. RESEARCH_PAPER
        4. AUDIO_NOTE
        5. LEGAL_DOC (Contracts, NDAs, Wills, Deeds, Agreements)
        6. OTHER
        
        Text: {content[:1000]}
        
        Respond ONLY with the category name.
        """
        raw = self._call_groq(prompt).strip().upper()
        
        if "INVOICE" in raw: return "INVOICE"
        if "RESUME" in raw: return "RESUME"
        if "RESEARCH" in raw: return "RESEARCH_PAPER"
        if "AUDIO" in raw: return "AUDIO_NOTE"
        
        if "LEGAL" in raw or "NDA" in raw or "AGREEMENT" in raw or "CONTRACT" in raw:
            return "LEGAL_DOC"
        
        return "OTHER"

    # --- 4. EXTRACTION TOOLS ---
    def extract_invoice(self, content: str) -> Dict:
        prompt = f"""
        Extract invoice data as JSON. 
        Fields: 'vendor', 'date', 'line_items' (list), 'subtotal', 'tax', 'total_amount'.
        If subtotal is missing, calculate it from line items.
        Text: {content[:3000]}
        """
        data = self._call_groq_json(prompt)
        try:
            items = data.get('line_items', [])
            calc_sub = sum([float(str(i.get('total',0)).replace(',','').replace('$','')) for i in items if i.get('total')])
            if calc_sub > 0 and (data.get('subtotal') == 0 or data.get('subtotal') is None):
                data['subtotal'] = calc_sub
        except: pass
        return data
    
    def extract_legal_doc(self, content: str) -> Dict:
        prompt = f"""
        Analyze this legal document.
        Return JSON with:
        - 'document_type': Specific type (e.g., "Mutual NDA", "Employment Contract").
        - 'parties': List of names/companies (e.g., ["TechFlow Solutions", "Global Data Systems"]).
        - 'effective_date': YYYY-MM-DD.
        - 'expiration_date': YYYY-MM-DD (Calculate if term is given, e.g., "2 years from effective").
        - 'key_clauses': List of 3-5 distinct terms (e.g., "Confidentiality lasts 5 years").
        - 'summary': A 2-sentence summary.
        
        Text: {content[:3000]}
        """
        return self._call_groq_json(prompt)
    
    def score_resume(self, content: str) -> Dict:
        return self._call_groq_json(f"Score resume 0-100. Return JSON with 'score', 'skills', 'name'.\n{content[:2000]}")

    def summarize_unknown(self, content: str) -> Dict:
        return self._call_groq_json(f"Return JSON with 'summary' (2 sentences) and 'keywords' (list).\n{content[:2000]}")

    def summarize_research_paper(self, content: str) -> Dict:
        prompt = f"Analyze this paper. Return JSON with: 'title', 'summary' (6-7 lines).\nText: {content[:3000]}"
        return self._call_groq_json(prompt)

    def summarize_audio_note(self, content: str) -> Dict:
        prompt = f"""
        Analyze this audio transcript.
        Return JSON with:
        - 'summary': A concise paragraph.
        - 'sentiment': (Positive, Neutral, Negative).
        
        Text: {content[:3000]}
        """
        data = self._call_groq_json(prompt)
        clean_content = content.replace("[METADATA: AUDIO_NOTE]", "").strip()
        data['transcript'] = clean_content 
        return data

    def query_database(self, query: str) -> Dict:
        print(f"   [Tool] ❓ Processing Query: '{query}'")
        schema_context = """
        Tables:
        - invoices (id, doc_id, vendor, inv_date, total_amount)
        - resumes (id, doc_id, candidate_name, score, skills)
        - research_papers (id, doc_id, title, summary)
        - audio_notes (id, doc_id, transcript, summary, sentiment)
        """
        try:
            sql_prompt = f"""
            Generate a PostgreSQL query for: "{query}"
            Context: {schema_context}
            Rules:
            - Return ONLY the raw SQL string.
            - Use ILIKE for text searches.
            - LIMIT to 10 rows unless specified otherwise.
            """
            sql_response = self._call_groq(sql_prompt)
            sql_query = sql_response.replace("```sql", "").replace("```", "").strip()
            print(f"   [Tool] 🔍 Executing SQL: {sql_query}")

            import pandas as pd
            from sqlalchemy import create_engine, text
            from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
            
            db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                df = pd.read_sql(text(sql_query), conn)
            
            if df.empty:
                nl_answer = "I searched the database, but found no records matching your request."
            else:
                data_preview = df.head(5).to_string(index=False)
                row_count = len(df)
                summary_prompt = f"""
                User Question: "{query}"
                Database Data ({row_count} total rows):
                {data_preview}
                Task: Answer the user's question in natural language based on this data. 
                - Be concise.
                """
                nl_answer = self._call_groq(summary_prompt)

            return {"status": "success", "data": df, "sql": sql_query, "answer": nl_answer}
        except Exception as e:
            print(f"SQL Execution Error: {e}")
            return {"status": "error", "message": str(e)}

    # --- 4. SAVING ---
    def save_data(self, doc_id: str, state: Dict):
        doc_type = state.get('type')
        try:
            self.db.log_process(doc_id, state.get('filename'), doc_type, state.get('file_hash'))

            if "INVOICE" in doc_type: self.db.save_invoice(doc_id, state.get('extracted_data', {}))
            elif "RESUME" in doc_type: self.db.save_resume(doc_id, state.get('score', {}))
            elif "RESEARCH" in doc_type: self.db.save_research_paper(doc_id, state.get('research_summary', {}))
            elif "AUDIO" in doc_type: self.db.save_audio_note(doc_id, state.get('audio_summary', {}))
            elif "LEGAL" in doc_type: self.db.save_legal_doc(doc_id, state.get('legal_data', {}))
            elif "OTHER" in doc_type: self.db.save_unknown(doc_id, state.get('summary_data', {}))
            
            return "Saved Successfully"
        except Exception as e:
            return f"DB Error: {e}"

    # --- HELPERS ---
    def _call_groq(self, prompt):
        return self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME, temperature=0
        ).choices[0].message.content

    def _call_groq_json(self, prompt):
        system_prompt = "You are an API that outputs strictly valid JSON. Do not output markdown blocks or comments."
        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=MODEL_NAME, temperature=0 
            )
            content = completion.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            return {}