# brain.py
import json
from groq import Groq
from typing import List, Dict
from config import GROQ_API_KEY, MODEL_NAME

class GroqBrain:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def decide(self, state: Dict, tools: List[str]) -> Dict:
        system_prompt = """
        You are an autonomous agent.
        WORKFLOWS:
        1. Unknown Type -> 'classify_document'.
        2. INVOICE -> 'extract_invoice' -> 'save_data'.
        3. RESUME -> 'score_resume' -> 'save_data'.
        4. RESEARCH_PAPER -> 'summarize_research_paper' -> 'save_data'.
        5. OTHER -> 'summarize_unknown' -> 'save_data'.
        
        RULE: Do NOT stop until you call 'save_data'.
        Output JSON: {"reasoning": "...", "action": "..."}
        """
        
        user_prompt = f"""
        State:
        - File: {state['filename']}
        - Type: {state.get('type', 'Unknown')}
        - History: {[h['action'] for h in state['history']]}
        """
        
        try:
            res = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL_NAME, temperature=0, response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            return {"action": "STOP", "reasoning": str(e)}