"""
GraphRAG Note Assistant - Configuration
Simplified - no folder-based or dimension-based settings
"""
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
    """Get a database connection with proper timeout and WAL mode.

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

# Display config on startup
print(f"🤖 LLM Model: {LLM_MODEL}")
print(f"📁 Notes Dir: {NOTES_DIR}")
