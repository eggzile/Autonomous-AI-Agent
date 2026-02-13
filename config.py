# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

# Database Settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "agent_db_v2")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "password")
DB_PORT = os.getenv("DB_PORT", "5432")

# Validation (Optional but recommended)
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY is missing from .env file")