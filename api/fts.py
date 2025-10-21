"""
Full-Text Search (FTS5) for GraphRAG Notes
Simplified - no dimension-based metadata
"""

# Schema is now managed centrally in api/db/schema.py
from .db.schema import ensure_db as _ensure_db_schema


def ensure_db():
    """Initialize database schema

    Delegates to api/db/schema.py for centralized schema management
    """
    _ensure_db_schema()


def index_note(note_id: str, title: str, body: str, tags: list,
               path: str, created: str, db_connection=None, **kwargs):
    """Add note to FTS5 index and metadata tables (GraphRAG version - simplified)

    Args:
        note_id: Note ID
        title: Note title
        body: Note body content
        tags: List of tags
        path: File path
        created: Creation timestamp
        db_connection: Optional shared database connection
        **kwargs: Accepts but ignores deprecated dimension parameters for compatibility
    """
    # Use provided connection or create new one
    should_close = db_connection is None
    if db_connection is None:
        from .config import get_db_connection
        con = get_db_connection()
    else:
        con = db_connection

    cur = con.cursor()
    tags_csv = ",".join(tags)

    # FTS5 index
    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    # Metadata table (minimal - no dimensions)
    cur.execute(
        """INSERT OR REPLACE INTO notes_meta
           (id, path, created, updated)
           VALUES (?, ?, ?, ?)""",
        (note_id, path, created, created)
    )

    # Only commit and close if we created the connection
    if should_close:
        con.commit()
        con.close()


def search_notes(query: str, limit: int = 20):
    """Search notes using FTS5 (GraphRAG version - simplified)

    Supports:
    - Boolean queries with OR: "sport OR baseball OR game"
    - Simple terms: "baseball"
    - Phrases in quotes: '"exact phrase"'

    Returns:
        List of dicts with path, snippet, score, created
    """
    from .config import get_db_connection
    con = get_db_connection()
    cur = con.cursor()

    # If query contains OR, AND, or is already quoted, use it as-is
    # Otherwise, wrap in quotes to handle special chars like apostrophes
    if ' OR ' in query or ' AND ' in query or query.startswith('"'):
        fts_query = query
    else:
        # Escape quotes and wrap as phrase for safety
        escaped_query = query.replace('"', '""')
        fts_query = f'"{escaped_query}"'

    sql = """
        SELECT n.path,
               snippet(notes_fts, 1, '<b>', '</b>', '…', 8) AS snippet,
               bm25(notes_fts) AS score,
               n.created
        FROM notes_fts
        JOIN notes_meta n ON n.id = notes_fts.id
        WHERE notes_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """

    cur.execute(sql, [fts_query, limit])

    results = [
        {
            "path": row[0],
            "snippet": row[1],
            "score": row[2],
            "metadata": {"created": row[3]}
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results
