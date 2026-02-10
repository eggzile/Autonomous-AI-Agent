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
                model="whisper-large-v3", # FIXED MODEL NAME
                response_format="text"
            )
            return transcription
        except Exception as e:
            return f"Error transcribing audio: {str(e)}"

    # --- 2. CLASSIFICATION ---
    def classify_document(self, content: str) -> str:
        # THE FIX: Instant catch for tagged audio
        if "[METADATA: AUDIO_NOTE]" in content:
            return "AUDIO_NOTE"

        prompt = f"""
        Classify into EXACTLY one category:
        1. INVOICE
        2. RESUME
        3. RESEARCH_PAPER
        4. AUDIO_NOTE
        5. OTHER
        
        Text: {content[:1000]}
        
        Respond ONLY with the category name.
        """
        raw = self._call_groq(prompt).strip().upper()
        
        if "INVOICE" in raw: return "INVOICE"
        if "RESUME" in raw: return "RESUME"
        if "RESEARCH" in raw: return "RESEARCH_PAPER"
        if "AUDIO" in raw: return "AUDIO_NOTE"
        return "OTHER"

    # --- 3. EXTRACTION TOOLS ---
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
        # Remove the metadata tag before saving to DB
        clean_content = content.replace("[METADATA: AUDIO_NOTE]", "").strip()
        data['transcript'] = clean_content 
        return data

    # --- 4. SAVING ---
    def save_data(self, doc_id: str, state: Dict):
        doc_type = state.get('type')
        filename = state.get('filename')
        print(f"   [Tool] 💾 Saving {doc_type}...")
        
        try:
            self.db.log_process(doc_id, filename, doc_type, state.get('file_hash'))

            if "INVOICE" in doc_type: self.db.save_invoice(doc_id, state.get('extracted_data', {}))
            elif "RESUME" in doc_type: self.db.save_resume(doc_id, state.get('score', {}))
            elif "RESEARCH" in doc_type: self.db.save_research_paper(doc_id, state.get('research_summary', {}))
            elif "AUDIO" in doc_type: self.db.save_audio_note(doc_id, state.get('audio_summary', {}))
            elif "OTHER" in doc_type: self.db.save_unknown(doc_id, state.get('summary_data', {}))
            
            print("--------------------------------------------------")
            print(f"✅  SUCCESS: Data for '{filename}' saved to DB.")
            print("--------------------------------------------------")
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
        # --- THE NUCLEAR FIX FOR JSON ERRORS ---
        # 1. We tell the System to only output JSON.
        # 2. We DO NOT use 'response_format={"type": "json_object"}' (It breaks).
        # 3. We manually parse the string result.
        
        system_prompt = "You are an API that outputs strictly valid JSON. Do not output markdown blocks or comments."
        
        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=MODEL_NAME, 
                temperature=0 
                # NO response_format param!
            )
            
            content = completion.choices[0].message.content
            # Clean up potential markdown wrappers
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            return {}