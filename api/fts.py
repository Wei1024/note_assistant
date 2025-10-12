import sqlite3
from pathlib import Path
from .config import DB_PATH

def ensure_db():
    """Initialize complete database schema (multi-dimensional metadata)"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA case_sensitive_like=OFF;")
    cur.execute("PRAGMA foreign_keys=ON;")

    # ========================================================================
    # FTS5 full-text search
    # ========================================================================
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
        USING fts5(id UNINDEXED, title, body, tags)
    """)

    # ========================================================================
    # Core metadata
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_meta (
            id TEXT PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            folder TEXT NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL,
            status TEXT,

            -- Review system (heuristic-based, no fake confidence)
            needs_review BOOLEAN DEFAULT 0,
            review_reason TEXT,
            reviewed_at TEXT,
            original_classification TEXT
        )
    """)

    # ========================================================================
    # Multi-dimensional metadata: Secondary contexts
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_dimensions (
            note_id TEXT NOT NULL,
            dimension_type TEXT NOT NULL,
            dimension_value TEXT NOT NULL,
            extraction_confidence REAL,
            created TEXT NOT NULL,

            FOREIGN KEY(note_id) REFERENCES notes_meta(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_dimensions
        ON notes_dimensions(dimension_type, dimension_value)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_dimensions_note
        ON notes_dimensions(note_id)
    """)

    # ========================================================================
    # Entity extraction: People, topics, projects, technologies
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_entities (
            note_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_value TEXT NOT NULL,
            entity_metadata TEXT,
            extraction_confidence REAL,
            created TEXT NOT NULL,

            FOREIGN KEY(note_id) REFERENCES notes_meta(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities
        ON notes_entities(entity_type, entity_value)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_note
        ON notes_entities(note_id)
    """)

    # ========================================================================
    # Graph relationships: Links between notes
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_links (
            from_note_id TEXT NOT NULL,
            to_note_id TEXT NOT NULL,
            link_type TEXT NOT NULL,
            created TEXT NOT NULL,

            FOREIGN KEY(from_note_id) REFERENCES notes_meta(id) ON DELETE CASCADE,
            FOREIGN KEY(to_note_id) REFERENCES notes_meta(id) ON DELETE CASCADE,

            PRIMARY KEY(from_note_id, to_note_id, link_type)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_from
        ON notes_links(from_note_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_to
        ON notes_links(to_note_id)
    """)

    # ========================================================================
    # Embeddings: Placeholder for Phase 7 (semantic search)
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_embeddings (
            note_id TEXT PRIMARY KEY,
            embedding BLOB,
            model TEXT,
            created TEXT NOT NULL,

            FOREIGN KEY(note_id) REFERENCES notes_meta(id) ON DELETE CASCADE
        )
    """)

    con.commit()
    con.close()

def index_note(note_id: str, title: str, body: str, tags: list,
               folder: str, path: str, created: str, status: str = None,
               needs_review: bool = False, review_reason: str = None):
    """Add note to FTS5 index and metadata tables"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    tags_csv = ",".join(tags)

    # FTS5 index
    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    # Metadata with review fields
    cur.execute(
        """INSERT OR REPLACE INTO notes_meta
           (id, path, folder, created, updated, status, needs_review, review_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (note_id, path, folder, created, created, status, needs_review, review_reason)
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
