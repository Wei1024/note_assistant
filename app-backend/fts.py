import sqlite3
from pathlib import Path
from .config import DB_PATH

def ensure_db():
    """Initialize SQLite FTS5 database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA case_sensitive_like=OFF;")

    # FTS5 table
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
        USING fts5(id UNINDEXED, title, body, tags)
    """)

    # Metadata table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_meta (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            folder TEXT NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL
        )
    """)

    con.commit()
    con.close()

def index_note(note_id: str, title: str, body: str, tags: list,
               folder: str, path: str, created: str):
    """Add note to FTS5 index"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    tags_csv = ",".join(tags)

    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    cur.execute(
        "INSERT OR REPLACE INTO notes_meta VALUES (?, ?, ?, ?, ?)",
        (note_id, path, folder, created, created)
    )

    con.commit()
    con.close()

def search_notes(query: str, limit: int = 20):
    """Search notes using FTS5"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT n.path,
               snippet(notes_fts, 1, '<b>', '</b>', '…', 8) AS snippet,
               bm25(notes_fts) AS score
        FROM notes_fts
        JOIN notes_meta n ON n.id = notes_fts.id
        WHERE notes_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """, (query, limit))

    results = [
        {"path": row[0], "snippet": row[1], "score": row[2]}
        for row in cur.fetchall()
    ]

    con.close()
    return results
