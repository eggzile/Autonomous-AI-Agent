# app.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from pypdf import PdfReader
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT
from agent import AutonomousAgent

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
# ------------------------------------

# ... rest of your imports and code ...

# Database Connection
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def get_data(table):
    try:
        return pd.read_sql(f"SELECT * FROM {table} ORDER BY doc_id DESC LIMIT 20", engine)
    except: return pd.DataFrame()

def read_file(file):
    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    return file.read().decode("utf-8")

# --- UI LAYOUT ---
st.title("⚡ Groq Autonomous Agent")

col1, col2 = st.columns([1, 1])

# --- LEFT COLUMN: LIVE PROCESS ---
with col1:
    st.subheader("📡 Agent Terminal")
    uploaded = st.file_uploader("Upload Document")
    btn = st.button("Process File", type="primary")

    # 1. Create a SCROLLABLE container for logs
    # height=500 makes it scroll if content exceeds 500px
    log_container = st.container(height=500, border=True)
    
    if btn and uploaded:
        content = read_file(uploaded)
        agent = AutonomousAgent()
        
        # 2. Callback appends to the scrollable container
        def update(msg):
            log_container.markdown(msg)
            
        final_state = agent.ingest(uploaded.name, content, update)
        
        # 3. Final Summary Display
        if final_state.get("status") != "skipped":
            st.success("🎉 Processing Complete!")
            
            with st.expander("📄 Document Summary", expanded=True):
                doc_type = final_state.get('type', 'UNKNOWN')
                st.markdown(f"**Type:** `{doc_type}`")
                
                if "INVOICE" in doc_type:
                    data = final_state.get('extracted_data', {})
                    st.metric("Total Amount", f"{data.get('total_amount', 0)}")
                    st.write(f"**Vendor:** {data.get('vendor')}")
                    st.write(f"**Date:** {data.get('date')}")
                    st.json(data)
                    
                elif "RESUME" in doc_type:
                    data = final_state.get('score', {})
                    st.metric("Candidate Score", f"{data.get('score')}/100")
                    st.write(f"**Name:** {data.get('name')}")
                    st.write("**Top Skills:**")
                    st.write(", ".join(data.get('skills', [])))
                    
                elif "RESEARCH" in doc_type:
                    data = final_state.get('research_summary', {})
                    st.subheader(data.get('title', 'Untitled'))
                    st.info(data.get('summary'))
                    
                elif "OTHER" in doc_type:
                    data = final_state.get('summary_data', {})
                    st.write(data.get('summary'))
                    st.write("**Keywords:**", data.get('keywords'))

# --- RIGHT COLUMN: DATABASE ---
with col2:
    st.subheader("💾 Database Records")
    if st.button("🔄 Refresh Tables"): st.rerun()
    
    t1, t2, t3, t4 = st.tabs(["Invoices", "Resumes", "Research", "Unknown Docs"])
    
    with t1: st.dataframe(get_data("invoices"), use_container_width=True)
    with t2: st.dataframe(get_data("resumes"), use_container_width=True)
    with t3: st.dataframe(get_data("research_papers"), use_container_width=True)
    with t4: st.dataframe(get_data("unknown_docs"), use_container_width=True)