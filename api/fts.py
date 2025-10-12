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
            updated TEXT NOT NULL,
            status TEXT
        )
    """)

    con.commit()
    con.close()

def index_note(note_id: str, title: str, body: str, tags: list,
               folder: str, path: str, created: str, status: str = None):
    """Add note to FTS5 index"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    tags_csv = ",".join(tags)

    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    cur.execute(
        "INSERT OR REPLACE INTO notes_meta VALUES (?, ?, ?, ?, ?, ?)",
        (note_id, path, folder, created, created, status)
    )

    con.commit()
    con.close()

def search_notes(query: str, limit: int = 20, status: str = None):
    """Search notes using FTS5

    Supports:
    - Boolean queries with OR: "sport OR baseball OR game"
    - Simple terms: "baseball"
    - Phrases in quotes: '"exact phrase"'
    - Status filtering: status="todo" to filter by task status
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # If query contains OR, AND, or is already quoted, use it as-is
    # Otherwise, wrap in quotes to handle special chars like apostrophes
    if ' OR ' in query or ' AND ' in query or query.startswith('"'):
        fts_query = query
    else:
        # Escape quotes and wrap as phrase for safety
        escaped_query = query.replace('"', '""')
        fts_query = f'"{escaped_query}"'

    # Build SQL query with optional status filter
    sql = """
        SELECT n.path,
               snippet(notes_fts, 1, '<b>', '</b>', '…', 8) AS snippet,
               bm25(notes_fts) AS score
        FROM notes_fts
        JOIN notes_meta n ON n.id = notes_fts.id
        WHERE notes_fts MATCH ?
    """
    params = [fts_query]

    if status:
        sql += " AND n.status = ?"
        params.append(status)

    sql += " ORDER BY score LIMIT ?"
    params.append(limit)

    cur.execute(sql, params)

    results = [
        {"path": row[0], "snippet": row[1], "score": row[2]}
        for row in cur.fetchall()
    ]

    con.close()
    return results
