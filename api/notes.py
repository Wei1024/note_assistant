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

def write_markdown(folder: str, title: str, tags: list, body: str, related_ids=None):
    """Write note to disk and index in SQLite"""
    related_ids = related_ids or []
    created = _iso_now()
    updated = created
    nid = f"{created}_{uuid.uuid4().hex[:4]}"

    # Create folder
    folder_path = NOTES_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    fname = pick_filename(title or "note", created)
    path = folder_path / fname

    # Prepare frontmatter
    front = {
        "id": nid,
        "title": title or body.splitlines()[0][:60] if body else "Untitled",
        "tags": tags,
        "folder": folder,
        "related_ids": related_ids,
        "created": created,
        "updated": updated
    }

    # Write file
    content = "---\n"
    content += yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    content += "---\n\n"
    content += body.strip() + "\n"

    path.write_text(content, encoding='utf-8')

    # Index in SQLite
    index_note(
        note_id=nid,
        title=front["title"],
        body=body,
        tags=tags,
        folder=folder,
        path=str(path),
        created=created
    )

    return nid, str(path), front["title"], folder
