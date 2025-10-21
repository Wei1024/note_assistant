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

def write_markdown(title: str, tags: list, body: str, related_ids=None, status=None,
                   needs_review=False, reasoning=None, enrichment=None, db_connection=None):
    """Write note to disk and index in SQLite with optional multi-dimensional metadata.

    Args:
        title: Note title
        tags: List of tags
        body: Note content
        related_ids: List of related note IDs
        status: Optional status (only for tasks)
        needs_review: Whether note needs review
        reasoning: Review reasoning
        enrichment: Optional dict from enrich_note_metadata() with:
            - has_action_items, is_social, is_emotional, is_knowledge, is_exploratory: Boolean dimensions
            - people: List[dict]
            - entities: List[str]
            - emotions: List[str]
            - time_references: List[dict]

    Returns:
        Tuple of (note_id, path, title)
    """
    related_ids = related_ids or []
    enrichment = enrichment or {}
    created = _iso_now()
    updated = created
    nid = f"{created}_{uuid.uuid4().hex[:4]}"

    # Flat structure - all notes go to NOTES_DIR root
    notes_dir = NOTES_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    fname = pick_filename(title or "note", created)
    path = notes_dir / fname

    # Prepare frontmatter
    front = {
        "id": nid,
        "title": title or body.splitlines()[0][:60] if body else "Untitled",
        "tags": tags,
        "related_ids": related_ids,
        "created": created,
        "updated": updated
    }

    # Add status if it's a task
    if status:
        front["status"] = status

    # Add review flag (no fake confidence in frontmatter)
    if needs_review:
        front["needs_review"] = needs_review
    if reasoning:
        front["review_reason"] = reasoning

    # Add enrichment metadata to frontmatter (Phase 2: emotions only, not contexts)
    if enrichment:
        # Emotions (stored in frontmatter for visibility)
        emotions = enrichment.get("emotions", [])
        if emotions:
            front["dimensions"] = [
                {"type": "emotion", "value": emotion}
                for emotion in emotions
            ]

        # Entities
        entities = {}
        people = enrichment.get("people", [])
        if people:
            entities["people"] = [
                p.get("name") if isinstance(p, dict) else p
                for p in people
            ]

        all_entities = enrichment.get("entities", [])
        if all_entities:
            entities["entities"] = all_entities

        if entities:
            front["entities"] = entities

        # Time references
        time_refs = enrichment.get("time_references", [])
        if time_refs:
            front["time_references"] = time_refs

    # Write file
    content = "---\n"
    content += yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    content += "---\n\n"
    content += body.strip() + "\n"

    path.write_text(content, encoding='utf-8')

    # Extract boolean dimensions from enrichment
    has_action_items = enrichment.get("has_action_items", False) if enrichment else False
    is_social = enrichment.get("is_social", False) if enrichment else False
    is_emotional = enrichment.get("is_emotional", False) if enrichment else False
    is_knowledge = enrichment.get("is_knowledge", False) if enrichment else False
    is_exploratory = enrichment.get("is_exploratory", False) if enrichment else False

    # Index in SQLite
    index_note(
        note_id=nid,
        title=front["title"],
        body=body,
        tags=tags,
        path=str(path),
        created=created,
        status=status,
        needs_review=needs_review,
        review_reason=reasoning,  # Use reasoning as review_reason
        has_action_items=has_action_items,
        is_social=is_social,
        is_emotional=is_emotional,
        is_knowledge=is_knowledge,
        is_exploratory=is_exploratory,
        db_connection=db_connection  # Pass shared connection
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
