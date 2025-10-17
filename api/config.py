import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Notes storage
NOTES_DIR = Path(os.getenv("NOTES_DIR", "~/Notes")).expanduser()
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"

# Database configuration
DB_TIMEOUT = 30.0  # 30 seconds timeout for locked database

def get_db_connection():
    """
    Get a database connection with proper timeout and WAL mode.

    WAL mode allows concurrent reads and writes, preventing most lock issues.
    """
    con = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    # Enable WAL mode for better concurrent access
    con.execute("PRAGMA journal_mode=WAL")
    return con

# Backend server
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8787"))

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b-instruct")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Editor
OPEN_EDITOR_CMD = os.getenv("OPEN_EDITOR_CMD", "code")

# Folder Structure - Brain-based Cognitive Model
WORKING_FOLDERS = {
    "tasks": {
        "description": "Actionable items - executive function",
        "has_status": True,
        "cognitive_context": "working_memory",
        "auto_archive_days": 7,  # After completion
    },
    "meetings": {
        "description": "Conversations, discussions - social cognition",
        "has_status": False,
        "cognitive_context": "working_memory",
        "auto_archive_days": 30,
    },
    "ideas": {
        "description": "Brainstorms, hypotheses - creative exploration",
        "has_status": False,
        "cognitive_context": "working_memory",
        "auto_archive_days": None,  # Manual, based on outcome
    },
    "reference": {
        "description": "How-tos, evergreen knowledge - procedural memory",
        "has_status": False,
        "cognitive_context": "working_memory",
        "auto_archive_days": 365,  # Rarely archived
    },
    "journal": {
        "description": "Personal reflections - emotional processing",
        "has_status": False,
        "cognitive_context": "emotional",
        "auto_archive_days": 365,
    }
}

# Archive (Long-term memory)
ARCHIVE_FOLDER = "archive"

# Valid folders list (for backward compatibility)
VALID_FOLDERS = list(WORKING_FOLDERS.keys())

# Classification confidence threshold
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.7

# Display config on startup
print(f"🤖 LLM Model: {LLM_MODEL}")
print(f"📁 Notes Dir: {NOTES_DIR}")
