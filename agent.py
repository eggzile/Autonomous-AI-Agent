# agent.py
import uuid
import hashlib
import time
from typing import Dict, Callable, Optional
from brain import GroqBrain
from tools import ToolRegistry
from database import Database

class AutonomousAgent:
    def __init__(self):
        self.brain = GroqBrain()
        self.tools = ToolRegistry()
        self.db = Database()

    def ingest(self, filename: str, content: str, status_callback: Optional[Callable] = None):
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check Duplicate
        if self.db.check_duplicate(file_hash):
            if status_callback: status_callback(f"🛑 **Duplicate:** `{filename}` already processed.")
            return {"status": "skipped", "reason": "duplicate"}
        
        if status_callback: status_callback(f"🚀 **New File.** Processing `{filename}`...")
        
        state = {
            "id": str(uuid.uuid4()),
            "filename": filename,
            "content": content,
            "file_hash": file_hash,
            "history": []
        }
        
        return self._run_loop(state, status_callback)

    def _run_loop(self, state: Dict, callback):
        steps = 0
        max_steps = 8
        
        while steps < max_steps:
            steps += 1
            
            # 1. Brain Decides
            decision = self.brain.decide(state, [])
            action = decision.get('action')
            reasoning = decision.get('reasoning')
            
            # --- LOGGING CHANGE: INCREMENTAL BLOCKS ---
            step_msg = f"""
---
### 🧠 Step {steps}
**Thinking:** {reasoning}

**⚡ Action:** `{action}`
            """
            if callback: callback(step_msg)
            time.sleep(2.0) # Delay for reading
            # ------------------------------------------

            if action == "STOP": 
                break

            # 2. Execute Action
            res = self._execute(action, state)
            
            # 3. Update History
            state['history'].append({"action": action})
            
            # Special UI updates (Incremental)
            if action == "classify_document":
                state['type'] = res
                if callback: callback(f"\n📂 **Classified as:** `{res}`")
                time.sleep(1.0)

            # Hard Stop logic for Save
            if action == "save_data":
                if "Error" in str(res) or "Failed" in str(res):
                     if callback: callback(f"\n❌ **Save Failed:** {res}")
                else:
                     if callback: callback(f"\n✅ **Data Saved Successfully.**")
                break 
            
        return state

    def _execute(self, action, state):
        t = self.tools
        if action == "classify_document": return t.classify_document(state['content'])
        elif action == "extract_invoice": state['extracted_data'] = t.extract_invoice(state['content'])
        elif action == "score_resume": state['score'] = t.score_resume(state['content'])
        elif action == "summarize_unknown": state['summary_data'] = t.summarize_unknown(state['content'])
        elif action == "summarize_research_paper": 
            state['research_summary'] = t.summarize_research_paper(state['content'])
            return "Summarized"
        elif action == "save_data": return t.save_data(state['id'], state)
        return "Done"