# Groq Autonomous Agent

An autonomous AI agent for processing documents and audio notes, classifying them (invoices, resumes, research papers, legal docs, audio notes, or other), extracting structured data, and saving results to a PostgreSQL database. Built with Streamlit, Groq API, and PostgreSQL.

**Key Features**
- Automatic document classification and extraction (invoices, resumes, research, legal, audio)
- Audio transcription and summarization (Groq Whisper)
- Incremental agent loop with explainable steps, using a `GroqBrain` to decide actions
- Saves structured results into PostgreSQL tables (invoices, resumes, research_papers, legal_docs, audio_notes, unknown_docs)
- Natural-language database queries converted to SQL and executed

**Repository Layout**
- `app.py` — Streamlit UI; upload documents/record audio and run the agent
- `agent.py` — Orchestration (ingest loop) and high-level agent lifecycle
- `brain.py` — Decision-making (uses Groq to return JSON actions)
- `tools.py` — Tool implementations (transcription, extraction, classification, SQL generation, save routines)
- `database.py` — Database helpers and save functions
- `database_setup.py` — Create database and schema (tables)
- `config.py` — Environment-backed configuration
- `env.example` — Example `.env` contents
- `requirements.txt` — Python dependencies

Prerequisites
- Python 3.10+ (recommended)
- PostgreSQL server accessible with credentials
- Groq API key

Quickstart

1) Clone repository

   git clone <your-repo>
   cd Autonomous-AI-Agent

2) Create and activate a Python virtual environment

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3) Install dependencies

```bash
pip install -r requirements.txt
```

4) Create a `.env` file (copy from `env.example`) and set values:

- `GROQ_API_KEY` — your Groq API key
- `MODEL_NAME` — optional model name (defaults to `llama-3.3-70b-versatile`)
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT`

Example (env.example is included):

```
GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
MODEL_NAME=llama-3.3-70b-versatile
DB_HOST=localhost
DB_NAME=agent_db_v2
DB_USER=postgres
DB_PASS=YOUR_DB_PASSWORD_HERE
DB_PORT=5432
```

5) Create the database and tables

Run the helper script which will attempt to connect to the `postgres` system DB and create the target database, then create required tables:

```bash
python database_setup.py
```

Notes:
- `database_setup.py` will connect to the `postgres` system DB using the credentials in `.env`. Ensure the user has privileges to create a database.

6) Run the Streamlit UI

```bash
streamlit run app.py
```

Usage Overview
- Streamlit UI (`app.py`) provides two input modes:
  - Document upload: upload PDFs or text files; the agent will classify and process them.
  - Voice notes: record or upload audio; the code transcribes via Groq Whisper and processes the transcript.
- After processing, results (structured data, summaries, scores) are saved into PostgreSQL and visible in the UI tabs.
- The "Ask Data" tab accepts text or voice queries, converts natural-language to SQL, runs the SQL, and returns both a natural-language answer and evidence rows.

Important Configuration & Behavior
- `config.py` loads environment variables and requires `GROQ_API_KEY` (will raise an error if missing).
- The agent uses hashing to avoid duplicates (`file_hash` stored in `processed_docs`).
- `ToolRegistry._call_groq_json` and related helpers attempt to ensure valid JSON responses from the Groq API. Robustness checks exist across `database.py` to sanitize data before saving.

Database Schema (created by `database_setup.py`)
- `processed_docs` (parent)
- `invoices` — `vendor`, `inv_date`, `total_amount`, `raw_data`
- `resumes` — `candidate_name`, `score`, `skills`
- `research_papers` — `title`, `summary`
- `audio_notes` — `transcript`, `summary`, `sentiment`
- `legal_docs` — `document_type`, `parties`, `effective_date`, `expiration_date`, `key_clauses`, `summary`
- `unknown_docs` — `summary`, `extracted_keywords`

Troubleshooting
- GROQ API key missing: `config.py` raises an error; set `GROQ_API_KEY` in `.env`.
- PostgreSQL connection errors: ensure `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` and `DB_PORT` are correct and that the server accepts connections.
- If `psycopg2` installation fails on Windows, `psycopg2-binary` is listed in `requirements.txt` and is a convenient fallback.

Development Notes
- The agent loop in `agent.py` calls `GroqBrain.decide` which returns a single JSON action. The loop executes tools in `tools.py` and ultimately saves results using `database.py`.
- Transcription uses `ToolRegistry.transcribe_audio` and expects audio objects with a `.read()` method. `app.py` adds a small metadata tag for audio: `[METADATA: AUDIO_NOTE]` so the classifier will treat it as audio.
- SQL generation in `tools.py` returns a raw SQL string which is executed using SQLAlchemy `text()` to avoid injection/formatting issues.

Contributing
- Please open issues or PRs for bugs or improvements. Suggested workflow:
  - Fork the repo
  - Create a feature branch
  - Add tests and update documentation
  - Open a PR with a clear description

License
- Add your preferred license or a LICENSE file to the repository.

Next Steps / Suggestions
- Add unit tests for `tools.py` extraction functions and `database.py` saving logic.
- Add CI to lint and run tests.
- Add Dockerfile and docker-compose for local Postgres + Streamlit setup.

If you'd like, I can:
- Add a `README.md` badge for build/CI/coverage.
- Create a simple `docker-compose.yml` and `Dockerfile` to containerize the app and Postgres.

---
Generated from inspecting project files: `app.py`, `agent.py`, `brain.py`, `tools.py`, `database.py`, `database_setup.py`, `config.py`, `env.example`.
