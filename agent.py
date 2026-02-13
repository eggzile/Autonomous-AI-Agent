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
            
            step_msg = f"""
---
### 🧠 Step {steps}
**Thinking:** {reasoning}

**⚡ Action:** `{action}`
            """
            if callback: callback(step_msg)
            time.sleep(2.0)

            if action == "STOP": 
                break

            # 2. Execute Action
            res = self._execute(action, state)
            
            # 3. Update History
            state['history'].append({"action": action})
            
            # Special UI updates
            if action == "classify_document":
                state['type'] = res
                if callback: callback(f"\n📂 **Classified as:** `{res}`")
                time.sleep(1.0)
            
            # Show image extraction result
            if action == "analyze_image":
                if callback: callback(f"\n👁️ **Vision:** Extracted text from image.")

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
        
        # --- NEW: IMAGE EXECUTION (UPDATED) ---
        if action == "analyze_image":
            try:
                # 1. Extract Base64 from tags
                raw = state['content']
                start = "[METADATA: IMAGE_Base64_START]"
                end = "[METADATA: IMAGE_Base64_END]"
                b64_str = raw.split(start)[1].split(end)[0]
                
                # 2. Run Vision Tool (Extract Text)
                extracted_text = t.analyze_image(b64_str)
                
                # 3. Update State Content
                state['content'] = extracted_text
                
                # --- THE FIX: IMMEDIATE RE-CLASSIFICATION ---
                # Don't ask the Brain to classify again (it might refuse).
                # We force the classification tool right now.
                new_type = t.classify_document(extracted_text)
                state['type'] = new_type
                # --------------------------------------------
                
                return f"👁️ Image Text Extracted & Re-classified as {new_type}"
                
            except Exception as e: return f"Image Error: {e}"
        # ----------------------------
        elif action == "classify_document": return t.classify_document(state['content'])
        elif action == "extract_invoice": state['extracted_data'] = t.extract_invoice(state['content'])
        elif action == "score_resume": state['score'] = t.score_resume(state['content'])
        elif action == "summarize_audio_note":
            state['audio_summary'] = t.summarize_audio_note(state['content'])
            return "Audio Summarized"
        elif action == "extract_legal_doc":
            state['legal_data'] = t.extract_legal_doc(state['content'])
            return "Legal Data Extracted"
        elif action == "summarize_research_paper": 
            state['research_summary'] = t.summarize_research_paper(state['content'])
            return "Summarized"
        elif action == "summarize_unknown": state['summary_data'] = t.summarize_unknown(state['content'])
        elif action == "save_data": return t.save_data(state['id'], state)
        return "Done"