# brain.py
import json
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME

class GroqBrain:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def decide(self, state, tools):
        # --- THE FIX: Create a 'Mini State' ---
        # We manually build a summary so the 'type' is NEVER cut off.
        # This prevents the "Infinite Classification Loop".
        mini_state = {
            "filename": state.get("filename"),
            "type": state.get("type", "MISSING"),  # <--- Crucial! Explicitly show status
            "history": state.get("history", []),
            "content_preview": state.get("content", "")[:1000] # Only show first 1000 chars
        }
        
        system_prompt = """
        You are an autonomous agent. 
        Output ONLY valid JSON. 
        No markdown, no thinking blocks, no chit-chat.
        """
        
        user_prompt = f"""
        Analyze the current state and decide the next action.
        
        Current State: {json.dumps(mini_state, indent=2)}
        
        Available Tools: [classify_document, extract_invoice, score_resume, summarize_research_paper, summarize_audio_note, summarize_unknown, save_data]
        
        Workflows:
        1. If 'type' is 'MISSING' -> action: "classify_document"
        2. If 'type' is 'INVOICE' and 'extracted_data' is missing -> action: "extract_invoice"
        3. If 'type' is 'RESUME' and 'score' is missing -> action: "score_resume"
        4. If 'type' is 'RESEARCH_PAPER' and 'research_summary' is missing -> action: "summarize_research_paper"
        5. If 'type' is 'AUDIO_NOTE' and 'audio_summary' is missing -> action: "summarize_audio_note"
        6. If 'type' is 'OTHER' and 'summary_data' is missing -> action: "summarize_unknown"
        7. If extraction is done -> action: "save_data"
        8. If 'save_data' is in history -> action: "STOP"
        
        Return JSON format:
        {{
            "reasoning": "Brief thought process",
            "action": "Next Tool Name"
        }}
        """

        try:
            # Call Groq
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL_NAME,
                temperature=0
            )
            
            content = completion.choices[0].message.content
            
            # Manually clean the output (Nuclear JSON Fix)
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except Exception as e:
            # Fallback (stops the loop if error occurs)
            print(f"Brain Error: {e}")
            return {"action": "STOP", "reasoning": f"Error: {e}"}