# brain.py
import json
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME

class GroqBrain:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def decide(self, state, tools):
        # 1. Force the prompt to be explicit about JSON
        system_prompt = """
        You are an autonomous agent. 
        Output ONLY valid JSON. 
        No markdown, no thinking blocks, no chit-chat.
        """
        
        user_prompt = f"""
        Analyze the current state and decide the next action.
        
        State: {str(state)[:3000]}
        
        Available Tools: [classify_document, extract_invoice, score_resume, summarize_research_paper, summarize_audio_note, summarize_unknown, save_data]
        
        Workflows:
        - If 'type' is missing -> action: "classify_document"
        - If 'type' is INVOICE and 'extracted_data' is missing -> action: "extract_invoice"
        - If 'type' is RESUME and 'score' is missing -> action: "score_resume"
        - If 'type' is RESEARCH and 'research_summary' is missing -> action: "summarize_research_paper"
        - If 'type' is AUDIO_NOTE and 'audio_summary' is missing -> action: "summarize_audio_note"
        - If 'type' is OTHER and 'summary_data' is missing -> action: "summarize_unknown"
        - If data is extracted -> action: "save_data"
        - If saved -> action: "STOP"
        
        Return JSON format:
        {{
            "reasoning": "Brief thought process",
            "action": "Next Tool Name"
        }}
        """

        try:
            # --- THE NUCLEAR FIX (Same as tools.py) ---
            # We REMOVE response_format={"type": "json_object"} entirely.
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL_NAME,
                temperature=0
                # NO response_format here!
            )
            
            content = completion.choices[0].message.content
            
            # Manually clean the output
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except Exception as e:
            # Fallback if JSON fails
            print(f"Brain Error: {e}")
            return {"action": "STOP", "reasoning": f"Error: {e}"}