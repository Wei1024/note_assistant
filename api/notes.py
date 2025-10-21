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

    # Index in SQLite (GraphRAG version - minimal FTS5 + metadata)
    index_note(
        note_id=nid,
        title=front["title"],
        body=body,
        tags=tags,
        path=str(path),
        created=created,
        db_connection=db_connection
    )

    return nid, str(path), front["title"]


# Legacy functions removed - moved to api/legacy/notes.py
# GraphRAG doesn't need update_note_status() or get_notes_created_today()
