"""
Memory Consolidation Service
Background linking service that connects today's notes to existing knowledge.

Inspired by brain's memory consolidation during sleep - runs asynchronously
to find and create meaningful connections without blocking note capture.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .config import DB_PATH
from .capture_service import get_llm
from .graph import add_link


def _iso_now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _iso_today_start():
    """Get ISO timestamp for start of today (00:00:00)"""
    today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return today.isoformat()


def get_notes_created_today() -> List[Dict]:
    """Get all notes created today with their enrichment metadata.

    Returns:
        List of dicts with keys: id, path, folder, body, entities, dimensions
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    today_start = _iso_today_start()

    # Get today's notes
    cur.execute(
        """SELECT id, path, folder, created
           FROM notes_meta
           WHERE created >= ?
           ORDER BY created""",
        (today_start,)
    )

    notes = []
    for row in cur.fetchall():
        note_id, path, folder, created = row

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
            "folder": folder,
            "body": body,
            "entities": entities,
            "dimensions": dimensions
        })

    con.close()
    return notes


def find_link_candidates(note: Dict, max_candidates: int = 10,
                         exclude_today: bool = True) -> List[Dict]:
    """Find potential notes to link to based on shared metadata.

    Args:
        note: Dict with id, entities, dimensions
        max_candidates: Maximum number of candidates to return
        exclude_today: If True, only search notes before today (established knowledge)

    Returns:
        List of candidate dicts with: id, title, snippet, match_reason
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    candidates = {}  # Use dict to deduplicate by note_id

    # Get date filter
    if exclude_today:
        today_start = _iso_today_start()
        date_filter = f"AND m.created < '{today_start}'"
    else:
        date_filter = ""

    # Search by people
    people = [e[1] for e in note.get("entities", []) if e[0] == "person"]
    for person in people:
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'person'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 5
        """, (person, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"mentions {person}"
                }

    # Search by topics
    topics = [e[1] for e in note.get("entities", []) if e[0] == "topic"]
    for topic in topics[:3]:  # Limit to top 3 topics
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'topic'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 3
        """, (topic, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"discusses {topic}"
                }

    # Search by projects
    projects = [e[1] for e in note.get("entities", []) if e[0] == "project"]
    for project in projects:
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'project'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 3
        """, (project, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"related to {project}"
                }

    # Search by tags (Phase 2.3b enhancement)
    # Tags are intentional metadata - high signal for relatedness
    from .fts import search_notes

    # Get tags from note metadata
    tags = []
    try:
        with open(note.get("path", ""), 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                    tags = frontmatter.get("tags", [])
    except Exception:
        pass

    # Search FTS5 by each tag
    for tag in tags[:3]:  # Top 3 tags
        tag_results = search_notes(tag, limit=2)
        for result in tag_results:
            result_id = result.get("id")
            result_path = result.get("path")

            # Skip self and today's notes
            if result_id == note["id"]:
                continue

            if exclude_today:
                # Check if result is from today
                try:
                    cur.execute("SELECT created FROM notes_meta WHERE id = ?", (result_id,))
                    row = cur.fetchone()
                    if row and row[0] >= today_start:
                        continue
                except Exception:
                    continue

            if result_id not in candidates:
                candidates[result_id] = {
                    "id": result_id,
                    "path": result_path,
                    "match_reason": f"shares tag: {tag}"
                }

    con.close()

    # Read snippets from files
    result = []
    for candidate in list(candidates.values())[:max_candidates]:
        try:
            with open(candidate["path"], 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract title and body
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        import yaml
                        frontmatter = yaml.safe_load(parts[1])
                        title = frontmatter.get("title", "Untitled")
                        body = parts[2].strip()
                        snippet = body[:200]  # First 200 chars
                    else:
                        title = "Untitled"
                        snippet = content[:200]
                else:
                    title = "Untitled"
                    snippet = content[:200]

                result.append({
                    "id": candidate["id"],
                    "title": title,
                    "snippet": snippet,
                    "match_reason": candidate["match_reason"]
                })
        except Exception as e:
            print(f"Error reading candidate {candidate['path']}: {e}")
            continue

    return result


async def suggest_links_batch(new_note_text: str, candidates: List[Dict]) -> List[Dict]:
    """Use LLM to analyze all candidates at once and suggest links.

    Args:
        new_note_text: Full text of the new note
        candidates: List of candidate notes to compare against

    Returns:
        List of suggested links: [{"id": "...", "link_type": "...", "reason": "..."}, ...]
    """
    if not candidates:
        return []

    llm = get_llm()

    # Format all candidates in one prompt
    candidates_text = "\n".join([
        f"{i+1}. [{c['id']}] {c['title']}\n   Snippet: {c['snippet']}\n   Match: {c['match_reason']}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are a knowledge graph linker. Analyze connections between notes.

NEW NOTE:
{new_note_text}

EXISTING NOTES:
{candidates_text}

Task: Which existing notes should link to the new note? Analyze ALL at once.

Return ONLY valid JSON array:
[
  {{"id": "note-id-from-above", "link_type": "related|spawned|references|contradicts", "reason": "specific shared concept"}},
  ...
]

Link Types:
- **related**: Discusses same topic/concept
- **spawned**: New note is follow-up/action from old note
- **references**: New note builds on old note's idea
- **contradicts**: New note challenges old note's conclusion

Rules:
1. Only include if STRONG connection (shared specific concept/person/project/decision)
2. Reason must be specific (not "both mention topics")
3. Max 5 links total (prioritize strongest)
4. Skip if connection is weak or vague
5. Must use exact note ID from brackets above

JSON:"""

    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)

        # Validate and filter results
        valid_links = []
        valid_ids = {c["id"] for c in candidates}

        for link in result:
            # Check required fields
            if not all(k in link for k in ["id", "link_type", "reason"]):
                continue

            # Validate ID
            if link["id"] not in valid_ids:
                continue

            # Validate link type
            if link["link_type"] not in ["related", "spawned", "references", "contradicts"]:
                continue

            # Heuristic: Skip vague reasons
            reason_lower = link["reason"].lower()
            vague_keywords = ["might be", "could be", "possibly", "both mention", "similar"]
            if any(kw in reason_lower for kw in vague_keywords):
                continue

            valid_links.append(link)

        return valid_links[:5]  # Max 5 links

    except Exception as e:
        print(f"Error in suggest_links_batch: {e}")
        return []


async def consolidate_daily_notes() -> Dict:
    """Consolidate today's notes - find and create links to existing knowledge.

    This is the main entry point for memory consolidation, mimicking the brain's
    process of connecting new memories to existing knowledge during sleep.

    Returns:
        Dict with consolidation statistics
    """
    notes = get_notes_created_today()

    stats = {
        "notes_processed": 0,
        "links_created": 0,
        "notes_with_links": 0,
        "started_at": _iso_now()
    }

    for note in notes:
        # Find candidates
        candidates = find_link_candidates(note, max_candidates=10, exclude_today=True)

        if not candidates:
            stats["notes_processed"] += 1
            continue

        # Suggest links using batch LLM call
        suggested_links = await suggest_links_batch(note["body"], candidates)

        # Store links in database
        links_added = 0
        for link in suggested_links:
            try:
                add_link(note["id"], link["id"], link["link_type"])
                links_added += 1
            except Exception as e:
                print(f"Error storing link from {note['id']} to {link['id']}: {e}")

        if links_added > 0:
            stats["notes_with_links"] += 1
            stats["links_created"] += links_added

        stats["notes_processed"] += 1

    stats["completed_at"] = _iso_now()

    return stats
