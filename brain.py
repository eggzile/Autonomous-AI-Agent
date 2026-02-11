# brain.py
import json
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME

class GroqBrain:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def decide(self, state, tools):
        # --- THE FIX: ADD SUCCESS FLAGS ---
        # The Brain needs to know IF data exists, without seeing the massive JSON.
        mini_state = {
            "filename": state.get("filename"),
            "type": state.get("type", "MISSING"),
            "history": state.get("history", []),
            "content_preview": state.get("content", "")[:500],
            
            # Boolean Flags (The Brain's "Eyes")
            "has_invoice_data": state.get("extracted_data") is not None,
            "has_resume_score": state.get("score") is not None,
            "has_research_summary": state.get("research_summary") is not None,
            "has_legal_data": state.get("legal_data") is not None,
            "has_audio_summary": state.get("audio_summary") is not None,
            "has_unknown_summary": state.get("summary_data") is not None
        }
        
        system_prompt = """
        You are an autonomous agent. Output ONLY valid JSON.
        """
        
        # We update the workflows to check the FLAGS, not the raw keys.
        user_prompt = f"""
        Analyze the current state and decide the next action.
        
        Current State: {json.dumps(mini_state, indent=2)}
        
        Available Tools: [classify_document, extract_invoice, score_resume, summarize_research_paper, extract_legal_doc, summarize_audio_note, summarize_unknown, save_data]
        
        Workflows:
        1. If 'type' is 'MISSING' -> action: "classify_document"
        
        2. If 'type' is 'INVOICE' and 'has_invoice_data' is false -> action: "extract_invoice"
        3. If 'type' is 'RESUME' and 'has_resume_score' is false -> action: "score_resume"
        4. If 'type' is 'RESEARCH_PAPER' and 'has_research_summary' is false -> action: "summarize_research_paper"
        5. If 'type' is 'LEGAL_DOC' and 'has_legal_data' is false -> action: "extract_legal_doc"
        6. If 'type' is 'AUDIO_NOTE' and 'has_audio_summary' is false -> action: "summarize_audio_note"
        7. If 'type' is 'OTHER' and 'has_unknown_summary' is false -> action: "summarize_unknown"
        
        8. If any data flag is true -> action: "save_data"
        9. If 'save_data' is in history -> action: "STOP"
        
        Return JSON format:
        {{
            "reasoning": "Brief thought process",
            "action": "Next Tool Name"
        }}
        """

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL_NAME,
                temperature=0
            )
            
            content = completion.choices[0].message.content
            # Nuclear JSON Fix
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Brain Error: {e}")
            return {"action": "STOP", "reasoning": f"Error: {e}"}