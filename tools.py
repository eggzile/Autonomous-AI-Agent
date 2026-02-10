# tools.py
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

    def classify_document(self, content: str) -> str:
        prompt = f"""
        Classify into EXACTLY one category:
        1. INVOICE
        2. RESUME
        3. RESEARCH_PAPER
        4. OTHER
        
        Text: {content[:1000]}
        
        Respond ONLY with the category name (e.g., 'RESUME'). Do not add numbers or punctuation.
        """
        raw_result = self._call_groq(prompt).strip().upper()
        
        if "INVOICE" in raw_result: return "INVOICE"
        if "RESUME" in raw_result: return "RESUME"
        if "RESEARCH" in raw_result: return "RESEARCH_PAPER"
        return "OTHER"

    def extract_invoice(self, content: str) -> Dict:
        # 1. Ask AI ONLY for the list of items (it is good at this)
        prompt = f"""
        Extract invoice data as JSON. 
        If a specific field is not found, return 0 or null.
        
        Required Fields:
        - 'vendor': Company name.
        - 'date': Invoice date (YYYY-MM-DD).
        - 'line_items': A list of objects, each containing:
             - 'description': Item name
             - 'qty': Quantity (number)
             - 'unit_price': Price per unit (number)
             - 'total': Row total (number)
        
        Text: {content[:3000]}
        """
        data = self._call_groq_json(prompt)
        
        # 2. PERFORM MATH IN PYTHON (Reliable)
        calculated_subtotal = 0.0
        line_items = data.get('line_items', [])
        
        for item in line_items:
            try:
                # Sum up the 'total' column for each row
                row_total = float(str(item.get('total', 0)).replace(',', '').replace('$', ''))
                calculated_subtotal += row_total
            except:
                continue
                
        # 3. Inject the calculated total back into the data
        data['subtotal'] = round(calculated_subtotal, 2)
        data['total_amount'] = data.get('total_amount') or data['subtotal'] # Fallback if no tax logic
        
        return data

    def score_resume(self, content: str) -> Dict:
        return self._call_groq_json(f"Score resume 0-100. Return JSON 'score', 'skills', 'name'.\n{content[:2000]}")

    def summarize_unknown(self, content: str) -> Dict:
        return self._call_groq_json(f"Return JSON with 'summary' (2 sentences) and 'keywords' (list).\n{content[:2000]}")

    def summarize_research_paper(self, content: str) -> Dict:
        prompt = f"""
        Analyze this research paper.
        Return a JSON object with:
        - 'title': The title of the paper.
        - 'summary': A concise summary of EXACTLY 6-7 lines.
        
        Text: {content[:3000]}
        """
        return self._call_groq_json(prompt)

    def save_data(self, doc_id: str, state: Dict):
        doc_type = state.get('type')
        filename = state.get('filename')
        
        print(f"   [Tool] 💾 Saving Data for Type: '{doc_type}'...") 
        
        try:
            self.db.log_process(doc_id, filename, doc_type, state.get('file_hash'))

            if "INVOICE" in doc_type:
                self.db.save_invoice(doc_id, state.get('extracted_data', {}))
            elif "RESUME" in doc_type:
                self.db.save_resume(doc_id, state.get('score', {}))
            elif "RESEARCH" in doc_type:
                self.db.save_research_paper(doc_id, state.get('research_summary', {}))
            elif "OTHER" in doc_type:
                self.db.save_unknown(doc_id, state.get('summary_data', {}))
            else:
                return f"Error: Unknown Document Type '{doc_type}'"
            
            # --- THE NEW TERMINAL OUTPUT ---
            print("--------------------------------------------------")
            print(f"✅  SUCCESS: Data for '{filename}' saved to DB.")
            print("--------------------------------------------------")
            # -------------------------------
            
            return "Saved Successfully"
        except Exception as e:
            print(f"❌  [Tool Error] Save Failed: {e}")
            return f"DB Error: {e}"

    def _call_groq(self, prompt):
        return self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME, temperature=0
        ).choices[0].message.content

    def _call_groq_json(self, prompt):
        try:
            res = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=MODEL_NAME, temperature=0, response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except: return {}