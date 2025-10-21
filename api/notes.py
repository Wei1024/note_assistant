import os
import re
import yaml
from datetime import datetime
import uuid
from pathlib import Path
from .config import NOTES_DIR
from .fts import index_note

SLUG_RE = re.compile(r"[^a-z0-9\-]+")

def _iso_now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = SLUG_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "note"

def pick_filename(title: str, created_iso: str) -> str:
    ymd = created_iso[:10]
    slug = slugify(title)[:80]
    return f"{ymd}-{slug}.md"

def write_markdown(title: str, tags: list, body: str, db_connection=None):
    """Write note to disk and index in SQLite (GraphRAG version - simplified).

    Args:
        title: Note title
        tags: List of tags
        body: Note content
        db_connection: Optional database connection for transaction

    Returns:
        Tuple of (note_id, path, title)
    """
    created = _iso_now()
    updated = created
    nid = f"{created}_{uuid.uuid4().hex[:4]}"

    # Flat structure - all notes go to NOTES_DIR root
    notes_dir = NOTES_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    fname = pick_filename(title or "note", created)
    path = notes_dir / fname

    # Prepare frontmatter (minimal - episodic metadata lives in graph_nodes table)
    front = {
        "id": nid,
        "title": title or body.splitlines()[0][:60] if body else "Untitled",
        "tags": tags,
        "created": created,
        "updated": updated
    }

    # Write file
    content = "---\n"
    content += yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    content += "---\n\n"
    content += body.strip() + "\n"

    path.write_text(content, encoding='utf-8')

    # Index in SQLite (minimal - no deprecated dimension flags)
    index_note(
        note_id=nid,
        title=front["title"],
        body=body,
        tags=tags,
        path=str(path),
        created=created,
        status=None,  # Deprecated
        needs_review=False,  # Deprecated
        review_reason=None,  # Deprecated
        has_action_items=False,  # Deprecated
        is_social=False,  # Deprecated
        is_emotional=False,  # Deprecated
        is_knowledge=False,  # Deprecated
        is_exploratory=False,  # Deprecated
        db_connection=db_connection
    )

    return nid, str(path), front["title"]


def update_note_status(note_path: str, new_status: str) -> bool:
    """Update the status field in a note's frontmatter and reindex

    Args:
        note_path: Full path to the note file
        new_status: New status value (todo/in_progress/done)

    Returns:
        True if successful, False otherwise
    """
    from .fts import index_note
    import sqlite3
    from .config import DB_PATH

    try:
        path = Path(note_path)
        if not path.exists():
            return False

        # Read the note
        content = path.read_text(encoding='utf-8')

        # Parse frontmatter
        if not content.startswith('---'):
            return False

        parts = content.split('---', 2)
        if len(parts) < 3:
            return False

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()

        # Update status
        frontmatter['status'] = new_status if new_status else None
        frontmatter['updated'] = _iso_now()

        # Write back
        new_content = "---\n"
        new_content += yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
        new_content += "---\n\n"
        new_content += body + "\n"

        path.write_text(new_content, encoding='utf-8')

        # Update database
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            "UPDATE notes_meta SET status = ?, updated = ? WHERE path = ?",
            (new_status, frontmatter['updated'], str(path))
        )
        con.commit()
        con.close()

        return True

    except Exception as e:
        print(f"Error updating note status: {e}")
        return False


def get_notes_created_today():
    """Get all notes created today with their enrichment metadata.

    Returns:
        List of dicts with keys: id, path, body, entities, dimensions, dimension_flags
    """
    import sqlite3
    from .config import DB_PATH
    from datetime import datetime

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Calculate today's start in ISO format
    today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today.isoformat()

    # Get today's notes with boolean dimension flags
    cur.execute(
        """SELECT id, path, created, has_action_items, is_social, is_emotional, is_knowledge, is_exploratory
           FROM notes_meta
           WHERE created >= ?
           ORDER BY created""",
        (today_start,)
    )

    notes = []
    for row in cur.fetchall():
        note_id, path, created = row[0], row[1], row[2]
        has_action_items, is_social, is_emotional, is_knowledge, is_exploratory = row[3], row[4], row[5], row[6], row[7]

        # Read note body from file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract body (after frontmatter)
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content
        except Exception as e:
            print(f"Error reading {path}: {e}")
            body = ""

        # Get entities for this note
        cur.execute(
            """SELECT entity_type, entity_value
               FROM notes_entities
               WHERE note_id = ?""",
            (note_id,)
        )
        entities = cur.fetchall()

        # Get dimensions for this note
        cur.execute(
            """SELECT dimension_type, dimension_value
               FROM notes_dimensions
               WHERE note_id = ?""",
            (note_id,)
        )
        dimensions = cur.fetchall()

        notes.append({
            "id": note_id,
            "path": path,
            "body": body,
            "entities": entities,
            "dimensions": dimensions,
            "dimension_flags": {
                "has_action_items": bool(has_action_items),
                "is_social": bool(is_social),
                "is_emotional": bool(is_emotional),
                "is_knowledge": bool(is_knowledge),
                "is_exploratory": bool(is_exploratory)
            }
        })

    con.close()
    return notes
