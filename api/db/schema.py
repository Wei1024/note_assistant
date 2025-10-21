"""Database Schema Management
Defines and initializes all database tables
"""
import sqlite3
from pathlib import Path
from ..config import DB_PATH


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
    # Core metadata (Phase 2: folder column removed, dimensions added)
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_meta (
            id TEXT PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL,
            status TEXT,

            -- Boolean dimensions (Phase 2: Multi-dimensional classification)
            has_action_items BOOLEAN DEFAULT 0,
            is_social BOOLEAN DEFAULT 0,
            is_emotional BOOLEAN DEFAULT 0,
            is_knowledge BOOLEAN DEFAULT 0,
            is_exploratory BOOLEAN DEFAULT 0,

            -- Review system (heuristic-based, no fake confidence)
            needs_review BOOLEAN DEFAULT 0,
            review_reason TEXT,
            reviewed_at TEXT,
            original_classification TEXT,

            -- Consolidation tracking (Phase 3: Knowledge graph)
            consolidated_at TEXT
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

    # ========================================================================
    # LLM Operations Audit Log (Phase 4: Debugging & Optimization)
    # ========================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS llm_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Operation context
            note_id TEXT,
            operation_type TEXT NOT NULL,
            created TEXT NOT NULL,

            -- LLM metadata
            model TEXT NOT NULL,
            prompt_version TEXT,

            -- Performance metrics
            duration_ms INTEGER,
            tokens_input INTEGER,
            tokens_output INTEGER,
            cost_usd REAL,

            -- Raw data (for debugging)
            prompt_text TEXT,
            raw_response TEXT,
            parsed_output TEXT,

            -- Error tracking
            error TEXT,
            success BOOLEAN DEFAULT 1,

            FOREIGN KEY(note_id) REFERENCES notes_meta(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_llm_ops_note
        ON llm_operations(note_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_llm_ops_type
        ON llm_operations(operation_type)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_llm_ops_created
        ON llm_operations(created)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_llm_ops_success
        ON llm_operations(success)
    """)

    con.commit()
    con.close()
