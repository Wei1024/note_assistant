import sqlite3
from pathlib import Path

# Schema is now managed centrally in api/db/schema.py
# Import ensure_db from there to avoid duplication
from .db.schema import ensure_db as _ensure_db_schema

def ensure_db():
    """Initialize complete database schema (multi-dimensional metadata)

    NOTE: This now delegates to api/db/schema.py to avoid duplication.
    The schema is maintained in a single source of truth.
    """
    # Use centralized schema initialization
    _ensure_db_schema()

def index_note(note_id: str, title: str, body: str, tags: list,
               path: str, created: str, status: str = None,
               needs_review: bool = False, review_reason: str = None,
               has_action_items: bool = False, is_social: bool = False,
               is_emotional: bool = False, is_knowledge: bool = False,
               is_exploratory: bool = False):
    """Add note to FTS5 index and metadata tables

    Args:
        note_id: Note ID
        title: Note title
        body: Note body content
        tags: List of tags
        path: File path
        created: Creation timestamp
        status: Task status (todo/in_progress/done)
        needs_review: Whether note needs review
        review_reason: Reason for review flag
        has_action_items: Boolean dimension - contains actionable todos
        is_social: Boolean dimension - involves conversations
        is_emotional: Boolean dimension - expresses feelings
        is_knowledge: Boolean dimension - contains learnings
        is_exploratory: Boolean dimension - brainstorming/ideas
    """
    from .config import DB_PATH
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    tags_csv = ",".join(tags)

    # FTS5 index
    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    # Metadata with review fields and boolean dimensions (no folder!)
    cur.execute(
        """INSERT OR REPLACE INTO notes_meta
           (id, path, created, updated, status,
            has_action_items, is_social, is_emotional, is_knowledge, is_exploratory,
            needs_review, review_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (note_id, path, created, created, status,
         has_action_items, is_social, is_emotional, is_knowledge, is_exploratory,
         needs_review, review_reason)
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
    from .config import DB_PATH
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

    # Build SQL query with optional status filter (include metadata)
    sql = """
        SELECT n.path,
               snippet(notes_fts, 1, '<b>', '</b>', '…', 8) AS snippet,
               bm25(notes_fts) AS score,
               n.created,
               n.has_action_items,
               n.is_social,
               n.is_emotional,
               n.is_knowledge,
               n.is_exploratory
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
        {
            "path": row[0],
            "snippet": row[1],
            "score": row[2],
            "metadata": {
                "created": row[3],
                "dimensions": {
                    "has_action_items": bool(row[4]),
                    "is_social": bool(row[5]),
                    "is_emotional": bool(row[6]),
                    "is_knowledge": bool(row[7]),
                    "is_exploratory": bool(row[8])
                }
            }
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results
