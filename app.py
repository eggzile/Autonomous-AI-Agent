import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from pypdf import PdfReader
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT
from agent import AutonomousAgent
from tools import ToolRegistry # Needed for transcription

# 1. Page Config & Layout
st.set_page_config(layout="wide", page_title="Groq AI Agent")

# --- CSS HACK TO REMOVE TOP SPACE ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            margin-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Database Connection
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def get_data(table):
    try:
        return pd.read_sql(f"SELECT * FROM {table} ORDER BY doc_id DESC LIMIT 20", engine)
    except:
        return pd.DataFrame()

def read_file(file):
    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    return file.read().decode("utf-8")

# --- UI LAYOUT ---
st.title("⚡ Groq Autonomous Agent")

col1, col2 = st.columns([1, 1])

# ==========================================
# LEFT COLUMN: INPUT & PROCESSING
# ==========================================
with col1:
    st.subheader("📡 Agent Terminal")

    input_method = st.radio("Select Input:", ["📄 Document Upload", "🎙️ Voice Note"], horizontal=True)

    content = ""
    file_name = "unknown"
    start_process = False

    # --- OPTION A: DOCUMENT UPLOAD ---
    if input_method == "📄 Document Upload":
        uploaded_file = st.file_uploader("Upload PDF or Text file", type=["pdf", "txt"])
        
        if uploaded_file and st.button("Process Document", type="primary"):
            with st.spinner("📖 Reading file..."):
                content = read_file(uploaded_file)
                file_name = uploaded_file.name
                start_process = True

    # --- OPTION B: VOICE INPUT ---
    elif input_method == "🎙️ Voice Note":
        st.info("Record or upload audio. The AI will transcribe and extract insights.")
        
        audio_mic = st.audio_input("Record Voice")
        audio_upload = st.file_uploader("Or Upload Audio", type=["mp3", "wav", "m4a"])
        
        final_audio = audio_mic if audio_mic else audio_upload

        if final_audio:
            st.audio(final_audio)
            
            if st.button("Transcribe & Process", type="primary"):
                with st.spinner("🎧 Transcribing via Groq Whisper..."):
                    try:
                        tools = ToolRegistry()
                        if not hasattr(final_audio, 'name'):
                            final_audio.name = "recording.wav"
                            
                        transcription_text = tools.transcribe_audio(final_audio)
                        
                        st.success("Transcription Complete!")
                        st.text_area("📝 Transcript:", transcription_text, height=150)
                        
                        # --- THE FIX: Metadata Injection ---
                        # We force the tag so the classifier knows 100% this is audio.
                        content = f"[METADATA: AUDIO_NOTE]\n{transcription_text}"
                        
                        timestamp = str(int(pd.Timestamp.now().timestamp()))
                        file_name = f"voice_note_{timestamp}.txt"
                        start_process = True
                        
                    except Exception as e:
                        st.error(f"Transcription Failed: {e}")

    # ==========================================
    # AGENT EXECUTION LOOP
    # ==========================================
    
    log_container = st.container(height=400, border=True)

    if start_process and content:
        agent = AutonomousAgent()
        
        def update_log(msg):
            log_container.markdown(msg)

        final_state = agent.ingest(file_name, content, update_log)

        # --- FINAL SUMMARY ---
        if final_state.get("status") != "skipped":
            st.success("🎉 Processing Complete!")
            
            with st.expander("📄 Extracted Data Summary", expanded=True):
                doc_type = final_state.get('type', 'UNKNOWN')
                st.markdown(f"### Type: `{doc_type}`")
                
                if "INVOICE" in doc_type:
                    data = final_state.get('extracted_data', {})
                    st.metric("💰 Total", f"{data.get('total_amount', 0)}")
                    st.write(f"**Vendor:** {data.get('vendor')}")
                    st.json(data)

                elif "RESUME" in doc_type:
                    data = final_state.get('score', {})
                    st.metric("🎓 Score", f"{data.get('score')}/100")
                    st.write(f"**Name:** {data.get('name')}")
                    st.write("**Skills:** " + ", ".join(data.get('skills', [])))

                elif "RESEARCH" in doc_type:
                    data = final_state.get('research_summary', {})
                    st.subheader(data.get('title'))
                    st.info(data.get('summary'))

                elif "AUDIO" in doc_type:
                    data = final_state.get('audio_summary', {})
                    st.write(f"**Sentiment:** {data.get('sentiment')}")
                    st.write(f"**Summary:** {data.get('summary')}")

                elif "OTHER" in doc_type:
                    data = final_state.get('summary_data', {})
                    st.write(data.get('summary'))

# ==========================================
# RIGHT COLUMN: DATABASE & CHAT
# ==========================================
with col2:
    st.subheader("💾 Data & Insights")
    
    # Add "Ask Data" to the tabs
    t1, t2, t3, t4, t5, t6 = st.tabs(["Invoices", "Resumes", "Research", "Audio Notes", "Unknown", "💬 Ask Data"])
    
    # --- Existing Tabs ---
    with t1: st.dataframe(get_data("invoices"), use_container_width=True)
    with t2: st.dataframe(get_data("resumes"), use_container_width=True)
    with t3: st.dataframe(get_data("research_papers"), use_container_width=True)
    with t4: st.dataframe(get_data("audio_notes"), use_container_width=True)
    with t5: st.dataframe(get_data("unknown_docs"), use_container_width=True)
    
    # ... inside the "Right Column" logic in app.py ...

    # ... inside the "💬 Ask Data" tab (t6) ...
    with t6:
        st.info("🤖 Ask questions about your data (Text or Voice)")
        
        # 1. Inputs
        c1, c2 = st.columns([3, 1])
        with c1:
            query_text = st.text_input("Type your question:", placeholder="e.g., Who has the highest resume score?")
        with c2:
            query_voice = st.audio_input("Or Record")
        
        final_query = None

        # Logic to handle Voice vs Text
        if query_voice:
            # We need to transcribe it first
            from tools import ToolRegistry
            t = ToolRegistry() # Temporary instance
            with st.spinner("🎧 Transcribing..."):
                final_query = t.transcribe_audio(query_voice)
                st.write(f"**🗣️ You said:** *{final_query}*")
        elif query_text:
            final_query = query_text

        # 2. Execution Button
        if final_query:
            if st.button("🚀 Run Analysis", type="primary"):
                from tools import ToolRegistry
                t = ToolRegistry()
                
                with st.spinner("🧠 Thinking & Querying Database..."):
                    result = t.query_database(final_query)
                    
                    if result['status'] == 'error':
                        st.error(f"❌ SQL Error: {result['message']}")
                    else:
                        # --- DISPLAY THE RESULT ---
                        
                        # A. Natural Language Answer
                        st.markdown(f"### 🤖 Answer:")
                        st.success(result['answer'])
                        
                        # B. The Database Entry (Evidence)
                        st.markdown("### 📊 Evidence (Database Rows):")
                        if result['data'] is not None and not result['data'].empty:
                            st.dataframe(result['data'], use_container_width=True)
                        else:
                            st.warning("No rows returned from query.")
                            
                        # C. Technical Details (Hidden by default)
                        with st.expander("🕵️ View Generated SQL Query"):
                            st.code(result.get('sql'), language='sql')