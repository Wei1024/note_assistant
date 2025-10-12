"""
Graph Helper Functions for Multi-Dimensional Note System
Provides CRUD operations for dimensions, entities, and links
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .config import DB_PATH


def _iso_now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


# ============================================================================
# WRITE OPERATIONS - Add metadata to notes
# ============================================================================

def add_dimension(note_id: str, dimension_type: str, dimension_value: str,
                  confidence: float = None, db_connection=None):
    """Add a dimension (secondary context, emotion, time reference) to a note.

    Args:
        note_id: Note ID
        dimension_type: Type of dimension (context, emotion, time_reference)
        dimension_value: Value of the dimension
        confidence: Optional confidence score
        db_connection: SQLite connection (or creates new one)
    """
    should_close = False
    if db_connection is None:
        db_connection = sqlite3.connect(DB_PATH)
        should_close = True

    cur = db_connection.cursor()
    cur.execute(
        """INSERT INTO notes_dimensions
           (note_id, dimension_type, dimension_value, extraction_confidence, created)
           VALUES (?, ?, ?, ?, ?)""",
        (note_id, dimension_type, dimension_value, confidence, _iso_now())
    )
    db_connection.commit()

    if should_close:
        db_connection.close()


def add_entity(note_id: str, entity_type: str, entity_value: str,
               entity_metadata: str = None, confidence: float = None,
               db_connection=None):
    """Add an entity (person, topic, project, technology) to a note.

    Args:
        note_id: Note ID
        entity_type: Type of entity (person, topic, project, tech)
        entity_value: Value/name of the entity
        entity_metadata: Optional JSON metadata
        confidence: Optional confidence score
        db_connection: SQLite connection (or creates new one)
    """
    should_close = False
    if db_connection is None:
        db_connection = sqlite3.connect(DB_PATH)
        should_close = True

    cur = db_connection.cursor()
    cur.execute(
        """INSERT INTO notes_entities
           (note_id, entity_type, entity_value, entity_metadata, extraction_confidence, created)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (note_id, entity_type, entity_value, entity_metadata, confidence, _iso_now())
    )
    db_connection.commit()

    if should_close:
        db_connection.close()


def add_link(from_note_id: str, to_note_id: str, link_type: str,
             db_connection=None):
    """Create a link between two notes.

    Args:
        from_note_id: Source note ID
        to_note_id: Target note ID
        link_type: Type of relationship (related, spawned, references, contradicts, etc.)
        db_connection: SQLite connection (or creates new one)
    """
    should_close = False
    if db_connection is None:
        db_connection = sqlite3.connect(DB_PATH)
        should_close = True

    cur = db_connection.cursor()
    cur.execute(
        """INSERT OR IGNORE INTO notes_links
           (from_note_id, to_note_id, link_type, created)
           VALUES (?, ?, ?, ?)""",
        (from_note_id, to_note_id, link_type, _iso_now())
    )
    db_connection.commit()

    if should_close:
        db_connection.close()


def index_note_with_enrichment(note_id: str, enrichment: dict, db_connection=None):
    """Store all enrichment metadata for a note (batch operation).

    This is the main function used by enrichment_service.py to store all
    multi-dimensional metadata at once.

    Args:
        note_id: Note ID
        enrichment: Dict from enrich_note_metadata() containing:
            - secondary_contexts: List[str]
            - people: List[dict] or List[str]
            - topics: List[str]
            - projects: List[str]
            - technologies: List[str]
            - emotions: List[str]
            - time_references: List[dict] or List[str]
        db_connection: SQLite connection (or creates new one)
    """
    should_close = False
    if db_connection is None:
        db_connection = sqlite3.connect(DB_PATH)
        should_close = True

    try:
        # Store secondary contexts as dimensions
        for context in enrichment.get("secondary_contexts", []):
            add_dimension(note_id, "context", context, db_connection=db_connection)

        # Store emotions as dimensions
        for emotion in enrichment.get("emotions", []):
            add_dimension(note_id, "emotion", emotion, db_connection=db_connection)

        # Store time references as dimensions
        for time_ref in enrichment.get("time_references", []):
            if isinstance(time_ref, dict):
                time_value = time_ref.get("datetime", "")
                import json
                metadata = json.dumps(time_ref)
            else:
                time_value = str(time_ref)
                metadata = None

            cur = db_connection.cursor()
            cur.execute(
                """INSERT INTO notes_dimensions
                   (note_id, dimension_type, dimension_value, created)
                   VALUES (?, ?, ?, ?)""",
                (note_id, "time_reference", time_value, _iso_now())
            )

        # Store people as entities
        for person in enrichment.get("people", []):
            if isinstance(person, dict):
                name = person.get("name", "")
                import json
                metadata = json.dumps(person)
            else:
                name = str(person)
                metadata = None
            add_entity(note_id, "person", name, metadata, db_connection=db_connection)

        # Store topics as entities
        for topic in enrichment.get("topics", []):
            add_entity(note_id, "topic", topic, db_connection=db_connection)

        # Store projects as entities
        for project in enrichment.get("projects", []):
            add_entity(note_id, "project", project, db_connection=db_connection)

        # Store technologies as entities
        for tech in enrichment.get("technologies", []):
            add_entity(note_id, "tech", tech, db_connection=db_connection)

        db_connection.commit()

    finally:
        if should_close:
            db_connection.close()


# ============================================================================
# READ OPERATIONS - Query metadata
# ============================================================================

def get_dimensions(note_id: str) -> List[Dict[str, str]]:
    """Get all dimensions for a note.

    Args:
        note_id: Note ID

    Returns:
        List of dicts with keys: dimension_type, dimension_value, created
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """SELECT dimension_type, dimension_value, created
           FROM notes_dimensions
           WHERE note_id = ?
           ORDER BY created""",
        (note_id,)
    )

    results = [
        {
            "dimension_type": row[0],
            "dimension_value": row[1],
            "created": row[2]
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results


def get_entities(note_id: str) -> List[Dict[str, str]]:
    """Get all entities for a note.

    Args:
        note_id: Note ID

    Returns:
        List of dicts with keys: entity_type, entity_value, entity_metadata, created
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """SELECT entity_type, entity_value, entity_metadata, created
           FROM notes_entities
           WHERE note_id = ?
           ORDER BY created""",
        (note_id,)
    )

    results = [
        {
            "entity_type": row[0],
            "entity_value": row[1],
            "entity_metadata": row[2],
            "created": row[3]
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results


def get_linked_notes(note_id: str, link_type: Optional[str] = None) -> List[Dict[str, str]]:
    """Get all notes linked from this note.

    Args:
        note_id: Source note ID
        link_type: Optional filter by link type

    Returns:
        List of dicts with keys: to_note_id, link_type, created
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    if link_type:
        cur.execute(
            """SELECT to_note_id, link_type, created
               FROM notes_links
               WHERE from_note_id = ? AND link_type = ?
               ORDER BY created""",
            (note_id, link_type)
        )
    else:
        cur.execute(
            """SELECT to_note_id, link_type, created
               FROM notes_links
               WHERE from_note_id = ?
               ORDER BY created""",
            (note_id,)
        )

    results = [
        {
            "to_note_id": row[0],
            "link_type": row[1],
            "created": row[2]
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results


def get_backlinks(note_id: str, link_type: Optional[str] = None) -> List[Dict[str, str]]:
    """Get all notes that link TO this note.

    Args:
        note_id: Target note ID
        link_type: Optional filter by link type

    Returns:
        List of dicts with keys: from_note_id, link_type, created
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    if link_type:
        cur.execute(
            """SELECT from_note_id, link_type, created
               FROM notes_links
               WHERE to_note_id = ? AND link_type = ?
               ORDER BY created""",
            (note_id, link_type)
        )
    else:
        cur.execute(
            """SELECT from_note_id, link_type, created
               FROM notes_links
               WHERE to_note_id = ?
               ORDER BY created""",
            (note_id,)
        )

    results = [
        {
            "from_note_id": row[0],
            "link_type": row[1],
            "created": row[2]
        }
        for row in cur.fetchall()
    ]

    con.close()
    return results


def get_all_links_for_note(note_id: str) -> Dict[str, List[Dict]]:
    """Get both outgoing and incoming links for a note.

    Args:
        note_id: Note ID

    Returns:
        Dict with keys 'outgoing' and 'incoming', each containing list of links
    """
    return {
        "outgoing": get_linked_notes(note_id),
        "incoming": get_backlinks(note_id)
    }


# ============================================================================
# QUERY OPERATIONS - Search by metadata
# ============================================================================

def find_notes_by_dimension(dimension_type: str, dimension_value: str) -> List[str]:
    """Find all notes with a specific dimension.

    Args:
        dimension_type: Type of dimension (context, emotion, time_reference)
        dimension_value: Value to search for

    Returns:
        List of note IDs
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """SELECT DISTINCT note_id
           FROM notes_dimensions
           WHERE dimension_type = ? AND dimension_value = ?
           ORDER BY created DESC""",
        (dimension_type, dimension_value)
    )

    results = [row[0] for row in cur.fetchall()]
    con.close()
    return results


def find_notes_by_entity(entity_type: str, entity_value: str) -> List[str]:
    """Find all notes with a specific entity.

    Args:
        entity_type: Type of entity (person, topic, project, tech)
        entity_value: Value to search for

    Returns:
        List of note IDs
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """SELECT DISTINCT note_id
           FROM notes_entities
           WHERE entity_type = ? AND entity_value = ?
           ORDER BY created DESC""",
        (entity_type, entity_value)
    )

    results = [row[0] for row in cur.fetchall()]
    con.close()
    return results


def find_notes_by_person(person_name: str) -> List[str]:
    """Find all notes mentioning a person.

    Args:
        person_name: Name of person (case-insensitive search)

    Returns:
        List of note IDs
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """SELECT DISTINCT note_id
           FROM notes_entities
           WHERE entity_type = 'person' AND entity_value LIKE ?
           ORDER BY created DESC""",
        (f"%{person_name}%",)
    )

    results = [row[0] for row in cur.fetchall()]
    con.close()
    return results


def get_graph_neighborhood(note_id: str, depth: int = 1) -> Dict:
    """Get graph neighborhood around a note (for visualization).

    Args:
        note_id: Center note ID
        depth: How many hops away to traverse (1 or 2 recommended)

    Returns:
        Dict with 'nodes' and 'edges' for graph visualization
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    visited = set()
    nodes = []
    edges = []

    def traverse(current_id, current_depth):
        if current_depth > depth or current_id in visited:
            return

        visited.add(current_id)

        # Get node metadata
        cur.execute(
            """SELECT id, path, folder, created
               FROM notes_meta
               WHERE id = ?""",
            (current_id,)
        )
        row = cur.fetchone()
        if row:
            nodes.append({
                "id": row[0],
                "path": row[1],
                "folder": row[2],
                "created": row[3]
            })

        # Get outgoing edges
        cur.execute(
            """SELECT to_note_id, link_type
               FROM notes_links
               WHERE from_note_id = ?""",
            (current_id,)
        )
        for row in cur.fetchall():
            to_id, link_type = row
            edges.append({
                "from": current_id,
                "to": to_id,
                "type": link_type
            })
            traverse(to_id, current_depth + 1)

        # Get incoming edges
        cur.execute(
            """SELECT from_note_id, link_type
               FROM notes_links
               WHERE to_note_id = ?""",
            (current_id,)
        )
        for row in cur.fetchall():
            from_id, link_type = row
            edges.append({
                "from": from_id,
                "to": current_id,
                "type": link_type
            })
            traverse(from_id, current_depth + 1)

    traverse(note_id, 0)
    con.close()

    return {
        "nodes": nodes,
        "edges": edges
    }
